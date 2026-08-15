"""
Module containing function related to the MLX90632 sensor.

(Infrared temperature sensor)
"""

import struct
from dataclasses import dataclass, field
from typing import override

import numpy as np
from pyqtgraph import GraphicsLayoutWidget, PlotDataItem, PlotItem

from src.utils.constants import COLORS
from src.utils.typedefs import SensorHeader
from src.versa.raw_data import RawData
from src.versa.sensor import Sensor, SensorParseConfig

HEADER_V0 = b"\xbb\xbb"


@dataclass
class MLX(Sensor):
    """Class storing variables of the MLX90632 sensor output file."""

    temp_a: list[float] = field(default_factory=list)
    """List of ambient temperatures in Celsius."""

    temp_o: list[float] = field(default_factory=list)
    """List of object temperatures in Celsius."""

    @classmethod
    @override
    def name(cls) -> str:
        return "MLX90632"

    @classmethod
    @override
    def attr_name(cls) -> str:
        return "mlx"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def clear(self) -> None:
        super().clear()

        self.temp_a.clear()
        self.temp_o.clear()

    # ============================== PLOTS ==============================

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        curves: dict[str, PlotDataItem] = {}

        # Plots
        plot: PlotItem = graphics.ci.addPlot(
            title="MLX90632 Temperature Measurement",
        )
        plot.setLabel("bottom", "Time (s)")
        plot.setLabel("left", "Temperature [°C]")
        plot.addLegend()
        plot.showGrid(x=True, y=True)

        # Create curves
        curves["temp_o"] = plot.plot(name="Object")
        curves["temp_a"] = plot.plot(name="Ambient")

        # Store plots
        self.plots = [plot]

        # Set initial data
        self.set_plot_data(curves)

        return curves

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        # Get timestamps in seconds
        time_list_secs = np.array(self.time_list) / 1000.0

        # Set curves data
        curves["temp_o"].setData(
            x=time_list_secs,
            y=self.temp_o,
            name="Object",
            pen=COLORS[0],
        )
        curves["temp_a"].setData(
            x=time_list_secs,
            y=self.temp_a,
            name="Ambient",
            pen=COLORS[1],
        )

    # ============================== PARSING ==============================

    @override
    def parse_file(
        self,
        raw_data: RawData,
        length: int,
        parse_config: SensorParseConfig,
    ) -> None:
        ambient_t_bytes = raw_data.read(4)
        ambient_t = struct.unpack("f", ambient_t_bytes)[0]
        object_t_bytes = raw_data.read(4)
        object_t = struct.unpack("f", object_t_bytes)[0]
        self.temp_a.append(ambient_t)
        self.temp_o.append(object_t)
