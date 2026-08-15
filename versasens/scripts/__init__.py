import os
import sys

from src.utils.paths import DLLS_PATH

if sys.platform == "win32":
    # Add DLLs to path before imports
    os.add_dll_directory(str(DLLS_PATH.resolve()))
    os.environ["PATH"] += f";{DLLS_PATH.resolve()}"
    sys.path.insert(0, str(DLLS_PATH.resolve()))

