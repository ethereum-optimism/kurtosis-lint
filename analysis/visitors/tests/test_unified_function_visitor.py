"""
Test module for the UnifiedFunctionVisitor class.

This module contains tests for the UnifiedFunctionVisitor class, which combines
the functionality of FunctionCollector, FunctionVisibilityVisitor, CallAnalyzer, and CallTracker.
"""

import unittest
import ast
import os
import tempfile

from analysis.visitors.unified_function_visitor import UnifiedFunctionVisitor
from analysis.visitors.common import FunctionSignature, ImportInfo


class TestUnifiedFunctionVisitor(unittest.TestCase):
    """Test cases for the UnifiedFunctionVisitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name
        
        # Create a test file path
        self.file_path = os.path.join(self.temp_path, "test_file.star")
        
        # Create a basic visitor
        self.visitor = UnifiedFunctionVisitor(
            file_path=self.file_path,
            workspace_root=self.temp_path
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_function_collection(self):
        """Test collection of function definitions."""
        code = """
def test_function(arg1, arg2=None, *args, kwarg1, kwarg2=None, **kwargs):
    return arg1
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that the function was collected
        self.assertEqual(len(self.visitor.functions), 1)
        self.assertIn("test_function", self.visitor.functions)
        
        # Check the function signature
        signature = self.visitor.functions["test_function"]
        self.assertEqual(signature.name, "test_function")
        self.assertEqual(signature.file_path, self.file_path)
        self.assertEqual(signature.args, ["arg1", "arg2"])
        self.assertEqual(signature.defaults, [None])
        self.assertEqual(signature.vararg, "args")
        self.assertEqual(signature.kwonlyargs, ["kwarg1", "kwarg2"])
        self.assertEqual(signature.kwdefaults, {"kwarg1": None, "kwarg2": None})
        self.assertEqual(signature.kwarg, "kwargs")
    
    def test_function_documentation_detection(self):
        """Test detection of function documentation."""
        code = '''
def documented_function():
    """This is a documented function."""
    return "documented"

def undocumented_function():
    return "undocumented"
'''
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that both functions were collected
        self.assertEqual(len(self.visitor.functions), 2)
        
        # Check documentation status
        self.assertTrue(self.visitor.function_docs["documented_function"])
        self.assertFalse(self.visitor.function_docs["undocumented_function"])
    
    def test_function_visibility_analysis(self):
        """Test analysis of function visibility."""
        code = '''
def _private_function():
    return "private"

def documented_function():
    """This is a documented function."""
    return "documented"

def undocumented_function():
    return "undocumented"
'''
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Create a list of functions for the analysis
        functions = []
        for func_name, func_sig in self.visitor.functions.items():
            func = type('Function', (), {})()
            func.name = func_name
            func.line = func_sig.lineno
            func.docstring = self.visitor.function_docs.get(func_name, "")
            functions.append(func)
        
        # Analyze function visibility
        violations = self.visitor.analyze_function_visibility(self.file_path, functions)
        
        # Check that a violation was reported for the undocumented function
        self.assertEqual(len(violations), 1)
        self.assertIn("undocumented_function", violations[0].message)
        self.assertIn("consider making it private", violations[0].message)
    
    def test_external_function_calls(self):
        """Test detection of external function calls."""
        # Create a visitor with imports and all_functions
        imports = {
            "module": ImportInfo(
                module_path="path/to/module",
                package_id=None,
                imported_names={}
            )
        }
        
        all_functions = {
            "path/to/module.star": {
                "external_function": FunctionSignature(
                    name="external_function",
                    file_path="path/to/module.star",
                    lineno=1,
                    args=[],
                    defaults=[],
                    kwonlyargs=[],
                    kwdefaults={},
                    vararg=None,
                    kwarg=None
                )
            }
        }
        
        module_to_file = {
            "path/to/module.star": "path/to/module.star"
        }
        
        visitor = UnifiedFunctionVisitor(
            file_path=self.file_path,
            imports=imports,
            all_functions=all_functions,
            module_to_file=module_to_file,
            workspace_root=self.temp_path
        )
        
        code = """
module.external_function()
"""
        node = ast.parse(code)
        visitor.visit(node)
        
        # Check that the external call was detected
        self.assertEqual(len(visitor.external_calls), 1)
        self.assertIn(("path/to/module.star", "external_function"), visitor.external_calls)
    
    def test_call_compatibility_checking(self):
        """Test checking of function call compatibility."""
        # Define a function
        code = """
def test_function(arg1, arg2=None):
    return arg1

# Valid call
test_function("value")

# Invalid call - missing required argument
test_function()

# Invalid call - too many arguments
test_function("value", "value2", "value3")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that violations were reported for the invalid calls
        self.assertEqual(len(self.visitor.violations), 2)
        self.assertIn("Missing required positional argument", self.visitor.violations[0][1])
        self.assertIn("Too many positional arguments", self.visitor.violations[1][1])
    
    def test_function_visibility_with_external_calls(self):
        """Test function visibility analysis with external calls."""
        code = '''
def undocumented_public_function():
    return "This function is called from another module"
'''
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Create a list of functions for the analysis
        functions = []
        for func_name, func_sig in self.visitor.functions.items():
            func = type('Function', (), {})()
            func.name = func_name
            func.line = func_sig.lineno
            func.docstring = self.visitor.function_docs.get(func_name, "")
            functions.append(func)
        
        # Set external calls
        self.visitor.external_calls.add((self.file_path, "undocumented_public_function"))
        
        # Analyze function visibility
        violations = self.visitor.analyze_function_visibility(self.file_path, functions)
        
        # Check that a violation was reported suggesting to document the function
        self.assertEqual(len(violations), 1)
        self.assertIn("undocumented_public_function", violations[0].message)
        self.assertIn("used in other modules and should be documented", violations[0].message)
    
    def test_disabled_checks(self):
        """Test that checks can be disabled."""
        # Create a visitor with checks disabled
        visitor = UnifiedFunctionVisitor(
            file_path=self.file_path,
            workspace_root=self.temp_path,
            check_calls=False,
            check_visibility=False
        )
        
        code = """
def undocumented_function():
    return "undocumented"

# Invalid call - missing required argument
undocumented_function("extra")
"""
        node = ast.parse(code)
        visitor.visit(node)
        
        # Create a list of functions for the analysis
        functions = []
        for func_name, func_sig in visitor.functions.items():
            func = type('Function', (), {})()
            func.name = func_name
            func.line = func_sig.lineno
            func.docstring = visitor.function_docs.get(func_name, "")
            functions.append(func)
        
        # Analyze function visibility
        violations = visitor.analyze_function_visibility(self.file_path, functions)
        
        # Check that no violations were reported
        self.assertEqual(len(violations), 0)
        self.assertEqual(len(visitor.violations), 0)
    
    def test_test_function_exemption(self):
        """Test that functions starting with test_ are exempted from the documented or private requirement."""
        code = """
def test_something():
    return "This is an undocumented test function"

def regular_function():
    return "This is an undocumented regular function"
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Create a list of functions for the analysis
        functions = []
        for func_name, func_sig in self.visitor.functions.items():
            func = type('Function', (), {})()
            func.name = func_name
            func.line = func_sig.lineno
            func.docstring = self.visitor.function_docs.get(func_name, "")
            functions.append(func)
        
        # Analyze function visibility
        violations = self.visitor.analyze_function_visibility(self.file_path, functions)
        
        # Only the regular function should have a violation
        self.assertEqual(len(violations), 1)
        self.assertIn("regular_function", violations[0].message)
        self.assertIn("consider making it private", violations[0].message)


if __name__ == "__main__":
    unittest.main() 