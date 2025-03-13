"""
Unified analyzer for Starlark files.

This module provides a unified interface for analyzing Starlark files with
different types of checks that can be independently enabled:

1. Call Analysis: Checks function calls for compatibility with function signatures
2. Function Visibility: Checks if functions are either private or documented
3. Import Naming: Checks if global variables assigned import_module() results start with underscore
"""

import sys
import os
import ast
import argparse
from typing import List, Tuple, Dict, Set, Optional, Any, Callable

# Handle imports for both module and script execution
try:
    # When run as a module
    from analysis.visitors.base_visitor import BaseVisitor
    from analysis.visitors.unified_import_visitor import UnifiedImportVisitor
    from analysis.visitors.unified_function_visitor import UnifiedFunctionVisitor
    from analysis.common import find_star_files, parse_file, debug_print, find_workspace_root
except ModuleNotFoundError:
    # When run as a script
    from visitors.base_visitor import BaseVisitor
    from visitors.unified_import_visitor import UnifiedImportVisitor
    from visitors.unified_function_visitor import UnifiedFunctionVisitor
    from common import find_star_files, parse_file, debug_print, find_workspace_root


def analyze_file(file_path: str, checks: Dict[str, bool], shared_data: Dict[str, Any], workspace_root: str = None) -> List[Tuple[int, str]]:
    """
    Analyze a file with the specified checks.
    
    Args:
        file_path: Path to the file to analyze
        checks: Dictionary mapping check names to booleans indicating whether to run them
        shared_data: Dictionary containing shared data between files
        workspace_root: Root directory of the workspace
        
    Returns:
        List of violations found
    """
    violations = []
    
    # If workspace_root is not provided, try to determine it
    if workspace_root is None:
        workspace_root = find_workspace_root(file_path)
        debug_print(f"Using workspace root: {workspace_root}")
    
    try:
        # Parse the source code into an AST
        tree = parse_file(file_path)
        
        # Always analyze imports first, regardless of which checks are enabled
        debug_print(f"Analyzing imports in file: {file_path}")
        import_visitor = UnifiedImportVisitor(file_path, workspace_root)
        import_visitor.visit(tree)
        
        # Add import naming violations if that check is enabled
        if checks.get("import_naming", False):
            violations.extend(import_visitor.violations)
        
        # Store import information for function analysis
        shared_data.setdefault("imports", {})[file_path] = import_visitor.get_import_info()
        
        # Update module_to_file mapping
        for var_name, imported_module in import_visitor.get_all_imports().items():
            if imported_module.resolved_path:
                shared_data.setdefault("module_to_file", {})[imported_module.module_path] = imported_module.resolved_path
        
        # Second pass: analyze functions
        if checks.get("calls", False) or checks.get("function_visibility", False):
            debug_print(f"Analyzing functions in file: {file_path}")
            
            # Get imports for this file
            imports = shared_data.get("imports", {}).get(file_path, {})
            
            # Get all functions collected so far
            all_functions = shared_data.get("all_functions", {})
            
            # Get module_to_file mapping
            module_to_file = shared_data.get("module_to_file", {})
            
            # Create the function visitor
            function_visitor = UnifiedFunctionVisitor(
                file_path=file_path,
                imports=imports,
                all_functions=all_functions,
                module_to_file=module_to_file,
                workspace_root=workspace_root,
                check_calls=checks.get("calls", False),
                check_visibility=checks.get("function_visibility", False),
                debug=False  # Enable debug mode
            )
            
            # Pass the shared_data to the function visitor
            function_visitor.shared_data = shared_data
            
            # Visit the AST
            function_visitor.visit(tree)
            
            # Store function definitions for other files to use
            functions = function_visitor.get_functions()
            if functions:
                all_functions[file_path] = functions
                debug_print(f"Collected {len(functions)} functions from {file_path}: {list(functions.keys())}")
            
            # Store external calls for function visibility analysis
            if checks.get("function_visibility", False):
                # Add all external calls to the shared data
                external_calls = function_visitor.get_external_calls()
                for call in external_calls:
                    shared_data["external_calls"].add(call)
            
            # Add function violations
            violations.extend(function_visitor.violations)
            
            # Analyze function visibility if needed
            if checks.get("function_visibility", False):
                # Create a list of function objects with the necessary attributes
                functions_list = []
                for func_name, func_sig in function_visitor.functions.items():
                    # Create a function object with the necessary attributes
                    func = type('Function', (), {})()
                    func.name = func_name
                    func.line = func_sig.lineno
                    # Get the docstring if available, otherwise set to empty string
                    docstring = function_visitor.function_docs.get(func_name, "")
                    func.docstring = docstring
                    functions_list.append(func)
                
                visibility_violations = function_visitor.analyze_function_visibility(
                    file_path,
                    functions_list,
                    shared_data
                )
                
                # Add any new violations
                violations.extend(visibility_violations)
        
        return violations
    except Exception as e:
        return [(0, f"Error analyzing file {file_path}: {str(e)}")]


def analyze_files(file_paths: List[str], checks: Dict[str, bool], workspace_root: str = None) -> Dict[str, List[Tuple[int, str]]]:
    """
    Analyze multiple files with the specified checks.
    
    Args:
        file_paths: List of paths to the files to analyze
        checks: Dictionary mapping check names to booleans indicating whether to run them
        workspace_root: Root directory of the workspace
        
    Returns:
        Dictionary mapping file paths to lists of violations
    """
    # If workspace_root is not provided, try to determine it
    if workspace_root is None:
        workspace_root = find_workspace_root(file_paths[0])
        debug_print(f"Using workspace root: {workspace_root}")
    
    # Initialize shared data
    shared_data = {
        "all_functions": {},
        "module_to_file": {},
        "imports": {},
        "external_calls": set()
    }
    
    # Create a module_to_file mapping
    for file_path in file_paths:
        # Only add entries for files with .star extension
        if not file_path.endswith('.star'):
            continue
            
        # Add the full file path as the module path
        shared_data["module_to_file"][file_path] = file_path
        
        # Add relative paths based on workspace_root
        if workspace_root and file_path.startswith(workspace_root):
            rel_path = file_path[len(workspace_root):].lstrip('/')
            shared_data["module_to_file"][rel_path] = file_path
            
            # Add with leading slash for absolute paths
            shared_data["module_to_file"]['/' + rel_path] = file_path
        
        # Add the basename for simple imports
        basename = os.path.basename(file_path)
        shared_data["module_to_file"][basename] = file_path
    
    # Add entries for relative paths between files
    for source_file in file_paths:
        if not source_file.endswith('.star'):
            continue
            
        source_dir = os.path.dirname(source_file)
        for target_file in file_paths:
            if source_file == target_file or not target_file.endswith('.star'):
                continue
                
            # Calculate relative path from source to target
            rel_path = os.path.relpath(target_file, source_dir)
            shared_data["module_to_file"][rel_path] = target_file
            
            # Add with ./ prefix
            shared_data["module_to_file"]['./' + rel_path] = target_file
    
    debug_print("First pass: collecting imports and function definitions")
    # First pass: collect imports and function definitions
    first_pass_checks = checks.copy()
    # Disable call checking and visibility checking for the first pass
    first_pass_checks["calls"] = True  # Enable call checking for the first pass
    first_pass_checks["function_visibility"] = False
    
    for file_path in file_paths:
        debug_print(f"First pass analyzing: {file_path}")
        analyze_file(file_path, first_pass_checks, shared_data, workspace_root)
    
    debug_print(f"After first pass, all functions: {list(shared_data['all_functions'].keys())}")
    for file_path, functions in shared_data['all_functions'].items():
        debug_print(f"  Functions in {file_path}: {list(functions.keys())}")
    
    debug_print("Second pass: checking calls and visibility")
    # Second pass: check calls and visibility
    violations = {}
    for file_path in file_paths:
        debug_print(f"Second pass analyzing: {file_path}")
        file_violations = analyze_file(file_path, checks, shared_data, workspace_root)
        if file_violations:
            violations[file_path] = file_violations
    
    debug_print(f"After second pass, external calls: {shared_data['external_calls']}")
    
    return violations


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Analyze Starlark files with configurable checks")
    parser.add_argument("paths", nargs="*", default=["."], help="Paths to the directories or files to analyze")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--checked-calls", action="store_true", help="Check function calls for compatibility")
    parser.add_argument("--function-visibility", action="store_true", help="Check function visibility")
    parser.add_argument("--import-naming", action="store_true", help="Check import_module variable naming")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    args = parser.parse_args()
    
    # Set verbose flag early
    BaseVisitor.set_verbose(args.verbose)
    
    if args.verbose:
        print(f"Analyzing paths: {args.paths}")
        print(f"Verbose mode: {args.verbose}")
    
    # Determine which checks to run
    checks = {
        "calls": args.checked_calls or args.all,
        "function_visibility": args.function_visibility or args.all,
        "import_naming": args.import_naming or args.all
    }
    
    if args.verbose:
        print(f"Enabled checks: {[name for name, enabled in checks.items() if enabled]}")
    
    # Find the workspace root (using the first path)
    workspace_root = find_workspace_root(args.paths[0])
    if args.verbose:
        print(f"Using workspace root: {workspace_root}")
    
    # Find all .star files in all paths
    star_files = []
    for path in args.paths:
        star_files.extend(find_star_files(path))
    
    # Remove duplicates while preserving order
    star_files = list(dict.fromkeys(star_files))
    
    if args.verbose:
        print(f"Found {len(star_files)} .star files to analyze")
    
    # Run the analysis on all files
    print("Running analysis...")
    violations = analyze_files(star_files, checks, workspace_root)
    
    # Print violations
    violations_found = False
    for file_path, file_violations in violations.items():
        if file_violations:
            violations_found = True
            for lineno, message in file_violations:
                print(f"{file_path}:{lineno}: {message}")
    
    print(f"\nAnalyzed {len(star_files)} .star files")
    if violations_found:
        print("Found violations in the analyzed file(s)")
    else:
        print("No violations found")
    
    # Exit with appropriate code
    sys.exit(0 if not violations_found else 1)


if __name__ == "__main__":
    main() 