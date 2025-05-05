"""
Test module for the BaseVisitor class.

This module contains tests for the BaseVisitor class.
"""

import unittest
import ast
import io
import sys
from contextlib import redirect_stdout

from analysis.visitors.base_visitor import BaseVisitor


class TestBaseVisitor(unittest.TestCase):
    """Test cases for the BaseVisitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.visitor = BaseVisitor()
        
        # Reset verbosity to False for each test
        BaseVisitor.set_verbose(False)
    
    def test_set_verbose(self):
        """Test setting verbosity."""
        # Initially, verbose should be False
        self.assertFalse(BaseVisitor.verbose)
        
        # Set verbose to True
        BaseVisitor.set_verbose(True)
        self.assertTrue(BaseVisitor.verbose)
        
        # Set verbose back to False
        BaseVisitor.set_verbose(False)
        self.assertFalse(BaseVisitor.verbose)
    
    def test_debug_print(self):
        """Test debug printing."""
        # Capture stdout
        stdout = io.StringIO()
        
        # With verbose=False, debug_print should not print anything
        with redirect_stdout(stdout):
            self.visitor.debug_print("Test message")
        
        self.assertEqual(stdout.getvalue(), "")
        
        # With verbose=True, debug_print should print the message
        BaseVisitor.set_verbose(True)
        with redirect_stdout(stdout):
            self.visitor.debug_print("Test message")
        
        self.assertEqual(stdout.getvalue(), "Test message\n")
    
    def test_scope_management(self):
        """Test scope management methods."""
        # Initially, there should be one empty scope
        self.assertEqual(len(self.visitor.scopes), 1)
        self.assertEqual(len(self.visitor.scopes[0]), 0)
        
        # Enter a new scope
        self.visitor._enter_scope()
        self.assertEqual(len(self.visitor.scopes), 2)
        
        # Add a variable to the current scope
        self.visitor._add_to_current_scope("test_var")
        self.assertIn("test_var", self.visitor.scopes[1])
        
        # Check if a variable is in scope
        self.assertTrue(self.visitor._is_in_scope("test_var"))
        self.assertFalse(self.visitor._is_in_scope("nonexistent_var"))
        
        # Exit the scope
        self.visitor._exit_scope()
        self.assertEqual(len(self.visitor.scopes), 1)
        
        # The variable should no longer be in scope
        self.assertFalse(self.visitor._is_in_scope("test_var"))
    
    def test_visit_module(self):
        """Test visiting a module."""
        code = """
x = 1
y = 2
"""
        node = ast.parse(code)
        
        # Visit the module
        self.visitor.visit_Module(node)
        
        # After visiting, we should be back to just one scope
        self.assertEqual(len(self.visitor.scopes), 1)
    
    def test_visit_function_def(self):
        """Test visiting a function definition."""
        code = """
def test_func(a, b=1, *args, c, d=2, **kwargs):
    x = 1
    y = 2
"""
        node = ast.parse(code)
        func_node = node.body[0]
        
        # Enter module scope first (as would happen in a real visit)
        self.visitor._enter_scope()
        
        # Visit the function
        self.visitor.visit_FunctionDef(func_node)
        
        # After visiting, we should be back to just the module scope
        # Plus the original scope we entered
        self.assertEqual(len(self.visitor.scopes), 2)
    
    def test_visit_for_loop(self):
        """Test visiting a for loop."""
        code = """
for i in range(10):
    x = i * 2
else:
    y = 0
"""
        node = ast.parse(code)
        for_node = node.body[0]
        
        # Enter module scope first (as would happen in a real visit)
        self.visitor._enter_scope()
        
        # Visit the for loop
        self.visitor.visit_For(for_node)
        
        # After visiting, we should be back to just the module scope
        # Plus the original scope we entered
        self.assertEqual(len(self.visitor.scopes), 2)
    
    def test_visit_if_statement(self):
        """Test visiting an if statement."""
        code = """
if condition:
    x = 1
else:
    y = 2
"""
        node = ast.parse(code)
        if_node = node.body[0]
        
        # Enter module scope first (as would happen in a real visit)
        self.visitor._enter_scope()
        
        # Visit the if statement
        self.visitor.visit_If(if_node)
        
        # After visiting, we should be back to just the module scope
        # Plus the original scope we entered
        self.assertEqual(len(self.visitor.scopes), 2)
    
    def test_visit_assign(self):
        """Test visiting an assignment statement."""
        code = """
x = 1
y, z = 2, 3
"""
        node = ast.parse(code)
        
        # Enter module scope first (as would happen in a real visit)
        self.visitor._enter_scope()
        
        # Visit the assignments
        for assign_node in node.body:
            self.visitor.visit_Assign(assign_node)
        
        # The variables should be added to the current scope
        self.assertIn("x", self.visitor.scopes[-1])
        self.assertIn("y", self.visitor.scopes[-1])
        self.assertIn("z", self.visitor.scopes[-1])
    
    def test_visit_list_comprehension(self):
        """Test visiting a list comprehension."""
        code = """
[s.replace('a', 'o') for s in ['a', 'b', 'c']]
"""
        node = ast.parse(code)

        list_comp_node = node.body[0].value
        
        # Enter module scope first (as would happen in a real visit)
        self.visitor._enter_scope()
        
        # Visit the list comprehension statement
        self.visitor.visit_ListComp(list_comp_node)
        
        # After visiting, we should be back to just the module scope
        # Plus the original scope we entered
        self.assertEqual(len(self.visitor.scopes), 2)
    
    def test_complex_scope_tracking(self):
        """Test tracking variables across complex nested scopes."""
        code = """
global_var = 1

def outer_func(param1, param2):
    outer_var = 2
    
    for i in range(10):
        loop_var = i
        
        if i > 5:
            if_var = i * 2
"""
        node = ast.parse(code)
        
        # Visit the module
        self.visitor.visit_Module(node)
        
        # After visiting, we should be back to just one scope
        self.assertEqual(len(self.visitor.scopes), 1)
        
        # The global variable should not be in any scope since we exited the module scope
        # We can only test that we're back to the initial empty scope
        self.assertEqual(len(self.visitor.scopes[0]), 0)
    
    def test_violations_tracking(self):
        """Test tracking violations."""
        # Add a violation
        self.visitor.violations.append((1, "Test violation"))
        
        # Check that the violation was added
        self.assertEqual(len(self.visitor.violations), 1)
        self.assertEqual(self.visitor.violations[0], (1, "Test violation"))
        
        # Add another violation
        self.visitor.violations.append((2, "Another violation"))
        self.assertEqual(len(self.visitor.violations), 2)
    
    def test_nested_scopes(self):
        """Test handling of nested scopes."""
        code = """
global_var = 1

def outer_func():
    outer_var = 2
    
    def inner_func():
        inner_var = 3
        
        for i in range(10):
            loop_var = i
            
            if i > 5:
                if_var = i * 2
"""
        node = ast.parse(code)
        
        # Visit the module
        self.visitor.visit_Module(node)
        
        # After visiting, we should be back to just one scope
        self.assertEqual(len(self.visitor.scopes), 1)
        
        # The global variable should not be in any scope since we exited the module scope
        # We can only test that we're back to the initial empty scope
        self.assertEqual(len(self.visitor.scopes[0]), 0)
    
    def test_empty_scopes_stack(self):
        """Test handling of empty scopes stack."""
        # Empty the scopes stack
        self.visitor.scopes = []
        
        # _exit_scope should not raise an exception
        self.visitor._exit_scope()
        
        # _add_to_current_scope should not raise an exception
        self.visitor._add_to_current_scope("test_var")
        
        # _is_in_scope should return False
        self.assertFalse(self.visitor._is_in_scope("test_var"))


if __name__ == "__main__":
    unittest.main() 