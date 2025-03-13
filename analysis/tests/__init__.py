"""
Test package for the analysis module.
"""

import sys
import os
import logging

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Configure loggers for tests - set to ERROR level to reduce noise during testing
logging.getLogger('analysis').setLevel(logging.ERROR)

# Ensure all child loggers are also set to ERROR level
for name in logging.root.manager.loggerDict:
    if name.startswith('analysis.'):
        logging.getLogger(name).setLevel(logging.ERROR) 