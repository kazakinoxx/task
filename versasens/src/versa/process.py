"""Module containing functions for parsing and saving data."""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from src.utils.constants import RAW_FILE_FILENAME
from src.utils.exceptions import UnknownHeaderError
from src.utils.logger import logger
from src.utils.typedefs import DeleteFiles, DryRun
from src.versa.db import create_import_folder
from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor_group import SensorGroup


@dataclass
class ParseConfig:
    """
    Class regrouping config options for the parse_and_save_files function.

    Attributes:
        delete_raw_files: Whether to delete the raw files after the import.
                          Defaults to DeleteFiles.NO.
        dry_run: Whether to write data or simulate the writes.
                 Defaults to DryRun.WRITE.
        set_file_progress: Callback function that takes as parameter the index
                           of the most recently processed file. Defaults to None.
        set_cur_file: Callback function that takes as parameter the path of the
                      currently processing file. Defaults to None.
        lead_off: The device's lead-off configuration at recording time, read
                  back from the device. Stored with the import metadata.
                  Defaults to None when it could not be read.

    """

    config_path: Path
    delete_raw_files: DeleteFiles = DeleteFiles.NO
    # TODO: remove dry_run
    dry_run: DryRun = DryRun.WRITE
    lead_off: dict[str, int] | None = None

    @dataclass
    class Callbacks:
        """Callbacks used during the parsing."""

        set_raw_file_path: Callable[[Path], None]
        set_raw_data: Callable[[RawData], None]
        finished_parsing_file: Callable[[], None]

    callbacks: Callbacks | None = None


def parse_and_save_files(  # noqa: C901, PLR0912
    raw_files: list[Path],
    subject_id: str,
    notes: str,
    config: ParseConfig,
) -> Path:
    """
    Parse the given files and stores them to disk.

    Args:
        raw_files: The list of paths to the raw files to parse
        subject_id: The ID of the subject
        notes: The notes given by the user for this import
        config: The config to use for the parsing and saving.
                Defaults to None.

    Returns:
        The path to the folder where the data was written

    """
    # TODO: remove dry_run
    # Store mapping of raw file to parsed data
    raw_file_to_parsed: dict[Path, SensorGroup] = {}

    # Get import folder
    import_folder = create_import_folder(
        subject_id,
        notes,
        config_path=config.config_path,
        lead_off=config.lead_off,
    )

    # Go through each raw file
    for raw_file_path in tqdm(raw_files, desc="Parsing files"):
        if not raw_file_path.exists():
            msg = f"File {raw_file_path.resolve()!s} does not exist"
            raise FileNotFoundError(msg)

        if not raw_file_path.is_file():
            msg = f"Path {raw_file_path.resolve()!s} is not a file"
            raise IsADirectoryError(msg)

        # Call file path callback
        if config.callbacks is not None:
            config.callbacks.set_raw_file_path(raw_file_path)

        # Create raw data instance
        with RawData.from_file(
            raw_file_path,
            WriteLocation.TO_DISK,
            config_path=config.config_path,
            delete_file=config.delete_raw_files,
        ) as raw_data:
            if config.callbacks is not None:
                config.callbacks.set_raw_data(raw_data)

            if config.dry_run == DryRun.WRITE:
                # Parse file and store result
                try:
                    sample_folder = SensorGroup.parse_and_save_raw_data(
                        raw_data,
                        import_folder,
                        config_path=config.config_path,
                        raw_file_name=raw_file_path.stem,
                    )

                    # Put raw path
                    new_raw_path = sample_folder / RAW_FILE_FILENAME

                    if config.delete_raw_files == DeleteFiles.YES:
                        # Can juste move
                        # Force close opened handle
                        # TODO: check if this causes errors
                        if raw_data.opened_file is not None:
                            raw_data.opened_file.close()
                            raw_data.temp_file_path = None

                        shutil.move(raw_file_path, new_raw_path)
                    else:
                        # Copy
                        shutil.copy2(raw_file_path, new_raw_path)

                except UnknownHeaderError:
                    shutil.rmtree(import_folder)
                    logger.error(
                        f"Failed to import {raw_file_path}. Unknown header found.",
                    )

        # Call finished file callback
        if config.callbacks is not None:
            config.callbacks.finished_parsing_file()

    # Delete files if needed
    if config.delete_raw_files == DeleteFiles.YES:
        # Only delete if not dry run
        if config.dry_run == DryRun.WRITE:
            for f in raw_file_to_parsed:
                f.unlink(missing_ok=True)

        logger.info(
            "Deleted files",
            paths=str([f.resolve() for f in raw_file_to_parsed]),
        )

    # Return import folder
    return import_folder
