"""File containing the add stream dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget

from src.generated.ui.stream.add_stream_dialog import Ui_AddStreamDialog


class AddStreamDialog(QDialog, Ui_AddStreamDialog):
    """Dialog shown when adding the data saved during streaming."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Create a new dialog to save the data obtained during streaming.

        Args:
            parent: The parent of this dialog. Defaults to None.

        """
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        # Connect button box
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    @classmethod
    def ask_subject_id_and_notes(cls) -> tuple[str, str] | None:
        """
        Create a new dialog and ask the user to input a subject ID and notes.

        Returns:
            The (subject ID, notes) tuple or None if refused to save data.

        """
        dlg = cls()
        button_add = dlg.exec()

        # Check if clicked accept
        if button_add:
            subject_id = dlg.patient_input.text()
            notes = dlg.notes_input.toPlainText()

            return subject_id, notes

        return None
