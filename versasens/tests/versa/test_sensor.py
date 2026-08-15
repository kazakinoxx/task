"""Module containing tests for the sensor module."""

import copy
import dataclasses
import pathlib
import random
import string
import tempfile
from collections.abc import Callable

import pytest
from pyqtgraph import GraphicsLayoutWidget, PlotDataItem, PlotItem
from pytestqt.qtbot import QtBot

from src.utils.config import Config
from src.utils.constants import DEFAULT_PLOT_X_AXIS_LENGTH
from src.utils.typedefs import DryRun, SensorHeader, WriteBehaviour
from src.versa.raw_data import RawData
from src.versa.sensor import Sensor

# =================================== UTILS ====================================


class DummySensor(Sensor):
    """Dummy sensor class for testing purposes."""

    def plot_graphics(self, graphics: GraphicsLayoutWidget) -> dict[str, PlotDataItem]:  # noqa: ARG002
        return {}

    def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:
        pass

    def parse_file(self, raw_data: RawData, length: int):
        pass

    @staticmethod
    def headers() -> list[SensorHeader]:
        return []


@pytest.fixture
def sensor() -> Sensor:
    return DummySensor()


class NotImplementedSensor(Sensor):
    pass


# ================================ Sensor.headers ================================


class TestSensorHeaders:
    def test_error_if_not_implemented(self):
        with pytest.raises(NotImplementedError):
            NotImplementedSensor.headers()  # pyright: ignore[reportAbstractUsage]


# ================================= Sensor.name ==================================


class TestSensorName:
    def test_works(self, sensor: Sensor):
        assert sensor.name() == "DummySensor"


# =============================== Sensor.attr_name ===============================


class TestSensorAttrName:
    def test_works(self, sensor: Sensor):
        assert sensor.attr_name() == "dummysensor"


# =============================== Sensor.is_empty ================================


class TestSensorIsEmpty:
    def test_works(self, sensor: Sensor):
        assert sensor.is_empty()

        # Add some data
        sensor.idx_list.append(0)
        sensor.last_idx = 0

        assert not sensor.is_empty()


# ==================================== Sensor.clear ====================================


class TestSensorClear:
    def test_works(self, sensor: Sensor, random_int: int):
        graphics = GraphicsLayoutWidget()

        # Add data
        sensor.last_idx = random_int

        for i in range(sensor.last_idx):
            sensor.idx_list.append(i)
            sensor.time_list.append(i)

            sensor.plots.append(graphics.ci.addPlot())

        # Clear sensor
        sensor.clear()

        # Check values
        assert sensor.last_idx == -1
        assert len(sensor.idx_list) == 0
        assert len(sensor.time_list) == 0
        assert len(sensor.plots) == 0

    def test_works_if_already_empty(self, sensor: Sensor):
        # Clear sensor
        sensor.clear()

        # Check values
        assert sensor.last_idx == -1
        assert len(sensor.idx_list) == 0
        assert len(sensor.time_list) == 0
        assert len(sensor.plots) == 0


# ============================= Sensor.plot_graphics =============================


class TestSensorPlotGraphics:
    def test_error_if_not_implemented(self):
        # TypeError as some functions are not implemented
        with pytest.raises(TypeError):
            NotImplementedSensor().plot_graphics(GraphicsLayoutWidget())  # pyright: ignore[reportAbstractUsage]


# ============================= Sensor.set_plot_data =============================


class TestSensorSetPlotData:
    def test_error_if_not_implemented(self):
        # TypeError as some functions are not implemented
        with pytest.raises(TypeError):
            NotImplementedSensor().set_plot_data({})  # pyright: ignore[reportAbstractUsage]


# ============================= Sensor._delete_stale_data ==============================


class TestSensorDeleteStaleData:
    def test_works(self, sensor: Sensor, config: Config):
        # Add some data
        last_time_ms = int(DEFAULT_PLOT_X_AXIS_LENGTH * 1000) * 2

        sensor.idx_list = [0, 1, 2]
        sensor.time_list = [0, last_time_ms // 4, last_time_ms]
        sensor.last_idx = 2

        # Call fct
        sensor._delete_stale_data(config)

        # Check kept only last sample
        assert sensor.last_idx == 2
        assert sensor.idx_list == [2]
        assert sensor.time_list == [last_time_ms]

    def test_does_nothing_if_empty(self, sensor: Sensor, config: Config):
        assert sensor.is_empty()

        sensor_old = copy.deepcopy(sensor)

        # Call fct
        sensor._delete_stale_data(config)

        # Check didn't change
        assert sensor == sensor_old

    def test_does_nothing_if_too_short(self, sensor: Sensor, config: Config):
        # Add some data
        last_time_ms = int(DEFAULT_PLOT_X_AXIS_LENGTH * 1000) // 2

        sensor.idx_list = [0, 1]
        sensor.time_list = [0, last_time_ms]
        sensor.last_idx = 1

        # Call fct
        sensor._delete_stale_data(config)

        # Check nothing changed
        assert sensor.last_idx == 1
        assert sensor.idx_list == [0, 1]
        assert sensor.time_list == [0, last_time_ms]


# ========================= Sensor.update_plot_graphics ==========================


class TestSensorUpdatePlotGraphics:
    def test_sets_new_data(self, random_int: int, config: Config):
        # Create a class that puts a new value in the set_plot_data function
        class _TestSensor(DummySensor):
            def set_plot_data(self, curves: dict[str, PlotDataItem]) -> None:  # noqa: ARG002
                self.last_idx = random_int

        # Call function
        sensor = _TestSensor()
        sensor.update_plot_graphics({}, config)

        # Check changes
        assert sensor.last_idx == random_int

    def test_no_error_if_empty(self, sensor: Sensor, config: Config):
        sensor.update_plot_graphics({}, config)


# =============================== Sensor._to_dict ================================


class TestSensorToDict:
    def test_works(self, random_int: int):
        @dataclasses.dataclass
        class _TestSensor(DummySensor):
            magic: int = random_int

        sensor = _TestSensor()

        exp_dict = {
            "last_idx": -1,
            "idx_list": [],
            "time_list": [],
            "magic": random_int,
        }

        assert sensor.to_dict() == exp_dict


# ============================== Sensor.parse_file ===============================


class TestSensorParseFile:
    def test_error_if_not_implemented(self, raw_data_memory: RawData):
        # TypeError as some functions are not implemented
        with pytest.raises(TypeError):
            NotImplementedSensor().parse_file(raw_data_memory, 0)  # pyright: ignore[reportAbstractUsage]


# ============================== Sensor._from_dict ===============================


class TestSensorFromDict:
    def test_works(self, random_int: int):
        @dataclasses.dataclass
        class _TestSensor(DummySensor):
            magic: int = -1

        exp = _TestSensor(magic=random_int)

        # Update the magic attribute
        res = _TestSensor()._from_dict({"magic": random_int})

        assert res.magic != -1
        assert res.magic == random_int
        assert exp.magic == res.magic
        assert exp == res

    def test_error_if_new_attribute(self, sensor: Sensor):
        # Verify that magic is not inside the class
        assert "magic" not in vars(sensor)

        # Update the magic attribute
        with pytest.raises(KeyError):
            sensor._from_dict({"magic": 0})

    def test_works_if_empty(self, sensor: Sensor):
        res = DummySensor()._from_dict({})
        assert sensor == res


# ================================= Sensor._write_csvs =================================


class TestSensorWriteCSVs:
    def test_works(self, tmp_path: pathlib.Path, sensor: Sensor):
        # Put some data
        magic_value = random.randint(0, 100)
        lst_len = random.randint(1, 10)

        for i in range(lst_len):
            sensor.idx_list.append(i)
            sensor.time_list.append(magic_value)

        sensor.last_idx = lst_len - 1

        # Get results
        file_path = tmp_path / "out.csv"
        sensor._write_csvs(
            [file_path],
            WriteBehaviour.OVERWRITE,
            dry_run=DryRun.WRITE,
        )

        # Check file was created
        assert file_path.exists()
        assert file_path.stat().st_size > 0

        # Read data
        res = file_path.read_text(encoding="utf-8")

        # Check content
        res_lines = res.splitlines()

        # Check the number of lines
        assert len(res_lines) == lst_len + 1

        # Check header
        assert res_lines[0] == "idx_list,time_list"

        # Check lines
        for i in range(lst_len):
            assert res_lines[i + 1] == f"{i},{magic_value}"

        # Check that the last line has the last_idx
        assert res_lines[-1] == f"{sensor.last_idx},{magic_value}"

    def test_dry_run(self, tmp_path: pathlib.Path, sensor: Sensor):
        # Put some data
        magic_value = random.randint(0, 100)
        lst_len = random.randint(1, 10)

        for i in range(lst_len):
            sensor.idx_list.append(i)
            sensor.time_list.append(magic_value)

        sensor.last_idx = lst_len - 1

        # Get results
        file_path = tmp_path / "out.csv"
        sensor._write_csvs(
            [file_path],
            WriteBehaviour.OVERWRITE,
            dry_run=DryRun.NO_WRITES,
        )

        # Check file was not created
        assert not file_path.exists()

    def test_no_writes_if_empty(self, tmp_path: pathlib.Path, sensor: Sensor):
        assert sensor.is_empty()

        file_path = tmp_path / "out.csv"
        sensor._write_csvs(
            [file_path],
            WriteBehaviour.OVERWRITE,
            dry_run=DryRun.WRITE,
        )

        assert not file_path.exists()

    def test_error_if_different_list_lengths(
        self,
        tmp_path: pathlib.Path,
        sensor: Sensor,
    ):
        sensor.idx_list.append(0)

        assert len(sensor.time_list) != len(sensor.idx_list)
        file_path = tmp_path / "out.csv"

        with pytest.raises(ValueError, match="Received multiple list lengths"):
            sensor._write_csvs(
                [file_path],
                WriteBehaviour.OVERWRITE,
                dry_run=DryRun.WRITE,
            )

    def test_error_if_wrong_number_of_files(
        self,
        tmp_path: pathlib.Path,
        sensor: Sensor,
    ):
        # Put data so it is not empty
        magic_value = random.randint(0, 100)
        lst_len = random.randint(1, 10)

        for i in range(lst_len):
            sensor.idx_list.append(i)
            sensor.time_list.append(magic_value)

        file_path = tmp_path / "out.csv"

        with pytest.raises(ValueError, match="Received wrong number of file paths"):
            sensor._write_csvs(
                [file_path, file_path],
                WriteBehaviour.OVERWRITE,
                dry_run=DryRun.WRITE,
            )

        with pytest.raises(ValueError, match="Received wrong number of file paths"):
            sensor._write_csvs(
                [],
                WriteBehaviour.OVERWRITE,
                dry_run=DryRun.WRITE,
            )

    def test_overwrite_works(self, tmp_path: pathlib.Path, sensor: Sensor):
        # Put some data
        magic_value = random.randint(0, 100)
        lst_len = random.randint(1, 10)

        for i in range(lst_len):
            sensor.idx_list.append(i)
            sensor.time_list.append(magic_value)

        sensor.last_idx = lst_len - 1

        # Write twice
        nbr_writes = random.randint(2, 4)

        file_path = tmp_path / "out.csv"
        for _ in range(nbr_writes):
            sensor._write_csvs(
                [file_path],
                WriteBehaviour.OVERWRITE,
                dry_run=DryRun.WRITE,
            )

        # Check file was created
        assert file_path.exists()
        assert file_path.stat().st_size > 0

        # Read data
        res = file_path.read_text(encoding="utf-8")

        # Check content
        res_lines = res.splitlines()

        # Check the number of lines
        assert len(res_lines) == lst_len + 1

        # Check header
        assert res_lines[0] == "idx_list,time_list"

        # Check lines
        for i in range(lst_len):
            assert res_lines[i + 1] == f"{i},{magic_value}"

    def test_append_works(self, tmp_path: pathlib.Path, sensor: Sensor):
        # Put some data
        magic_value = random.randint(0, 100)
        lst_len = random.randint(1, 10)

        for i in range(lst_len):
            sensor.idx_list.append(i)
            sensor.time_list.append(magic_value)

        sensor.last_idx = lst_len - 1

        # Write twice
        nbr_writes = random.randint(2, 4)

        file_path = tmp_path / "out.csv"
        for _ in range(nbr_writes):
            sensor._write_csvs(
                [file_path],
                WriteBehaviour.APPEND,
                dry_run=DryRun.WRITE,
            )

        # Check file was created
        assert file_path.exists()
        assert file_path.stat().st_size > 0

        # Read data
        res = file_path.read_text(encoding="utf-8")

        # Check content
        res_lines = res.splitlines()

        # Check the number of lines
        assert len(res_lines) == (lst_len * nbr_writes) + 1

        # Check header
        assert res_lines[0] == "idx_list,time_list"

        for i_write in range(nbr_writes):
            start_index = i_write * lst_len + 1

            # Check lines
            for i in range(lst_len):
                assert res_lines[i + start_index] == f"{i},{magic_value}"


# ============================ Sensor._csv_filenames =============================


class TestSensorCsvFilenames:
    def test_works(self, random_text: str):
        @dataclasses.dataclass
        class _TestSensor(DummySensor):
            @classmethod
            def name(cls) -> str:
                return random_text

        sensor = _TestSensor()
        assert sensor._csv_filenames() == [f"{random_text}.csv"]


# ============================== Sensor.write_data ===============================


class TestSensorWriteData:
    def test_works(self, sensor: Sensor, tmp_path: pathlib.Path):
        # Add some data
        magic_idx = random.randint(0, 100)
        magic_time = random.randint(0, 100)

        sensor.idx_list.append(magic_idx)
        sensor.time_list.append(magic_time)
        sensor.last_idx = magic_idx

        # Write data
        res_files = sensor.write_data(tmp_path)

        # Check results
        assert len(res_files) == 1
        assert res_files[0].name == "DummySensor.csv"
        assert res_files[0].parent == tmp_path

        # Check contents
        with res_files[0].open("r") as f:
            lines = f.read().splitlines()
            assert len(lines) == 2
            assert lines[0] == "idx_list,time_list"
            assert lines[1] == f"{magic_idx},{magic_time}"

    def test_works_if_no_data(self, sensor: Sensor, tmp_path: pathlib.Path):
        assert sensor.write_data(tmp_path) == []

    def test_error_if_folder_doesnt_exist(
        self,
        sensor: Sensor,
        tmp_path: pathlib.Path,
    ):
        folder_path = tmp_path / "dummy"

        # Add some data
        # Only want an error if data is present
        sensor.idx_list.append(0)
        sensor.time_list.append(0)
        sensor.last_idx = 0

        assert not folder_path.exists()

        with pytest.raises(FileNotFoundError):
            sensor.write_data(folder_path)


# ============================ Sensor._csv_row_str_type_conv ===========================


class TestSensorCsvRowStrTypeConv:
    def test_works(self, random_int: int):
        assert (
            Sensor._csv_row_str_type_conv("list[int]", "col1", str(random_int))
            == random_int
        )
        assert (
            Sensor._csv_row_str_type_conv("list[float]", "col2", str(random_int))
            == random_int
        )
        assert Sensor._csv_row_str_type_conv("list[bytes]", "col3", "hello") == "hello"

        rnd_str = "".join(random.choices(string.ascii_lowercase, k=10))

        with pytest.raises(ValueError, match="Unknown type"):
            Sensor._csv_row_str_type_conv(f"list[{rnd_str}]", "col4", "data")


# ================================ Sensor.from_csv_files ===============================


class TestSensorFromCsvFiles:
    def test_error_if_invalid_header(self, sensor: Sensor, tmp_path: pathlib.Path):
        # Add a new value in the CSV
        rnd_str = "".join(random.choices(string.ascii_lowercase, k=10))

        magic_idx = random.randint(0, 100)
        magic_time = random.randint(0, 100)
        magic_attr = random.randint(0, 100)

        # Add some data
        sensor.idx_list.append(magic_idx)
        sensor.time_list.append(magic_time)
        sensor.last_idx = magic_idx

        # Get CSVs
        file_path = tmp_path / "out.csv"
        sensor._write_csvs(
            [file_path],
            WriteBehaviour.OVERWRITE,
            dry_run=DryRun.WRITE,
        )

        csv_str = file_path.read_text(encoding="utf-8")

        # Manually prepend a new column
        lines = csv_str.splitlines(keepends=True)
        lines[0] = f"{rnd_str},{lines[0]}"
        lines[1] = f"{magic_attr},{lines[1]}"

        # Recreate CSV string
        new_csv_str = "".join(lines)

        with tempfile.TemporaryDirectory() as folder:
            folder_path = pathlib.Path(folder)
            file_path = folder_path / "dummy.csv"

            # Write the new CSV string to a file
            with file_path.open("w") as f:
                f.write(new_csv_str)

            # Check that error is raised
            with pytest.raises(ValueError, match=f"Key {rnd_str} not in"):
                DummySensor().from_csv_files([file_path])

    def test_error_if_empty_csv(self, tmp_path: pathlib.Path):
        file_path = tmp_path / "dummy.csv"

        # Write the new CSV string to a file
        with file_path.open("w") as f:
            f.write("")

        # Check that error is raised
        with pytest.raises(ValueError, match="No field names found in given CSV"):
            DummySensor().from_csv_files([file_path])

    def test_error_if_file_does_not_exist(self, tmp_path: pathlib.Path):
        file_path = tmp_path / "dummy.csv"

        # Check that error is raised
        with pytest.raises(FileNotFoundError, match="does not exist"):
            DummySensor().from_csv_files([file_path])

    def test_error_if_given_folder(self, tmp_path: pathlib.Path):
        # Check that error is raised
        with pytest.raises(ValueError, match="is not a file"):
            DummySensor().from_csv_files([tmp_path])

    def test_works(self, tmp_path: pathlib.Path):
        magic_idx = random.randint(0, 100)
        magic_time = random.randint(0, 100)

        # Get CSVs
        csv_str = "\n".join(
            [
                "idx_list,time_list",
                f"{magic_idx},{magic_time}",
            ],
        )

        file_path = tmp_path / "dummy.csv"

        # Write the new CSV string to a file
        with file_path.open("w") as f:
            f.write(csv_str)

        # Recreate instance from CSV string
        res = DummySensor().from_csv_files([file_path])

        # Check values
        assert res.idx_list == [magic_idx]
        assert res.time_list == [magic_time]
        assert res.last_idx == magic_idx

    def test_to_from_csv_files(self, sensor: Sensor, tmp_path: pathlib.Path):
        magic_idx = random.randint(0, 100)
        magic_time = random.randint(0, 100)

        # Add some data
        sensor.idx_list.append(magic_idx)
        sensor.time_list.append(magic_time)
        sensor.last_idx = magic_idx

        # Get CSVs
        csv_paths = sensor.write_data(tmp_path)

        # Recreate instance from CSV string
        res = DummySensor().from_csv_files(csv_paths)

        # Check values
        assert res.idx_list == [magic_idx]
        assert res.time_list == [magic_time]
        assert res.last_idx == magic_idx

    def test_to_from_csv_files_empty(self, sensor: Sensor, tmp_path: pathlib.Path):
        # Get CSVs
        csv_paths = sensor.write_data(tmp_path)

        # Recreate instance from CSV string
        res = DummySensor().from_csv_files(csv_paths)

        # Check values
        assert res.idx_list == []
        assert res.time_list == []
        assert res.last_idx == -1
