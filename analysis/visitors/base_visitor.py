"""
Base visitor module for AST analysis.

This module contains the base visitor class that other visitors can inherit from.
"""

import ast
import os
from typing import List, Tuple, Set, Dict, Optional, Any

class BaseVisitor(ast.NodeVisitor):
    """Base visitor class with common functionality."""
    
    # Class-level verbosity setting
    verbose = False
    
    @classmethod
    def set_verbose(cls, verbose: bool):
        """Set the verbosity for all BaseVisitor instances."""
        cls.verbose = verbose
    
    def __init__(self, file_path: str = "", workspace_root: Optional[str] = None):
        self.violations: List[Tuple[int, str]] = []
        self.scopes: List[Set[str]] = [set()]  # Stack of variable scopes
        self.variable_assignments: List[Dict[str, Any]] = [{}]  # Stack of variable assignments
        self.file_path = file_path
        self.dir_path = os.path.dirname(file_path) if file_path else ""
        self.workspace_root = workspace_root
    
    def debug_print(self, *args, **kwargs):
        """Print debug messages only when verbose mode is enabled."""
        if self.verbose:
            print(*args, **kwargs)
    
    def _enter_scope(self):
        """Enter a new variable scope."""
        self.scopes.append(set())
        self.variable_assignments.append({})
    
    def _exit_scope(self):
        """Exit the current variable scope."""
        if self.scopes:
            self.scopes.pop()
        if self.variable_assignments:
            self.variable_assignments.pop()
    
    def _add_to_current_scope(self, var_name: str):
        """Add a variable to the current scope."""
        if self.scopes:
            self.scopes[-1].add(var_name)
    
    def _add_variable_assignment(self, var_name: str, value: Any):
        """Add a variable assignment to the current scope."""
        if self.variable_assignments:
            self.variable_assignments[-1][var_name] = value
    
    def _is_in_scope(self, var_name: str) -> bool:
        """Check if a variable is in any scope."""
        return any(var_name in scope for scope in self.scopes)
    
    def _get_variable_value(self, var_name: str) -> Optional[Any]:
        """Get the value of a variable from any scope, starting from the innermost."""
        # Check from innermost to outermost scope
        for scope in reversed(self.variable_assignments):
            if var_name in scope:
                return scope[var_name]
        return None
    
    def visit_Module(self, node):
        """Visit the module node."""
        # If the node has a filename attribute, update our file_path
        if hasattr(node, 'filename'):
            self.file_path = node.filename
            self.dir_path = os.path.dirname(self.file_path)
        
        # Enter the module scope
        self._enter_scope()
        
        # Visit all statements in the module
        for stmt in node.body:
            self.visit(stmt)
        
        # Exit the module scope
        self._exit_scope()
    
    def visit_FunctionDef(self, node):
        """Visit function definition nodes."""
        # Enter a new scope for the function
        self._enter_scope()
        
        # Add function parameters to the scope
        for arg in node.args.args:
            self._add_to_current_scope(arg.arg)
        
        if node.args.vararg:
            self._add_to_current_scope(node.args.vararg.arg)
        
        for arg in node.args.kwonlyargs:
            self._add_to_current_scope(arg.arg)
        
        if node.args.kwarg:
            self._add_to_current_scope(node.args.kwarg.arg)
        
        # Visit the function body
        for stmt in node.body:
            self.visit(stmt)
        
        # Exit the function scope
        self._exit_scope()
    
    def visit_For(self, node):
        """Visit for loop nodes."""
        # Visit the iterable expression
        self.visit(node.iter)
        
        # Enter a new scope for the loop
        self._enter_scope()
        
        # Add loop variables to the scope
        if isinstance(node.target, ast.Name):
            self._add_to_current_scope(node.target.id)
        elif isinstance(node.target, ast.Tuple):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    self._add_to_current_scope(elt.id)
        
        # Visit the loop body
        for stmt in node.body:
            self.visit(stmt)
        
        # Visit the else clause if present
        if node.orelse:
            for stmt in node.orelse:
                self.visit(stmt)
        
        # Exit the loop scope
        self._exit_scope()
    
    def visit_If(self, node):
        """Visit if statement nodes."""
        # Visit the condition expression
        self.visit(node.test)
        
        # Enter a new scope for the if branch
        self._enter_scope()
        
        # Visit the if body
        for stmt in node.body:
            self.visit(stmt)
        
        # Exit the if scope
        self._exit_scope()
        
        # Enter a new scope for the else branch
        self._enter_scope()
        
        # Visit the else clause if present
        if node.orelse:
            for stmt in node.orelse:
                self.visit(stmt)
        
        # Exit the else scope
        self._exit_scope()

    def visit_ListComp(self, node):
        """Handle list comprehension."""

        # Enter a new scope for the comprehension contents
        self._enter_scope()

        # Add generators to the scope
        for generator in node.generators:
            self._add_to_current_scope(generator.target.id)
        
        # Visit the list comprehension expression
        self.visit(node.elt)

        # Exit the list comprehension scope
        self._exit_scope()
    
    def _handle_name_assignment(self, name_node, value_node):
        """Handle assignment to a simple variable name."""
        var_name = name_node.id
        self._add_to_current_scope(var_name)
        
        # Track the variable assignment generically
        if isinstance(value_node, ast.Name):
            # Simple variable assignment (e.g., x = longer_x)
            self._add_variable_assignment(var_name, value_node.id)
        else:
            # For other types of assignments, store the AST node
            # This allows subclasses to interpret the value as needed
            self._add_variable_assignment(var_name, value_node)
    
    def _handle_tuple_element_assignment(self, elt_node, value_node, index):
        """Handle assignment to a single element in a tuple unpacking."""
        if not isinstance(elt_node, ast.Name):
            return
            
        var_name = elt_node.id
        self._add_to_current_scope(var_name)
        
        # For tuple unpacking, we can't easily track the exact value
        # assigned to each variable, but we can store the AST node
        # and the index for subclasses to interpret
        if isinstance(value_node, ast.Tuple) and index < len(value_node.elts):
            # If unpacking a literal tuple, we can track individual elements
            element_value = value_node.elts[index]
            if isinstance(element_value, ast.Name):
                self._add_variable_assignment(var_name, element_value.id)
            else:
                self._add_variable_assignment(var_name, element_value)
        else:
            # For other cases, store the full value and the index
            self._add_variable_assignment(var_name, (value_node, index))
    
    def visit_Assign(self, node):
        """Visit an assignment statement."""
        # Process the value expression first
        self.visit(node.value)
        
        # Add assigned variables to the current scope
        for target in node.targets:
            if not isinstance(target, (ast.Name, ast.Tuple)):
                continue
                
            if isinstance(target, ast.Name):
                self._handle_name_assignment(target, node.value)
            else:  # isinstance(target, ast.Tuple)
                # Handle tuple unpacking (e.g., a, b = some_tuple)
                for i, elt in enumerate(target.elts):
                    self._handle_tuple_element_assignment(elt, node.value, i) 