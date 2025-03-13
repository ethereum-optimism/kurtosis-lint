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
            os.path.join(self.temp_dir, "calls.star")
        ]
        
        # Analyze all files
        violations = analyze_files(test_files, checks, self.temp_dir)
        
        # Check that violations were found in all files
        self.assertEqual(len(violations), 3)
        
        # Check that the correct violations were reported
        for file_path, file_violations in violations.items():
            if "imports.star" in file_path:
                # Check import naming violations
                violation_messages = [msg for _, msg in file_violations]
                self.assertTrue(any("module" in msg and "should start with an underscore" in msg for msg in violation_messages))
            elif "calls.star" in file_path:
                # Check function call violations
                violation_messages = [msg for _, msg in file_violations]
                self.assertTrue(any("Missing required positional argument" in msg for msg in violation_messages))
            elif "module.star" in file_path:
                # Check function visibility violations
                violation_messages = [msg for _, msg in file_violations]
                self.assertTrue(any("undocumented_function" in msg for msg in violation_messages))


if __name__ == "__main__":
    unittest.main() 