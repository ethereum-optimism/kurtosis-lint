# Starlark Code Analyzer

This directory contains a unified analyzer for Starlark files that can perform various checks to ensure code quality and consistency. The analyzer uses a consolidated architecture with unified visitors to perform multiple checks in a single pass, allowing for more efficient and flexible code analysis.

## Available Checks

The analyzer supports the following checks:

1. **Call Analysis**: Checks function calls for compatibility with function signatures.
2. **Function Visibility**: Checks if functions are either private (start with an underscore) or documented.
3. **Import Naming**: Checks if global variables assigned the result of `import_module()` calls start with an underscore.

## Usage

You can run the analyzer with one or more checks enabled:

```bash
# Run all checks (default behavior)
python -m analysis.unified_analyzer --all [paths...]

# Run specific checks
python -m analysis.unified_analyzer --checked-calls [paths...]
python -m analysis.unified_analyzer --function-visibility [paths...]
python -m analysis.unified_analyzer --import-naming [paths...]

# Run multiple checks
python -m analysis.unified_analyzer --checked-calls --function-visibility [paths...]

# Enable verbose output
python -m analysis.unified_analyzer -v --all [paths...]
```

### Examples

```bash
# Analyze a single file with all checks
python -m analysis.unified_analyzer --all path/to/file.star

# Analyze all .star files in a directory with import naming check
python -m analysis.unified_analyzer --import-naming path/to/directory

# Analyze multiple files with function visibility check
python -m analysis.unified_analyzer --function-visibility file1.star file2.star

# Analyze all .star files in the current directory with all checks and verbose output
python -m analysis.unified_analyzer -v --all .
```

## Check Details

### Call Analysis

This check verifies that function calls are compatible with the function signatures. It checks:

- If the function exists
- If the correct number of arguments are provided
- If required arguments are provided
- If keyword arguments are valid

The goal is to eliminate a class of issues that's typical of interpreted
languages: discrepencies between definitions and calls are normally caught at
runtime.

### Function Visibility

This check ensures that functions follow proper visibility conventions:

- Private functions (starting with an underscore) are fine as-is
- Public functions (not starting with an underscore) must have a docstring
- Undocumented public functions that are not used in other modules should be made private
- Undocumented public functions that are used in other modules should be documented

The goal here is to minimize and properly document the public interface of each
module.

### Import Naming

This check ensures that global variables assigned the result of `import_module()` calls follow proper naming conventions:

- Global variables assigned the result of `import_module()` should start with an underscore
- Aliases to variables holding `import_module()` results should also start with an underscore

The goal is to easily identify which imports are still needed. Public variables
are importable, so we can't decide whether they're being read or not.
Conversely, there is no value in exporting the result of an `import_module()` call.

## Architecture

The analyzer uses a streamlined architecture with just three visitor classes:

1. **Base Visitor**: `BaseVisitor` provides common functionality for all visitors, including scope management and workspace resolution.

2. **Unified Visitors**: The analyzer uses two specialized visitor classes:
   - `UnifiedImportVisitor`: Handles all import-related functionality, including import tracking and naming conventions.
   - `UnifiedFunctionVisitor`: Handles all function-related functionality, including function collection, visibility checking, and call analysis.

3. **Unified Analyzer**: The `unified_analyzer.py` file provides an efficient interface for running checks on a set of files. It performs fewer AST traversals by using the unified visitors.

4. **Error Handling**: The visitors include robust error handling to prevent crashes and provide helpful warnings when issues are encountered.

## Benefits of the Unified Architecture

1. **Reduced Code Duplication**: The unified visitors eliminate duplicate code for handling scopes, variable tracking, and AST traversal.

2. **Improved Efficiency**: Fewer AST traversals are required, reducing the overall analysis time.

3. **Simplified Architecture**: The codebase is more modular and easier to understand, with just three visitor classes instead of nine.

4. **Better Maintainability**: Changes to common functionality only need to be made in one place.

5. **Robust Error Handling**: The unified visitors include comprehensive error handling to prevent crashes and provide helpful diagnostics.

## Development

The analyzer is designed to be modular and extensible. Each check is implemented as a separate function that can be enabled or disabled independently.

To add a new check:

1. Extend one of the unified visitor classes in the `visitors/` directory
2. Update the `analyze_file` function in `unified_analyzer.py` to include the new check
3. Add a new command-line argument in the `main` function
4. Update the README.md file to document the new check 