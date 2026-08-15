"""File containing the view stream dialog."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, override

from bleak import BleakClient

from src.generated.sensors_info import SENSOR_CLASSES
from src.qt.utils.data_import_dialog import DataImportDialog
from src.utils.config import Config
from src.utils.constants import (
    BLE_CMD_CHARACTERISTIC_UUID,
    BLE_CMD_LEAD_OFF_CHECK,
    BLE_CMD_LEAD_OFF_CHECK_LIVE,
    BLE_CONNECTION_TIMEOUT,
    BLE_FIND_DEVICES_TIMEOUT,
    BLE_LEAD_OFF_CHECK_TIMEOUT,
    BLE_MAX_CONNECTION_ATTEMPTS,
)
from src.versa.raw_data import RawData, WriteLocation

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

    from src.versa.sensor import Sensor

import contextlib

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.generated.ui.stream.stream_dialog import Ui_StreamDialog
from src.qt.lead_off.lead_off_dialog import LeadOffDialog
from src.qt.lead_off.loff_settings_dialog import LeadOffSettingsDialog
from src.qt.stream.add_stream_dialog import AddStreamDialog
from src.qt.utils.loading_dialog import LoadingDialog, loading_dialog
from src.qt.utils.plot_dialog import PlotDialog
from src.utils.logger import logger
from src.utils.typedefs import ClearSensorDataOnClose, DeleteFiles, ShouldUpdateGraph
from src.versa.ble import (
    BLEStreamConfig,
    ble_get_loff_config,
    ble_run_lead_off_check,
    ble_start_stream,
    find_versasens_ble_devices,
)
from src.versa.sensor_group import SENSOR_ATTR_NAMES, SensorGroup
from src.versa.sensors.ads import ADS


class StreamDialog(QDialog, Ui_StreamDialog):
    """Dialog containing the device stream."""

    def __init__(  # noqa: PLR0915
        self,
        config_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create a new dialog to stream data from the VersaSens device.

            config_path: Alternative path to the config file
            parent: The parent of this dialog. Defaults to None.
            hello: test

        """
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        # Setup sensor buttons
        self.sensor_name_to_widgets: dict[str, tuple[QLabel, QPushButton]] = {}

        # Add sensor labels and buttons
        size_policy_label = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        size_policy_label.setHorizontalStretch(0)
        size_policy_label.setVerticalStretch(0)

        size_policy_plot_button = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        size_policy_plot_button.setHorizontalStretch(0)
        size_policy_plot_button.setVerticalStretch(0)

        for i, sens_class in enumerate(SENSOR_CLASSES):
            # Label
            label = QLabel(self.main_layout)
            label.setObjectName(f"{sens_class.attr_name()}_label")
            label.setText(sens_class.name())
            label.setEnabled(False)

            size_policy_label.setHeightForWidth(label.sizePolicy().hasHeightForWidth())
            label.setSizePolicy(size_policy_label)

            self.gridLayout.addWidget(label, i, 0, 1, 1)

            # Plot button
            plot_button = QPushButton(self.main_layout)
            plot_button.setText("Show plot")
            plot_button.setObjectName(f"{sens_class.attr_name()}_button")
            plot_button.setEnabled(False)

            size_policy_plot_button.setHeightForWidth(
                plot_button.sizePolicy().hasHeightForWidth(),
            )
            plot_button.setSizePolicy(size_policy_plot_button)

            self.gridLayout.addWidget(plot_button, i, 1, 1, 1)

            # Add to sensor_name_to_widgets
            self.sensor_name_to_widgets[sens_class.attr_name()] = (label, plot_button)

        # Store args
        self.config_path = config_path

        # Initialize tasks
        self.refresh_devices_task: asyncio.Task | None = None
        self.start_stream_task: asyncio.Task | None = None
        self.check_task: asyncio.Task | None = None

        # Lead-off configuration read from the device when the session started,
        # stored with the recording's metadata. None when it could not be read.
        self.lead_off_config: dict[str, int] | None = None

        # Live streaming connection, exposed so a lead-off check can run over it
        # mid-recording (the device allows a single central). None when not
        # streaming. Command-characteristic replies land in the queue.
        self._stream_client: BleakClient | None = None
        self._cmd_result_queue: asyncio.Queue[bytearray] = asyncio.Queue()

        # Initialize events
        self.stop_event = asyncio.Event()
        self.device_disconnected_event = asyncio.Event()
        # Set while the device is currently connected and streaming
        self.is_running_event = asyncio.Event()
        # Set for the whole streaming session, including reconnection attempts.
        # Used to gate UI actions (close, refresh, device change) so that an
        # ongoing reconnection is treated as an active session.
        self.stream_active_event = asyncio.Event()

        # Initialize variables
        self.devices: list[BLEDevice] = []
        self.ending_stream = False
        self._reconnect_attempt = 0

        # Disable stream buttons at first
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        # Setup refresh button to find devices and find devices
        self.refresh_button.clicked.connect(self._start_refresh_devices_task)
        self._start_refresh_devices_task()

        # Connect function to detect device selection changes
        self.device_box.currentIndexChanged.connect(self._handle_device_box_change)

        # Set data variables
        self.data = SensorGroup()
        self.raw_data = RawData(WriteLocation.TO_DISK, config_path=self.config_path)
        # Manually open the file
        self.raw_data.open()

        # Setup start and stop buttons
        self.start_button.clicked.connect(self._create_start_stream_task)
        self.stop_button.clicked.connect(self._handle_stop_stream_button)

        # Lead-off status button: opens the live electrode-contact head diagram.
        self._setup_lead_off_button()

        # Setup dict for found sensors
        self.found_sensors = dict.fromkeys(SENSOR_ATTR_NAMES, False)

        # Setup event called when stopping the streaming by closing the window
        self.close_stream_stop_event: asyncio.Event | None = None

        # Setup button handlers
        for name, (_, button) in self.sensor_name_to_widgets.items():
            button.clicked.connect(self._get_plot_button_handler(name))

        # Setup dict to tell if device is currently plotting
        self.sensor_name_to_plotting: dict[str, bool] = dict.fromkeys(
            SENSOR_ATTR_NAMES,
            False,
        )

    # ===================================== Events =====================================

    def _reset_events(self) -> None:
        self.device_disconnected_event.clear()
        self.is_running_event.clear()

    # ================================== Utils tasks ===================================

    def _handle_task_exception(self, task: asyncio.Task) -> None:
        """Handle exceptions from tasks."""
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:  # noqa: BLE001
            logger.exception("Task failed", exc=e)
            QMessageBox.critical(
                self,
                "Error",
                f"Task failed: {e}",
            )

    # ================================ Refresh devices =================================

    def _start_refresh_devices_task(self) -> None:
        """Start task to refresh the list of devices."""
        # Ignore if task already running
        if (
            self.refresh_devices_task is not None
            and not self.refresh_devices_task.done()
        ):
            return

        self.refresh_devices_task = asyncio.create_task(self._refresh_devices())
        self.refresh_devices_task.add_done_callback(self._handle_task_exception)

    async def _refresh_devices(self) -> None:
        """Refresh the list of available Bluetooth devices."""
        if self.stream_active_event.is_set():
            logger.warning(
                "A streaming session is active. Ignoring refresh of devices.",
            )
            return

        # Add loading dialog
        with loading_dialog(
            self,
            "Loading Bluetooth devices...",
            expected_time_s=BLE_FIND_DEVICES_TIMEOUT,
        ):
            # Disable close button
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, on=False)
            self.show()

            # Find devices
            self.devices = await find_versasens_ble_devices()

            # Update device combo box
            self.device_box.clear()

            for d in self.devices:
                # Find name for device
                text = d.address if d.name is None else f"{d.name} ({d.address})"

                self.device_box.addItem(text)

        # Re-enable close button
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, on=True)
        self.show()

        # If found devices, select first one
        if len(self.devices) > 0:
            self.device_box.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Warning", "No devices found")

    # ================================ Device selection ================================

    def _handle_device_box_change(self) -> None:
        """Handle the selection of devices."""
        if self.stream_active_event.is_set():
            logger.warning(
                "A streaming session is active. Ignoring device box change.",
            )
            return

        # Enable the start button only if a device is selected
        self.start_button.setEnabled(self.device_box.currentIndex() != -1)

    # ===================================== Plots ======================================

    def _get_plot_button_handler(self, sensor_name: str) -> Callable[[], None]:
        """
        Get the handler to show the plot corresponding to the given sensor.

        Args:
            sensor_name: The name of the sensor.

        Returns:
            The button handler function.

        """

        def _set_sensor_plotting(plotting: bool) -> None:  # noqa: FBT001
            self.sensor_name_to_plotting[sensor_name] = plotting
            logger.debug("Setting plotting", plotting=plotting, name=sensor_name)

        # Currying to pass name
        def _handler() -> None:
            logger.info("Opening plot window", name=sensor_name)

            # Get sensor
            sensor: Sensor = getattr(self.data, sensor_name.lower())

            # Show plot
            dlg = PlotDialog(
                sensor,
                parent=self,
                set_is_open=_set_sensor_plotting,
                should_update=ShouldUpdateGraph.YES,
                clear_sensor_data_on_close=ClearSensorDataOnClose.YES,
                config_path=self.config_path,
            )
            dlg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
            dlg.show()

        return _handler

    def _show_plot_button_for_sensor(self, sensor_name: str) -> None:
        """
        Show the plot buttons when a new sensor was found.

        Args:
            sensor_name: The name of the sensor.

        """
        # Check that the sensor's name is known
        if sensor_name not in self.found_sensors:
            logger.error("Unknown sensor name", sensor_name=sensor_name)
            return

        # Show button when the sensor is found
        if not self.found_sensors[sensor_name]:
            logger.info("Received data from new sensor", sensor_name=sensor_name)
            self.found_sensors[sensor_name] = True

            label, plot_button = self.sensor_name_to_widgets[sensor_name]
            label.setEnabled(True)
            plot_button.setEnabled(True)

    # ================================== Close window ==================================

    def _ask_to_save_data(self) -> bool:
        """
        Ask whether to save the streamed data.

        Returns:
            True if the data needs to be saved.

        """
        # Ask to save data
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Streamed data collected")
        dlg.setText("Save streamed data to disk?")
        dlg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        dlg.setIcon(QMessageBox.Icon.Question)
        button = dlg.exec()

        return button == QMessageBox.StandardButton.Yes

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        # Save data if some was stored
        if self.raw_data.has_data() and self._ask_to_save_data():
            self._parse_data_and_save()

        # Stop stream if a streaming session is currently active
        if self.stream_active_event.is_set():
            self._handle_stop_stream_button()
            self._schedule_close(event)
        else:
            self._finalize_close(event)

    def _schedule_close(self, event: QCloseEvent) -> None:
        """Schedule window close after the stream task finishes."""
        try:
            loop = asyncio.get_running_loop()
            self.close_task = loop.create_task(self._wait_and_close(event))
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to schedule close", exc=e)
            self._finalize_close(event)

    async def _wait_and_close(self, event: QCloseEvent) -> None:
        """Wait for the stream task to finish, then close the window."""
        task = self.start_stream_task
        if task is not None and not task.done():
            # CancelledError (BaseException) still propagates; task errors are
            # already surfaced by the task's done callback.
            with contextlib.suppress(Exception):
                await task
        self._finalize_close(event)

    def _finalize_close(self, event: QCloseEvent) -> None:
        """Perform final cleanup and close the window."""
        self.stream_active_event.clear()
        self.is_running_event.clear()

        # Ignore issues when closing after the fact
        with contextlib.suppress(Exception):
            self.raw_data.close()
            super().closeEvent(event)

    # =================================== End stream ===================================

    def _parse_data_and_save(self) -> None:
        # Parse the data
        logger.debug("Parsing streamed data")

        # Check if some data was saved
        if not self.raw_data.has_data():
            # Otherwise tell the user and exit
            msg = "No data was received"
            logger.warning(msg)
            QMessageBox.warning(self, "Warning", msg)
            return

        # Ask if want to save the data
        add_res = AddStreamDialog.ask_subject_id_and_notes()

        if add_res is None:
            logger.info("Streaming data not saved")
            return

        subject_id, notes = add_res

        # TODO: make sure that writes and reads are blocked from RawData during this

        DataImportDialog.show_and_import(
            [self.raw_data.get_file_path()],
            subject_id,
            notes,
            config_path=self.config_path,
            delete_files=DeleteFiles.NO,
            parent=self,
            lead_off=self.lead_off_config,
        )

    def end_streaming(self, exception: Exception | None) -> None:
        """
        End the streaming of data.

        Args:
            exception: The exception if it was thrown

        """
        if not self.stream_active_event.is_set() or self.ending_stream:
            # Ignore if no streaming session is active
            return

        # Block multiple executions of end_streaming just in case
        self.ending_stream = True
        logger.debug("Ending stream")

        # Reset inputs
        self.device_box.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        self.stop_button.setDown(False)

        # Reset found sensors
        self.found_sensors = {s.lower(): False for s in SENSOR_ATTR_NAMES}
        for s in self.found_sensors:
            label, plot_button = self.sensor_name_to_widgets[s]
            label.setEnabled(False)
            plot_button.setEnabled(False)

        # Check for exceptions
        if exception is not None:
            address = self.devices[self.device_box.currentIndex()].address

            # There was an error
            QMessageBox.critical(
                self,
                "Error",
                f"Error connecting to the BLE device ({address=})\nReason: {exception}",
            )

        # Parse the data and save if needed
        self._parse_data_and_save()

        # Reset data variables
        self.data = SensorGroup()
        self.raw_data.close()
        self.raw_data = RawData(WriteLocation.TO_DISK, config_path=self.config_path)
        # Manually open the file
        self.raw_data.open()

        # Reset events
        self._reset_events()

        # Mark the streaming session as inactive
        self.stream_active_event.clear()
        self.ending_stream = False

    # ================================== Lead-off ======================================

    def _setup_lead_off_button(self) -> None:
        """Create the lead-off buttons next to the start/stop buttons."""
        self.lead_off_button = QPushButton(self.stream_buttons)
        self.lead_off_button.setObjectName("lead_off_button")
        self.lead_off_button.setText("Lead-off status")
        self.horizontalLayout_5.addWidget(self.lead_off_button)
        self.lead_off_button.clicked.connect(self._open_lead_off_dialog)

        # Pre-recording one-shot electrode check (accurate RLD, device idle).
        self.check_electrodes_button = QPushButton(self.stream_buttons)
        self.check_electrodes_button.setObjectName("check_electrodes_button")
        self.check_electrodes_button.setText("Check electrodes")
        self.horizontalLayout_5.addWidget(self.check_electrodes_button)
        self.check_electrodes_button.clicked.connect(self._create_check_task)

        # Lead-off comparator threshold, applied while the device is idle.
        self.loff_settings_button = QPushButton(self.stream_buttons)
        self.loff_settings_button.setObjectName("loff_settings_button")
        self.loff_settings_button.setText("Lead-off settings")
        self.horizontalLayout_5.addWidget(self.loff_settings_button)
        self.loff_settings_button.clicked.connect(self._open_loff_settings_dialog)

    def _open_loff_settings_dialog(self) -> None:
        """Open the lead-off threshold dialog, if the device is reachable and idle."""
        if self.stream_active_event.is_set():
            QMessageBox.information(
                self,
                "Lead-off settings",
                "Stop streaming before changing the lead-off settings.",
            )
            return

        if self.device_box.currentIndex() == -1 or len(self.devices) == 0:
            QMessageBox.warning(self, "Lead-off settings", "No device selected.")
            return

        address = self.devices[self.device_box.currentIndex()].address
        dlg = LeadOffSettingsDialog(address, parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dlg.show()

    def _open_lead_off_dialog(self) -> None:
        """Open the live lead-off status view bound to the current ADS sensor."""
        dlg = LeadOffDialog(lambda: getattr(self.data, "ads", None), parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dlg.show()

    def _create_check_task(self) -> None:
        """Start the pre-recording electrode-check task (ignored if one is running)."""
        if self.check_task is not None and not self.check_task.done():
            return
        self.check_task = asyncio.create_task(self._run_electrode_check())
        self.check_task.add_done_callback(self._handle_task_exception)

    async def _live_electrode_check(self) -> tuple[int, int, int] | None:
        """
        Run a lead-off check over the active streaming connection (0x13).

        Returns the (statp, statn, rld) tuple, or None on timeout/error.
        """
        client = self._stream_client
        if client is None or not client.is_connected:
            return None

        # Drop any stale replies before issuing the request.
        while not self._cmd_result_queue.empty():
            self._cmd_result_queue.get_nowait()

        result_len = 4
        await client.write_gatt_char(
            BLE_CMD_CHARACTERISTIC_UUID,
            bytes([BLE_CMD_LEAD_OFF_CHECK_LIVE]),
            response=True,
        )

        deadline = asyncio.get_running_loop().time() + BLE_LEAD_OFF_CHECK_TIMEOUT
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return None
            try:
                data = await asyncio.wait_for(
                    self._cmd_result_queue.get(),
                    timeout=remaining,
                )
            except TimeoutError:
                return None
            # The device tags the live result with the same header as 0x10.
            if len(data) == result_len and data[0] == BLE_CMD_LEAD_OFF_CHECK:
                return (data[1], data[2], data[3])

    async def _run_electrode_check(self) -> None:
        """
        Run a lead-off check and show the result.

        While streaming, the check runs over the live connection (0x13), briefly
        connecting the lead-off resistors and marking the perturbed window. While
        idle, it opens its own connection and does the accurate RLD check (0x10).
        """
        streaming = self.stream_active_event.is_set()

        if not streaming and (
            self.device_box.currentIndex() == -1 or len(self.devices) == 0
        ):
            QMessageBox.warning(self, "Electrode check", "No device selected.")
            return

        # NB: no loading_dialog here on purpose. Its progress-bar timer re-enters
        # the QtAsyncio loop during the await and can crash; a button-text change
        # is enough feedback for this short operation.
        self.check_electrodes_button.setEnabled(False)
        self.check_electrodes_button.setText("Checking...")
        try:
            if streaming:
                result = await self._live_electrode_check()
            else:
                address = self.devices[self.device_box.currentIndex()].address
                result = await ble_run_lead_off_check(address)
        finally:
            self.check_electrodes_button.setText("Check electrodes")
            self.check_electrodes_button.setEnabled(True)

        if result is None:
            QMessageBox.warning(
                self,
                "Electrode check",
                "Could not reach the device. Make sure it is powered on and "
                "connected, then try again."
                if streaming
                else "Could not reach the device. Make sure it is powered on, not "
                "currently streaming, and advertising, then try again.",
            )
            return

        statp, statn, rld = result
        # Pack into the same byte layout the live path uses: bit0 = shared
        # negative, bit1 = RLD.
        stat_x = (statn & 0x01) | ((rld & 0x01) << 1)
        status = ADS.decode_lead_off(statp, stat_x)

        # Reuse the existing result window if one is open (so repeated checks
        # update in place instead of stacking new windows); otherwise create it.
        dlg = getattr(self, "_check_result_dlg", None)
        if dlg is not None and dlg.isVisible():
            dlg.update_snapshot(status)
        else:
            dlg = LeadOffDialog(snapshot=status, parent=self)
            dlg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
            self._check_result_dlg = dlg
            dlg.show()

        # Bring it to the front so the (updated) result is clearly shown.
        dlg.raise_()
        dlg.activateWindow()

    # ================================== Start stream ==================================

    async def _reconnect_delay(self) -> None:
        """
        Wait before a reconnection attempt with exponential backoff.

        Interruptible: returns early once ``stop_event`` is set so a stop
        request is not delayed by the backoff.
        """
        delay = min(2 ** (self._reconnect_attempt - 1), 8)
        logger.debug("Waiting before reconnecting", delay_s=delay)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self.stop_event.wait(), timeout=delay)

    async def _attempt_connection(self, address: str) -> Exception | None:
        """
        Run a single connection attempt and stream until it ends.

        Args:
            address: The BLE address of the device to connect to.

        Returns:
            The exception raised during the attempt, if any.

        """
        # Prepare loading dialog
        if self._reconnect_attempt == 0:
            msg = "Connecting to VersaSens device..."
        else:
            msg = (
                "Connection lost, reconnecting... "
                f"(attempt {self._reconnect_attempt}/{BLE_MAX_CONNECTION_ATTEMPTS})"
            )

        logger.info(msg)

        load_dlg = LoadingDialog(self, msg, expected_time_s=BLE_CONNECTION_TIMEOUT)
        load_dlg.show()

        def _connected_callback(dlg: LoadingDialog = load_dlg) -> None:
            # Close loading dialog when connected
            dlg.close()
            dlg.deleteLater()
            self.is_running_event.set()
            self._reconnect_attempt = 0

        def _connection_error_callback(dlg: LoadingDialog = load_dlg) -> None:
            # Close the loading dialog. A consolidated error (if any) is
            # shown by end_streaming once reconnection attempts are
            # exhausted, instead of a modal popup per failed attempt.
            dlg.close()
            logger.warning("BLE connection error during attempt")

        def _client_ready(client: BleakClient) -> None:
            # Exposed so a lead-off check can be sent over the live connection.
            self._stream_client = client

        def _command_result(data: bytearray) -> None:
            self._cmd_result_queue.put_nowait(data)

        # Setup stream config
        config = BLEStreamConfig(
            should_process_data_of_sensor=self.sensor_name_to_plotting,
            stop_event=self.stop_event,
            device_disconnected_event=self.device_disconnected_event,
            connected_callback=_connected_callback,
            error_callback=_connection_error_callback,
            found_sensor_callback=self._show_plot_button_for_sensor,
            sensor_parse_config=Config.get_sensor_parse_config(self.config_path),
            client_ready_callback=_client_ready,
            command_result_callback=_command_result,
        )

        # Start stream and wait for it to be finished
        try:
            return await ble_start_stream(address, self.data, self.raw_data, config)
        finally:
            # The client object is gone once ble_start_stream's context exits.
            self._stream_client = None

    def _create_start_stream_task(self) -> None:
        """Start task to refresh the list of devices."""
        # Ignore if task already running
        if self.start_stream_task is not None and not self.start_stream_task.done():
            return

        self.start_stream_task = asyncio.create_task(self._start_stream())
        self.start_stream_task.add_done_callback(self._handle_task_exception)

    async def _start_stream(self) -> None:
        """Start a streaming session."""
        # Ensure that devices were found
        if len(self.devices) == 0:
            msg = "No devices were found. Cannot start stream."
            logger.warning(msg)
            QMessageBox.critical(self, "Error", msg)
            return

        # Verify that device is selected and not already running
        if self.device_box.currentIndex() == -1:
            msg = "No device was selected. Cannot start stream."
            logger.warning(msg)
            QMessageBox.critical(self, "Error", msg)
            return

        # Ignore start if a streaming session is already active
        if self.stream_active_event.is_set():
            logger.warning(
                "A streaming session is already active. Ignoring stream start.",
            )
            return

        # Disable inputs
        self.device_box.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.start_button.setEnabled(False)

        # Enable stop button
        self.stop_button.setEnabled(True)

        # Get address of device
        address = self.devices[self.device_box.currentIndex()].address

        # Record which lead-off configuration this session runs with. Read from
        # the device rather than from what the GUI last set, and read it here:
        # the device takes a single central at a time, so this has to happen
        # before the streaming connection opens.
        loff = await ble_get_loff_config(address)
        self.lead_off_config = loff.to_metadata() if loff is not None else None
        if loff is None:
            logger.warning(
                "[BLE] Could not read the lead-off config; it will be missing "
                "from this recording's metadata",
            )

        # Mark the streaming session as active (stays set across reconnects)
        self.stream_active_event.set()

        stream_exc: Exception | None = None
        self._reconnect_attempt = 0
        self.stop_event.clear()

        # Attempt to reconnect if needed (+ 1 for first connection)
        while not self.stop_event.is_set():
            # Exponential backoff before reconnecting (skipped on first attempt)
            if self._reconnect_attempt > 0:
                await self._reconnect_delay()
                if self.stop_event.is_set():
                    break

            # Reset events
            self._reset_events()

            stream_exc = await self._attempt_connection(address)

            self._reconnect_attempt += 1

            if self._reconnect_attempt >= BLE_MAX_CONNECTION_ATTEMPTS:
                self.stop_event.set()
                break

        logger.debug("Finished streaming")
        self.end_streaming(stream_exc)

    # =============================== Stop stream button ===============================

    def _handle_stop_stream_button(self) -> None:
        """Stop the stream."""
        self.stop_event.set()
        logger.debug("Disconnect event set. Stopping stream")
