from collections.abc import Callable
from pathlib import Path

import pytest

from src.generated.sensors_info import SENSOR_CLASSES
from src.utils.typedefs import DryRun, WriteBehaviour
from src.versa.sensor import Sensor
from src.versa.sensor_group import SENSOR_ATTR_NAMES, SensorGroup


def _get_data_to_sensor_callable(name: str) -> Callable[[SensorGroup], Sensor]:
    def _data_to_sensor(data: SensorGroup) -> Sensor:
        return data._get_sensor(name)

    return _data_to_sensor


_data_to_sensor_list: list[Callable[[SensorGroup], Sensor]] = [
    _get_data_to_sensor_callable(name) for name in SENSOR_ATTR_NAMES
]
_classes_list: list[type[Sensor]] = SENSOR_CLASSES

# Parametrize all tests
pytestmark = pytest.mark.parametrize(
    ("data_to_sensor", "sensor_class"),
    list(zip(_data_to_sensor_list, _classes_list, strict=True)),
)


def test_to_csv(
    test_files_parsed: list[SensorGroup],
    data_to_sensor: Callable[[SensorGroup], Sensor],
    sensor_class: type[Sensor],
    tmp_path: Path,
):
    filenames = sensor_class._csv_filenames()
    csv_file_paths = [(tmp_path / fn) for fn in filenames]

    for group_data in test_files_parsed:
        sensor_data = data_to_sensor(group_data)
        sensor_data._write_csvs(
            csv_file_paths,
            write_behaviour=WriteBehaviour.OVERWRITE,
            dry_run=DryRun.WRITE,
        )


def test_to_from_csv(
    test_files_parsed: list[SensorGroup],
    data_to_sensor: Callable[[SensorGroup], Sensor],
    sensor_class: type[Sensor],
    tmp_path: Path,
):
    filenames = sensor_class._csv_filenames()
    csv_file_paths = [(tmp_path / fn) for fn in filenames]

    for group_data in test_files_parsed:
        data = data_to_sensor(group_data)
        # Sensors introduced after the legacy fixture files (for example exact
        # condition markers) legitimately have no rows in those recordings.
        if data.is_empty():
            continue
        data._write_csvs(
            csv_file_paths,
            write_behaviour=WriteBehaviour.OVERWRITE,
            dry_run=DryRun.WRITE,
        )

        csv_data = sensor_class.from_csv_files(csv_file_paths)

        assert data == csv_data


def test_to_from_dict(
    test_files_parsed: list[SensorGroup],
    data_to_sensor: Callable[[SensorGroup], Sensor],
    sensor_class: type[Sensor],
):
    for group_data in test_files_parsed:
        data = data_to_sensor(group_data)

        data_dict = data.to_dict()
        data_from_dict = sensor_class._from_dict(data_dict)

        assert data == data_from_dict
