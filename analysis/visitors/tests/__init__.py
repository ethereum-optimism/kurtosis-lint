from . import test_base_visitor
from . import test_unified_import_visitor
from . import test_unified_function_visitor
from . import test_error_handling

import logging

# Configure loggers for tests - set to ERROR level to reduce noise during testing
logging.getLogger('analysis.visitors').setLevel(logging.ERROR)

# Ensure all child loggers are also set to ERROR level
for name in logging.root.manager.loggerDict:
    if name.startswith('analysis.visitors.'):
        logging.getLogger(name).setLevel(logging.ERROR)
