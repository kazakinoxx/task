"""Module containing code that is run before tests start."""

import os
import pathlib
import random
import string
import sys
from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from src.utils.config import Config, get_or_create_config, update_config
from src.utils.paths import DLLS_PATH, ROOT_PATH
from src.utils.time import get_now
from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor import SensorParseConfig
from src.versa.sensor_group import SensorGroup


def pytest_sessionstart():
    if sys.platform == "win32":
        # Add DLLs to path before imports
        os.add_dll_directory(str(DLLS_PATH.resolve()))
        os.environ["PATH"] += f";{DLLS_PATH.resolve()}"
        sys.path.insert(0, str(DLLS_PATH.resolve()))


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    timestamp = get_now().strftime("%Y%m%d_%H%M%S")

    reports_path = ROOT_PATH / "tests" / "reports"

    if config.option.htmlpath:
        config.option.htmlpath = reports_path / f"report_{timestamp}.html"

    if config.option.xmlpath:
        config.option.xmlpath = reports_path / f"results_{timestamp}.xml"


# ======================================= Mocks ========================================


@pytest.fixture
def magic_mock() -> MagicMock:
    return MagicMock()


# ======================================= Config =======================================


@pytest.fixture
def sensor_parse_config() -> SensorParseConfig:
    return {"ads_gain": 12, "ads_vref": 4}


@pytest.fixture
def config(tmp_path_factory) -> Config:
    """Create a temporary config file and database directory."""
    tmp_path = tmp_path_factory.mktemp("config")
    config_path = tmp_path / "config.json"
    db_path = tmp_path / "db"
    db_path.mkdir()

    # Yield the paths to the test
    return get_or_create_config(config_path)


@pytest.fixture
def config_with_path(tmp_path_factory) -> pathlib.Path:
    """Create a temporary config file and database directory."""
    tmp_path = tmp_path_factory.mktemp("config")
    config_path = tmp_path / "config.json"
    db_path = tmp_path / "db"
    db_path.mkdir()
    update_config(db_path=db_path, config_file_path=config_path)

    # Yield the paths to the test
    return config_path


@pytest.fixture
def config_with_path_and_db(tmp_path_factory) -> tuple[pathlib.Path, pathlib.Path]:
    """Create a temporary config file and database directory."""
    tmp_path = tmp_path_factory.mktemp("config")
    config_path = tmp_path / "config.json"
    db_path = tmp_path / "db"
    db_path.mkdir()
    update_config(db_path=db_path, config_file_path=config_path)

    # Yield the paths to the test
    return config_path, db_path


@pytest.fixture
def sensor_group() -> SensorGroup:
    """Blank SensorGroup instance."""
    return SensorGroup()


# ====================================== Raw data ======================================


@pytest.fixture
def raw_data_memory_factory() -> Callable[[], RawData]:
    def _factory() -> RawData:
        return RawData(WriteLocation.TO_MEMORY)

    return _factory


@pytest.fixture
def raw_data_memory(raw_data_memory_factory) -> RawData:
    return raw_data_memory_factory()


@pytest.fixture
def raw_data_disk_factory(config_with_path) -> Callable[[], RawData]:
    def _factory() -> RawData:
        return RawData(WriteLocation.TO_DISK, config_path=config_with_path)

    return _factory


@pytest.fixture
def raw_data_disk(raw_data_disk_factory) -> RawData:
    return raw_data_disk_factory()


# ==================================== Random bytes ====================================


@pytest.fixture
def random_bytes_factory() -> Callable[[], bytes]:
    def _factory() -> bytes:
        return random.randbytes(20)

    return _factory


@pytest.fixture
def random_bytes(random_bytes_factory) -> bytes:
    return random_bytes_factory()


# ==================================== Random ints =====================================


@pytest.fixture
def random_int_factory() -> Callable[[], int]:
    def _factory() -> int:
        return random.randint(0, 100)

    return _factory


@pytest.fixture
def random_int(random_int_factory) -> int:
    return random_int_factory()


# =================================== Random floats ====================================


@pytest.fixture
def random_float_factory() -> Callable[[], float]:
    def _factory() -> float:
        return random.random() * 100.0

    return _factory


@pytest.fixture
def random_float(random_float_factory) -> float:
    return random_float_factory()


# ==================================== Random text =====================================


@pytest.fixture
def random_text_factory():
    def _factory(nbr_letters: int = 10, prefix: str = "") -> str:
        return prefix + "".join(random.choices(string.ascii_letters, k=nbr_letters))

    return _factory


@pytest.fixture
def random_text(random_text_factory) -> str:
    return random_text_factory(nbr_letters=10)


@pytest.fixture
def subject_id(random_text_factory) -> str:
    return random_text_factory(nbr_letters=10, prefix="subject_")


# TODO: use fixtures for all tests


@pytest.fixture
def notes(random_text_factory) -> str:
    return random_text_factory(nbr_letters=20, prefix="notes_")


# ===================================== Test files =====================================

_TEST_FILES_FOLDER = ROOT_PATH / "tests" / "test_files"
_TEST_FILE_NAMES = ["file1.TXT", "file2.TXT"]

_TEST_FILES = [_TEST_FILES_FOLDER / name for name in _TEST_FILE_NAMES]


def _split_raw_file_into_samples(
    raw_file_path: pathlib.Path,
    sensor_parse_config: SensorParseConfig,
) -> list[bytes]:
    all_bytes = raw_file_path.read_bytes()
    chunks: list[bytes] = []

    with RawData.from_bytes(all_bytes, WriteLocation.TO_MEMORY) as raw_data:
        data = SensorGroup()

        last_start = 0

        while not data.add_data_single_read(raw_data, sensor_parse_config)[0]:
            cur_pos = raw_data.tell()
            chunks.append(all_bytes[last_start:cur_pos])
            last_start = cur_pos

    return chunks


@pytest.fixture
def test_files_paths() -> list[pathlib.Path]:
    return _TEST_FILES


@pytest.fixture
def test_file(test_files_paths: list[pathlib.Path]) -> pathlib.Path:
    return test_files_paths[0]


@pytest.fixture
def test_files_chunks(
    test_files_paths: list[pathlib.Path],
    sensor_parse_config: SensorParseConfig,
) -> list[list[bytes]]:
    return [
        _split_raw_file_into_samples(f, sensor_parse_config) for f in test_files_paths
    ]


@pytest.fixture
def test_file_chunks(
    test_file: pathlib.Path,
    sensor_parse_config: SensorParseConfig,
) -> list[bytes]:
    return _split_raw_file_into_samples(test_file, sensor_parse_config)


@pytest.fixture
def test_files_parsed_dict(
    test_files_paths: list[pathlib.Path],
    config_with_path: pathlib.Path,
) -> dict[pathlib.Path, SensorGroup]:
    return {
        p: SensorGroup.parse_raw_file(p, config_path=config_with_path)
        for p in test_files_paths
    }


@pytest.fixture
def test_files_parsed(
    test_files_paths: list[pathlib.Path],
    config_with_path: pathlib.Path,
) -> list[SensorGroup]:
    return [
        SensorGroup.parse_raw_file(p, config_path=config_with_path)
        for p in test_files_paths
    ]


@pytest.fixture
def test_files_chunks_and_parsed(
    test_files_chunks: list[list[bytes]],
    test_files_parsed: list[SensorGroup],
) -> list[tuple[list[bytes], SensorGroup]]:
    return list(zip(test_files_chunks, test_files_parsed, strict=True))


@pytest.fixture
def test_files_path_chunks_and_parsed(
    test_files_paths: list[pathlib.Path],
    test_files_chunks: list[list[bytes]],
    test_files_parsed: list[SensorGroup],
) -> list[tuple[pathlib.Path, list[bytes], SensorGroup]]:
    return list(
        zip(test_files_paths, test_files_chunks, test_files_parsed, strict=True),
    )
