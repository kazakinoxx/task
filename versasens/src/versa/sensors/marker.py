"""Parser for USB/BLE/SD experiment condition marker records."""

import dataclasses
from dataclasses import dataclass
from typing import override

import numpy as np
from pyqtgraph import GraphicsLayoutWidget, PlotDataItem, PlotItem

from src.utils.constants import COLORS
from src.utils.typedefs import SensorHeader
from src.versa.raw_data import RawData
from src.versa.sensor import Sensor, SensorParseConfig

HEADER_V0 = b"\x77\x77"
MARKER_PAYLOAD_BYTES = 3


@dataclass
class Marker(Sensor):
    """Exact condition command timestamps embedded in the raw acquisition stream."""

    command_list: list[int] = dataclasses.field(default_factory=list)
    transition_sequence_list: list[int] = dataclasses.field(default_factory=list)

    @classmethod
    @override
    def name(cls) -> str:
        return "Condition Marker"

    @classmethod
    @override
    def attr_name(cls) -> str:
        return "marker"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        self.plots.clear()
        plot: PlotItem = graphics.ci.addPlot(title="Condition transitions")
        plot.setLabel("left", "Command")
        plot.setLabel("bottom", "Time", units="s")
        plot.setYRange(-0.1, 4.1)
        plot.getAxis("left").setTicks(
            [
                [
                    (0, "0"),
                    (1, "1"),
                    (2, "ping"),
                    (3, "chk start"),
                    (4, "chk end"),
                ],
            ],
        )
        self.plots.append(plot)
        curves = {"command": plot.plot(stepMode="left")}
        self.set_plot_data(curves)
        return curves

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        curves["command"].setData(
            x=np.asarray(self.time_list) / 1000.0,
            y=self.command_list,
            pen=COLORS[3],
            stepMode="left",
        )

    @override
    def parse_file(
        self,
        raw_data: RawData,
        length: int,
        parse_config: SensorParseConfig,
    ) -> None:
        del parse_config
        payload_length = max(0, length - 1)  # index was consumed by SensorGroup
        payload = raw_data.read(payload_length)
        self.command_list.append(payload[0] if payload else 0)
        sequence = (
            int.from_bytes(payload[1:3], "little")
            if len(payload) >= MARKER_PAYLOAD_BYTES
            else 0
        )
        self.transition_sequence_list.append(sequence)
