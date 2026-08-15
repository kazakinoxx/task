"""File containing the main window."""

import asyncio
import contextlib
from pathlib import Path
from typing import override

from PySide6 import QtCore
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow

from src.generated.ui.main_window import Ui_MainWindow
from src.qt.add_samples_dialog import AddSamplesDialog
from src.qt.settings_dialog import SettingsDialog
from src.qt.stream.stream_dialog import StreamDialog
from src.qt.view_samples.view_samples_dialog import ViewImportedDataDialog
from src.utils.config import get_or_create_config
from src.utils.exceptions import DataNotFoundError
from src.utils.logger import logger
from src.utils.time import get_now
from src.versa.ble import ble_disconnect_all
from src.versa.db import SubjectID, Timestamp, find_last_added


class MainWindow(QMainWindow, Ui_MainWindow):
    """The main window of the program."""

    def __init__(self, config_file_path: Path) -> None:
        """
        Create a new main window.

        Args:
            config_file_path: Alternative path to the config file.

        """
        super().__init__()

        self.setupUi(self)

        # Guards a single BLE-cleanup pass on shutdown (see closeEvent).
        self._ble_cleanup_done = False

        # Store arguments
        self.config_file_path = config_file_path
        # Create config if doesn't exist
        get_or_create_config(config_file_path)

        # Setup time ago text
        self.subject_id: SubjectID | None = None
        self.timestamp: Timestamp | None = None

        self.ago_timer = QtCore.QTimer()
        self.ago_timer.timeout.connect(self._update_ago_text)

        self._update_last_added()

        # Setup handlers
        self.add_button.clicked.connect(self._add_button_clicked)
        self.settings_button.clicked.connect(self._settings_button_clicked)
        self.view_button.clicked.connect(self._view_button_clicked)
        self.stream_button.clicked.connect(self._stream_button_clicked)

        # TODO: check if any leftover temporary files are present

    def _update_last_added(self) -> None:
        """Update the last added sample."""
        # End timer
        logger.debug("Updating last added")
        self.ago_timer.stop()

        try:
            self.subject_id, self.timestamp = find_last_added(self.config_file_path)

            timestamp_str = self.timestamp.strftime("%d.%m.%y at %H:%M:%S")
            self.last_id_text.setText(f"ID {self.subject_id} - {timestamp_str}")
            self._update_ago_text()
            self.ago_timer.start(1000)

        except DataNotFoundError:
            self.last_id_text.setText("No samples")
            self.time_ago_text.setText("")

    def _update_ago_text(self) -> None:
        """Update the X time ago text from the class' last added variable."""
        if self.timestamp is not None:
            elapsed = get_now() - self.timestamp
            days = elapsed.days
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds // 60) - hours * 60
            seconds = elapsed.seconds - minutes * 60 - hours * 3600
            elapsed_texts: list[str] = []

            if days != 0:
                elapsed_texts.append(f"{days} day" + ("s" if days != 1 else ""))
            if hours != 0:
                elapsed_texts.append(
                    f"{hours} hour" + ("s" if hours != 1 else ""),
                )
            if minutes != 0:
                elapsed_texts.append(
                    f"{minutes} minute" + ("s" if minutes != 1 else ""),
                )

            elapsed_texts.append(f"{seconds} second" + ("s" if seconds != 1 else ""))

            if len(elapsed_texts) > 1:
                elapsed_text = ", ".join(elapsed_texts[:-1])
                elapsed_text += f" and {elapsed_texts[-1]}"
            else:
                elapsed_text = elapsed_texts[0]

            self.time_ago_text.setText(f"({elapsed_text} ago)")

    def _add_button_clicked(self) -> None:
        """Handle a click of the add button."""
        dlg = AddSamplesDialog(self.config_file_path, parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.exec()

        self._update_last_added()

    def _settings_button_clicked(self) -> None:
        """Handle a click of the settings button."""
        dlg = SettingsDialog(self.config_file_path, parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.exec()

        self._update_last_added()

    def _view_button_clicked(self) -> None:
        """Handle a click of the view button."""
        dlg = ViewImportedDataDialog(self.config_file_path, parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.exec()

    def _stream_button_clicked(self) -> None:
        """Handle a click of the stream button."""
        dlg = StreamDialog(self.config_file_path, parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.exec()

        self._update_last_added()

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Disconnect any active BLE clients before the event loop closes.

        A CoreBluetooth callback delivered after the loop is torn down crashes
        the app on macOS, so defer the close until the disconnect completes.
        """
        if self._ble_cleanup_done:
            super().closeEvent(event)
            return

        self._ble_cleanup_done = True
        try:
            # Only defer the close if the async cleanup was actually scheduled,
            # so a scheduling failure can never leave the window unclosable.
            asyncio.ensure_future(self._cleanup_and_close())  # noqa: RUF006
            event.ignore()
        except Exception:  # noqa: BLE001
            super().closeEvent(event)

    async def _cleanup_and_close(self) -> None:
        """Disconnect BLE, then re-trigger the (now clean) window close."""
        with contextlib.suppress(Exception):
            await ble_disconnect_all()
        self.close()
