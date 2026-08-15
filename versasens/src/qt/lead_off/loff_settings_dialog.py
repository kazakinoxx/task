"""Dialog for reading and changing the device's lead-off comparator threshold."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.utils.constants import (
    LOFF_CFG_STATUS_TEXT,
    LOFF_THRESHOLDS,
)
from src.versa.ble import ble_get_loff_config, ble_set_loff_config

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from PySide6.QtWidgets import QWidget

    from src.versa.ble import LeadOffConfig

_EXPLANATION = (
    "The comparator trip point, as a percentage of the supply. Lower "
    "percentages flag a poor contact sooner; 95% / 5% is the least sensitive "
    "and is what the device powers on with.\n\n"
    "The device only applies this while it is idle. The setting survives "
    "recordings but resets when the device is power-cycled."
)


class LeadOffSettingsDialog(QDialog):
    """Read and change the lead-off comparator threshold over BLE."""

    def __init__(self, address: str, parent: QWidget | None = None) -> None:
        """
        Create the lead-off settings dialog.

        Args:
            address: The BLE address of the device to configure.
            parent: The parent widget. Defaults to None.

        """
        super().__init__(parent)
        self._address = address
        self._task: asyncio.Task | None = None

        self.setWindowTitle("Lead-Off Settings")
        self.resize(420, 240)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.threshold_box = QComboBox(self)
        for value, label in LOFF_THRESHOLDS:
            self.threshold_box.addItem(label, value)
        form.addRow("Comparator threshold", self.threshold_box)
        layout.addLayout(form)

        explanation = QLabel(_EXPLANATION, self)
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(self)
        self.read_button = QPushButton("Read from device", self)
        self.apply_button = QPushButton("Apply", self)
        buttons.addButton(self.read_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(self.apply_button, QDialogButtonBox.ButtonRole.ApplyRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.read_button.clicked.connect(self._start_read)
        self.apply_button.clicked.connect(self._start_apply)

        # Never trust a remembered value: ask the device what it is running.
        self._start_read()

    # ================================== Helpers ===================================

    def _set_busy(self, *, busy: bool, message: str = "") -> None:
        self.read_button.setEnabled(not busy)
        self.apply_button.setEnabled(not busy)
        self.threshold_box.setEnabled(not busy)
        if message:
            self.status_label.setText(message)

    def _show_result(self, config: LeadOffConfig | None, action: str) -> None:
        if config is None:
            self.status_label.setText(
                f"Could not {action}. Make sure the device is powered on, not "
                "streaming, and in range.",
            )
            return

        # The reply always carries what the device is really running, including
        # on the error paths, so resync the selector either way.
        index = self.threshold_box.findData(config.comp_th)
        if index >= 0:
            self.threshold_box.setCurrentIndex(index)

        if config.ok:
            label = self.threshold_box.currentText()
            register = f"0x{config.raw_register:02x}"
            self.status_label.setText(
                f"Device is running {label} (LOFF register {register}).",
            )
        else:
            reason = LOFF_CFG_STATUS_TEXT.get(
                config.status,
                f"Unknown status {config.status}.",
            )
            self.status_label.setText(f"Not applied. {reason}")

    def _start_task(
        self,
        coro: Coroutine[Any, Any, LeadOffConfig | None],
        action: str,
    ) -> None:
        if self._task is not None and not self._task.done():
            coro.close()
            return

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Constructed outside the Qt async loop. Do not fail: the dialog is
            # still usable, the user just has to trigger the read themselves
            # once the loop is running.
            coro.close()
            self.status_label.setText(
                'Press "Read from device" to load the current setting.',
            )
            return

        self._set_busy(busy=True, message=f"Waiting for the device to {action}...")

        async def _run() -> None:
            try:
                config = await coro
            finally:
                self._set_busy(busy=False)
            self._show_result(config, action)

        self._task = asyncio.create_task(_run())

    # ================================== Actions ===================================

    def _start_read(self) -> None:
        self._start_task(ble_get_loff_config(self._address), "report its settings")

    def _start_apply(self) -> None:
        comp_th = self.threshold_box.currentData()
        self._start_task(
            ble_set_loff_config(self._address, comp_th),
            "apply the setting",
        )
