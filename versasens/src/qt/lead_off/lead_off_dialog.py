"""Dialog showing the live lead-off (electrode contact) status of the headset."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, override

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.qt.lead_off.headset_widget import HeadsetStatusWidget
from src.versa.sensors.ads import LeadOffStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtGui import QCloseEvent

    from src.versa.sensors.ads import ADS

# Poll cadence and the age after which the last sample is considered stale.
_POLL_MS = 200
_STALE_S = 1.5

_GOOD = "#12a568"
_OFF = "#e0403f"
_NODATA = "#93a2ad"


class LeadOffDialog(QDialog):
    """Live view of which headset electrodes have good contact."""

    def __init__(
        self,
        get_sensor: Callable[[], ADS | None] | None = None,
        parent: QWidget | None = None,
        *,
        snapshot: LeadOffStatus | None = None,
    ) -> None:
        """
        Create the lead-off status dialog.

        Args:
            get_sensor: Callable returning the live ADS1298 sensor (or None). It is
                        called on every refresh so the dialog keeps working across
                        streaming sessions, where the sensor object is recreated.
                        Ignored when ``snapshot`` is given.
            parent: The parent widget. Defaults to None.
            snapshot: A fixed lead-off status to display once (from a pre-recording
                      electrode check) instead of polling live data. When set, the
                      dialog does not poll.

        """
        super().__init__(parent)
        self._snapshot = snapshot
        self.setWindowTitle(
            "Electrode Check" if snapshot is not None else "Lead-Off Status",
        )
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)
        self.resize(520, 640)

        self._get_sensor = get_sensor
        self._timer: QTimer | None = None
        self._last_count = -1
        self._last_change = time.monotonic()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # --- header ---
        title = QLabel("Electrode Contact — Lead-Off Status")
        title.setStyleSheet("font-size: 17px; font-weight: 600;")
        root.addWidget(title)

        subtitle_text = (
            "One-shot electrode contact check (RLD measured with drive briefly "
            "disabled). Run before starting a recording."
            if snapshot is not None
            else "Live per-electrode connection quality from the ADS1298 "
            "lead-off detector."
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {_NODATA};")
        root.addWidget(subtitle)

        # --- summary ---
        self._summary = QLabel("Waiting for data…")
        self._summary.setStyleSheet("font-size: 15px; font-weight: 600;")
        root.addWidget(self._summary)

        # --- head diagram ---
        self._headset = HeadsetStatusWidget(self)
        root.addWidget(self._headset, stretch=1)

        # --- legend ---
        root.addLayout(self._build_legend())

        # --- separator + footnote ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)

        note = QLabel(
            "Green = connected · Red = off / high impedance · Grey = no data.  "
            "Channel→scalp positions are a placeholder montage.",
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {_NODATA}; font-size: 11px;")
        root.addWidget(note)

        if self._snapshot is not None:
            # One-shot check result: display once, no polling.
            self._show_snapshot(self._snapshot)
        else:
            # --- polling timer (live view) ---
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._refresh)
            self._timer.start(_POLL_MS)
            self._refresh()

    def _show_snapshot(self, status: LeadOffStatus) -> None:
        """Display a one-shot check result and stamp it with the current time."""
        self._snapshot = status
        self._headset.set_status(status)
        self._update_summary(status, stale=False)
        # Append a timestamp so a repeated check is visibly a fresh reading,
        # even when the electrode states are identical.
        stamp = time.strftime("%H:%M:%S")
        self._summary.setText(f"{self._summary.text()}  ·  checked {stamp}")

    def update_snapshot(self, status: LeadOffStatus) -> None:
        """Refresh an already-open snapshot dialog with a new check result."""
        self._show_snapshot(status)

    # ------------------------------------------------------------------ ui
    def _build_legend(self) -> QHBoxLayout:
        legend = QHBoxLayout()
        legend.setSpacing(16)
        for color, text in (
            (_GOOD, "Connected"),
            (_OFF, "Off / high-Z"),
            (_NODATA, "No data"),
        ):
            item = QLabel(
                f'<span style="color:{color}; font-size:15px;">●</span> {text}',
            )
            item.setStyleSheet("font-size: 12px;")
            legend.addWidget(item)
        legend.addStretch(1)
        return legend

    # --------------------------------------------------------------- update
    def _refresh(self) -> None:
        sensor = self._get_sensor()
        status: LeadOffStatus | None = (
            sensor.latest_lead_off() if sensor is not None else None
        )

        # Staleness: track how many samples have been decoded; if the count has
        # not moved for _STALE_S, the stream has stopped delivering data.
        count = len(sensor.ch1_connected_list) if sensor is not None else 0
        now = time.monotonic()
        if count != self._last_count:
            self._last_count = count
            self._last_change = now
        stale = (now - self._last_change) > _STALE_S

        self._headset.set_status(status, stale=stale)
        self._update_summary(status, stale=stale)

    def _update_summary(
        self,
        status: LeadOffStatus | None,
        *,
        stale: bool,
    ) -> None:
        if status is None:
            self._summary.setText(
                f'<span style="color:{_NODATA};">●</span> '
                "Waiting for data — start streaming to see electrode status",
            )
            return

        if stale:
            self._summary.setText(
                f'<span style="color:{_NODATA};">●</span> '
                "No fresh data — stream stopped",
            )
            return

        off = status.off_count
        connected = status.total - off
        if off == 0:
            self._summary.setText(
                f'<span style="color:{_GOOD};">●</span> '
                f"All {status.total} electrodes connected",
            )
        else:
            plural = "s" if off > 1 else ""
            self._summary.setText(
                f'<span style="color:{_OFF};">●</span> '
                f"{off} electrode{plural} off — check contact "
                f"({connected}/{status.total} connected)",
            )

    # ---------------------------------------------------------------- close
    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop the polling timer when the dialog is closed."""
        if self._timer is not None:
            self._timer.stop()
        super().closeEvent(event)


# --------------------------------------------------------------------------
# Standalone demo: run this file directly to preview the page with fake data
# (no hardware / BLE needed).
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    import sys

    from PySide6.QtWidgets import QApplication

    class _FakeADS:
        def __init__(self) -> None:
            self.ch1_connected_list = [1]
            self._statp = 0
            self._stat_x = 0

        def tick(self) -> None:
            self._statp = random.getrandbits(8) & random.getrandbits(8)
            self._stat_x = random.getrandbits(2)
            # Grows one entry per tick so the dialog's staleness counter advances.
            self.ch1_connected_list.append(0 if self._statp & 1 else 1)

        def latest_lead_off(self) -> LeadOffStatus:
            return LeadOffStatus(
                channels=[bool((self._statp >> i) & 1) for i in range(8)],
                reference=bool(self._stat_x & 1),
                bias=bool((self._stat_x >> 1) & 1),
            )

    app = QApplication(sys.argv)
    fake = _FakeADS()
    dlg = LeadOffDialog(lambda: fake)  # type: ignore[arg-type,return-value]

    feed = QTimer()
    feed.timeout.connect(fake.tick)
    feed.start(900)

    dlg.show()
    sys.exit(app.exec())
