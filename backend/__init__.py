# Rewind Backend Package

import sys
from pathlib import Path

# Add rewind_backend directory to sys.path
# This allows "from core.xxx" imports within the package to work properly
_backend_dir = Path(__file__).parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
