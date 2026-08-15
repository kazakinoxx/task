import datetime
import math
import os
import tempfile
from pathlib import Path

import pytest

from src.utils.constants import RAW_EST_BYTES_PER_MS
from src.utils.exceptions import RawDataError, RawDataStateError
from src.versa.raw_data import RawData, WriteLocation

# ====================================== Fixtures ======================================


@pytest.fixture
def raw_data_skip_init() -> RawData:
    # Create raw data without going through __init__
    raw_data = object.__new__(RawData)

    # Initialize state
    raw_data.mem_buffer = None
    raw_data.temp_file_path = None
    raw_data.opened_file = None
    raw_data.config_path = None

    return raw_data


# ====================================== __init__ ======================================


class TestInitDisk:
    def test_error_if_disk_and_no_config_path(self):
        with pytest.raises(
            RawDataStateError,
            match="Path to the config file is missing while trying to write to disk.",
        ):
            RawData(WriteLocation.TO_DISK)

    def test_works(self, config_with_path: Path):
        RawData(WriteLocation.TO_DISK, config_path=config_with_path)

    def test_correct_initialize(self, config_with_path: Path):
        raw_data = RawData(WriteLocation.TO_DISK, config_path=config_with_path)

        # Check file created, exists and opened
        assert raw_data.temp_file_path is not None
        assert raw_data.temp_file_path.exists()

        assert raw_data.opened_file is not None
        assert not raw_data.opened_file.closed

        # Check buffer not created
        assert raw_data.mem_buffer is None

    def test_adds_initial_bytes(self, config_with_path: Path, random_bytes: bytes):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        # Check file created and contains bytes
        assert raw_data.temp_file_path is not None

        res_bytes = raw_data.temp_file_path.read_bytes()
        assert res_bytes == random_bytes

    def test_is_at_start_after_initial_bytes(
        self,
        config_with_path: Path,
        random_bytes: bytes,
    ):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        # Check file created and is at start
        assert raw_data.opened_file is not None
        assert raw_data.opened_file.tell() == 0


class TestInitMemory:
    def test_works(self):
        RawData(WriteLocation.TO_MEMORY)

    def test_correct_initialize(self):
        raw_data = RawData(WriteLocation.TO_MEMORY)

        # Check no file created
        assert raw_data.temp_file_path is None
        assert raw_data.opened_file is None

        # Check buffer created and not closed
        assert raw_data.mem_buffer is not None
        assert not raw_data.mem_buffer.closed

    def test_adds_initial_bytes(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        # Check buffer created and contains the bytes
        assert raw_data.mem_buffer is not None
        assert raw_data.mem_buffer.getvalue() == random_bytes

    def test_is_at_start_after_initial_bytes(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        # Check buffer created and is at start
        assert raw_data.mem_buffer is not None
        assert raw_data.mem_buffer.tell() == 0


# =============================== _initialize_temp_file ================================


class TestInitializeTempFile:
    def test_error_if_file_already_opened(
        self,
        raw_data_skip_init,
        tmp_path,
        config_with_path,
    ):
        # Add an opened file
        file_path = tmp_path / "tmp.file"
        raw_data_skip_init.opened_file = file_path.open("w")

        # Call function
        with pytest.raises(
            RawDataStateError,
            match="The RawData instance already has an opened file",
        ):
            raw_data_skip_init._initialize_temp_file(config_with_path)

    def test_error_if_file_already_created(
        self,
        raw_data_skip_init,
        tmp_path,
        config_with_path,
    ):
        # Add a file path
        file_path = tmp_path / "tmp.file"
        raw_data_skip_init.temp_file_path = file_path

        # Call function
        with pytest.raises(
            RawDataStateError,
            match="The RawData instance already has a temporary file",
        ):
            raw_data_skip_init._initialize_temp_file(config_with_path)

    def test_error_if_not_writing_to_disk(
        self,
        raw_data_skip_init,
        config_with_path,
    ):
        # Add writing to memory
        raw_data_skip_init.write_location = WriteLocation.TO_MEMORY

        # Call function
        with pytest.raises(
            RawDataStateError,
            match="Trying to initialize a temporary file while writing to disk",
        ):
            raw_data_skip_init._initialize_temp_file(config_with_path)

    def test_works_if_no_config_at_path(
        self,
        raw_data_skip_init: RawData,
        tmp_path: Path,
    ):
        # Add writing to disk
        raw_data_skip_init.write_location = WriteLocation.TO_DISK

        # Link to blank config path
        config_path = tmp_path / "config.json"
        assert not config_path.exists()

        # Call function
        raw_data_skip_init._initialize_temp_file(config_path)

        # Delete temp file manually
        if raw_data_skip_init.temp_file_path is not None:
            raw_data_skip_init.temp_file_path.unlink()

    def test_works_if_db_folder_doesnt_exist(
        self,
        raw_data_skip_init: RawData,
        config_with_path_and_db: tuple[Path, Path],
    ):
        # Add writing to disk
        raw_data_skip_init.write_location = WriteLocation.TO_DISK

        # Delete db path
        config_path, db_path = config_with_path_and_db
        db_path.rmdir()
        assert not db_path.exists()

        # Call function
        raw_data_skip_init._initialize_temp_file(config_path)

    def test_doesnt_open_file(
        self,
        raw_data_skip_init: RawData,
        config_with_path: Path,
    ):
        # Add writing to disk
        raw_data_skip_init.write_location = WriteLocation.TO_DISK

        # Call function
        raw_data_skip_init._initialize_temp_file(config_with_path)

        # Check that the file is not opened by trying to delete it
        assert raw_data_skip_init.opened_file is None
        assert raw_data_skip_init.temp_file_path is not None
        assert raw_data_skip_init.temp_file_path.exists()

        raw_data_skip_init.temp_file_path.unlink()

    def test_file_is_created(
        self,
        raw_data_skip_init: RawData,
        config_with_path: Path,
    ):
        # Add writing to disk
        raw_data_skip_init.write_location = WriteLocation.TO_DISK

        # Call function
        raw_data_skip_init._initialize_temp_file(config_with_path)

        # Check that the temp file was created
        assert raw_data_skip_init.temp_file_path is not None
        assert raw_data_skip_init.temp_file_path.exists()

    def test_error_if_temp_file_not_created(
        self,
        raw_data_skip_init: RawData,
        config_with_path: Path,
        monkeypatch,
    ):
        # Add writing to disk
        raw_data_skip_init.write_location = WriteLocation.TO_DISK

        # Patch so tempfile.mkstemp doesn't create the file
        # and so os.close is not called
        def _fake_mkstemp(*args, **kwargs) -> tuple[int, str]:  # noqa: ANN002, ARG001
            return (123, "fake.file")

        def _fake_close(*args, **kwargs) -> None:  # noqa: ANN002
            pass

        monkeypatch.setattr(tempfile, "mkstemp", _fake_mkstemp)
        monkeypatch.setattr(os, "close", _fake_close)

        # Check that error is raised
        with pytest.raises(FileNotFoundError, match="Failed to create temp file"):
            raw_data_skip_init._initialize_temp_file(config_with_path)

    def test_error_if_initialize_twice(
        self,
        raw_data_skip_init: RawData,
        config_with_path: Path,
    ):
        # Add writing to disk
        raw_data_skip_init.write_location = WriteLocation.TO_DISK

        # Call function
        raw_data_skip_init._initialize_temp_file(config_with_path)

        # Check that error is raised
        with pytest.raises(RawDataError):
            raw_data_skip_init._initialize_temp_file(config_with_path)

    def test_works(
        self,
        raw_data_skip_init: RawData,
        config_with_path: Path,
    ):
        # Add writing to disk
        raw_data_skip_init.write_location = WriteLocation.TO_DISK

        # Call function
        res_tmp_file = raw_data_skip_init._initialize_temp_file(config_with_path)

        # Check that the temp file was created
        assert raw_data_skip_init.temp_file_path is not None
        assert raw_data_skip_init.temp_file_path.exists()

        # Check returned the correct file
        assert res_tmp_file == raw_data_skip_init.temp_file_path

        # Check the memory buffer was not created
        assert raw_data_skip_init.mem_buffer is None

        # Check that the file was not opened
        assert raw_data_skip_init.opened_file is None


# ==================================== Large files =====================================


@pytest.mark.slow
@pytest.mark.parametrize(
    ("time_delta"),
    [
        pytest.param(datetime.timedelta(minutes=1), id="1 minute"),
        pytest.param(datetime.timedelta(minutes=5), id="5 minutes"),
        pytest.param(datetime.timedelta(minutes=10), id="10 minutes"),
        pytest.param(datetime.timedelta(minutes=15), id="15 minutes"),
        pytest.param(datetime.timedelta(minutes=30), id="30 minutes"),
        pytest.param(datetime.timedelta(hours=1), id="1 hour"),
        pytest.param(datetime.timedelta(hours=2), id="2 hours"),
        pytest.param(datetime.timedelta(hours=5), id="5 hours"),
        pytest.param(datetime.timedelta(hours=10), id="10 hours"),
    ],
)
def test_handles_large_files(
    test_file: Path,
    test_file_chunks: list[bytes],
    raw_data_disk: RawData,
    time_delta: datetime.timedelta,
):
    # Get estimated number of bytes needed
    duration_ms = time_delta.total_seconds() * 1000.0
    est_bytes = int(duration_ms * RAW_EST_BYTES_PER_MS)

    # Get the number of copies of the file that needs to be given
    base_file_nbr_bytes = test_file.stat().st_size
    nbr_files = math.ceil(est_bytes / base_file_nbr_bytes)

    # Open raw data
    raw_data_disk.open()

    # Add the chunks in the raw data
    for _ in range(nbr_files):
        for chunk in test_file_chunks:
            raw_data_disk.add_data(chunk)

    # Get underlying file
    raw_file = raw_data_disk.temp_file_path
    assert raw_file is not None

    # Check correct length
    exp_length = base_file_nbr_bytes * nbr_files
    assert raw_file.stat().st_size == exp_length

    # Check contents
    base_file_bytes = test_file.read_bytes()

    with raw_file.open("rb") as f:
        for _ in range(nbr_files):
            raw_file_part = f.read(base_file_nbr_bytes)
            assert raw_file_part == base_file_bytes


# ==================================== copy_file ====================================


class TestCopyFile:
    def test_works_disk(
        self, config_with_path: Path, tmp_path: Path, random_bytes: bytes
    ):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        destination = tmp_path / "copied.raw"

        # Copy file
        raw_data.copy_file(destination)

        # Check file exists
        assert destination.exists()
        assert destination.read_bytes() == random_bytes

    def test_works_memory(self, tmp_path: Path, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        destination = tmp_path / "copied.raw"

        # Copy file
        raw_data.copy_file(destination)

        # Check file exists
        assert destination.exists()
        assert destination.read_bytes() == random_bytes

    def test_error_if_disk_no_file(self, config_with_path: Path, tmp_path: Path):
        raw_data = RawData(WriteLocation.TO_DISK, config_path=config_with_path)
        # Manually clear the temp file path to simulate missing file
        raw_data.temp_file_path = None

        destination = tmp_path / "copied.raw"

        with pytest.raises(RawDataStateError, match="no created file"):
            raw_data.copy_file(destination)

    def test_error_if_memory_no_buffer(self, tmp_path: Path):
        raw_data = RawData(WriteLocation.TO_MEMORY)
        # Manually clear buffer to simulate missing buffer
        raw_data.mem_buffer = None

        destination = tmp_path / "copied.raw"

        with pytest.raises(RawDataStateError, match="no created buffer"):
            raw_data.copy_file(destination)


# ==================================== has_data ====================================


class TestHasData:
    def test_returns_true_if_data_disk(
        self, config_with_path: Path, random_bytes: bytes
    ):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )
        assert raw_data.has_data()

    def test_returns_false_if_no_data_disk(self, config_with_path: Path):
        raw_data = RawData(WriteLocation.TO_DISK, config_path=config_with_path)
        assert not raw_data.has_data()

    def test_returns_true_if_data_memory(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)
        assert raw_data.has_data()

    def test_returns_false_if_no_data_memory(self):
        raw_data = RawData(WriteLocation.TO_MEMORY)
        assert not raw_data.has_data()

    def test_error_if_disk_no_file(self, config_with_path: Path):
        raw_data = RawData(WriteLocation.TO_DISK, config_path=config_with_path)
        raw_data.temp_file_path = None

        with pytest.raises(RawDataStateError, match="Temporary file was not created"):
            raw_data.has_data()

    def test_error_if_memory_no_buffer(self):
        raw_data = RawData(WriteLocation.TO_MEMORY)
        raw_data.mem_buffer = None

        with pytest.raises(RawDataStateError, match="Buffer was not created"):
            raw_data.has_data()


# ==================================== get_file_path ====================================


class TestGetFilePath:
    def test_works_disk(self, config_with_path: Path):
        raw_data = RawData(WriteLocation.TO_DISK, config_path=config_with_path)
        result = raw_data.get_file_path()

        assert result is not None
        assert result == raw_data.temp_file_path
        assert result.exists()

    def test_error_if_memory(self):
        raw_data = RawData(WriteLocation.TO_MEMORY)

        with pytest.raises(
            ValueError, match="Cannot get file path if not writing to disk"
        ):
            raw_data.get_file_path()

    def test_error_if_disk_no_file(self, config_with_path: Path):
        raw_data = RawData(WriteLocation.TO_DISK, config_path=config_with_path)
        raw_data.temp_file_path = None

        with pytest.raises(RawDataStateError, match="Temporary file was not created"):
            raw_data.get_file_path()


# ==================================== Additional RawData Methods =========================


class TestRawDataMethods:
    def test_read_disk(self, config_with_path: Path, random_bytes: bytes):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        # Read all bytes
        result = raw_data.read()
        assert result == random_bytes

        # Read with size
        raw_data.go_to_start()
        half = len(random_bytes) // 2
        result = raw_data.read(half)
        assert result == random_bytes[:half]

    def test_read_memory(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        result = raw_data.read()
        assert result == random_bytes

    def test_add_data_disk(self, config_with_path: Path):
        raw_data = RawData(WriteLocation.TO_DISK, config_path=config_with_path)

        # Add some data
        data1 = b"hello"
        data2 = b"world"
        raw_data.add_data(data1)
        raw_data.add_data(data2)

        # Check contents
        raw_data.go_to_start()
        result = raw_data.read()
        assert result == data1 + data2

    def test_add_data_memory(self):
        raw_data = RawData(WriteLocation.TO_MEMORY)

        data1 = b"hello"
        data2 = b"world"
        raw_data.add_data(data1)
        raw_data.add_data(data2)

        result = raw_data.get_contents()
        assert result == data1 + data2

    def test_go_to_start_disk(self, config_with_path: Path, random_bytes: bytes):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        # Read some data
        _ = raw_data.read(10)

        # Go to start
        raw_data.go_to_start()

        # Read again and get same data
        result = raw_data.read(10)
        assert result == random_bytes[:10]

    def test_go_to_start_memory(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        _ = raw_data.read(10)
        raw_data.go_to_start()

        result = raw_data.read(10)
        assert result == random_bytes[:10]

    def test_go_to_end_disk(self, config_with_path: Path, random_bytes: bytes):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        raw_data.go_to_start()
        _ = raw_data.read(10)

        raw_data.go_to_end()

        # Check position is at end
        assert raw_data.tell() == len(random_bytes)

    def test_go_to_end_memory(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        raw_data.go_to_start()
        _ = raw_data.read(10)

        raw_data.go_to_end()

        assert raw_data.tell() == len(random_bytes)

    def test_get_contents_disk(self, config_with_path: Path, random_bytes: bytes):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        result = raw_data.get_contents()
        assert result == random_bytes

    def test_get_contents_memory(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        result = raw_data.get_contents()
        assert result == random_bytes

    def test_tell_disk(self, config_with_path: Path, random_bytes: bytes):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        assert raw_data.tell() == 0

        raw_data.read(10)
        assert raw_data.tell() == 10

    def test_tell_memory(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        assert raw_data.tell() == 0

        raw_data.read(10)
        assert raw_data.tell() == 10

    def test_clear_disk(self, config_with_path: Path, random_bytes: bytes):
        raw_data = RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        )

        assert raw_data.has_data()

        old_temp_path = raw_data.temp_file_path
        assert old_temp_path is not None

        raw_data.clear()

        # Re-open file to check position
        raw_data.open()

        # Check data is cleared
        assert not raw_data.has_data()
        assert raw_data.tell() == 0

        # Check new file was created
        new_temp_path = raw_data.temp_file_path
        assert new_temp_path is not None
        assert new_temp_path != old_temp_path
        assert new_temp_path.exists()

        # Clean up old file if it still exists
        if old_temp_path.exists():
            old_temp_path.unlink()

    def test_clear_memory(self, random_bytes: bytes):
        raw_data = RawData(WriteLocation.TO_MEMORY, initial_bytes=random_bytes)

        assert raw_data.has_data()

        raw_data.clear()

        assert not raw_data.has_data()
        assert raw_data.tell() == 0

    def test_context_manager(self, config_with_path: Path, random_bytes: bytes):
        with RawData(
            WriteLocation.TO_DISK,
            config_path=config_with_path,
            initial_bytes=random_bytes,
        ) as raw_data:
            assert raw_data.has_data()
            assert raw_data.opened_file is not None

        # Check file is cleaned up after context exit
        assert raw_data.temp_file_path is None
        assert raw_data.opened_file is None

    def test_from_bytes_context_manager(self, random_bytes: bytes):
        with RawData.from_bytes(random_bytes, WriteLocation.TO_MEMORY) as raw_data:
            assert raw_data.has_data()
            assert raw_data.get_contents() == random_bytes

        # Check buffer is cleaned up
        assert raw_data.mem_buffer is None

    def test_from_file_memory(self, test_file: Path):
        with RawData.from_file(test_file, WriteLocation.TO_MEMORY) as raw_data:
            assert raw_data.has_data()
            assert raw_data.get_contents() == test_file.read_bytes()

        assert raw_data.mem_buffer is None
