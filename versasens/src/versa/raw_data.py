"""Module containing the RawData class."""

import io
import os
import shutil
import tempfile
from collections.abc import Buffer, Generator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Self

from src.utils.config import get_or_create_config
from src.utils.exceptions import RawDataStateError
from src.utils.logger import logger
from src.utils.typedefs import DeleteFiles


class WriteLocation(Enum):
    """Enum to tell where to write data."""

    TO_MEMORY = 0
    TO_DISK = 1


class RawData:
    """
    Class handling raw data reads and writes.

    It includes a in-disk cache to prevent the raw data from taking too much space.

    Args:
        write_location: Where to write the stored data.
        mem_buffer: The in-memory buffer where data is written.
        temp_file_path: The path to the temporary file used when storing raw data
                        directly to disk.
        opened_file: The handle to the opened file.
        config_path: The path to the config file.

    """

    def __init__(
        self,
        write_location: WriteLocation,
        config_path: Path | None = None,
        initial_bytes: Buffer = b"",
        file_path: Path | None = None,
    ) -> None:
        """
        Create a new RawData instance.

        Args:
            write_location: Where the raw data needs to be written.
            config_path: The path to the config file. Required if writing to disk, as
                         the temporary file will be placed in the database folder.
                         Defaults to None.
            initial_bytes: The bytes that will initially be put in raw data instance.
                           Defaults to b"".
            file_path: If given, the underlying file used to cache memory to disk.

        """
        # Init variables
        self.write_location: WriteLocation = write_location
        """Where to write the stored data"""

        self.mem_buffer: io.BytesIO | None = None
        """The in-memory buffer where data is written"""

        self.temp_file_path: Path | None = None
        """The path to the temporary file used when storing raw data directly to disk"""
        self.opened_file: io.BufferedRandom | None = None
        """The handle to the opened file"""
        self.config_path: Path | None = config_path
        """The path to the config file"""

        # Initialize file if writing to disk
        if write_location == WriteLocation.TO_DISK:
            if config_path is None:
                msg = (
                    "Path to the config file is missing while trying to write to disk."
                )
                raise RawDataStateError(msg)

            if file_path is None:
                self._initialize_temp_file(config_path)
            else:
                self.temp_file_path = file_path
        else:
            # Otherwise, initialize internal buffer
            self.mem_buffer = io.BytesIO()

        # Add the initial bytes
        self.open()
        self.add_data(initial_bytes)
        self.go_to_start()

    def _initialize_temp_file(self, config_path: Path) -> Path:
        # Check that no file is currently stored
        if self.opened_file is not None:
            msg = "The RawData instance already has an opened file"
            raise RawDataStateError(msg)

        # Check that no temporary file was already initialized
        if self.temp_file_path is not None:
            msg = "The RawData instance already has a temporary file"
            raise RawDataStateError(msg)

        # Ensure that writing to disk
        if self.write_location != WriteLocation.TO_DISK:
            msg = "Trying to initialize a temporary file while writing to disk"
            raise RawDataStateError(msg)

        # Get path to the database
        config = get_or_create_config(config_path)
        parent_folder = config.db_path

        # Create parent folder if not exists
        parent_folder.mkdir(parents=True, exist_ok=True)

        # Create a new file
        fd, name = tempfile.mkstemp(
            suffix=".raw",
            prefix="temp_",
            dir=parent_folder,
        )
        # Close the descriptor given by the OS
        os.close(fd)

        # Store the file path
        self.temp_file_path = parent_folder / name
        logger.debug("Created temp file", path=str(self.temp_file_path.resolve()))

        # Ensure that the file has been created
        if not self.temp_file_path.exists():
            msg = f"Failed to create temp file {self.temp_file_path.resolve()!s}"
            raise FileNotFoundError(msg)

        return self.temp_file_path

    def read(self, size: int = -1) -> bytes:
        """
        Read a number of bytes from the raw data.

        Args:
            size: The number of bytes to read. If None, read all of the bytes available.
                  Defaults to None.

        Returns:
            The bytes read.

        """
        if self.write_location == WriteLocation.TO_DISK:
            # Need to read file
            if self.opened_file is None:
                msg = f"File {self.temp_file_path} was not opened"
                raise ValueError(msg)

            return self.opened_file.read(size)

        # Otherwise, need to open buffer
        if self.mem_buffer is None:
            msg = "Buffer was not created"
            raise ValueError(msg)

        return self.mem_buffer.read(size)

    def add_data(self, data: Buffer) -> None:
        """
        Add data into the raw data object.

        Args:
            data: The data to add

        """
        if self.write_location == WriteLocation.TO_DISK:
            # Need to add to file
            if self.opened_file is None:
                msg = f"File {self.temp_file_path} was not opened"
                raise ValueError(msg)

            self.opened_file.write(data)
        else:
            # Need to add to buffer
            if self.mem_buffer is None:
                msg = "Buffer was not created"
                raise ValueError(msg)

            self.mem_buffer.write(data)

        # Manually go to the end
        # TODO: verify that every time it needs to go to the end
        self.go_to_end()

    def go_to_start(self) -> None:
        """Go to the start of the file/buffer (same as seek(0))."""
        if self.write_location == WriteLocation.TO_DISK:
            # File
            if self.opened_file is None:
                msg = f"File {self.temp_file_path} was not opened"
                raise ValueError(msg)

            self.opened_file.seek(0)
        else:
            # Buffer
            if self.mem_buffer is None:
                msg = "Buffer was not created"
                raise ValueError(msg)

            self.mem_buffer.seek(0)

    def go_to_end(self) -> None:
        """Go to the end of the file/buffer (same as seek(0, os.SEEN_END))."""
        if self.write_location == WriteLocation.TO_DISK:
            # File
            if self.opened_file is None:
                msg = f"File {self.temp_file_path} was not opened"
                raise ValueError(msg)

            self.opened_file.seek(0, os.SEEK_END)
        else:
            # Buffer
            if self.mem_buffer is None:
                msg = "Buffer was not created"
                raise ValueError(msg)

            self.mem_buffer.seek(0, os.SEEK_END)

    def get_contents(self) -> bytes:
        """
        Get all of the bytes contained in the raw data.

        Returns:
            The bytes contained in the raw data.

        """
        if self.write_location == WriteLocation.TO_DISK:
            # File
            if self.temp_file_path is None:
                msg = f"File {self.temp_file_path} was not created"
                raise ValueError(msg)

            return self.temp_file_path.read_bytes()

        # Buffer
        if self.mem_buffer is None:
            msg = "Buffer was not created"
            raise ValueError(msg)

        return self.mem_buffer.getvalue()

    def copy_file(self, destination_path: Path) -> None:
        """
        Copy the contents of the raw data to the given file path.

        Args:
            destination_path: The path where to copy data.

        """
        # TODO: write tests
        if self.write_location == WriteLocation.TO_DISK:
            # Check temp file exists
            if self.temp_file_path is None:
                msg = (
                    "The RawData instance in TO_DISK writing location has no "
                    "created file."
                )
                raise RawDataStateError(msg)

            # Copy file
            shutil.copy2(self.temp_file_path, destination_path)

        else:
            # Check buffer
            if self.mem_buffer is None:
                msg = (
                    "The RawData instance in TO_MEMORY writing location has no "
                    "created buffer."
                )
                raise RawDataStateError(msg)

            # Create a temp file and copy
            with tempfile.TemporaryDirectory() as temp_dir:
                mem_path = Path(temp_dir) / "mem.raw"
                mem_path.touch(exist_ok=False)

                # Write data to disk
                mem_path.write_bytes(self.mem_buffer.getvalue())

                # Move file
                shutil.move(mem_path, destination_path)

    def tell(self) -> int:
        """
        Get the current position inside the file/buffer.

        Returns:
            The current position in the file/buffer.

        """
        if self.write_location == WriteLocation.TO_DISK:
            # File
            if self.opened_file is None:
                msg = f"File {self.temp_file_path} was not opened"
                raise ValueError(msg)

            return self.opened_file.tell()

        # Buffer
        if self.mem_buffer is None:
            msg = "Buffer was not created"
            raise ValueError(msg)

        return self.mem_buffer.tell()

    def clear(self) -> None:
        """
        Delete the contents of the raw file.

        When writing to disk, the temporary file is deleted and a new one is created.
        """
        # Close file, ignore if not opened
        if self.opened_file is not None:
            self.opened_file.close()
            self.opened_file = None

        # Delete the temporary file, ignore if doesn't exist
        if self.temp_file_path is not None:
            self.temp_file_path.unlink()
            self.temp_file_path = None

        # Clear the buffer, ignore if no buffer was set
        if self.mem_buffer is not None:
            self.mem_buffer = io.BytesIO()

        # Create a new temporary file if needed
        if self.write_location == WriteLocation.TO_DISK:
            if self.config_path is None:
                msg = "Config path was not given"
                raise ValueError(msg)

            self._initialize_temp_file(self.config_path)

    def has_data(self) -> bool:
        """
        Check whether the instance contains any data.

        Returns:
            Whether the instance contains any data.

        """
        # TODO: write test
        # TODO: add lock to prevent writes and reads while checking this, as it messes
        # with the current position
        if self.write_location == WriteLocation.TO_DISK:
            # Check file size
            if self.temp_file_path is None:
                msg = "Temporary file was not created"
                raise RawDataStateError(msg)

            return self.temp_file_path.stat().st_size != 0

        if self.write_location == WriteLocation.TO_MEMORY:
            # Check buffer size
            if self.mem_buffer is None:
                msg = "Buffer was not created"
                raise RawDataStateError(msg)

            old_pos = self.mem_buffer.tell()

            # Go to end
            self.mem_buffer.seek(0, os.SEEK_END)

            # If current position is larger than 0, has data
            res = self.mem_buffer.tell() > 0

            # Reset position
            self.mem_buffer.seek(old_pos)

            return res

        msg = f"Invalid write location {self.write_location}"
        raise RawDataStateError(msg)

    def get_file_path(self) -> Path:
        """
        Get the path to the underlying file.

        Only works if the raw data is being written to disk.

        Raises:
            ValueError: If not writing to disk.
            RawDataStateError: If the temporary file was not created.

        Returns:
            The path to the underlying file.

        """
        # TODO: write test
        if self.write_location != WriteLocation.TO_DISK:
            # TODO: check if need to change
            msg = "Cannot get file path if not writing to disk"
            raise ValueError(msg)

        if self.temp_file_path is None:
            msg = "Temporary file was not created"
            raise RawDataStateError(msg)

        return self.temp_file_path

    # ================================= Open and close =================================

    def open(self) -> None:
        """Open the underlying file."""
        # If writing to buffer, do nothing
        if self.write_location != WriteLocation.TO_DISK:
            return

        # If the file is already opened, do nothing
        if self.opened_file is not None:
            return

        # Open the file
        if self.temp_file_path is not None:
            self.opened_file = self.temp_file_path.open("r+b")
        else:
            msg = "Tried to open file but not temporary file was initialized"
            raise ValueError(msg)

    def close(self) -> None:
        """Close and delete files and buffers."""
        if self.opened_file is not None:
            self.opened_file.close()
            self.opened_file = None

        if self.temp_file_path is not None:
            logger.debug("Deleted temp file", file=str(self.temp_file_path))
            self.temp_file_path.unlink()
            self.temp_file_path = None

        if self.mem_buffer is not None:
            self.mem_buffer = None

    # ================================ Context manager =================================

    def __enter__(self) -> Self:
        """Enter the context manager."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # noqa: ANN001
        """Exit the context manager."""
        self.close()

    # ================================ Create instances ================================

    @classmethod
    @contextmanager
    def from_bytes(
        cls,
        data: Buffer,
        write_location: WriteLocation,
        config_path: Path | None = None,
    ) -> Generator[Self]:
        """
        Create a new RawData instance from the given bytes.

        Args:
            data: The bytes from which the raw data is initialized.
            write_location: Where to write the stored data.
            config_path: The path to the config file. Required if writing to disk.
                         Defaults to None.

        Yields:
            The RawData instance.

        """
        raw_data = cls(write_location, config_path=config_path, initial_bytes=data)

        try:
            raw_data.open()
            yield raw_data
        finally:
            raw_data.close()

    @classmethod
    @contextmanager
    def from_file(
        cls,
        file_path: Path,
        write_location: WriteLocation,
        config_path: Path | None = None,
        delete_file: DeleteFiles = DeleteFiles.NO,
    ) -> Generator[Self]:
        """
        Create a new RawData instance from the given file.

        Args:
            file_path: The path to the file containing the raw data.
            write_location: Where to write the stored data.
            config_path: The path to the config file. Required if writing to disk.
                         Defaults to None.
            delete_file: Whether to delete the given file after creating the instance.

        Yields:
            The RawData instance.

        """
        if write_location == WriteLocation.TO_DISK:
            if delete_file == DeleteFiles.NO:
                logger.debug("Copying file")
                # Manually add data in batches to save memory
                raw_data = cls(write_location, config_path=config_path)

                # 64KB batch size
                batch_size = 1024 * 64

                with file_path.open("rb") as file:
                    while True:
                        data = file.read(batch_size)

                        if data == b"":
                            break

                        raw_data.add_data(data)

                raw_data.go_to_start()

            else:
                logger.debug("Giving file")
                # Give file directly
                raw_data = cls(
                    write_location,
                    config_path=config_path,
                    file_path=file_path,
                )
        else:
            logger.debug("Writing to memory")
            data = file_path.read_bytes()
            raw_data = cls(write_location, config_path=config_path, initial_bytes=data)

        try:
            logger.debug("Created RawData from file", file=str(file_path.resolve()))
            raw_data.open()
            yield raw_data
        finally:
            raw_data.close()
