"""Module containing the class representing each sensor."""

import bisect
import csv
import dataclasses
import typing
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Self

from pyqtgraph import GraphicsLayoutWidget, PlotDataItem, PlotItem

from src.utils.config import Config, SensorParseConfig
from src.utils.logger import logger
from src.utils.typedefs import DryRun, SensorHeader, WriteBehaviour
from src.versa.raw_data import RawData


@dataclasses.dataclass
class Sensor(ABC):
    """Superclass containing the data of a sensor."""

    last_idx: int = -1
    idx_list: list[int] = dataclasses.field(default_factory=list)

    time_list: list[int] = dataclasses.field(default_factory=list)
    """List of timestamps of the stored data (ms)"""

    plots: list[PlotItem] = dataclasses.field(default_factory=list)

    @staticmethod
    @abstractmethod
    def headers() -> list[SensorHeader]:
        """
        Retrieve the list of sensor headers.

        Returns:
            list[SensorHeader]: A list containing the details of sensor headers.

        """
        msg = "headers not implemented"
        raise NotImplementedError(msg)

    @classmethod
    def name(cls) -> str:
        """
        Get the name of the sensor.

        Returns:
            The name of the sensor

        """
        return cls.__name__

    @classmethod
    def attr_name(cls) -> str:
        """
        Get the name of the sensor.

        Returns:
            The name of the sensor

        """
        return cls.name().lower()

    def is_empty(self) -> bool:
        """Check if the instance contains data."""
        return len(self.idx_list) == 0

    def clear(self) -> None:
        """Clear the data of the sensor."""
        # TODO: test this
        self.last_idx = -1

        # Clear all lists except plots
        for field in dataclasses.fields(self):
            if field.name == "plots":
                continue

            if isinstance(getattr(self, field.name), list):
                getattr(self, field.name).clear()

        # Delete plots
        for plot in self.plots:
            plot.clear()
            plot.deleteLater()

        self.plots.clear()

        # TODO: check if garbage collection needed

    @abstractmethod
    def plot_graphics(
        self,
        graphics: GraphicsLayoutWidget,
    ) -> dict[str, PlotDataItem]:  # pragma: no cover
        """
        Plot the data contained inside the instance using the given graphics widget.

        Args:
            graphics: the graphics widget where the data will be plotted.

        Returns:
            A dictionary of curve name to curve.

        """
        msg = "plot_graphics not implemented"
        raise NotImplementedError(msg)

    @abstractmethod
    def set_plot_data(
        self,
        curves: dict[str, PlotDataItem],
    ) -> None:  # pragma: no cover
        """
        Set the current data to the given plot curves.

        Args:
            curves: The dictionary of curve names to curves.

        """
        msg = "set_plot_data not implemented"
        raise NotImplementedError(msg)

    def exact_x_range_links(self) -> list[tuple[PlotItem, PlotItem]]:
        """
        Return ``(master, follower)`` plots that need identical X ranges.

        PyQtGraph's native X linking aligns scene coordinates. That is useful for
        plots with the same on-screen width, but it gives different numerical
        ranges when (for example) a follower spans two layout columns. Graph uses
        these pairs to copy the master's numerical range explicitly instead.
        """
        return []

    def _delete_stale_data(self, config: Config) -> bool:
        """Remove data older than the displayed window to reduce memory usage."""
        if len(self.time_list) == 0:
            return False

        last_time_ms = self.time_list[-1]
        cutoff_time_ms = last_time_ms - ((config.plot_x_axis_length) * 1000)

        # Find first visible index
        start_idx = bisect.bisect_left(self.time_list, cutoff_time_ms)

        # If no trimming needed
        if start_idx <= 0:
            return False

        # Trim all list fields of the dataclass
        for field in dataclasses.fields(self):
            # Skip the plots field to avoid deleting PlotItem references
            if field.name == "plots":
                continue

            value = getattr(self, field.name)

            # Only trim lists of scalars
            if isinstance(value, list):
                del value[:start_idx]

        # Update last_idx
        self.last_idx = self.idx_list[-1]
        return True

    def update_plot_graphics(
        self,
        curves: dict[str, PlotDataItem],
        config: Config,
    ) -> None:
        """
        Update the given curves.

        Args:
            curves: the dictionary of curve names to curves.
            config: the config of the program.

        """
        self._delete_stale_data(config)

        # Update curves
        self.set_plot_data(curves)

        # TODO: temporarily removed auto scale (only useful for the start)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the instance into a dictionary.

        Returns:
            The dictionary

        """
        res = dataclasses.asdict(self)

        # Remove the plots
        res.pop("plots")

        return res

    @abstractmethod
    def parse_file(
        self,
        raw_data: RawData,
        length: int,
        parse_config: SensorParseConfig,
    ) -> None:  # pragma: no cover
        """
        Parse information contained in the given raw data.

        Args:
            length: Length of the data to read
            raw_data: The raw data
            parse_config: Config parameters to pass to the parser function

        """
        msg = "parse_file not implemented"
        raise NotImplementedError(msg)

    @classmethod
    def _from_dict(cls, dict_var: dict) -> Self:
        """
        Create a new instance from a dictionary.

        Args:
            dict_var: The dictionary

        """
        res = cls()

        field_names = [f.name for f in dataclasses.fields(cls)]

        for k, v in dict_var.items():
            if k not in field_names:
                msg = f"Key {k} not in {cls.name()}"
                raise KeyError(msg)

            setattr(res, k, v)

        return res

    def _write_csvs(
        self,
        file_paths: list[Path],
        write_behaviour: WriteBehaviour,
        dry_run: DryRun = DryRun.WRITE,
    ) -> None:
        """
        Convert the instance into a CSV string.

        Args:
            file_paths: List of paths to the csv files
            write_behaviour: How to handle writes when data is already present in the
                             given files
            dry_run: (optional) whether to simulate the writes

        """
        # If empty, don't do anything
        if self.is_empty():
            return

        # If received wrong number of file paths, raise error
        if len(file_paths) != 1:
            msg = f"Received wrong number of file paths {len(file_paths)}"
            raise ValueError(msg)

        # Get data
        data_dict = self.to_dict()

        # Only keep lists
        lists = {k: v for k, v in data_dict.items() if isinstance(v, list)}
        keys = list(lists.keys())

        # Choose write mode
        mode = "w" if write_behaviour == WriteBehaviour.OVERWRITE else "a"

        # Check if file was empty
        was_empty = not file_paths[0].exists() or file_paths[0].stat().st_size == 0

        # Check all lists have the same length
        # Get length of first list
        lst_len = len(next(iter(lists.values())))
        same_lengths = all(len(lst) == lst_len for lst in lists.values())

        if not same_lengths:
            msg = (
                "to_csv_strings: Received multiple list lengths, need to "
                "implement function in subclass"
            )
            raise ValueError(msg)

        # Get the list of rows
        rows: list[dict] = []
        for i in range(lst_len):
            row_vals = [v[i] for v in lists.values()]
            row = dict(zip(keys, row_vals, strict=False))
            rows.append(row)

        if dry_run == DryRun.NO_WRITES:
            return

        # Open file
        with file_paths[0].open(mode, encoding="utf-8", newline="") as file:
            # Create the CSV writer
            writer = csv.DictWriter(file, fieldnames=keys)

            # Only write header if empty and appending, or when overwriting
            if (
                was_empty and write_behaviour == WriteBehaviour.APPEND
            ) or write_behaviour == WriteBehaviour.OVERWRITE:
                writer.writeheader()

            # Write to file
            writer.writerows(rows)

    @classmethod
    def _csv_filenames(cls) -> list[str]:
        """
        Get the names of the CSV files corresponding to this class.

        Returns:
            The name of the file

        """
        return [f"{cls.name()}.csv"]

    def write_data(
        self,
        folder_path: Path,
        dry_run: DryRun = DryRun.WRITE,
        write_behaviour: WriteBehaviour = WriteBehaviour.APPEND,
    ) -> list[Path]:
        """
        Write the contained data to the disk.

        Args:
            folder_path: The path of the folder containing the file
            dry_run: (optional) whether to simulate the writes
            write_behaviour: (optional) how to handle writes when data is already
                             present

        Returns:
            The paths of the written files

        """
        if self.is_empty():
            logger.debug("No data, skipped writing", sensor=self.name())
            return []

        # Check that the folder exists
        if not folder_path.exists():
            msg = f"Folder {folder_path} does not exist"
            raise FileNotFoundError(msg)

        filenames = self._csv_filenames()
        file_paths = [(folder_path / fn) for fn in filenames]

        self._write_csvs(file_paths, write_behaviour, dry_run=dry_run)

        return file_paths

    @staticmethod
    def _csv_row_str_type_conv(
        type_hint: str,
        col_name: str,
        value: str,
    ) -> int | float | str:
        # Convert to correct value
        if type_hint == "list[int]":
            v_conv = int(value)
        elif type_hint == "list[float]":
            v_conv = float(value)
        elif type_hint == "list[bytes]":
            v_conv = str(value)
        else:
            msg = f"Unknown type ({(col_name, value)})"
            raise ValueError(msg)

        return v_conv

    @classmethod
    def from_csv_files(cls, file_paths: list[Path]) -> Self:
        """
        Read an instance from a CSV file.

        Args:
            file_paths: The path to the CSV file

        Returns:
            The read instance

        """
        res_dict = cls().to_dict()
        cls_fieldnames = [f.name for f in dataclasses.fields(cls)]

        for file_path in file_paths:
            if not file_path.exists():
                msg = f"File {file_path.resolve()!s} does not exist"
                raise FileNotFoundError(msg)

            if not file_path.is_file():
                msg = f"{file_path.resolve()!s} is not a file"
                raise ValueError(msg)

            # Read file
            with file_path.open("r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                if reader.fieldnames is None:
                    msg = "No field names found in given CSV"
                    raise ValueError(msg)

                type_hints: list[str] = []

                for fieldname in reader.fieldnames:
                    if fieldname not in cls_fieldnames:
                        msg = f"Key {fieldname} not in {cls.name()}"
                        raise ValueError(msg)

                    type_hints.append(str(typing.get_type_hints(cls)[fieldname]))

                for row in reader:
                    for i, (col_name, value) in enumerate(row.items()):
                        # Convert to correct value
                        v_conv = cls._csv_row_str_type_conv(
                            type_hints[i],
                            col_name,
                            value,
                        )
                        res_dict[col_name].append(v_conv)

        res = cls._from_dict(res_dict)

        if len(res.idx_list) > 0:
            res.last_idx = res.idx_list[-1]

        return res
