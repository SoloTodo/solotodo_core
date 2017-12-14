from .defaults import *

try:
    from .local import *
except ImportError:
    # If user did not provide local settings, skip them
    pass
