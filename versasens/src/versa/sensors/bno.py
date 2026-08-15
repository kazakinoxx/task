"""
Module containing function related to the BNO086 sensor.

(Accelerometer)
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

HEADER_V0 = b"\xcc\xcc"


@dataclass
class BNO(Sensor):
    """Class storing variables of the BNO086 sensor output file."""

    # Accel lists
    x_list: list[int] = dataclasses.field(default_factory=list)
    y_list: list[int] = dataclasses.field(default_factory=list)
    z_list: list[int] = dataclasses.field(default_factory=list)

    yaw_list: list[int] = dataclasses.field(default_factory=list)
    pitch_list: list[int] = dataclasses.field(default_factory=list)
    roll_list: list[int] = dataclasses.field(default_factory=list)

    @classmethod
    @override
    def name(cls) -> str:
        return "BNO086"

    @classmethod
    @override
    def attr_name(cls) -> str:
        return "bno"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def clear(self) -> None:
        super().clear()

        self.x_list.clear()
        self.y_list.clear()
        self.z_list.clear()

        self.yaw_list.clear()
        self.pitch_list.clear()
        self.roll_list.clear()

    # ============================== PLOTS ==============================

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        # Reset variables
        curves: dict[str, PlotDataItem] = {}

        # Create acceleration plot
        plot_acc: PlotItem = graphics.ci.addPlot(
            title="BNO086 recorded accelerations",
            row=0,
            col=0,
        )
        plot_acc.setLabel("bottom", "Time (s)")
        plot_acc.setLabel("left", "Acceleration (mg)")
        plot_acc.addLegend()
        plot_acc.showGrid(x=True, y=True)

        # Create axes plot
        plot_axes: PlotItem = graphics.ci.addPlot(
            title="BNO086 recorded axes",
            row=1,
            col=0,
        )
        plot_axes.setLabel("bottom", "Time (s)")
        plot_axes.setLabel("left", "Angle (deg)")
        plot_axes.addLegend()
        plot_axes.showGrid(x=True, y=True)

        # Store plots
        self.plots = [plot_acc, plot_axes]

        # Create acceleration curves
        curves["accel_x"] = plot_acc.plot(name="X Accel")
        curves["accel_y"] = plot_acc.plot(name="Y Accel")
        curves["accel_z"] = plot_acc.plot(name="Z Accel")

        # Create axes curves
        curves["axes_yaw"] = plot_axes.plot(name="Yaw")
        curves["axes_pitch"] = plot_axes.plot(name="Pitch")
        curves["axes_roll"] = plot_axes.plot(name="Roll")

        # Set initial data
        self.set_plot_data(curves)

        return curves

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        time_list_secs = np.array(self.time_list) / 1000

        # Acceleration
        curves["accel_x"].setData(
            x=time_list_secs,
            y=self.x_list,
            name="X Accel",
            pen=COLORS[0],
        )
        curves["accel_y"].setData(
            x=time_list_secs,
            y=self.y_list,
            name="Y Accel",
            pen=COLORS[1],
        )
        curves["accel_z"].setData(
            x=time_list_secs,
            y=self.z_list,
            name="Z Accel",
            pen=COLORS[2],
        )

        # Axes
        curves["axes_yaw"].setData(
            x=time_list_secs,
            y=np.array(self.yaw_list) / 100,
            name="Yaw",
            pen=COLORS[0],
        )
        curves["axes_pitch"].setData(
            x=time_list_secs,
            y=np.array(self.pitch_list) / 100,
            name="Pitch",
            pen=COLORS[1],
        )
        curves["axes_roll"].setData(
            x=time_list_secs,
            y=np.array(self.roll_list) / 100,
            name="Roll",
            pen=COLORS[2],
        )

    # ============================== PARSING ==============================

    @override
    def parse_file(
        self, raw_data: RawData, length: int, parse_config: SensorParseConfig,
    ) -> None:
        # Remove last added timestamp

        timestamp = self.time_list.pop()

        for i in range(10):
            # First was already read
            if i != 0:
                idx = int.from_bytes(raw_data.read(1), "little")
                self.idx_list.append(idx)  # Append index to list

            self.time_list.append(timestamp - 90 + 10 * i)

            yaw = int.from_bytes(raw_data.read(2), "little", signed=True)
            pitch = int.from_bytes(raw_data.read(2), "little", signed=True)
            roll = int.from_bytes(raw_data.read(2), "little", signed=True)
            x_accel = int.from_bytes(raw_data.read(2), "little", signed=True)
            y_accel = int.from_bytes(raw_data.read(2), "little", signed=True)
            z_accel = int.from_bytes(raw_data.read(2), "little", signed=True)

            self.x_list.append(x_accel)
            self.y_list.append(y_accel)
            self.z_list.append(z_accel)
            self.yaw_list.append(yaw)
            self.pitch_list.append(pitch)
            self.roll_list.append(roll)

        self.last_idx = self.idx_list[-1]
