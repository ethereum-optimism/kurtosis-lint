"""
Test module for function visibility analysis.

This module contains tests for the function visibility analysis functionality
now implemented in the UnifiedFunctionVisitor class.
"""

import unittest
import ast
import os
import tempfile

from analysis.visitors.unified_function_visitor import UnifiedFunctionVisitor


class TestFunctionVisibilityVisitor(unittest.TestCase):
    """Test cases for function visibility analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a UnifiedFunctionVisitor with check_visibility=True
        self.visitor = UnifiedFunctionVisitor(file_path="test_file.star", check_visibility=True)
        self.file_path = "test_file.star"
    
    def test_private_function(self):
        """Test a private function (starts with underscore)."""
        code = """
def _private_function():
    return "This is a private function"
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
        
        # No violations should be reported for private functions
        self.assertEqual(len(violations), 0)
    
    def test_documented_public_function(self):
        """Test a documented public function."""
        code = '''
def public_function():
    """This is a documented public function."""
    return "This is a documented public function"
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
        
        # No violations should be reported for documented public functions
        self.assertEqual(len(violations), 0)
    
    def test_undocumented_public_function_not_used_elsewhere(self):
        """Test an undocumented public function not used elsewhere."""
        code = """
def public_function():
    return "This is an undocumented public function"
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
        
        # A violation should be reported suggesting to make it private
        self.assertEqual(len(violations), 1)
        self.assertIn("consider making it private", violations[0].message)
    
    def test_undocumented_public_function_used_elsewhere(self):
        """Test an undocumented public function used elsewhere."""
        code = """
def public_function():
    return "This is an undocumented public function"
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
        
        # Set external calls to include this function
        self.visitor.external_calls.add((self.file_path, "public_function"))
        
        # Analyze function visibility
        violations = self.visitor.analyze_function_visibility(self.file_path, functions)
        
        # A violation should be reported suggesting to document it
        self.assertEqual(len(violations), 1)
        self.assertIn("used in other modules and should be documented", violations[0].message)
    
    def test_multiple_functions(self):
        """Test multiple functions with different visibility and documentation."""
        code = '''
def _private_function():
    return "This is a private function"

def documented_public_function():
    """This is a documented public function."""
    return "This is a documented public function"

def undocumented_public_function():
    return "This is an undocumented public function"

def used_undocumented_public_function():
    return "This is an undocumented public function used elsewhere"
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
        
        # Set external calls to include one of the undocumented functions
        self.visitor.external_calls.add((self.file_path, "used_undocumented_public_function"))
        
        # Analyze function visibility
        violations = self.visitor.analyze_function_visibility(self.file_path, functions)
        
        # Two violations should be reported:
        # 1. undocumented_public_function -> make it private
        # 2. used_undocumented_public_function -> document it
        self.assertEqual(len(violations), 2)
        
        # Find the violations for each function
        undocumented_violation = None
        used_undocumented_violation = None
        for violation in violations:
            if "undocumented_public_function" in violation.message and "consider making it private" in violation.message:
                undocumented_violation = violation
            elif "used_undocumented_public_function" in violation.message and "used in other modules" in violation.message:
                used_undocumented_violation = violation
        
        # Check that both violations were found
        self.assertIsNotNone(undocumented_violation, "Missing violation for undocumented_public_function")
        self.assertIsNotNone(used_undocumented_violation, "Missing violation for used_undocumented_public_function")
    
    def test_multiline_docstring(self):
        """Test a function with a multiline docstring."""
        code = '''
def public_function():
    """
    This is a multiline docstring.
    It spans multiple lines.
    """
    return "This is a documented public function"
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
        
        # No violations should be reported for documented public functions
        self.assertEqual(len(violations), 0)
    
    def test_test_function_exemption(self):
        """Test that functions starting with test_ are exempted from the documented or private requirement."""
        code = """
def test_something():
    return "This is an undocumented test function"
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
        
        # No violations should be reported for test functions
        self.assertEqual(len(violations), 0)
    
    def test_test_function_exemption_when_used_elsewhere(self):
        """Test that functions starting with test_ are exempted even when they're used in other modules."""
        code = """
def test_something():
    return "This is an undocumented test function used elsewhere"
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
        
        # Set external calls to include this function
        self.visitor.external_calls.add((self.file_path, "test_something"))
        
        # Analyze function visibility
        violations = self.visitor.analyze_function_visibility(self.file_path, functions)
        
        # No violations should be reported for test functions, even when used elsewhere
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main() 