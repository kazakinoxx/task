"""Module containing code related to the handling of the sensors and their data."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from src.generated.sensors_info import (
    SENSOR_ATTR_NAMES,
    SENSOR_HEADERS,
    SENSOR_NAME_TO_ATTR_NAME,
    SensorGroupBase,
)
from src.utils.config import Config
from src.utils.exceptions import UnknownHeaderError, UnknownSensorError
from src.utils.typedefs import (
    DryRun,
    SensorAttrName,
    SensorHeader,
    SensorName,
    WriteBehaviour,
)
from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor import Sensor, SensorParseConfig

BATCH_PARSE_AND_WRITE_SIZE = 10


# =================================== UTILS ====================================


def sensor_name_to_attr_name(sensor_name: str) -> str:
    """
    Convert a sensor name to the corresponding attribute name.

    If the given is already an attribute name, it returns its input.

    Args:
        sensor_name: The sensor name

    Returns:
        The attribute name

    """
    if sensor_name in SENSOR_ATTR_NAMES:
        # If already attribute name, do nothing
        return sensor_name
    if sensor_name in SENSOR_NAME_TO_ATTR_NAME:
        # If sensor name, get attribute name
        return SENSOR_NAME_TO_ATTR_NAME[sensor_name]

    msg = f"Sensor name {sensor_name} not found"
    raise UnknownSensorError(msg)


def _header_to_attr_name(header: SensorHeader) -> str:
    """
    Get the attribute name of the sensor corresponding to the given header.

    Args:
        header: The header to check.

    Raises:
        UnknownHeaderError: If the header is not a known header

    Returns:
        The attribute name of the corresponding sensor

    """
    for sensor_headers, attr in zip(SENSOR_HEADERS, SENSOR_ATTR_NAMES, strict=False):
        if header in sensor_headers:
            return attr

    msg = f"Header {header} not found"
    raise UnknownHeaderError(msg)


def data_to_sensor_attr_name(data: bytearray) -> str:
    """
    Read the header of the given data.

    Args:
        data: the sensor data from which the sensor's name is being guessed.

    Raises:
        UnknownHeaderError: If the data contains an unknown header

    Returns:
        The attribute name corresponding to the found sensor.

    """
    header = bytes(data[:2])
    return _header_to_attr_name(header)


# ================================ SensorsData =================================


@dataclass
class SensorGroup(SensorGroupBase):
    """Class storing variables for all sensors."""

    def has_data(self) -> bool:
        """
        Check whether some data is stored in at least one of the sensors.

        Returns:
            Whether some data is stored in at least one of the sensors

        """
        return any(not s.is_empty() for s in self._get_all_sensors())

    def _get_sensor(self, name: SensorName | SensorAttrName) -> Sensor:
        """
        Get the data corresponding to the given sensor name.

        Args:
            name: The name of the sensor (or the attribute name)

        Returns:
            The data of the sensor

        """
        attr_name = sensor_name_to_attr_name(name)
        return getattr(self, attr_name)

    def clear(self) -> None:
        """Clear the data stored inside the sensors."""
        # TODO: test this
        for sensor in self._get_all_sensors():
            sensor.clear()

    def _header_to_sensor(self, header: SensorHeader) -> Sensor:
        """
        Get the stored sensor corresponding to the given header.

        Args:
            header: The header to check

        Raises:
            UnknownHeaderError: If the header is not a known header

        Returns:
            The corresponding sensor

        """
        attr_name = _header_to_attr_name(header)
        return getattr(self, attr_name)

    def add_raw_data(
        self,
        raw_data: RawData,
        parse_config: SensorParseConfig,
    ) -> Self:
        """
        Add raw data to the sensor group.

        The raw data is parsed, then added to the relevant sensor.

        Args:
            raw_data: The raw data from which data is read
            parse_config: Config parameters to pass to the parser function

        Raises:
            UnknownHeaderError: If the stream contains an unknown header

        Returns:
            Self

        """
        should_finish = False

        while not should_finish:
            should_finish, _ = self.add_data_single_read(raw_data, parse_config)

        return self

    def add_data_single_read(
        self,
        raw_data: RawData,
        parse_config: SensorParseConfig,
    ) -> tuple[bool, str]:
        """
        Read a single sample from the raw data.

        Args:
            raw_data: The raw data
            parse_config: Config parameters to pass to the parser function

        Raises:
            UnknownHeaderError: If the data contains an unknown header

        Returns:
            Whether to stop reading the stream and the sensor's attribute name

        """
        # Sensor ID: 16 bits
        # Timestamp seconds: 32 bits
        # Timestamp milliseconds: 16 bits
        # Length: 8 bits
        # Index: 8 bits

        # Get header (16 bits, 2 bytes)
        header = raw_data.read(2)

        # Stop when the header is empty
        if header == b"":
            return True, ""

        # Get sensor data
        sensor = self._header_to_sensor(header)

        # Get the rest of the values
        # Seconds (32 bits, 4 bytes)
        seconds = int.from_bytes(raw_data.read(4), "little")
        # Milliseconds (16 bits, 2 bytes)
        milliseconds = int.from_bytes(raw_data.read(2), "little")
        timestamp = seconds * 1000 + milliseconds
        # Length (8 bits, 1 byte)
        length = int.from_bytes(raw_data.read(1), "little")
        # Index (8 bits, 1 byte)
        idx = int.from_bytes(raw_data.read(1), "little")

        # Put values in the sensor
        sensor.last_idx = idx
        sensor.idx_list.append(idx)
        sensor.time_list.append(timestamp)

        sensor.parse_file(raw_data, length, parse_config)

        return False, sensor.attr_name()

    @classmethod
    def parse_raw_file(
        cls,
        raw_file_path: Path,
        config_path: Path,
        raw_data_callback: Callable[[RawData], None] | None = None,
    ) -> Self:
        """
        Process data from a given raw file.

        Args:
            raw_file_path: The path to the file to read
            config_path: The path to the config. Used to cache the raw file to disk.
            raw_data_callback: Callback to give the raw data.

        Raises:
            UnknownHeaderError: If the raw file contains an unknown header

        Returns:
            The SensorsData instance

        """
        res = cls()
        parse_config = Config.get_sensor_parse_config(config_path)

        with RawData.from_file(
            raw_file_path,
            WriteLocation.TO_DISK,
            config_path=config_path,
        ) as raw_data:
            if raw_data_callback is not None:
                raw_data_callback(raw_data)
            res.add_raw_data(raw_data, parse_config)

        return res

    # ================================= Parse and save =================================

    @classmethod
    def parse_and_save_raw_data(
        cls,
        raw_data: RawData,
        import_folder: Path,
        config_path: Path,
        raw_file_name: str | None = None,
    ) -> Path:
        """
        Parse the given raw data and save the results into the given folder.

        Args:
            raw_data: The raw data to parse
            import_folder: The folder where to put the parsed data.
            config_path: The path to the config. Used to cache the raw file to disk.
            raw_file_name: If given, the original file name of the raw data file.
                           Defaults to None.

        Returns:
            The path to the folder containing the parsed data.

        """
        # TODO: write test
        parse_config = Config.get_sensor_parse_config(config_path)

        # Ensure that folder exists
        import_folder.mkdir(parents=True, exist_ok=True)

        raw_file_path = raw_data.get_file_path()

        # Get filename
        if raw_file_name is None:
            raw_file_name = raw_file_path.stem

        sample_folder = import_folder / raw_file_name
        sample_folder.mkdir(parents=True, exist_ok=True)

        # Batch writes
        writes_in_queue: dict[str, int] = {}

        for attr_name in SENSOR_ATTR_NAMES:
            writes_in_queue[attr_name] = 0

        parsed_data = cls()

        while True:
            # Create new blank instance to save memory
            should_finish, sens_attr_name = parsed_data.add_data_single_read(
                raw_data, parse_config,
            )

            if should_finish:
                break

            writes_in_queue[sens_attr_name] += 1

            if writes_in_queue[sens_attr_name] >= BATCH_PARSE_AND_WRITE_SIZE:
                # Save sensor data
                parsed_data._get_sensor(sens_attr_name).write_data(
                    sample_folder,
                    write_behaviour=WriteBehaviour.APPEND,
                    dry_run=DryRun.WRITE,
                )
                # Clear data to save memory
                parsed_data._get_sensor(sens_attr_name).clear()
                # Reset count
                writes_in_queue[sens_attr_name] = 0

        # Do any leftover writes
        for sens_attr_name, cnt in writes_in_queue.items():
            if cnt == 0:
                continue

            # Save sensor data
            parsed_data._get_sensor(sens_attr_name).write_data(
                sample_folder,
                write_behaviour=WriteBehaviour.APPEND,
                dry_run=DryRun.WRITE,
            )

        return sample_folder

    # ================================== CSV ===================================

    def write_to_disk(
        self,
        folder_path: Path,
        finished_writing_sensor_callback: Callable[[], None] | None = None,
    ) -> dict[
        SensorAttrName,
        list[Path],
    ]:
        """
        Write the CSVs of each sensor's data into the given folder.

        Args:
            folder_path: The folder where the files are written.
            finished_writing_sensor_callback: Function called when finished writing a
                                              sensor.

        Returns:
            The dictionary of sensor name to CSV file paths

        """
        res: dict[str, list[Path]] = {}

        # Ensure that folder exists
        folder_path.mkdir(parents=True, exist_ok=True)

        for name in SENSOR_ATTR_NAMES:
            res[name] = self._get_sensor(name).write_data(
                folder_path,
                write_behaviour=WriteBehaviour.OVERWRITE,
            )

            if finished_writing_sensor_callback is not None:
                finished_writing_sensor_callback()

        return res

    @classmethod
    def from_csv_files(
        cls,
        file_paths: dict[SensorName | SensorAttrName, list[Path]],
    ) -> Self:
        """
        Create a new instance from the given CSV file paths.

        Args:
            file_paths: The dictionary of sensor name to CSV file path

        Returns:
            The new instance

        """
        res = cls()

        for name, file_path in file_paths.items():
            setattr(res, name, res._get_sensor(name).from_csv_files(file_path))

        return res
