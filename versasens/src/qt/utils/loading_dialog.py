"""File containing the loading dialog."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, override

from PySide6 import QtCore
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QWidget

from src.generated.ui.utils.loading_dialog import Ui_Dialog
from src.utils.time import get_now

if TYPE_CHECKING:
    import datetime


class LoadingDialog(QDialog, Ui_Dialog):
    """Dialog used while loading."""

    def __init__(
        self,
        parent: QWidget | None = None,
        message: str | None = None,
        expected_time_s: float | None = None,
    ) -> None:
        """
        Create a new loading dialog.

        Args:
            parent: The parent of the loading dialog. Defaults to None.
            message: If given, message to show in the loading dialog. Defaults to None.
            expected_time_s: If given, the amount of time that the dialog is expected
                             to take. Defaults to None.

        """
        super().__init__(parent)

        self.setupUi(self)

        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, on=False)

        self.expected_time_s = expected_time_s

        self.start_time: datetime.datetime | None = None
        self.progress_timer: QTimer | None = None

        if message is not None:
            self.label.setText(message)

        if expected_time_s is not None:
            # Setup progress bar
            expected_time_ms = int(expected_time_s * 1000.0)
            self.progressBar.setMaximum(expected_time_ms)
            self.progressBar.setValue(0)
        else:
            # Remove progress bar
            self.verticalLayout.removeWidget(self.progressBar)

    def _update_progress_bar(self) -> None:
        if self.start_time is None or self.expected_time_s is None:
            self.progressBar.setValue(0)
            return

        # Get time difference
        cur_time = get_now()
        diff = cur_time - self.start_time
        diff_s = diff.total_seconds()
        diff_ms = int(diff_s * 1000.0)

        # Set value
        self.progressBar.setValue(diff_ms)

        # Manually set text
        self.progressBar.setFormat(f"{diff_s:.2f}s/{self.expected_time_s:.2f}s")

    @override
    def show(self, /) -> None:
        super().show()

        # Start progress bar timer when showing
        if self.expected_time_s is not None:
            self.start_time = get_now()

            self.progress_timer = QTimer()
            self.progress_timer.timeout.connect(self._update_progress_bar)
            self.progress_timer.start(100)

        QtCore.QCoreApplication.processEvents()


@contextmanager
def loading_dialog(
    parent: QWidget,
    message: str | None = None,
    expected_time_s: float | None = None,
) -> Generator[LoadingDialog]:
    """
    Create a new loading dialog.

    Args:
        parent: The parent of the loading dialog.
        message: If given, message to show in the loading dialog. Defaults to None.
        expected_time_s: If given, the amount of time that the dialog is expected
                             to take. Defaults to None.


    Yields:
        The loading dialog.

    """
    dialog = LoadingDialog(
        parent=parent,
        message=message,
        expected_time_s=expected_time_s,
    )

    try:
        dialog.show()
        yield dialog
    finally:
        dialog.close()
