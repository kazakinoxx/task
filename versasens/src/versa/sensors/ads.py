"""
Module containing function related to the ADS1298 sensor.

(Electrocardiography & Electromyography & Electroencephalography analog front end)
"""

import csv
import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Self, override

import numpy as np
from pyqtgraph import GraphicsLayoutWidget, PlotDataItem, PlotItem

from src.utils.constants import COLORS
from src.utils.typedefs import SensorHeader
from src.versa.raw_data import RawData
from src.versa.sensor import Sensor, SensorParseConfig

# Pre-rename CSV columns that stored the raw lead-off bytes. Recordings made
# before the per-channel *_connected columns still carry these; they are decoded
# back into the current columns on load (see from_csv_files).
_LEGACY_STATP_COL = "loff_statp_list"
_LEGACY_STATX_COL = "loff_stat_x_list"

HEADER_V0 = b"\xdd\xdd"

# TODO: can change
V_REF = 4

BITS = 24
RES = 2 * V_REF / ((2**BITS) - 1)

# TODO: to config
GAIN = 12

NBR_CHANNELS = 8

# Number of raw channel bytes per sample (8 channels x 3 bytes, int24 big-endian)
CHANNEL_BYTES = NBR_CHANNELS * 3


@dataclass
class LeadOffStatus:
    """
    Decoded lead-off (electrode contact) status for one ADS1298 sample.

    Each flag is True when the electrode is *off* (disconnected / high impedance).
    """

    channels: list[bool]
    """8 entries: channels[n] is True when the CH(n+1) positive electrode is off."""

    reference: bool
    """True when the shared negative (reference) electrode is off."""

    bias: bool
    """True when the RLD / bias electrode is off."""

    @property
    def off_count(self) -> int:
        """Number of electrodes currently reported off."""
        return sum(self.channels) + int(self.reference) + int(self.bias)

    @property
    def total(self) -> int:
        """Total number of monitored electrodes (8 channels + reference + bias)."""
        return NBR_CHANNELS + 2


@dataclass
class ADS(Sensor):
    """Class storing variables of the ADS1298 sensor output file."""

    ch1_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 1."""

    ch2_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 2."""

    ch3_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 3."""

    ch4_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 4."""

    ch5_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 5."""

    ch6_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 6."""

    ch7_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 7."""

    ch8_list: list[float] = dataclasses.field(default_factory=list)
    """List of voltage measurements for the channel 8."""

    # --- Electrode contact (lead-off) status ---------------------------------
    # Per-channel "connected" flags: 1 = connected (healthy contact),
    # 0 = off (disconnected / high impedance). One per positive input, CH1..CH8.
    ch1_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH1 contact: 1 = connected, 0 = off / high-Z."""
    ch2_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH2 contact: 1 = connected, 0 = off / high-Z."""
    ch3_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH3 contact: 1 = connected, 0 = off / high-Z."""
    ch4_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH4 contact: 1 = connected, 0 = off / high-Z."""
    ch5_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH5 contact: 1 = connected, 0 = off / high-Z."""
    ch6_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH6 contact: 1 = connected, 0 = off / high-Z."""
    ch7_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH7 contact: 1 = connected, 0 = off / high-Z."""
    ch8_connected_list: list[int] = dataclasses.field(default_factory=list)
    """CH8 contact: 1 = connected, 0 = off / high-Z."""

    ref_connected_list: list[int] = dataclasses.field(default_factory=list)
    """Shared negative (REF) electrode: 1 = connected, 0 = off / high-Z."""
    bias_connected_list: list[int] = dataclasses.field(default_factory=list)
    """Bias / RLD electrode: 1 = connected, 0 = off / high-Z."""

    condition_id_list: list[int] = dataclasses.field(default_factory=list)
    """Persistent experiment condition decoded from the status byte bit2."""

    @classmethod
    @override
    def name(cls) -> str:
        return "ADS1298"

    @classmethod
    @override
    def attr_name(cls) -> str:
        return "ads"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def clear(self) -> None:
        super().clear()
        self.ch1_list.clear()
        self.ch2_list.clear()
        self.ch3_list.clear()
        self.ch4_list.clear()
        self.ch5_list.clear()
        self.ch6_list.clear()
        self.ch7_list.clear()
        self.ch8_list.clear()
        for lst in self._connected_channel_lists():
            lst.clear()
        self.ref_connected_list.clear()
        self.bias_connected_list.clear()
        self.condition_id_list.clear()

    def _connected_channel_lists(self) -> list[list[int]]:
        """Return the 8 per-channel connected-flag lists, in order CH1..CH8."""
        return [
            self.ch1_connected_list,
            self.ch2_connected_list,
            self.ch3_connected_list,
            self.ch4_connected_list,
            self.ch5_connected_list,
            self.ch6_connected_list,
            self.ch7_connected_list,
            self.ch8_connected_list,
        ]

    def _channels_data(self) -> list[list[float]]:
        return [
            self.ch1_list,
            self.ch2_list,
            self.ch3_list,
            self.ch4_list,
            self.ch5_list,
            self.ch6_list,
            self.ch7_list,
            self.ch8_list,
        ]

    @staticmethod
    def _get_res(v_ref: float) -> float:
        return 2 * v_ref / ((2**BITS) - 1)

    # ============================== PLOTS ==============================

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        # Reset variables
        curves: dict[str, PlotDataItem] = {}
        self.plots.clear()

        # Create plots and curves for each channel
        for i in range(NBR_CHANNELS):
            plot: PlotItem = graphics.ci.addPlot(
                title=f"Channel {i + 1}",
                row=i // 2,
                col=i % 2,
            )
            plot.setLabel("left", "Voltage", units="V")
            plot.setLabel("bottom", "Time", units="s")

            # Add plot to list
            self.plots.append(plot)

            # Create curve
            curves[str(i)] = plot.plot()

        condition_plot: PlotItem = graphics.ci.addPlot(
            title="Condition",
            row=4,
            col=0,
            colspan=2,
        )
        condition_plot.setLabel("left", "Condition")
        condition_plot.setLabel("bottom", "Time", units="s")
        condition_plot.setYRange(-0.1, 1.1)
        condition_plot.getAxis("left").setTicks([[(0, "0"), (1, "1")]])
        self.plots.append(condition_plot)
        curves["condition"] = condition_plot.plot(stepMode="left")

        # Set initial data
        self.set_plot_data(curves)

        return curves

    @override
    def exact_x_range_links(self) -> list[tuple[PlotItem, PlotItem]]:
        """Keep the full-width condition strip on Channel 1's time range."""
        if len(self.plots) < NBR_CHANNELS + 1:
            return []
        return [(self.plots[0], self.plots[-1])]

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        # Get data of channels
        channels = self._channels_data()

        # Convert timestamps to seconds once (reused for all 8 channels)
        time_list_secs = np.array(self.time_list) / 1000.0

        # Set the data and convert data
        for i, ch_data in enumerate(channels):
            curves[str(i)].setData(x=time_list_secs, y=ch_data, pen=COLORS[0])

        curves["condition"].setData(
            x=time_list_secs,
            y=self.condition_id_list,
            pen=COLORS[3],
            stepMode="left",
        )

    # ============================== PARSING ==============================

    @override
    def parse_file(
        self, raw_data: RawData, length: int, parse_config: SensorParseConfig,
    ) -> None:
        channels = self._channels_data()
        res = self._get_res(parse_config["ads_vref"])
        gain = parse_config["ads_gain"]

        for ch_data in channels:
            ch = int.from_bytes(raw_data.read(3), "big", signed=True) * res / gain
            ch_data.append(ch)

        # Bytes remaining after the 8x3 channel bytes. `length` (the record's len
        # field) counts index + measurements + optional lead-off bytes; the caller
        # already consumed the 1-byte index, so channel + trailing bytes = length - 1.
        # Reading exactly `remaining` keeps the record stream aligned for both old
        # firmware (no lead-off bytes) and new firmware (2 lead-off bytes appended).
        remaining = length - 1 - CHANNEL_BYTES
        statp = 0
        stat_x = 0
        if remaining > 0:
            tail = raw_data.read(remaining)
            if len(tail) >= 2:  # noqa: PLR2004
                statp = tail[0]
                stat_x = tail[1]
        # Decode to per-channel "connected" flags (1 = connected, 0 = off).
        # Lead-off bit set means the electrode is off, so connected is its inverse.
        for i, lst in enumerate(self._connected_channel_lists()):
            lst.append(0 if (statp >> i) & 0x01 else 1)
        self.ref_connected_list.append(0 if stat_x & 0x01 else 1)
        self.bias_connected_list.append(0 if (stat_x >> 1) & 0x01 else 1)
        self.condition_id_list.append((stat_x >> 2) & 0x01)

    @staticmethod
    def decode_lead_off(statp: int, stat_x: int) -> LeadOffStatus:
        """
        Decode the two ADS1298 lead-off status bytes into a LeadOffStatus.

        Args:
            statp: LOFF_STATP byte (bit n = CH(n+1) positive electrode off).
            stat_x: Packed byte (bit0 = shared negative off, bit1 = RLD/bias off).

        Returns:
            The decoded lead-off status.

        """
        return LeadOffStatus(
            channels=[bool((statp >> i) & 0x01) for i in range(NBR_CHANNELS)],
            reference=bool(stat_x & 0x01),
            bias=bool((stat_x >> 1) & 0x01),
        )

    def latest_lead_off(self) -> LeadOffStatus | None:
        """Build the most recent lead-off status, or None if no data yet."""
        if not self.ch1_connected_list:
            return None
        # connected flag 0 = off, so an electrode is off when its flag is 0.
        return LeadOffStatus(
            channels=[lst[-1] == 0 for lst in self._connected_channel_lists()],
            reference=self.ref_connected_list[-1] == 0,
            bias=self.bias_connected_list[-1] == 0,
        )

    # ============================== CSV LOADING ==============================

    @classmethod
    @override
    def from_csv_files(cls, file_paths: list[Path]) -> Self:
        """
        Read an ADS instance from CSV(s), accepting old and new column layouts.

        Recordings made before the per-channel *_connected columns stored the two
        raw lead-off bytes (loff_statp_list / loff_stat_x_list). Those columns are
        no longer fields, so the base reader would reject them; here they are
        decoded into the current per-channel / ref / bias / condition columns so
        older recordings still open.

        Args:
            file_paths: The paths to the CSV file(s).

        Returns:
            The read instance.

        """
        legacy: list[Path] = []
        current: list[Path] = []
        for file_path in file_paths:
            with file_path.open("r", encoding="utf-8") as file:
                header = next(csv.reader(file), [])
            (legacy if _LEGACY_STATP_COL in header else current).append(file_path)

        # Current-layout files go through the base reader unchanged.
        res = super().from_csv_files(current) if current else cls()

        # Legacy files are decoded row by row and appended.
        for file_path in legacy:
            res._append_legacy_csv(file_path)  # noqa: SLF001

        if res.idx_list:
            res.last_idx = res.idx_list[-1]
        return res

    def _append_legacy_csv(self, file_path: Path) -> None:
        """Decode a pre-rename ADS CSV into the current columns and append it."""
        channels = self._channels_data()
        connected = self._connected_channel_lists()
        with file_path.open("r", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                self.idx_list.append(int(row["idx_list"]))
                self.time_list.append(int(row["time_list"]))
                for i, ch in enumerate(channels):
                    ch.append(float(row[f"ch{i + 1}_list"]))

                statp = int(row.get(_LEGACY_STATP_COL, 0))
                stat_x = int(row.get(_LEGACY_STATX_COL, 0))
                for i, lst in enumerate(connected):
                    lst.append(0 if (statp >> i) & 0x01 else 1)
                self.ref_connected_list.append(0 if stat_x & 0x01 else 1)
                self.bias_connected_list.append(0 if (stat_x >> 1) & 0x01 else 1)
                self.condition_id_list.append(
                    int(row.get("condition_id_list", (stat_x >> 2) & 0x01)),
                )
