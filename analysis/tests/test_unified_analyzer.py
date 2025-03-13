"""
Test module for the unified analyzer.

This module contains tests for the unified analyzer, which integrates
the UnifiedImportVisitor and UnifiedFunctionVisitor.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch

# Import the analyzer module
try:
    from analysis.unified_analyzer import analyze_file, analyze_files
except ImportError:
    from unified_analyzer import analyze_file, analyze_files


class TestUnifiedAnalyzer(unittest.TestCase):
    """Test cases for the unified analyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a mock kurtosis.yml file to identify the workspace root
        with open(os.path.join(self.temp_dir, "kurtosis.yml"), "w") as f:
            f.write("# Mock kurtosis.yml file for testing")
        
        # Create test files
        self.create_test_files()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def create_test_files(self):
        """Create test files for analysis."""
        # Create a module file
        module_file = os.path.join(self.temp_dir, "module.star")
        with open(module_file, "w") as f:
            f.write('''"""
Module with functions to be imported.
"""

def _private_function():
    """This is a private function."""
    return "private"

def documented_function():
    """This is a documented function."""
    return "documented"

def undocumented_function():
    return "undocumented"
''')
        
        # Create a file with import naming violations
        import_file = os.path.join(self.temp_dir, "imports.star")
        with open(import_file, "w") as f:
            f.write('''"""
File with import naming violations.
"""

# Import naming violation
module = import_module("./module.star")

# Correct import
_correct = import_module("/another/module.star")

# Alias violation
alias = module
''')
        
        # Create a file with function calls
        calls_file = os.path.join(self.temp_dir, "calls.star")
        with open(calls_file, "w") as f:
            f.write('''"""
File with function calls.
"""

# Import the module
_module = import_module("./module.star")

def local_function(arg1, arg2=None):
    """This is a local function."""
    return arg1

# Valid call to local function
local_function("value")

# Invalid call to local function
local_function()

# Call to imported function
_module.documented_function()

# Call to undocumented function
_module.undocumented_function()
''')

        # Create a file with nested function calls to non-existent functions
        nested_calls_file = os.path.join(self.temp_dir, "nested_calls.star")
        with open(nested_calls_file, "w") as f:
            f.write('''"""
File with nested function calls to non-existent functions.
"""

# Import the module
_module = import_module("./module.star")

def wrapper_function(arg):
    """This is a wrapper function."""
    return arg

# Nested call to a non-existent function
result = wrapper_function(_module.non_existent_function())

# Nested call in an argument
another_result = _module.documented_function(wrapper_function(_module.another_non_existent()))

# Nested call in a keyword argument
third_result = local_function(arg1="value", arg2=_module.third_non_existent())
''')

        # Create a file that simulates the input_parser.plop() scenario
        plop_scenario_file = os.path.join(self.temp_dir, "plop_scenario.star")
        with open(plop_scenario_file, "w") as f:
            f.write('''"""
File that simulates the input_parser.plop() scenario.
"""

# Import the modules
input_parser = import_module("./module.star")

def get_args():
    """This function returns arguments."""
    return {"key": "value"}

# Call with nested non-existent function as an argument to args.get()
optimism_args = input_parser.documented_function(get_args().get("optimism_package", input_parser.plop()))
''')
    
    def test_analyze_file_import_naming(self):
        """Test analyzing a file for import naming violations."""
        # Set up checks
        checks = {
            "import_naming": True,
            "calls": False,
            "function_visibility": False
        }
        
        # Analyze the imports file
        import_file = os.path.join(self.temp_dir, "imports.star")
        violations = analyze_file(import_file, checks, {}, self.temp_dir)
        
        # Check that violations were found
        self.assertTrue(violations)
        
        # Check that the correct violations were reported
        violation_messages = [msg for _, msg in violations]
        self.assertTrue(any("module" in msg and "should start with an underscore" in msg for msg in violation_messages))
        self.assertTrue(any("alias" in msg and "should start with an underscore" in msg for msg in violation_messages))
    
    def test_analyze_file_function_calls(self):
        """Test analyzing a file for function call violations."""
        # Set up checks
        checks = {
            "import_naming": False,
            "calls": True,
            "function_visibility": False
        }
        
        # Set up shared data
        shared_data = {}
        
        # Analyze the calls file
        calls_file = os.path.join(self.temp_dir, "calls.star")
        violations = analyze_file(calls_file, checks, shared_data, self.temp_dir)
        
        # Check that violations were found
        self.assertTrue(violations)
        
        # Check that the correct violations were reported
        violation_messages = [msg for _, msg in violations]
        self.assertTrue(any("Missing required positional argument" in msg for msg in violation_messages))
    
    def test_analyze_file_function_visibility(self):
        """Test analyzing a file for function visibility violations."""
        # Set up checks
        checks = {
            "import_naming": False,
            "calls": False,
            "function_visibility": True
        }
        
        # Set up shared data with external calls
        shared_data = {
            "external_calls": {}
        }
        
        # Analyze the module file
        module_file = os.path.join(self.temp_dir, "module.star")
        violations = analyze_file(module_file, checks, shared_data, self.temp_dir)
        
        # Check that violations were found
        self.assertTrue(violations)
        
        # Check that the correct violations were reported
        violation_messages = [msg for _, msg in violations]
        self.assertTrue(any("undocumented_function" in msg and "consider making it private" in msg for msg in violation_messages))
    
    def test_analyze_files_all_checks(self):
        """Test analyzing multiple files with all checks enabled."""
        # Set up checks
        checks = {
            "import_naming": True,
            "calls": True,
            "function_visibility": True
        }
        
        # Get all test files
        test_files = [
            os.path.join(self.temp_dir, "module.star"),
            os.path.join(self.temp_dir, "imports.star"),
            os.path.join(self.temp_dir, "calls.star"),
            os.path.join(self.temp_dir, "nested_calls.star"),
            os.path.join(self.temp_dir, "plop_scenario.star")
        ]
        
        # Analyze all files
        violations = analyze_files(test_files, checks, self.temp_dir)
        
        # Check that violations were found in all files
        self.assertEqual(len(violations), 5)
        
        # Check that each file has at least one violation
        for file_path in test_files:
            self.assertTrue(any(file_path in viol_path for viol_path in violations.keys()),
                           f"No violations found for {file_path}")

    def test_analyze_nested_function_calls(self):
        """Test analyzing a file for nested function call violations."""
        # Set up checks
        checks = {
            "import_naming": False,
            "calls": True,
            "function_visibility": False
        }
        
        # Set up shared data
        shared_data = {}
        
        # Analyze the nested calls file
        nested_calls_file = os.path.join(self.temp_dir, "nested_calls.star")
        violations = analyze_file(nested_calls_file, checks, shared_data, self.temp_dir)
        
        # Check that violations were found
        self.assertTrue(violations)
        
        # Check that the correct violations were reported
        violation_messages = [msg for _, msg in violations]
        
        # Check for non-existent function calls in nested contexts
        self.assertTrue(any("non_existent_function" in msg for msg in violation_messages), 
                       "Failed to detect non-existent function in first nested call")
        self.assertTrue(any("another_non_existent" in msg for msg in violation_messages), 
                       "Failed to detect non-existent function in second nested call")
        self.assertTrue(any("third_non_existent" in msg for msg in violation_messages), 
                       "Failed to detect non-existent function in keyword argument")

    def test_plop_scenario(self):
        """Test the specific input_parser.plop() scenario."""
        # Set up checks
        checks = {
            "import_naming": False,
            "calls": True,
            "function_visibility": False
        }
        
        # Set up shared data
        shared_data = {}
        
        # Analyze the plop scenario file
        plop_scenario_file = os.path.join(self.temp_dir, "plop_scenario.star")
        violations = analyze_file(plop_scenario_file, checks, shared_data, self.temp_dir)
        
        # Check that violations were found
        self.assertTrue(violations)
        
        # Check that the correct violations were reported
        violation_messages = [msg for _, msg in violations]
        
        # Check for the non-existent plop function call
        self.assertTrue(any("plop" in msg for msg in violation_messages), 
                       "Failed to detect non-existent plop function in nested call")


if __name__ == "__main__":
    unittest.main() 