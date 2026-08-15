"""
Module containing function related to the T5838 sensor.

(Microphone)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self, override

import numpy as np
import opuslib
import soundfile as sf
from pyqtgraph import PlotDataItem, PlotItem
from pyqtgraph.widgets.GraphicsLayoutWidget import GraphicsLayoutWidget

from src.utils.constants import COLORS
from src.utils.logger import logger
from src.utils.typedefs import DryRun, SensorHeader, WriteBehaviour
from src.versa.raw_data import RawData
from src.versa.sensor import Sensor, SensorParseConfig

HEADER_V0 = b"\xaa\xaa"

SAMPLE_RATE = 12000
MAX_FREQUENCY = 6000
MAX_FRAME_SIZE = 240 * 2


@dataclass
class T5838(Sensor):
    """Class storing variables of the T5838 sensor output file."""

    pcm_data: list[bytes] = field(default_factory=list)
    audio_last_time: float = 0.0

    @classmethod
    @override
    def name(cls) -> str:
        return "T5838"

    @staticmethod
    @override
    def headers() -> list[SensorHeader]:
        return [HEADER_V0]

    @override
    def clear(self) -> None:
        super().clear()

        self.pcm_data.clear()
        self.audio_last_time = 0.0

    @override
    def to_dict(self) -> dict[str, Any]:
        return {
            "last_idx": self.last_idx,
            "pcm_data": [b.hex() for b in self.pcm_data],
            "time_list": self.time_list,
            "idx_list": self.idx_list,
        }

    def _get_audio_data(self) -> np.ndarray:
        # Get data
        pcm_data_bytes = b"".join(self.pcm_data)
        return np.frombuffer(pcm_data_bytes, dtype=np.int16)

    # ============================== PLOTS ==============================

    @override
    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:
        curves: dict[str, PlotDataItem] = {}

        # Plots
        plot: PlotItem = graphics.ci.addPlot(
            title="T5838 Microphone (dB)",
        )
        plot.setLabel("bottom", "Time (s)")
        plot.setLabel("left", "Amplitude", units="dB")

        # Set plots
        self.plots = [plot]

        # Create curve
        curves["plot"] = plot.plot()

        # Set initial data
        self.set_plot_data(curves)

        return curves

    @override
    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        # Get audio data
        audio_data = self._get_audio_data()

        # Recreate times using the sample rate
        time_list = np.arange(len(audio_data)) / SAMPLE_RATE

        if len(self.time_list) > 0:
            time_list += self.time_list[0] / 1000.0

        curves["plot"].setData(x=time_list, y=audio_data, pen=COLORS[0])

    # ============================== PARSING ==============================

    @classmethod
    @override
    def _from_dict(cls, dict_var: dict) -> Self:
        res = cls()

        res.last_idx = dict_var["last_idx"]
        res.pcm_data = [bytes.fromhex(h) for h in dict_var["pcm_data"]]
        res.time_list = dict_var["time_list"]
        res.idx_list = dict_var["idx_list"]

        return res

    @override
    def parse_file(
        self,
        raw_data: RawData,
        length: int,
        parse_config: SensorParseConfig,
    ) -> None:
        frame = raw_data.read(length - 1)
        decoder = opuslib.Decoder(SAMPLE_RATE, 1)
        pcm = decoder.decode(frame, MAX_FRAME_SIZE)
        self.pcm_data.append(pcm)

    def _write_audio_wav(
        self,
        file_path: Path,
        write_behaviour: WriteBehaviour = WriteBehaviour.APPEND,
    ) -> None:
        # Get the audio data
        audio = self._get_audio_data()
        if audio.size == 0:
            logger.debug("No audio data to write (skipped)", sensor=self.name())
            return

        # Ensure parent folder exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # If we should overwrite, just write a fresh file
        if write_behaviour == WriteBehaviour.OVERWRITE or not file_path.exists():
            sf.write(str(file_path), audio, SAMPLE_RATE, subtype="PCM_16")
            logger.info("Wrote WAV file", path=str(file_path))
            return

        # Otherwise append: read existing file (ensuring matching samplerate/channels)
        existing_data, _ = sf.read(str(file_path), dtype="int16")

        # Concatenate and write back
        combined = np.concatenate(
            [existing_data.astype(np.int16), audio.astype(np.int16)],
        )
        sf.write(str(file_path), combined, SAMPLE_RATE, subtype="PCM_16")

    @override
    def write_data(
        self,
        folder_path: Path,
        dry_run: DryRun = DryRun.WRITE,
        write_behaviour: WriteBehaviour = WriteBehaviour.APPEND,
    ) -> list[Path]:
        if self.is_empty():
            logger.debug("No data, skipped writing", sensor=self.name())
            return []

        # Write WAV file
        file_path = folder_path / f"{self.name()}.wav"

        if dry_run == DryRun.WRITE:
            self._write_audio_wav(file_path, write_behaviour=write_behaviour)

        return super().write_data(
            folder_path,
            dry_run=dry_run,
            write_behaviour=write_behaviour,
        )
