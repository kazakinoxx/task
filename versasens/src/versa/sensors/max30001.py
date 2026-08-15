"""
Module containing function related to the MAX30001 sensor.

(Electrodermal activity & Respiration front end)
"""

import dataclasses
from dataclasses import dataclass
from typing import override

import numpy as np
from pyqtgraph import GraphicsLayoutWidget, PlotDataItem, PlotItem

from src.utils.constants import COLORS
from src.utils.typedefs import SensorHeader
from src.versa.raw_data import RawData
from src.versa.sensor import Sensor, SensorParseConfig

HEADER_V0 = b"\xee\xee"


@dataclass
class MAX30001(Sensor):
    """Class storing variables of the MAX30001 sensor output file."""

    ecg_list: list[int] = dataclasses.field(default_factory=list)
    bioz_list: list[int] = dataclasses.field(default_factory=list)

    @classmethod
    @override
    def name(cls) -> str:
        return "MAX30001"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def clear(self) -> None:
        super().clear()

        self.ecg_list.clear()
        self.bioz_list.clear()

    # ============================== PLOTS ==============================

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        # Create curves dict
        curves: dict[str, PlotDataItem] = {}

        # Create ECG plot
        plot_ecg: PlotItem = graphics.ci.addPlot(
            title="MAX30001 ECG",
            row=0,
            col=0,
        )
        plot_ecg.setLabel("bottom", "Time (s)")
        plot_ecg.setLabel("left", "Voltage", units="V")

        # Create BIOZ plot
        plot_bioz: PlotItem = graphics.ci.addPlot(
            title="MAX30001 Respiration Signal",
            row=1,
            col=0,
        )
        plot_bioz.setLabel("bottom", "Time (s)")
        plot_bioz.setLabel("left", "BIOZ", units="Ohm")

        # Create curves
        curves["ecg"] = plot_ecg.plot()
        curves["bioz"] = plot_bioz.plot()

        # Store plots
        self.plots = [plot_ecg, plot_bioz]

        # Set initial data
        self.set_plot_data(curves)

        return curves

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        # Get timestamps in seconds
        time_list_secs = np.array(self.time_list) / 1000.0

        # ECG
        curves["ecg"].setData(
            x=time_list_secs,
            y=np.array(self.ecg_list) * 1 / (2**17 * 80) * 1000,
            pen=COLORS[0],
        )

        # BIOZ
        curves["bioz"].setData(
            x=time_list_secs,
            y=np.array(self.bioz_list) * (1 / 20 / 48 * 1000000 / pow(2, 19)) / 1000.0,
            pen=COLORS[0],
        )

    # ============================== PARSING ==============================

    @override
    def parse_file(
        self,
        raw_data: RawData,
        length: int,
        parse_config: SensorParseConfig,
    ) -> None:
        read_data = raw_data.read(3)
        data_signed = int.from_bytes(read_data, "big", signed=True)
        shifted_data = data_signed >> 6
        self.ecg_list.append(shifted_data)

        read_data = raw_data.read(3)
        data_signed = int.from_bytes(read_data, "big", signed=True)
        shifted_data = -(data_signed >> 4)
        self.bioz_list.append(shifted_data)
