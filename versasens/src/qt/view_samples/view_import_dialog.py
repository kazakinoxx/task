"""File containing the view import dialog."""

from collections.abc import Callable
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtWidgets import (
    QDialog,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.generated.sensors_info import SENSOR_CLASSES
from src.generated.ui.view_samples.subitem import Ui_SamplesListSubitem
from src.generated.ui.view_samples.view_import import Ui_ViewImportDialog
from src.qt.utils.loading_dialog import LoadingDialog
from src.qt.utils.plot_dialog import PlotDialog
from src.utils.typedefs import SensorCSVPath, SensorName, ShouldUpdateGraph
from src.versa.db import get_data_for_sensor, get_import_data


class _SamplesListSubitem(QWidget, Ui_SamplesListSubitem):
    def __init__(
        self,
        filename: str,
        sensor_to_paths: dict[SensorName, list[SensorCSVPath]],
        config_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setupUi(self)

        # Add sensor buttons
        self.buttons: dict[str, QPushButton] = {}

        for sens_class in SENSOR_CLASSES:
            button = QPushButton(self.widget)
            button.setText(sens_class.attr_name().upper())
            button.setObjectName(sens_class.attr_name())
            button.setEnabled(True)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            # Fit width to text
            fm = button.fontMetrics()
            padding = 16  # adjust to taste
            button.setFixedWidth(fm.horizontalAdvance(button.text()) + padding)

            self.buttons_layout.addWidget(button)
            self.buttons[sens_class.attr_name()] = button

        self.config_path = config_path

        # Set buttons hidden as default
        for button in self.buttons.values():
            button.setVisible(False)

        # Setup button clicked and visible
        for sensor_name, paths in sensor_to_paths.items():
            self.buttons[sensor_name].clicked.connect(
                self.button_handler(sensor_name, paths),
            )
            self.buttons[sensor_name].setVisible(True)

        # Show no data label if needed
        self.label.setVisible(len(sensor_to_paths) == 0)

        # File name
        self.index_label.setText(filename)

    def button_handler(self, sensor_name: str, paths: list[Path]) -> Callable[[], None]:
        """
        Get the handler for the presses of a sensor's button.

        Args:
            sensor_name: The name of the sensor.
            paths: The paths to the files of the sensor.

        Returns:
            The handler.

        """

        def _fct() -> None:
            # Add loading
            load_dlg = LoadingDialog(
                self,
                message=f"Loading data for {sensor_name.upper()}...",
            )
            load_dlg.show()
            QtCore.QCoreApplication.processEvents()

            sensor = get_data_for_sensor(sensor_name, paths)
            dlg = PlotDialog(
                sensor,
                should_update=ShouldUpdateGraph.NO,
                config_path=self.config_path,
            )
            dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            dlg.exec()

            load_dlg.hide()

        return _fct


class ViewImportDialog(QDialog, Ui_ViewImportDialog):
    """
    Dialog containing the list of samples in the database.

    It shows a list of subject IDs.
    """

    def __init__(
        self,
        import_folder: Path,
        config_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create a new dialog to view the data of a given import folder.

        Args:
            import_folder: The import folder to view.
            config_path: Path to the config file.
            parent: The parent of the dialog. Defaults to None.

        """
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        # Get data from DB
        metadata, sample_to_sensor_to_files = get_import_data(import_folder)

        # Set labels from metadata
        subject_id = metadata.subject_id
        self.id_label.setText(subject_id)

        notes = metadata.notes
        self.notes_text.setText(notes)

        timestamp = metadata.timestamp
        timestamp_str = timestamp.strftime("%d.%m.%y at %H:%M:%S")
        self.timestamp_label.setText(timestamp_str)

        # Add the list of sample files
        for filename, sensor_to_files in sample_to_sensor_to_files.items():
            # Create the widget
            widget = _SamplesListSubitem(
                filename, sensor_to_files, config_path=config_path,
            )

            # Create the list item
            item = QListWidgetItem(self.samples_list)
            item.setSizeHint(widget.sizeHint())

            # Add item to the list
            self.samples_list.addItem(item)
            self.samples_list.setItemWidget(item, widget)
            self.samples_list.setItemWidget(item, widget)
