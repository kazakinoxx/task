"""File containing the view samples dialog."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from src.generated.ui.view_samples.imports_for_id import Ui_ImportsForIDDialog
from src.generated.ui.view_samples.main import Ui_ViewSamplesDialog
from src.qt.view_samples.view_import_dialog import ViewImportDialog
from src.utils.config import Config
from src.versa.db import get_ids_info, get_imports_of_subject


class _ImportsForIDDialog(QDialog, Ui_ImportsForIDDialog):
    """
    Shows the imports of a subject ID.

    i.e., the list of imports, the raw file names and their sensors.
    """

    # TODO: add a way to view all at once

    def __init__(
        self,
        subject_id: str,
        config_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        self.setWindowTitle(f"Samples for: {subject_id}")
        self.subject_ID.setText(subject_id)

        # Store args
        self.config_path = config_path

        # Create items for each timestamp
        imports_info = get_imports_of_subject(subject_id, self.config_path)
        imports_info = sorted(imports_info, key=lambda x: x[1], reverse=True)

        spacer = QSpacerItem(
            40,
            20,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )

        if len(imports_info) == 0:
            # Show no imports if none was found
            self.imports_layout.addItem(spacer)

            label = QLabel("No imports found for this subject ID")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.imports_layout.addWidget(label)

            self.imports_layout.addItem(spacer)

        else:
            for import_folder, timestamp, nbr_samples in imports_info:
                timestamp_str = timestamp.strftime("%d.%m.%y at %H:%M:%S")

                # Create button
                button = QPushButton(f"{timestamp_str} ({nbr_samples} samples)")
                button.setMinimumHeight(35)

                button.clicked.connect(
                    self.handle_import_button(import_folder, config_path),
                )

                self.imports_layout.addWidget(button)

            # Add spacer at the end
            self.imports_layout.addItem(spacer)

    @staticmethod
    def handle_import_button(
        import_folder: Path,
        config_path: Path,
    ) -> Callable[[], None]:
        def _fct() -> None:
            dlg = ViewImportDialog(import_folder, config_path=config_path)
            dlg.exec()

        return _fct


class ViewImportedDataDialog(QDialog, Ui_ViewSamplesDialog):
    """
    Dialog containing the list of database imports.

    It shows a list of subject IDs.
    """

    def __init__(self, config_path: Path, parent: QWidget | None = None) -> None:
        """
        Create a new dialog showing the list of subject IDs.

        Args:
            config_path: The path to the config file.
            parent: The parent of the dialog. Defaults to None.

        """
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        # Store args
        self.config_path = config_path

        self.refresh_data()

        self.refresh_button.clicked.connect(self.refresh_data)
        self.open_db_button.clicked.connect(self.open_db_button_clicked)

    def open_db_button_clicked(self) -> None:
        """Handle open db button clicks."""
        db_path = Config.get_db_path(self.config_path)

        # Open file
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(db_path.resolve())))

    def refresh_data(self) -> None:
        """Refresh the data inside the dialog."""
        # Get ids
        ids_info = get_ids_info(self.config_path)

        spacer = QSpacerItem(
            40,
            20,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )

        # Clear layout
        while self.ids_layout.count() > 0:
            self.ids_layout.takeAt(0)

        if len(ids_info) == 0:
            self.ids_layout.addItem(spacer)

            label = QLabel("No data found")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ids_layout.addWidget(label)

            self.ids_layout.addItem(spacer)

        else:
            for subject_id, nbr_imports in sorted(ids_info):
                # Create button
                widget = QPushButton(f"{subject_id}\n({nbr_imports} imports)")
                widget.setMinimumHeight(35)

                widget.clicked.connect(self.handle_subject_id_button(subject_id))

                self.ids_layout.addWidget(widget)

            # Add spacer at the end
            self.ids_layout.addItem(spacer)

    def handle_subject_id_button(self, subject_id: str) -> Callable[[], None]:
        """Handle subject ID button presses."""

        def _fct() -> None:
            dlg = _ImportsForIDDialog(subject_id, self.config_path)
            dlg.exec()

        return _fct
