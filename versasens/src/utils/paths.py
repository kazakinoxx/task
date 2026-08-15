"""Utility functions for path management."""

import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent.parent
"""Path to the root directory of the project"""

DLLS_PATH = ROOT_PATH / "dlls"
"""Path to the DLLs directory"""

CWD = Path(sys.executable).parent.resolve()
"""Path object to the current working directory"""

# Config path
if Path(sys.executable).stem == "python":
    # Different path if running as script
    CONFIG_PATH = ROOT_PATH / "config.ini"
else:
    CONFIG_PATH = CWD / "config.ini"
