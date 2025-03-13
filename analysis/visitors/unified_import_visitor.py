"""
Unified import visitor for AST analysis.

This module contains the UnifiedImportVisitor that combines the functionality of
ImportScanner, ModuleAnalyzer, and ImportNamingVisitor.
"""

import ast
import os
import sys
import logging
from typing import Dict, List, Set, Tuple, Optional, NamedTuple

from .base_visitor import BaseVisitor
from .common import ImportInfo


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Default to warnings in normal environment


class ImportedModule(NamedTuple):
    """Information about an imported module."""
    module_path: str  # The path to the imported module
    is_external: bool  # Whether the module is external (github.com/...)
    is_absolute: bool  # Whether the path is absolute (/path/...)
    is_relative: bool  # Whether the path is relative (./path/... or ../path/...)
    resolved_path: Optional[str]  # The resolved path to the module (if available)
    lineno: int  # Line number where the import occurs


class UnifiedImportVisitor(BaseVisitor):
    """
    Unified visitor that combines import scanning, module analysis, and import naming checks.
    
    This visitor:
    1. Identifies all calls to import_module and tracks variables that receive the result
    2. Determines the type of import (external, absolute, or relative)
    3. Resolves the path to the imported module when possible
    4. Checks if global variables assigned the result of import_module() start with an underscore
    5. Tracks aliases to import_module results and checks their naming
    """
    
    def __init__(self, file_path: str = "", workspace_root: Optional[str] = None, check_file_exists: bool = True):
        super().__init__(file_path, workspace_root)
        
        # Track import_module calls and the variables they're assigned to
        self.import_module_calls: Dict[str, ImportedModule] = {}
        
        # Track variables that hold import_module results
        self.import_module_vars: Set[str] = set()
        
        # Track violations for naming conventions
        self.violations: List[Tuple[int, str]] = []
        
        # Keep track of global scope variables separately
        self.global_vars: Set[str] = set()
        
        # Track aliases to import_module results
        self.aliases: Dict[str, str] = {}
        
        # Track the current scope level (0 = global scope)
        self.scope_level = 0
        
        # Flag to control whether to check if imported files exist
        self.check_file_exists = check_file_exists
    
    def debug_print(self, message: str) -> None:
        """
        Print a debug message if the logger is in debug mode.
        
        Args:
            message: The message to print
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(message)

    def _check_file_exists(self, path: str) -> bool:
        """
        Check if a file exists at the given path.
        
        Args:
            path: The path to check
            
        Returns:
            True if the file exists, False otherwise
        """
        return os.path.isfile(path)

    def _resolve_module_path(self, module_path: str) -> Tuple[Optional[str], bool, bool, bool]:
        """
        Resolve a module path to a file path.
        
        Args:
            module_path: The module path to resolve
            
        Returns:
            A tuple of (resolved_path, is_external, is_absolute, is_relative)
        """
        try:
            # Check if the module path is external (github.com/...)
            is_external = module_path.startswith("github.com/")
            if is_external:
                self.debug_print(f"External module path '{module_path}' cannot be resolved")
                return None, True, False, False
            
            # Check if the module path is absolute (/path/...)
            is_absolute = module_path.startswith("/")
            
            # Check if the module path is relative (./path/... or ../path/...)
            is_relative = module_path.startswith("./") or module_path.startswith("../")
            
            resolved_path = None
            
            # Handle absolute paths
            if is_absolute:
                # Join with the workspace root
                if self.workspace_root:
                    # Remove the leading slash
                    module_path_no_slash = module_path[1:]
                    resolved_path = os.path.join(self.workspace_root, module_path_no_slash)
                    self.debug_print(f"Resolved absolute module path '{module_path}' to '{resolved_path}'")
            
            # Handle relative paths
            elif is_relative:
                # Get the directory of the current file
                file_dir = os.path.dirname(self.file_path)
                
                # Join with the relative path
                resolved_path = os.path.normpath(os.path.join(file_dir, module_path))
                self.debug_print(f"Resolved relative module path '{module_path}' to '{resolved_path}'")
            
            # Handle simple imports (path/...)
            else:
                # Try to find the module in the workspace
                resolved_path = os.path.join(self.workspace_root, module_path)
                self.debug_print(f"Resolved simple module path '{module_path}' to '{resolved_path}'")
            
            return resolved_path, is_external, is_absolute, is_relative
            
        except Exception as e:
            logger.warning(f"Error resolving module path '{module_path}': {str(e)}")
            return None, False, False, False
    
    def _is_import_module_var(self, var_name: str, visited: set = None) -> bool:
        """
        Check if a variable holds an import_module result.
        
        Args:
            var_name: The variable name to check
            visited: Set of already visited variables (to detect circular references)
            
        Returns:
            True if the variable holds an import_module result, False otherwise
        """
        try:
            # Initialize visited set if not provided
            if visited is None:
                visited = set()
            
            # Check for circular references
            if var_name in visited:
                logger.warning(f"Circular reference detected for variable '{var_name}'")
                return False
            
            # Add current variable to visited set
            visited.add(var_name)
            
            # Check if the variable is directly assigned an import_module result
            if var_name in self.import_module_vars:
                return True
            
            # Check if the variable is an alias to an import_module result
            if var_name in self.aliases:
                source_var = self.aliases[var_name]
                return self._is_import_module_var(source_var, visited)
            
            return False
        except Exception as e:
            logger.warning(f"Error checking if '{var_name}' is an import_module variable: {str(e)}")
            return False
    
    def _enter_scope(self):
        """Enter a new scope."""
        super()._enter_scope()
        self.scope_level += 1
    
    def _exit_scope(self):
        """Exit the current scope."""
        super()._exit_scope()
        self.scope_level -= 1
    
    def _is_import_module_call(self, node):
        """
        Check if a node is an import_module call and extract the module path.
        
        Args:
            node: The node to check
            
        Returns:
            A tuple (is_import_module, module_path) where:
            - is_import_module: True if the node is an import_module call
            - module_path: The module path if it's an import_module call, None otherwise
        """
        is_import_module = False
        module_path = None
        
        if (isinstance(node, ast.Call) and 
            isinstance(node.func, ast.Name) and 
            node.func.id == "import_module"):
            is_import_module = True
            
            # Extract the module path
            if (len(node.args) > 0 and 
                isinstance(node.args[0], ast.Constant) and 
                isinstance(node.args[0].value, str)):
                module_path = node.args[0].value
            else:
                logger.warning(f"Invalid import_module call: missing or non-string argument")
        
        return is_import_module, module_path

    def _check_naming_convention(self, node, var_name, is_alias=False):
        """
        Check if a variable name follows the naming convention for import_module results.
        
        Args:
            node: The node where the variable is defined
            var_name: The variable name to check
            is_alias: Whether the variable is an alias to an import_module result
        """
        # Only check global variables
        if self.scope_level > 0:
            return
            
        # Add to global vars
        self.global_vars.add(var_name)
        
        # Check if the variable name starts with an underscore
        if not var_name.startswith('_'):
            if is_alias:
                self.violations.append((
                    node.lineno,
                    f"Global variable '{var_name}' is an alias to an `import_module` result and should be private"
                ))
            else:
                self.violations.append((
                    node.lineno,
                    f"Global variable '{var_name}' contains the result of `import_module` and should be private"
                ))

    def _process_assignment(self, node, target_id, is_import_module):
        """
        Process an assignment to a variable.
        
        Args:
            node: The assignment node
            target_id: The target variable name
            is_import_module: Whether the assignment is from an import_module call
        """
        # Add the variable to the current scope
        self._add_to_current_scope(target_id)
        
        # If we're in the global scope, add to global_vars
        if self.scope_level == 0:
            self.global_vars.add(target_id)
        
        # If this is an import_module call, add to import_module_vars
        if is_import_module:
            self.import_module_vars.add(target_id)
            
            # Check naming convention for global variables
            if self.scope_level == 0:
                self._check_naming_convention(node, target_id)

    def visit_Module(self, node):
        """Visit the module node."""
        # Reset the scope level to 0 (global scope)
        self.scope_level = 0
        
        # Visit all statements in the module
        for stmt in node.body:
            self.visit(stmt)
    
    def visit_FunctionDef(self, node):
        """Visit function definition nodes."""
        try:
            # Enter a new scope
            self._enter_scope()
            
            # Visit the function body
            for stmt in node.body:
                self.visit(stmt)
            
            # Exit the scope
            self._exit_scope()
        except Exception as e:
            logger.warning(f"Error visiting function definition '{node.name}': {str(e)}")
            # Continue with the next statement
    
    def visit_If(self, node):
        """Visit if statement nodes."""
        try:
            # Visit the test expression
            self.visit(node.test)
            
            # Enter a new scope
            self._enter_scope()
            
            # Visit the body
            for stmt in node.body:
                self.visit(stmt)
            
            # Exit the scope
            self._exit_scope()
            
            # Enter a new scope for the else block
            self._enter_scope()
            
            # Visit the else block
            for stmt in node.orelse:
                self.visit(stmt)
            
            # Exit the scope
            self._exit_scope()
        except Exception as e:
            logger.warning(f"Error visiting if statement: {str(e)}")
            # Continue with the next statement
    
    def _handle_name_assignment(self, node, target_id, is_import_module, module_path=None):
        """
        Handle assignment to a name.
        
        Args:
            node: The AST node
            target_id: The name being assigned to
            is_import_module: Whether the assignment is from an import_module call
            module_path: The module path if known
        """
        # Add the variable to the current scope
        self._add_to_current_scope(target_id)
        
        # If this is an import_module call, track it
        if is_import_module:
            # If we don't have a module path, try to get it from the node
            if module_path is None and isinstance(node.value, ast.Call) and len(node.value.args) > 0:
                # Get the module path from the first argument
                arg = node.value.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    module_path = arg.value
            
            # If we have a module path, resolve it and add it to our tracking
            if module_path is not None:
                # Resolve the module path
                resolved_path, is_external, is_absolute, is_relative = self._resolve_module_path(module_path)
                
                # Create an ImportedModule object
                imported_module = ImportedModule(
                    module_path=module_path,
                    is_external=is_external,
                    is_absolute=is_absolute,
                    is_relative=is_relative,
                    resolved_path=resolved_path,
                    lineno=node.lineno
                )
                
                # Add to our tracking
                self.import_module_vars.add(target_id)
                self.import_module_calls[target_id] = imported_module
                
                # Check if the file exists
                if self.check_file_exists and resolved_path is not None and not self._check_file_exists(resolved_path):
                    self.violations.append((
                        node.lineno,
                        f"Imported module '{module_path}' does not exist at resolved path '{resolved_path}'"
                    ))
                
                # Check naming convention if we're in the global scope
                if self.scope_level == 0:
                    self._check_naming_convention(node, target_id)
        
        # If this is an alias to another variable, track it
        elif isinstance(node.value, ast.Name):
            source_var = node.value.id
            self.aliases[target_id] = source_var
            
            # If the source variable is an import_module result, check naming convention
            if self._is_import_module_var(source_var) and self.scope_level == 0:
                self._check_naming_convention(node, target_id, is_alias=True)

    def _handle_tuple_element_assignment(self, node, elt, i, value_elts):
        """
        Handle assignment to a tuple element.
        
        Args:
            node: The assignment node
            elt: The target element
            i: The index of the element
            value_elts: The value elements
        """
        if not isinstance(elt, ast.Name) or i >= len(value_elts):
            return
            
        elt_id = elt.id
        
        # Check if this element is assigned an import_module result
        elt_is_import_module, elt_module_path = self._is_import_module_call(value_elts[i])
        
        # Process the assignment
        self._process_assignment(node, elt_id, elt_is_import_module)
        
        # If this is an import_module call with a valid module path,
        # store information about the imported module
        if elt_is_import_module and elt_module_path:
            # Resolve the module path and determine its type
            resolved_path, is_external, is_absolute, is_relative = self._resolve_module_path(elt_module_path)
            
            # Store the imported module information
            self.import_module_calls[elt_id] = ImportedModule(
                module_path=elt_module_path,
                is_external=is_external,
                is_absolute=is_absolute,
                is_relative=is_relative,
                resolved_path=resolved_path,
                lineno=node.lineno
            )
        
        # If this is an alias to another variable, store the relationship
        elif isinstance(value_elts[i], ast.Name):
            source_id = value_elts[i].id
            
            # Store the alias relationship
            self.aliases[elt_id] = source_id
            
            # If the source is an import_module variable and we're in the global scope,
            # check the naming convention
            if self._is_import_module_var(source_id) and self.scope_level == 0:
                self._check_naming_convention(node, elt_id, is_alias=True)

    def visit_Assign(self, node):
        """Visit assignment nodes."""
        try:
            # Visit the right-hand side first
            self.visit(node.value)
            
            # Check if this is an import_module call
            is_import_module, module_path = self._is_import_module_call(node.value)
            if is_import_module and module_path is None:
                logger.warning(f"Invalid import_module call at line {node.lineno}: missing or non-string argument")
            
            # Process each target
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Handle simple name assignment
                    self._handle_name_assignment(node, target.id, is_import_module, module_path)
                elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                    # Handle tuple unpacking
                    for i, elt in enumerate(target.elts):
                        self._handle_tuple_element_assignment(node, elt, i, node.value.elts)
        except Exception as e:
            logger.warning(f"Error visiting assignment at line {node.lineno}: {str(e)}")
            # Continue with the next statement
    
    def get_all_imports(self) -> Dict[str, ImportedModule]:
        """
        Get all imported modules.
        
        Returns:
            Dictionary mapping variable names to imported module information
        """
        return self.import_module_calls
    
    def get_import_info(self) -> Dict[str, ImportInfo]:
        """
        Get import information for all imported modules.
        
        Returns:
            Dictionary mapping variable names to import information
        """
        import_info = {}
        
        for var_name, imported_module in self.import_module_calls.items():
            # Determine if this is an external package
            package_id = None
            if imported_module.is_external:
                # Extract the package ID from the module path
                # For example, "github.com/ethpandaops/ethereum-package/src/shared_utils/shared_utils.star"
                # would have a package ID of "github.com/ethpandaops/ethereum-package"
                parts = imported_module.module_path.split('/')
                if len(parts) >= 3:
                    package_id = '/'.join(parts[:3])
            
            import_info[var_name] = ImportInfo(
                module_path=imported_module.module_path,
                package_id=package_id,
                imported_names={}
            )
        
        return import_info 