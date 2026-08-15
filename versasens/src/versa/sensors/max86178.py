"""
Module containing function related to the MAX86178 sensor.

(Photoplethysmography & Electrocardiography & Respiration front end)
"""

import bisect
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import override

import numpy as np
from pyqtgraph import PlotDataItem, PlotItem
from pyqtgraph.widgets.GraphicsLayoutWidget import GraphicsLayoutWidget

from src.utils.config import Config
from src.utils.constants import COLORS
from src.utils.typedefs import DryRun, SensorHeader, WriteBehaviour
from src.versa.raw_data import RawData
from src.versa.sensor import Sensor, SensorParseConfig

HEADER_V0 = b"\x99\x99"


@dataclass
class MAX86178(Sensor):
    """Class storing variables of the MAX86178 sensor output file."""

    time_list_ppg0: list[int] = field(default_factory=list)
    time_list_ppg1: list[int] = field(default_factory=list)
    time_list_ppg2: list[int] = field(default_factory=list)
    time_list_ppg3: list[int] = field(default_factory=list)
    time_list_bioz_86: list[int] = field(default_factory=list)
    time_list_ecg_86: list[int] = field(default_factory=list)

    ppg0_list: list[int] = field(default_factory=list)
    ppg1_list: list[int] = field(default_factory=list)
    ppg2_list: list[int] = field(default_factory=list)
    ppg3_list: list[int] = field(default_factory=list)
    ecg_list_86: list[float] = field(default_factory=list)
    bioz_list_86: list[int] = field(default_factory=list)

    @classmethod
    @override
    def name(cls) -> str:
        return "MAX86178"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def clear(self) -> None:
        super().clear()

        self.time_list_ppg0.clear()
        self.time_list_ppg1.clear()
        self.time_list_ppg2.clear()
        self.time_list_ppg3.clear()
        self.time_list_bioz_86.clear()
        self.time_list_ecg_86.clear()

        self.ppg0_list.clear()
        self.ppg1_list.clear()
        self.ppg2_list.clear()
        self.ppg3_list.clear()
        self.ecg_list_86.clear()
        self.bioz_list_86.clear()

    def _get_ppgs_info(self) -> list[tuple[np.ndarray, list[int], str, str]]:
        return [
            (
                np.array(self.time_list_ppg0) / 1000.0,
                self.ppg0_list,
                "Raw IR LED PPG",
                COLORS[1],
            ),
            (
                np.array(self.time_list_ppg1) / 1000.0,
                self.ppg1_list,
                "Raw RED LED PPG",
                COLORS[3],
            ),
            (
                np.array(self.time_list_ppg2) / 1000.0,
                self.ppg2_list,
                "Raw GREEN LED PPG",
                COLORS[2],
            ),
        ]

    @override
    def _delete_stale_data(self, config: Config) -> bool:
        """Remove data older than the displayed window to reduce memory usage."""
        if len(self.time_list) == 0:
            return False

        time_data_lst: list[tuple[list[int], str]] = [
            (self.time_list_ppg0, "ppg0_list"),
            (self.time_list_ppg1, "ppg1_list"),
            (self.time_list_ppg2, "ppg2_list"),
            (self.time_list_bioz_86, "bioz_list_86"),
            (self.time_list_ecg_86, "ecg_list_86"),
        ]

        for time_list, field_name in time_data_lst:
            last_time_ms = time_list[-1]
            cutoff_time_ms = last_time_ms - ((config.plot_x_axis_length) * 1000)

            # Find first visible index
            start_idx = bisect.bisect_left(time_list, cutoff_time_ms)

            # If no trimming needed
            if start_idx <= 0:
                continue

            # Trim list
            value = getattr(self, field_name)

            # Trim data list
            del value[:start_idx]
            # Trim time list
            del time_list[:start_idx]

        # Normal list
        last_time_ms = self.time_list[-1]
        cutoff_time_ms = last_time_ms - ((config.plot_x_axis_length + 1) * 1000)

        # Find first visible index
        start_idx = bisect.bisect_left(self.time_list, cutoff_time_ms)

        # If no trimming needed
        if start_idx <= 0:
            return False

        # Trim idx list
        del self.idx_list[:start_idx]
        # Trim time list
        del self.time_list[:start_idx]

        # Update last_idx
        self.last_idx = self.idx_list[-1]
        return True

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        # Setup variables
        curves: dict[str, PlotDataItem] = {}
        self.plots.clear()

        # PPGs
        ppgs = self._get_ppgs_info()

        for i, (_, _, title, _) in enumerate(ppgs):
            plot: PlotItem = graphics.ci.addPlot(
                title=title,
                row=i,
                col=0,
            )
            plot.setLabel("bottom", "Time (s)")
            plot.setLabel("left", "Amplitude", units="A.U.")
            plot.showGrid(x=True, y=True)
            self.plots.append(plot)

            curves[f"ppg{i}"] = plot.plot()

        # ECG
        plot_ecg: PlotItem = graphics.ci.addPlot(
            title="MAX86178 ECG",
            row=len(ppgs) + 1,
            col=0,
        )
        plot_ecg.setLabel("bottom", "Time (s)")
        plot_ecg.setLabel("left", "Voltage", units="V")

        self.plots.append(plot_ecg)
        plot_ecg.showGrid(x=True, y=True)

        # BIOZ
        plot_bioz: PlotItem = graphics.ci.addPlot(
            title="MAX86178 Respiration Signal",
            row=len(ppgs) + 2,
            col=0,
        )
        plot_bioz.setLabel("bottom", "Time (s)")
        plot_bioz.setLabel("left", "Impedance", units="Ohm")

        self.plots.append(plot_bioz)
        plot_bioz.showGrid(x=True, y=True)

        # ECG
        curves["ecg"] = plot_ecg.plot()

        # Bioz
        curves["bioz"] = plot_bioz.plot()

        self.set_plot_data(curves)

        return curves

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        # ECG
        curves["ecg"].setData(
            x=np.array(self.time_list_ecg_86) / 1000.0,
            y=self.ecg_list_86,
            pen=COLORS[0],
        )

        # Bioz
        curves["bioz"].setData(
            x=np.array(self.time_list_bioz_86) / 1000.0,
            y=self.bioz_list_86,
            pen=COLORS[0],
        )

        # PPGs
        ppgs = self._get_ppgs_info()

        for i, (time_list, ppg_list, _, color) in enumerate(ppgs):
            curves[f"ppg{i}"].setData(
                x=time_list,
                y=ppg_list,
                pen=color,
            )

    @override
    def parse_file(
        self,
        raw_data: RawData,
        length: int,
        parse_config: SensorParseConfig,
    ) -> None:
        timestamp = self.time_list[-1]

        for _ in range(50):
            meas = raw_data.read(3)
            first_byte = meas[0]
            first_4_bits = first_byte >> 4
            if first_4_bits == 0xF:  # noqa: PLR2004
                pass
            if first_4_bits == 0x0:
                self.ppg0_list.append(
                    (int.from_bytes(meas, "big") & ((1 << 20) - 1))
                    - ((int.from_bytes(meas, "big") & (1 << 19)) << 1),
                )
                self.time_list_ppg0.append(timestamp)
            if first_4_bits == 0x1:
                self.ppg1_list.append(
                    (int.from_bytes(meas, "big") & ((1 << 20) - 1))
                    - ((int.from_bytes(meas, "big") & (1 << 19)) << 1),
                )
                self.time_list_ppg1.append(timestamp)
            if first_4_bits == 0x2:  # noqa: PLR2004
                self.ppg2_list.append(
                    (int.from_bytes(meas, "big") & ((1 << 20) - 1))
                    - ((int.from_bytes(meas, "big") & (1 << 19)) << 1),
                )
                self.time_list_ppg2.append(timestamp)
            if first_4_bits == 0x3:  # noqa: PLR2004
                self.ppg3_list.append(
                    (int.from_bytes(meas, "big") & ((1 << 20) - 1))
                    - ((int.from_bytes(meas, "big") & (1 << 19)) << 1),
                )
                self.time_list_ppg3.append(timestamp)
            if first_4_bits == 0x9:  # noqa: PLR2004
                self.bioz_list_86.append(
                    (int.from_bytes(meas, "big") & ((1 << 20) - 1))
                    - ((int.from_bytes(meas, "big") & (1 << 19)) << 1),
                )
                self.time_list_bioz_86.append(timestamp)
            if first_4_bits == 0xB:  # noqa: PLR2004
                v_ecg_list_86 = (
                    (
                        (int.from_bytes(meas, "big") & ((1 << 18) - 1))
                        - ((int.from_bytes(meas, "big") & (1 << 17)) << 1)
                    )
                    * 1
                    / (2**17 * 20)
                )
                self.ecg_list_86.append(v_ecg_list_86)
                self.time_list_ecg_86.append(timestamp)
            if first_4_bits == 0xE:  # noqa: PLR2004
                pass

    @override
    def _write_csvs(
        self,
        file_paths: list[Path],
        write_behaviour: WriteBehaviour,
        dry_run: DryRun = DryRun.WRITE,
    ) -> None:
        # Bundle timelist with data list
        data_lst: list = [
            (["time_list", "idx_list"], self.time_list, self.idx_list),
            (["time_list_ppg0", "ppg0_list"], self.time_list_ppg0, self.ppg0_list),
            (["time_list_ppg1", "ppg1_list"], self.time_list_ppg1, self.ppg1_list),
            (["time_list_ppg2", "ppg2_list"], self.time_list_ppg2, self.ppg2_list),
            (["time_list_ppg3", "ppg3_list"], self.time_list_ppg3, self.ppg3_list),
            (
                ["time_list_bioz_86", "bioz_list_86"],
                self.time_list_bioz_86,
                self.bioz_list_86,
            ),
            (
                ["time_list_ecg_86", "ecg_list_86"],
                self.time_list_ecg_86,
                self.ecg_list_86,
            ),
        ]

        if len(file_paths) != len(data_lst):
            msg = f"Invalid number of file paths {len(file_paths)}"
            raise ValueError(msg)

        if dry_run == DryRun.NO_WRITES:
            return

        # Choose write mode
        mode = "w" if write_behaviour == WriteBehaviour.OVERWRITE else "a"

        for file_path, (keys, time_list, data_list) in zip(
            file_paths,
            data_lst,
            strict=True,
        ):
            # Check if file was empty
            was_empty = not file_path.exists() or file_path.stat().st_size == 0

            # Open file
            with file_path.open(mode, encoding="utf-8") as file:
                # Create CSV writer
                writer = csv.DictWriter(file, fieldnames=keys)

                # Only write header if empty and appending, or when overwriting
                if (
                    was_empty and write_behaviour == WriteBehaviour.APPEND
                ) or write_behaviour == WriteBehaviour.OVERWRITE:
                    writer.writeheader()

                rows: list = []
                # Create rows
                for time, data in zip(time_list, data_list, strict=False):
                    rows.append({keys[0]: time, keys[1]: data})

                writer.writerows(rows)

    @override
    @classmethod
    def _csv_filenames(cls) -> list[str]:
        suffixes = ["", "_ppg0", "_ppg1", "_ppg2", "_ppg3", "_bioz", "_ecg"]

        return [f"{cls.name()}{s}.csv" for s in suffixes]
