"""
Module containing function related to the MAX77658 sensor.

(Battery charger & Fuel gauge)
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

HEADER_V0 = b"\x88\x88"


@dataclass
class MAX77658(Sensor):
    """Class storing variables of the MAX77658 sensor output file."""

    temp_list: list[float] = dataclasses.field(default_factory=list)
    """List of internal die temperature measurements."""

    volt_list: list[int] = dataclasses.field(default_factory=list)
    """List of battery voltage measurements."""

    current_list: list[int] = dataclasses.field(default_factory=list)
    """List of battery current measurements."""

    soc_list: list[int] = dataclasses.field(default_factory=list)
    """List of state of charge of the battery measurements,
    from 0x000 to 0xFFF."""

    @classmethod
    @override
    def name(cls) -> str:
        return "MAX77658"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def clear(self) -> None:
        super().clear()

        self.temp_list.clear()
        self.volt_list.clear()
        self.current_list.clear()
        self.soc_list.clear()

    # ============================== PLOTS ==============================

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        curves: dict[str, PlotDataItem] = {}

        # Plots
        plot_temp: PlotItem = graphics.ci.addPlot(
            title="MAX77658 temperature",
            row=0,
            col=0,
        )
        plot_temp.setLabel("bottom", "Time (s)")
        plot_temp.setLabel("left", "Temperature (°C)")

        plot_volt: PlotItem = graphics.ci.addPlot(
            title="MAX77658 Battery voltage",
            row=0,
            col=1,
        )
        plot_volt.setLabel("bottom", "Time (s)")
        plot_volt.setLabel("left", "Voltage", units="V")

        plot_current: PlotItem = graphics.ci.addPlot(
            title="MAX77658 Battery current",
            row=1,
            col=0,
        )
        plot_current.setLabel("bottom", "Time (s)")
        plot_current.setLabel("left", "Current", units="A")

        plot_soc: PlotItem = graphics.ci.addPlot(
            title="MAX77658 Battery charge",
            row=1,
            col=1,
        )
        plot_soc.setLabel("bottom", "Time (s)")
        plot_soc.setLabel("left", "Charge (%)")

        # Store plots
        self.plots = [plot_temp, plot_volt, plot_current, plot_soc]

        # Create curves
        curves["temp"] = plot_temp.plot()
        curves["volt"] = plot_volt.plot()
        curves["current"] = plot_current.plot()
        curves["soc"] = plot_soc.plot()

        # Set initial data
        self.set_plot_data(curves)

        return curves

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        # Get timestamps in seconds
        time_list_secs = np.array(self.time_list) / 1000.0

        # Temperature
        curves["temp"].setData(x=time_list_secs, y=self.temp_list, pen=COLORS[0])

        # Volt
        curves["volt"].setData(
            x=time_list_secs,
            y=np.array(self.volt_list) * 78.125 / 1_000_000,
            pen=COLORS[0],
        )

        # Current (in Amperes)
        curves["current"].setData(
            x=time_list_secs,
            # From 10^5
            y=np.array(self.current_list) / 100_000,
            pen=COLORS[0],
        )

        # SOC
        curves["soc"].setData(
            x=time_list_secs,
            y=np.array(self.soc_list) / 0xFFFF * 100,
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
        temp = int.from_bytes(raw_data.read(2), "little") / 255
        self.temp_list.append(temp)

        volt = int.from_bytes(raw_data.read(2), "little")
        self.volt_list.append(volt)

        # Receive current in 10^5 A
        current = int.from_bytes(raw_data.read(2), "little")
        self.current_list.append(current)

        soc = int.from_bytes(raw_data.read(2), "little")
        self.soc_list.append(soc)
