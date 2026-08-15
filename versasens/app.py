"""File that launches the application."""

# Compilation mode, support OS-specific options
# nuitka-project-if: {OS} in ("Windows", "Linux", "Darwin", "FreeBSD"):
#    nuitka-project: --mode=onefile
# nuitka-project-else:
#    nuitka-project: --mode=standalone

# The PySide6 plugin covers qt-plugins
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-qt-plugins=qml

# DLLs
# nuitka-project: --include-data-dir=dlls=dlls


import os
import sys

# from src.utils import dynaconf_config
from src.utils.logger import log_file
from src.utils.paths import CONFIG_PATH, DLLS_PATH

if sys.platform == "win32":
    # Add DLLs to path before imports
    os.add_dll_directory(str(DLLS_PATH.resolve()))
    os.environ["PATH"] += f";{DLLS_PATH.resolve()}"
    sys.path.insert(0, str(DLLS_PATH.resolve()))


from PySide6 import QtAsyncio
from PySide6.QtWidgets import QApplication

from src.qt.main_window import MainWindow


def _main() -> None:
    app = QApplication(sys.argv)  # noqa: F841

    window = MainWindow(CONFIG_PATH)
    window.show()

    QtAsyncio.run(handle_sigint=True)


if __name__ == "__main__":
    _main()

    # Delete log file if empty
    if log_file.exists():
        is_empty = False

        with log_file.open("r") as f:
            if len(f.readlines()) == 0:
                is_empty = True

        if is_empty:
            print("Deleting log file")  # noqa: T201
            log_file.unlink()
