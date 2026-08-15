"""File containing the add new samples dialog."""

from pathlib import Path
from typing import override

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from src.generated.ui.add_samples.add_samples_dialog import Ui_AddSamplesDialog
from src.qt.utils.data_import_dialog import DataImportDialog
from src.utils.logger import logger
from src.utils.typedefs import DeleteFiles


class AddSamplesDialog(QDialog, Ui_AddSamplesDialog):
    """Dialog shown when adding new samples from the SD card."""

    def __init__(self, config_path: Path, parent: QWidget | None = None) -> None:
        """
        Create a new dialog to add new samples in the database.

        Args:
            config_path: Path to the config file
            parent: The parent of this dialog. Defaults to None.

        """
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        # Store config path
        self.config_path = config_path

        # Connect select files button
        self.files_button.clicked.connect(self._select_files)
        self.filepaths: list[Path] = []

        # Connect button box
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # No folder selected at first
        self.patient_input.setEnabled(False)
        self.notes_input.setEnabled(False)
        self.delete_checkbox.setEnabled(False)

    def _select_files(self) -> None:
        """Open a file dialog to select the files to import."""
        # Open file dialog
        filenames, _ = QFileDialog.getOpenFileNames(self, "Select raw files to import")

        logger.debug(f"Selected {len(filenames)} files", files=filenames)

        self.filepaths = [Path(f) for f in filenames]
        has_selected_files = len(filenames) > 0

        # Update text
        if has_selected_files:
            self.selected_label.setText(f"{len(filenames)} files selected")
            self.selected_label.setToolTip("\n".join([f.name for f in self.filepaths]))
        else:
            self.selected_label.setText("No files selected")
            self.selected_label.setToolTip("")

        # Enable inputs
        self.patient_input.setEnabled(has_selected_files)
        self.notes_input.setEnabled(has_selected_files)
        self.delete_checkbox.setEnabled(has_selected_files)

    @override
    def accept(self) -> None:
        # Check if no files
        if len(self.filepaths) == 0:
            QMessageBox.critical(
                self,
                "Error",
                "No files selected. Please select at least one file.",
            )
            return None

        # Check if no patient ID
        if self.patient_input.text() == "":
            QMessageBox.critical(
                self,
                "Error",
                "No patient ID. Please enter a patient ID.",
            )
            return None

        patient_id = self.patient_input.text()

        # Get notes
        notes = self.notes_input.toPlainText()

        # Get data from device
        delete_files = self.delete_checkbox.isChecked()

        # Check if really want to delete files
        if delete_files:
            button = QMessageBox.warning(
                self,
                "Delete files",
                "Are you sure you want to delete files after import?",
                buttons=(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ),
            )
            logger.debug(f"Pressed {button}")
            if button == QMessageBox.StandardButton.No:
                return super().accept()

        delete_files = (
            DeleteFiles.YES if self.delete_checkbox.isChecked() else DeleteFiles.NO
        )

        DataImportDialog.show_and_import(
            self.filepaths,
            patient_id,
            notes,
            config_path=self.config_path,
            delete_files=delete_files,
            parent=self,
        )

        return super().accept()
