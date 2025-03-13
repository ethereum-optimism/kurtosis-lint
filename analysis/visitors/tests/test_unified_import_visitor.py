"""
Test module for the UnifiedImportVisitor class.

This module contains tests for the UnifiedImportVisitor class, which combines
the functionality of ImportScanner, ModuleAnalyzer, and ImportNamingVisitor.
"""

import unittest
import ast
import os
import tempfile
import logging
from io import StringIO

from analysis.visitors.unified_import_visitor import UnifiedImportVisitor, ImportedModule


class TestUnifiedImportVisitor(unittest.TestCase):
    """Test cases for the UnifiedImportVisitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing file resolution
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name
        
        # Create a mock kurtosis.yml file to identify the workspace root
        with open(os.path.join(self.temp_path, "kurtosis.yml"), "w") as f:
            f.write("# Mock kurtosis.yml file for testing")
        
        # Create the visitor with the workspace root
        self.visitor = UnifiedImportVisitor(
            file_path=os.path.join(self.temp_path, "test_file.star"),
            workspace_root=self.temp_path,
            check_file_exists=False
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_import_module_call(self):
        """Test tracking of import_module calls."""
        code = """
_imports = import_module("/path/to/module.star")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that the import was tracked correctly
        self.assertEqual(len(self.visitor.import_module_calls), 1)
        self.assertIn("_imports", self.visitor.import_module_calls)
        
        # Check that the variable was added to import_module_vars
        self.assertIn("_imports", self.visitor.import_module_vars)
        
        # Check that no violations were reported
        self.assertEqual(len(self.visitor.violations), 0)
    
    def test_import_naming_violation(self):
        """Test detection of import naming violations."""
        code = """
imports = import_module("/path/to/module.star")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that a violation was reported
        self.assertEqual(len(self.visitor.violations), 1)
        self.assertIn("should be private", self.visitor.violations[0][1])
    
    def test_alias_tracking(self):
        """Test tracking of aliases to import_module results."""
        code = """
_imports = import_module("/path/to/module.star")
alias = _imports
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that a violation was reported for the alias
        self.assertEqual(len(self.visitor.violations), 1)
        self.assertIn("alias", self.visitor.violations[0][1])
        self.assertIn("should be private", self.visitor.violations[0][1])
    
    def test_module_path_resolution(self):
        """Test resolution of module paths."""
        # Create a test module file
        module_path = os.path.join(self.temp_path, "test_module.star")
        with open(module_path, "w") as f:
            f.write("# Test module")
        
        code = f"""
_imports = import_module("test_module.star")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that the module path was resolved correctly
        self.assertEqual(len(self.visitor.import_module_calls), 1)
        imported_module = self.visitor.import_module_calls["_imports"]
        self.assertEqual(imported_module.module_path, "test_module.star")
        self.assertEqual(imported_module.resolved_path, module_path)
    
    def test_external_import(self):
        """Test an import_module call with an external path (github.com/...)."""
        code = """
_imports = import_module("github.com/some/external/module")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that the import was tracked correctly
        self.assertEqual(len(self.visitor.import_module_calls), 1)
        imported_module = self.visitor.import_module_calls["_imports"]
        self.assertEqual(imported_module.module_path, "github.com/some/external/module")
        self.assertTrue(imported_module.is_external)
        self.assertFalse(imported_module.is_absolute)
        self.assertFalse(imported_module.is_relative)
        self.assertIsNone(imported_module.resolved_path)
    
    def test_absolute_import(self):
        """Test an import_module call with an absolute path (/path/...)."""
        code = """
_imports = import_module("/absolute/path/module.star")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that the import was tracked correctly
        self.assertEqual(len(self.visitor.import_module_calls), 1)
        imported_module = self.visitor.import_module_calls["_imports"]
        self.assertEqual(imported_module.module_path, "/absolute/path/module.star")
        self.assertFalse(imported_module.is_external)
        self.assertTrue(imported_module.is_absolute)
        self.assertFalse(imported_module.is_relative)
    
    def test_relative_import(self):
        """Test an import_module call with a relative path (./path/... or ../path/...)."""
        code = """
_imports1 = import_module("./relative/path/module.star")
_imports2 = import_module("../parent/path/module.star")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Check that both imports were tracked correctly
        self.assertEqual(len(self.visitor.import_module_calls), 2)
        
        # Check the first import
        imported_module1 = self.visitor.import_module_calls["_imports1"]
        self.assertEqual(imported_module1.module_path, "./relative/path/module.star")
        self.assertFalse(imported_module1.is_external)
        self.assertFalse(imported_module1.is_absolute)
        self.assertTrue(imported_module1.is_relative)
        
        # Check the second import
        imported_module2 = self.visitor.import_module_calls["_imports2"]
        self.assertEqual(imported_module2.module_path, "../parent/path/module.star")
        self.assertFalse(imported_module2.is_external)
        self.assertFalse(imported_module2.is_absolute)
        self.assertTrue(imported_module2.is_relative)
    
    def test_function_scope_imports(self):
        """Test that imports within function scope are not checked for naming conventions."""
        code = """
_global_import = import_module("/path/to/global_module")

def function_scope():
    local_import = import_module("/path/to/local_module")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # No violations should be reported for local_import
        self.assertEqual(len(self.visitor.violations), 0)
    
    def test_get_import_info(self):
        """Test the get_import_info method."""
        code = """
_imports = import_module("/path/to/module.star")
"""
        node = ast.parse(code)
        self.visitor.visit(node)
        
        # Get import info
        import_info = self.visitor.get_import_info()
        
        # Check that the import info was created correctly
        self.assertEqual(len(import_info), 1)
        self.assertIn("_imports", import_info)
        self.assertEqual(import_info["_imports"].module_path, "/path/to/module.star")
        self.assertIsNone(import_info["_imports"].package_id)
        self.assertEqual(import_info["_imports"].imported_names, {})
    
    def test_circular_alias_detection(self):
        """Test that circular aliases don't cause infinite recursion."""
        # Directly create a circular reference in the visitor's aliases dictionary
        self.visitor.aliases["a"] = "b"
        self.visitor.aliases["b"] = "c"
        self.visitor.aliases["c"] = "d"
        self.visitor.aliases["d"] = "e"
        self.visitor.aliases["e"] = "a"  # This creates a circular reference: a -> b -> c -> d -> e -> a
        
        # Also create a self-reference
        self.visitor.aliases["f"] = "f"  # This creates a self-reference: f -> f
        
        # Temporarily silence the logger
        logger = logging.getLogger('analysis.visitors.unified_import_visitor')
        original_level = logger.level
        logger.setLevel(logging.ERROR)  # Only show ERROR and above, not WARNING
        
        try:
            # Try to check if one of the circular aliases is an import_module variable
            # This should not cause infinite recursion
            result = self.visitor._is_import_module_var("a")
            self.assertFalse(result)  # It should return False, not cause infinite recursion
            
            # Try to check if the self-reference is an import_module variable
            result = self.visitor._is_import_module_var("f")
            self.assertFalse(result)  # It should return False, not cause infinite recursion
        finally:
            # Restore the original logger level
            logger.setLevel(original_level)
    
    def test_function_parameter_self_reference(self):
        """Test that a function with a self-referencing parameter doesn't cause infinite recursion."""
        code = """
# First create a valid import
_imports = import_module("/path/to/module.star")

# Create a function with a self-referencing parameter
def func(param):
    param = param
    return param

# Use the function
result = func(_imports)
"""
        node = ast.parse(code)
        
        # Temporarily silence the logger
        logger = logging.getLogger('analysis.visitors.unified_import_visitor')
        original_level = logger.level
        logger.setLevel(logging.ERROR)  # Only show ERROR and above, not WARNING
        
        try:
            # This should not cause infinite recursion
            self.visitor.visit(node)
        finally:
            # Restore the original logger level
            logger.setLevel(original_level)
    
    def test_complex_import_alias_scenario(self):
        """Test a complex scenario that might trigger infinite recursion."""
        code = """
# Create multiple imports
_imports1 = import_module("/path/to/module1.star")
_imports2 = import_module("/path/to/module2.star")

# Create aliases
module1 = _imports1
module2 = _imports2

# Create a dictionary with references to the modules
modules = {
    "module1": module1,
    "module2": module2
}

# Create variables that reference elements from the dictionary
el_module1 = modules["module1"]
el_module2 = modules["module2"]

# Create a circular reference through a dictionary
circular_dict = {}
circular_dict["key"] = circular_dict

# Create a variable that references the circular dictionary
el_circular_dict = circular_dict

# Create a function that uses all these variables
def process_modules(m1, m2, circ):
    # Self-reference in function parameters
    m1 = m1
    m2 = m2
    circ = circ
    
    # Create more aliases inside the function
    local_m1 = m1
    local_m2 = m2
    local_circ = circ
    
    # Create a circular reference inside the function
    local_var = local_var
    
    return local_m1, local_m2, local_circ

# Call the function
result1, result2, result_circ = process_modules(el_module1, el_module2, el_circular_dict)

# Create more aliases to the results
final_module1 = result1
final_module2 = result2
final_circular = result_circ

# Create a self-referencing variable at the end
el_cl_data_files_artifact_uuid = el_cl_data_files_artifact_uuid
"""
        node = ast.parse(code)
        
        # Temporarily silence the logger
        logger = logging.getLogger('analysis.visitors.unified_import_visitor')
        original_level = logger.level
        logger.setLevel(logging.ERROR)  # Only show ERROR and above, not WARNING
        
        try:
            # This should not cause infinite recursion
            self.visitor.visit(node)
            
            # Try to check if the problematic variable is an import_module variable
            result = self.visitor._is_import_module_var("el_cl_data_files_artifact_uuid")
            self.assertFalse(result)  # It should return False, not cause infinite recursion
        except RecursionError:
            self.fail("RecursionError when checking if el_cl_data_files_artifact_uuid is an import_module variable")
        finally:
            # Restore the original logger level
            logger.setLevel(original_level)


if __name__ == "__main__":
    unittest.main() 