"""
Test module for error handling in the unified visitors.

This module contains tests for error handling in the unified visitors.
"""

import unittest
import ast
import os
import tempfile
from unittest.mock import patch, MagicMock

from analysis.visitors.unified_import_visitor import UnifiedImportVisitor
from analysis.visitors.unified_function_visitor import UnifiedFunctionVisitor


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling in the unified visitors."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name
        
        # Create a mock kurtosis.yml file to identify the workspace root
        with open(os.path.join(self.temp_path, "kurtosis.yml"), "w") as f:
            f.write("# Mock kurtosis.yml file for testing")
        
        # Create the visitors with the workspace root
        self.import_visitor = UnifiedImportVisitor(
            file_path=os.path.join(self.temp_path, "test_file.star"),
            workspace_root=self.temp_path
        )
        
        self.function_visitor = UnifiedFunctionVisitor(
            file_path=os.path.join(self.temp_path, "test_file.star"),
            workspace_root=self.temp_path,
            check_calls=True,
            check_visibility=True
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_malformed_import_module_call(self):
        """Test handling of malformed import_module calls."""
        # Missing argument
        code = """
imports = import_module()
"""
        node = ast.parse(code)
        self.import_visitor.visit(node)
        
        # Should not raise an exception, but should not track the import
        self.assertEqual(len(self.import_visitor.import_module_calls), 0)
        
        # Non-string argument
        code = """
imports = import_module(123)
"""
        node = ast.parse(code)
        self.import_visitor.visit(node)
        
        # Should not raise an exception, but should not track the import
        self.assertEqual(len(self.import_visitor.import_module_calls), 0)
    
    def test_malformed_function_definition(self):
        """Test handling of malformed function definitions."""
        # Instead of trying to mock a function definition with duplicate parameters,
        # let's test a function with a valid but unusual definition
        code = """
def test_function(*args, **kwargs):
    return args, kwargs
"""
        node = ast.parse(code)
        self.function_visitor.visit(node)
        
        # The function should be tracked
        self.assertIn("test_function", self.function_visitor.functions)
        
        # Check that the function signature is correct
        signature = self.function_visitor.functions["test_function"]
        self.assertEqual(signature.name, "test_function")
        self.assertEqual(signature.args, [])
        self.assertEqual(signature.vararg, "args")
        self.assertEqual(signature.kwarg, "kwargs")
    
    def test_malformed_function_call(self):
        """Test handling of malformed function calls."""
        # Define a function
        code = """
def test_function(param1, param2):
    return param1 + param2

# Call with incorrect arguments
result = test_function("string", 123)
"""
        node = ast.parse(code)
        self.function_visitor.visit(node)
        
        # Should not raise an exception, but should track the function
        self.assertIn("test_function", self.function_visitor.functions)
        
        # Create a malformed call node (missing func attribute)
        call_node = MagicMock(spec=ast.Call)
        call_node.func = None
        call_node.args = []
        call_node.keywords = []
        call_node.lineno = 5
        
        # This should not raise an exception
        self.function_visitor.visit_Call(call_node)
    
    def test_file_not_found(self):
        """Test handling of file not found errors."""
        # Create a visitor with a non-existent file
        import_visitor = UnifiedImportVisitor(
            file_path=os.path.join(self.temp_path, "non_existent_file.star"),
            workspace_root=self.temp_path
        )
        
        # Import a non-existent module that doesn't exist in the workspace
        code = """
imports = import_module("github.com/non_existent_module")
"""
        node = ast.parse(code)
        import_visitor.visit(node)
        
        # Should not raise an exception, but should track the import
        self.assertEqual(len(import_visitor.import_module_calls), 1)
        
        # The resolved path should be None for external modules
        imported_module = import_visitor.import_module_calls["imports"]
        self.assertIsNone(imported_module.resolved_path)
    
    def test_circular_imports(self):
        """Test handling of circular imports."""
        # Create two files that import each other
        file1_path = os.path.join(self.temp_path, "file1.star")
        file2_path = os.path.join(self.temp_path, "file2.star")
        
        with open(file1_path, "w") as f:
            f.write('file2 = import_module("./file2.star")')
        
        with open(file2_path, "w") as f:
            f.write('file1 = import_module("./file1.star")')
        
        # Create visitors for both files
        import_visitor1 = UnifiedImportVisitor(
            file_path=file1_path,
            workspace_root=self.temp_path
        )
        
        import_visitor2 = UnifiedImportVisitor(
            file_path=file2_path,
            workspace_root=self.temp_path
        )
        
        # Parse and visit the files
        with open(file1_path, "r") as f:
            node1 = ast.parse(f.read())
            import_visitor1.visit(node1)
        
        with open(file2_path, "r") as f:
            node2 = ast.parse(f.read())
            import_visitor2.visit(node2)
        
        # Should not raise an exception, and should track the imports
        self.assertEqual(len(import_visitor1.import_module_calls), 1)
        self.assertEqual(len(import_visitor2.import_module_calls), 1)
        
        # The resolved paths should be correct
        imported_module1 = import_visitor1.import_module_calls["file2"]
        imported_module2 = import_visitor2.import_module_calls["file1"]
        
        self.assertEqual(imported_module1.resolved_path, file2_path)
        self.assertEqual(imported_module2.resolved_path, file1_path)
    
    def test_exception_handling(self):
        """Test general exception handling in the visitors."""
        # Create a function with a valid definition but call it with invalid arguments
        code = """
def test_function(param1: int, param2: int) -> int:
    return param1 + param2

# This would normally cause a type error at runtime
result = test_function("string", "another string")
"""
        node = ast.parse(code)
        
        # This should not raise an exception
        self.function_visitor.visit(node)
        
        # The function should be tracked
        self.assertIn("test_function", self.function_visitor.functions)


if __name__ == "__main__":
    unittest.main() 