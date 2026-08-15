"""File containing the data import dialog."""

from pathlib import Path

from PySide6 import QtCore
from PySide6.QtWidgets import QDialog, QWidget

from src.generated.ui.utils.data_import_dialog import Ui_DataImportDialog
from src.utils.logger import logger
from src.utils.typedefs import DeleteFiles, DryRun
from src.versa.process import ParseConfig, parse_and_save_files
from src.versa.raw_data import RawData


class ParseWorker(QtCore.QObject):
    """Worker used to parse files and provide GUI updates."""

    finished = QtCore.Signal()

    set_raw_file_path = QtCore.Signal(Path)
    set_raw_data = QtCore.Signal(object)
    finished_parsing_file = QtCore.Signal()

    def __init__(  # noqa: PLR0913
        self,
        files: list[Path],
        subject_id: str,
        notes: str,
        config_path: Path,
        delete_files: DeleteFiles,
        dry_run: DryRun,
        lead_off: dict[str, int] | None = None,
    ) -> None:
        """
        Create a new worker to parse files asyncronously.

        Args:
            files: The list of raw files to parse.
            subject_id: The ID of the subject.
            notes: The notes given by the user.
            config_path: The path to the config file.
            delete_files: Whether to delete the raw files.
            dry_run: Whether to simulate disk writes.
            lead_off: The device's lead-off configuration at recording time.
                      Defaults to None when it is unknown.

        """
        super().__init__()
        self.files = files
        self.subject_id = subject_id
        self.notes = notes

        self.config_path = config_path
        self.delete_files = delete_files
        self.dry_run = dry_run
        self.lead_off = lead_off

    def run(self) -> None:
        """Run the parse worker."""
        callbacks = ParseConfig.Callbacks(
            set_raw_file_path=self.set_raw_file_path.emit,
            set_raw_data=self.set_raw_data.emit,
            finished_parsing_file=self.finished_parsing_file.emit,
        )

        parse_config = ParseConfig(
            config_path=self.config_path,
            delete_raw_files=self.delete_files,
            dry_run=self.dry_run,
            callbacks=callbacks,
            lead_off=self.lead_off,
        )

        parse_and_save_files(
            self.files,
            self.subject_id,
            self.notes,
            parse_config,
        )

        self.finished.emit()


class DataImportDialog(QDialog, Ui_DataImportDialog):
    """Dialog used when importing data to show progress."""

    def __init__(  # noqa: PLR0913
        self,
        files: list[Path],
        subject_id: str,
        notes: str,
        config_path: Path,
        delete_files: DeleteFiles = DeleteFiles.NO,
        dry_run: DryRun = DryRun.WRITE,
        parent: QWidget | None = None,
        lead_off: dict[str, int] | None = None,
    ) -> None:
        """
        Create a new data import dialog.

        Args:
            files: The list of file paths to import.
            subject_id: The ID of the subject.
            notes: The notes given by the user for the import.
            config_path: The path to the config file.
            delete_files: Whether to delete the raw files after import.
                          Defaults to DeleteFiles.NO.
            dry_run: Whether to write to the database or to simulate the writes.
                     Defaults to DryRun.WRITE.
            parent: The parent of this dialog. Defaults to None.
            lead_off: The device's lead-off configuration at recording time,
                      stored with the import metadata. Defaults to None when it
                      is unknown, e.g. when importing files from disk.

        """
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        # Store args
        self.config_path = config_path
        self.files = files
        self.subject_id = subject_id
        self.notes = notes
        self.delete_files = delete_files
        self.dry_run = dry_run
        self.lead_off = lead_off

        self.file_timer = QtCore.QTimer()
        self.raw_data: RawData | None = None

        self.cur_file_bar.setMaximum(0)
        self.cur_file_bar.setValue(0)

        # Remove close button
        self.setWindowFlags(
            self.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint,
        )

    def show(self, /) -> None:
        """Show the dialog window."""
        super().show()
        QtCore.QCoreApplication.processEvents()

    def _set_raw_file_path(self, file_path: Path) -> None:
        # Change label
        self.cur_file_label.setText(file_path.name)

        # Setup current file progress bar
        self.cur_file_bar.setMaximum(file_path.stat().st_size)
        self.cur_file_bar.setValue(0)
        self.cur_file_bar_label.setText("0.00%")

    def _set_raw_data(self, raw_data: RawData) -> None:
        # Setup timer to update progress bar
        self.file_timer = QtCore.QTimer()

        self.raw_data = raw_data
        self.file_timer.timeout.connect(self._update_raw_file_progress_bar)

        self.file_timer.start(1000)

    def _update_raw_file_progress_bar(self) -> None:
        if self.raw_data is None:
            msg = "Updating progress bar but no raw data set"
            raise ValueError(msg)

        cur_pos = self.raw_data.tell()
        self.cur_file_bar.setValue(cur_pos)

        # Manually update text
        progress_percentage = (cur_pos / self.cur_file_bar.maximum()) * 100.0
        self.cur_file_bar_label.setText(f"{progress_percentage:.2f}%")

    def _finished_parsing_file(self) -> None:
        # Advance file progress bar
        self.files_bar.setValue(self.files_bar.value() + 1)
        self.cur_file_bar.setValue(self.cur_file_bar.maximum())

        # Stop timer
        if self.file_timer is None:
            raise ValueError

        self.file_timer.stop()

        # Reset variables
        self.file_timer = None
        self.raw_data = None

    def process_and_save(
        self,
        subject_id: str,
        notes: str,
        delete_files: DeleteFiles = DeleteFiles.NO,
        dry_run: DryRun = DryRun.WRITE,
    ) -> None:
        """
        Process the raw files and saves them.

        Args:
            subject_id: The ID of the subject.
            notes: The notes given by the user.
            delete_files: Whether to delete the raw files that were imported.
            dry_run: Whether to save the files.

        """
        # Setup progress bars
        self.files_bar.setMaximum(len(self.files))
        self.files_bar.setValue(0)

        # Setup thread
        self.parse_thread = QtCore.QThread()
        self.parse_worker = ParseWorker(
            self.files,
            subject_id,
            notes,
            self.config_path,
            delete_files,
            dry_run,
            lead_off=self.lead_off,
        )
        self.parse_worker.moveToThread(self.parse_thread)

        # Setup worker signals
        self.parse_worker.set_raw_file_path.connect(self._set_raw_file_path)
        self.parse_worker.set_raw_data.connect(self._set_raw_data)
        self.parse_worker.finished_parsing_file.connect(self._finished_parsing_file)

        # Setup finished thread connection
        self.parse_worker.finished.connect(self.parse_thread.quit)
        self.parse_thread.finished.connect(self.parse_thread.deleteLater)

        # Start thread
        self.parse_thread.started.connect(self.parse_worker.run)
        self.parse_thread.start()

        logger.info(
            f"Added {len(self.files)} samples",
            subject_id=subject_id,
        )

    @classmethod
    def show_and_import(  # noqa: PLR0913
        cls,
        files: list[Path],
        subject_id: str,
        notes: str,
        config_path: Path,
        delete_files: DeleteFiles = DeleteFiles.NO,
        dry_run: DryRun = DryRun.WRITE,
        parent: QWidget | None = None,
        lead_off: dict[str, int] | None = None,
    ) -> None:
        """
        Show the dialog window and imports the raw files.

        Args:
            files: The list of file paths to import.
            subject_id: The ID of the subject.
            notes: The notes given by the user for the import.
            config_path: The path to the config file.
            delete_files: Whether to delete the raw files after import.
                          Defaults to DeleteFiles.NO.
            dry_run: Whether to write to the database or to simulate the writes.
                     Defaults to DryRun.WRITE.
            parent: The parent of this dialog. Defaults to None.
            lead_off: The device's lead-off configuration at recording time,
                      stored with the import metadata. Defaults to None.

        """
        # Create dialog
        dlg = cls(
            files,
            subject_id,
            notes,
            config_path,
            delete_files=delete_files,
            dry_run=dry_run,
            parent=parent,
            lead_off=lead_off,
        )

        # Process data
        dlg.process_and_save(subject_id, notes, delete_files, dry_run)
        # Connect thread finished to dialog close
        dlg.parse_thread.finished.connect(dlg.close)

        dlg.exec()
