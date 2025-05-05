"""
Test module for the unified analyzer.

This module contains tests for the unified analyzer, which integrates
the UnifiedImportVisitor and UnifiedFunctionVisitor.
"""

import unittest
import os
import tempfile
import shutil
from typing import List, Dict, Any, Union, Tuple
from unittest.mock import patch

# Import the analyzer module
try:
    from analysis.unified_analyzer import analyze_file, analyze_files
    from analysis.visitors.unified_function_visitor import Violation
except ImportError:
    from unified_analyzer import analyze_file, analyze_files
    from visitors.unified_function_visitor import Violation


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
            
        comps_file = os.path.join(self.temp_dir, "comps.star")
        with open(comps_file, "w") as f:
            f.write('''"""
File with comprehensions.
"""

# Valid list comprehension                   
[s.replace('a', 'b') for s in ['a', 'b']]
                    
# Invalid list comprehension                   
[x.replace('a', 'b') for s in ['a', 'b']]
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
    
    def _extract_violation_messages(self, violations: List[Union[Tuple[int, str], Violation]]) -> List[str]:
        """Extract messages from violations, handling both tuple and Violation objects."""
        messages = []
        for violation in violations:
            if isinstance(violation, tuple):
                _, message = violation
            else:
                message = violation.message
            messages.append(message)
        return messages
    
    def _assert_contains_message(self, messages: List[str], substring: str, error_msg: str = None):
        """Assert that at least one message contains the given substring."""
        self.assertTrue(
            any(substring in msg for msg in messages),
            error_msg or f"No message containing '{substring}' found in violations"
        )
    
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
        messages = self._extract_violation_messages(violations)
        self._assert_contains_message(messages, "module", "No violation for 'module' found")
        self._assert_contains_message(messages, "should be private", "No 'should be private' message found")
        self._assert_contains_message(messages, "alias", "No violation for 'alias' found")
    
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
        messages = self._extract_violation_messages(violations)
        self._assert_contains_message(messages, "Missing required positional argument")
    
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
        messages = self._extract_violation_messages(violations)
        self._assert_contains_message(messages, "undocumented_function", "No violation for 'undocumented_function' found")
        self._assert_contains_message(messages, "consider making it private", "No 'consider making it private' message found")
    
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
            os.path.join(self.temp_dir, "comps.star"),
            os.path.join(self.temp_dir, "nested_calls.star"),
            os.path.join(self.temp_dir, "plop_scenario.star")
        ]
        
        # Analyze all files
        violations = analyze_files(test_files, checks, self.temp_dir)
        
        # Check that violations were found in all files
        self.assertEqual(len(violations), 6)
        
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
        messages = self._extract_violation_messages(violations)
        
        # Check for non-existent function calls in nested contexts
        self._assert_contains_message(
            messages, 
            "non_existent_function", 
            "Failed to detect non-existent function in first nested call"
        )
        self._assert_contains_message(
            messages, 
            "another_non_existent", 
            "Failed to detect non-existent function in second nested call"
        )
        self._assert_contains_message(
            messages, 
            "third_non_existent", 
            "Failed to detect non-existent function in keyword argument"
        )

    def test_analyze_comps(self):
        """Test analyzing a file for comprehension violations."""
        # Set up checks
        checks = {
            "import_naming": False,
            "calls": True,
            "function_visibility": False
        }
        
        # Set up shared data
        shared_data = {}
        
        # Analyze the nested calls file
        nested_calls_file = os.path.join(self.temp_dir, "comps.star")
        violations = analyze_file(nested_calls_file, checks, shared_data, self.temp_dir)
        
        # Check that violations were found
        self.assertTrue(violations)
        
        # Check that the correct violations were reported
        messages = self._extract_violation_messages(violations)
        
        # Check for non-existent function calls in nested contexts
        self._assert_contains_message(
            messages, 
            "'x'", 
            "Invalid object 'x' in call to 'x.replace': object is not defined"
        )

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
        messages = self._extract_violation_messages(violations)
        
        # Check for the non-existent plop function call
        self._assert_contains_message(
            messages, 
            "plop", 
            "Failed to detect non-existent plop function in nested call"
        )
        
    def test_function_reference_scenario(self):
        """Test that function references (not calls) are recognized as external references."""
        # Create test files
        test_dir = os.path.join(tempfile.gettempdir(), "kurtosis_lint_test_function_reference")
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a module with a function
        module_file = os.path.join(test_dir, "module.star")
        with open(module_file, "w") as f:
            f.write("""
def public_function():
    \"\"\"This is a documented public function.\"\"\"
    return "Hello, world!"

def undocumented_function():
    return "No docs here"
""")
        
        # Create a file that references the function without calling it
        reference_file = os.path.join(test_dir, "reference.star")
        with open(reference_file, "w") as f:
            f.write("""
_module = import_module("./module.star")

# Reference the function without calling it
func_reference = _module.public_function

# Pass the function as an argument
def take_func(func):
    return func()

result = take_func(_module.undocumented_function)
""")
        
        # Run the analyzer
        checks = {
            "calls": True,
            "function_visibility": True,
            "import_naming": True,
            "local_imports": True
        }
        
        violations = analyze_files([module_file, reference_file], checks)
        
        # Check that no violations were found for the documented function
        module_violations = violations.get(module_file, [])
        
        # The undocumented function should have a violation since it's used externally
        messages = self._extract_violation_messages(module_violations)
        self._assert_contains_message(
            messages,
            "undocumented_function",
            "Should have found a violation for the undocumented function referenced externally"
        )
        self._assert_contains_message(
            messages,
            "should be documented",
            "Should have found a message indicating the function should be documented"
        )

    def test_function_reference_in_array(self):
        """Test that function references in arrays are recognized as external references."""
        # Create test files
        test_dir = os.path.join(tempfile.gettempdir(), "kurtosis_lint_test_function_reference_array")
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a module with a function
        module_file = os.path.join(test_dir, "module.star")
        with open(module_file, "w") as f:
            f.write("""
def public_function():
    \"\"\"This is a documented public function.\"\"\"
    return "Hello, world!"

def undocumented_function():
    return "No docs here"
""")
        
        # Create a file that references the function in an array
        reference_file = os.path.join(test_dir, "array_reference.star")
        with open(reference_file, "w") as f:
            f.write("""
_module = import_module("./module.star")

# Reference the function in an array
func_references = [
    _module.public_function,
    _module.undocumented_function
]

# Use the functions from the array
def execute_functions(funcs):
    results = []
    for func in funcs:
        results.append(func())
    return results

results = execute_functions(func_references)
""")
        
        # Run the analyzer
        checks = {
            "calls": True,
            "function_visibility": True,
            "import_naming": True,
            "local_imports": True
        }
        
        violations = analyze_files([module_file, reference_file], checks)
        
        # Check that no violations were found for the documented function
        module_violations = violations.get(module_file, [])
        
        # The undocumented function should have a violation since it's used externally
        messages = self._extract_violation_messages(module_violations)
        self._assert_contains_message(
            messages,
            "undocumented_function",
            "Should have found a violation for the undocumented function referenced in an array"
        )
        self._assert_contains_message(
            messages,
            "should be documented",
            "Should have found a message indicating the function should be documented"
        )

    def test_function_reference_in_tuple(self):
        """Test that function references in tuples are recognized as external references."""
        # Create test files
        test_dir = os.path.join(tempfile.gettempdir(), "kurtosis_lint_test_function_reference_tuple")
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a module with a function
        module_file = os.path.join(test_dir, "module.star")
        with open(module_file, "w") as f:
            f.write("""
def public_function():
    \"\"\"This is a documented public function.\"\"\"
    return "Hello, world!"

def undocumented_function():
    return "No docs here"
""")
        
        # Create a file that references the function in a tuple
        reference_file = os.path.join(test_dir, "tuple_reference.star")
        with open(reference_file, "w") as f:
            f.write("""
_module = import_module("./module.star")

# Reference the function in a tuple
func_references = (
    _module.public_function,
    _module.undocumented_function
)

# Use the functions from the tuple
def execute_functions(funcs):
    results = []
    for func in funcs:
        results.append(func())
    return results

results = execute_functions(func_references)
""")
        
        # Run the analyzer
        checks = {
            "calls": True,
            "function_visibility": True,
            "import_naming": True,
            "local_imports": True
        }
        
        violations = analyze_files([module_file, reference_file], checks)
        
        # Check that no violations were found for the documented function
        module_violations = violations.get(module_file, [])
        
        # The undocumented function should have a violation since it's used externally
        messages = self._extract_violation_messages(module_violations)
        self._assert_contains_message(
            messages,
            "undocumented_function",
            "Should have found a violation for the undocumented function referenced in a tuple"
        )
        self._assert_contains_message(
            messages,
            "should be documented",
            "Should have found a message indicating the function should be documented"
        )


if __name__ == "__main__":
    unittest.main() 