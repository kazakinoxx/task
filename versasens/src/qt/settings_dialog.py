"""File containing the settings dialog."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from src.generated.ui.settings import Ui_Settings
from src.utils.config import get_or_create_config, update_config
from src.utils.logger import logger


class SettingsDialog(QDialog, Ui_Settings):
    """Dialog to edit the config file."""

    def __init__(self, config_path: Path, parent: QWidget | None = None) -> None:
        """
        Create a new settings dialog.

        Args:
            config_path: Alternative path to the config file
            parent: The parent of this dialog. Defaults to None.

        """
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        # Store args
        self.config_path = config_path

        self._refresh_config()

        self.open_button.clicked.connect(self._open_config_file)
        self.db_button.clicked.connect(self._change_db_path)
        self.x_axis_length.valueChanged.connect(self._change_x_axis_length)
        self.ads_gain.valueChanged.connect(self._change_ads_gain)
        self.ads_vref.valueChanged.connect(self._change_ads_vref)

    def _refresh_config(self) -> None:
        """Read the config file and updates the dialog."""
        config = get_or_create_config(self.config_path)

        # Update fields
        self.db_lineedit.setText(str(config.db_path.resolve()))
        self.x_axis_length.setValue(config.plot_x_axis_length)
        self.ads_gain.setValue(config.ads_gain)
        self.ads_vref.setValue(config.ads_vref)

    def _change_db_path(self) -> None:
        """Change the path to the database in the config."""
        # Get a new folder for the database
        folder = QFileDialog.getExistingDirectory(
            self,
            options=QFileDialog.Option.ShowDirsOnly,
        )
        folder_path = Path(folder)

        # Update config with new path
        update_config(self.config_path, db_path=folder_path)

        # Edit dialog contents
        self.db_lineedit.setText(str(folder_path))

    def _change_x_axis_length(self, value: float) -> None:
        update_config(self.config_path, plot_x_axis_length=value)

    def _change_ads_vref(self, value: int) -> None:
        update_config(self.config_path, ads_vref=value)

    def _change_ads_gain(self, value: int) -> None:
        update_config(self.config_path, ads_gain=value)

    def _open_config_file(self) -> None:
        """Open the config file."""
        # Check the config path for security
        # Check exists
        if not self.config_path.exists():
            msg = f"The config file at {self.config_path} doesn't exist."
            QMessageBox.critical(self, "Error", msg)
            logger.warning(msg)
            return

        # Check that it is a file
        if not self.config_path.is_file():
            msg = f"{self.config_path} is not a file (possibly a folder)."
            QMessageBox.critical(self, "Error", msg)
            logger.warning(msg)
            return

        # Open file
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config_path.resolve())))
