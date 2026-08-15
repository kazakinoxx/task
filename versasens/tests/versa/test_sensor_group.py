import asyncio
import dataclasses
import pathlib
import shutil
import stat
import tempfile

import pytest

from src.generated.sensors_info import SENSOR_CLASSES
from src.utils.exceptions import UnknownHeaderError, UnknownSensorError
from src.versa.db import create_import_folder, get_data_for_sensor, get_import_data
from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor import Sensor, SensorParseConfig
from src.versa.sensor_group import (
    SENSOR_ATTR_NAMES,
    SensorGroup,
    _header_to_attr_name,
    data_to_sensor_attr_name,
    sensor_name_to_attr_name,
)

# ========================== sensor_name_to_attr_name ==========================


@pytest.mark.parametrize("sensor_class", SENSOR_CLASSES)
class TestSensorNameToAttrName:
    def test_works(self, sensor_class: type[Sensor]):
        # Check existing sensor names
        assert sensor_name_to_attr_name(sensor_class.name()) == sensor_class.attr_name()

    def test_works_already_attr(self, sensor_class: type[Sensor]):
        # Check if attribute names return the same
        assert (
            sensor_name_to_attr_name(sensor_class.attr_name())
            == sensor_class.attr_name()
        )

    def test_error_if_not_sensor_name(self, sensor_class: type[Sensor]):
        # Check that exception if thrown when not a sensor name is sent
        with pytest.raises(UnknownSensorError, match="not found"):
            sensor_name_to_attr_name("AAA")


# ============================ _header_to_attr_name ============================


class TestHeaderToAttrName:
    @pytest.mark.parametrize("sensor_class", SENSOR_CLASSES)
    def test_works(self, sensor_class: type[Sensor]):
        # Check that headers give correct attribute name
        for header in sensor_class.headers():
            assert _header_to_attr_name(header) == sensor_class.attr_name()

    def test_error_if_invalid_header(self):
        # Check that an exception is thrown when an unknown header is given
        with pytest.raises(UnknownHeaderError):
            _header_to_attr_name(b"\xab\xcd")

        with pytest.raises(UnknownHeaderError):
            _header_to_attr_name(b"")

        with pytest.raises(UnknownHeaderError):
            _header_to_attr_name(b"\xab\xcd\xab\xcd")


# ========================== data_to_sensor_attr_name ==========================


class TestDataToSensorAttrName:
    @pytest.mark.parametrize("sensor_class", SENSOR_CLASSES)
    def test_works(self, sensor_class: type[Sensor]):
        for header in sensor_class.headers():
            data: bytes = header + b"\xaa\xaa"
            assert data_to_sensor_attr_name(bytearray(data)) == sensor_class.attr_name()

    def test_error_if_invalid_header(self):
        with pytest.raises(UnknownHeaderError):
            data_to_sensor_attr_name(bytearray(b""))

        with pytest.raises(UnknownHeaderError):
            data_to_sensor_attr_name(bytearray(b"\xab\xcd"))


# ============================ SensorsData.has_data ============================


class TestHasData:
    @pytest.mark.parametrize("sensor_class", SENSOR_CLASSES)
    def test_works(self, sensor_class: type[Sensor]):
        # Put data inside
        data = SensorGroup()
        assert not data.has_data()

        # Get sensor
        sensor = data._get_sensor(sensor_class.attr_name())

        # Add data
        for field in dataclasses.fields(sensor_class):
            match str(field.type):
                case "list[int]":
                    getattr(sensor, field.name).append(0)
                case "list[float]":
                    getattr(sensor, field.name).append(0.0)
                case "<class 'int'>":
                    setattr(sensor, field.name, 0)
                case "<class 'float'>":
                    setattr(sensor, field.name, 0.0)
                case "list[pyqtgraph.graphicsItems.PlotItem.PlotItem.PlotItem]":
                    pass
                case "list[bytes]":
                    getattr(sensor, field.name).append(b"\xab\xcd")
                case _:
                    raise NotImplementedError(str(field.type))

        assert data.has_data()

    def test_works_with_no_data(self):
        data = SensorGroup()
        assert not data.has_data()


# =========================== SensorsData.get_sensor ===========================


class TestGetSensor:
    @pytest.mark.parametrize("sensor_class", SENSOR_CLASSES)
    def test_works(
        self,
        sensor_class: type[Sensor],
        test_files_parsed: list[SensorGroup],
    ):
        for data in test_files_parsed:
            exp_sensor = getattr(data, sensor_class.attr_name())

            assert exp_sensor == data._get_sensor(sensor_class.name())
            assert exp_sensor == data._get_sensor(sensor_class.attr_name())

    def test_error_if_wrong_name(self):
        data = SensorGroup()

        with pytest.raises(UnknownSensorError):
            data._get_sensor("ABCD")


# ======================= SensorsData._header_to_sensor ========================


class TestHeaderToSensor:
    @pytest.mark.parametrize("sensor_class", SENSOR_CLASSES)
    def test_works(
        self,
        sensor_class: type[Sensor],
        test_files_parsed: list[SensorGroup],
    ):
        for data in test_files_parsed:
            sensor = getattr(data, sensor_class.attr_name())

            for header in sensor_class.headers():
                assert data._header_to_sensor(header) == sensor

    def test_error_if_wrong_header(self):
        data = SensorGroup()

        with pytest.raises(UnknownHeaderError):
            data._header_to_sensor(b"")

        with pytest.raises(UnknownHeaderError):
            data._header_to_sensor(b"\xab\xcd")


# ====================== SensorsData.add_data_from_stream ======================


def test_sensors_data_add_data_from_stream(
    test_files_paths,
    sensor_parse_config: SensorParseConfig,
):
    # No errors if everything went well
    for path in test_files_paths:
        with RawData.from_file(path, WriteLocation.TO_MEMORY) as raw_data:
            SensorGroup().add_raw_data(raw_data, sensor_parse_config)


def test_sensors_data_add_data_from_stream_bad_data(
    test_files_paths,
    sensor_parse_config: SensorParseConfig,
):
    # No errors if everything went well
    for path in test_files_paths:
        with RawData.from_file(path, WriteLocation.TO_MEMORY) as raw_data:
            # Add bad data at the end of the file
            raw_data.go_to_end()
            raw_data.add_data(b"\xab\xcd")
            raw_data.go_to_start()

            # Check that a header exception is raised
            data = SensorGroup()

            with pytest.raises(UnknownHeaderError):
                data.add_raw_data(raw_data, sensor_parse_config)


# ======================== SensorsData.parse_raw_file =========================


def test_sensors_data_parse_raw_file(test_files_paths, config_with_path):
    for path in test_files_paths:
        SensorGroup.parse_raw_file(path, config_path=config_with_path)


def test_sensors_data_parse_raw_file_bad_data(test_files_paths, config_with_path):
    for path in test_files_paths:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy data
            temp_file = pathlib.Path(temp_dir) / path.name
            shutil.copy2(path, temp_file)

            # Corrupt data as the end
            with temp_file.open("ab") as f:
                f.write(b"\xab\xcd")

            with pytest.raises(UnknownHeaderError):
                SensorGroup.parse_raw_file(temp_file, config_path=config_with_path)


def test_sensors_data_parse_raw_file_no_file(config_with_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        dummy_file = pathlib.Path(temp_dir) / "dummy.txt"

        with pytest.raises(FileNotFoundError):
            SensorGroup.parse_raw_file(dummy_file, config_path=config_with_path)


# ======================== SensorsData.parse_and_save_raw_data =========================


class TestParseAndSaveRawData:
    @pytest.mark.asyncio
    async def test_works(
        self,
        test_files_paths: list[pathlib.Path],
        config_with_path: pathlib.Path,
        subject_id: str,
        notes: str,
        random_text_factory,
        tmp_path: pathlib.Path,
    ):
        for test_file in test_files_paths:
            # Copy the file
            test_file_copy = tmp_path / test_file.name
            shutil.copy2(test_file, test_file_copy)

            import_folder = create_import_folder(
                subject_id,
                notes,
                config_with_path,
            )

            filename: str = random_text_factory()

            with RawData.from_file(
                test_file_copy,
                WriteLocation.TO_DISK,
                config_path=config_with_path,
            ) as raw_data:
                SensorGroup.parse_and_save_raw_data(
                    raw_data,
                    import_folder,
                    config_path=config_with_path,
                    raw_file_name=filename,
                )

            # Check that it was parsed
            assert import_folder.exists()
            assert (import_folder / filename).exists()

            # Get expected parsed data
            exp_data = SensorGroup.parse_raw_file(
                test_file_copy,
                config_path=config_with_path,
            )

            # Read parsed data
            _, sample_to_sensor_to_files = get_import_data(import_folder)
            for sensor_to_paths in sample_to_sensor_to_files.values():
                for sensor_name, paths in sensor_to_paths.items():
                    sensor = get_data_for_sensor(sensor_name, paths)
                    exp_sensor = exp_data._get_sensor(sensor_name)

                    assert exp_sensor == sensor

            # Ensure different timestamps
            await asyncio.sleep(1)


# ========================= SensorsData.write_to_disk ==========================


def test_sensors_data_write_to_disk(test_files_parsed, tmp_path):
    for data in test_files_parsed:
        res_files_dict = data.write_to_disk(tmp_path)

        # Check length of dict
        assert len(res_files_dict) == len(SENSOR_ATTR_NAMES)

        # Check all files exist
        for res_lst_files in res_files_dict.values():
            for res_file in res_lst_files:
                assert res_file.exists()


# ========================= SensorsData.from_csv_files =========================


def test_sensors_data_write_to_disk_from_csv_files(test_files_parsed, tmp_path_factory):
    for exp_data in test_files_parsed:
        tmp_path = tmp_path_factory.mktemp("folder")
        res_files_dict = exp_data.write_to_disk(tmp_path)
        res_data = SensorGroup.from_csv_files(res_files_dict)

        assert exp_data == res_data
