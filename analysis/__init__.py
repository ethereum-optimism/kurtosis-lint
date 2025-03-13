"""
Analysis package for Starlark code.

This package contains tools for analyzing Starlark code, including:

1. A unified analyzer that can check:
   - Function call compatibility
   - Function visibility and documentation
   - Import module variable naming conventions

2. Visitor classes for AST traversal and analysis
   - Base visitor with common functionality
   - Specialized visitors for different types of analysis

See the README.md file for more information on how to use the analyzer.
"""

# The analyzer module should be imported directly by users
# from analysis.analyzer import analyze_file, main 