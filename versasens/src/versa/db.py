"""File containing functions accessing and writing to the database."""

import datetime
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.utils.config import Config
from src.utils.constants import METADATA_FILENAME, RAW_FILE_FILENAME
from src.utils.exceptions import DataNotFoundError
from src.utils.logger import logger
from src.utils.time import datetime_to_tz_aware, get_now
from src.utils.typedefs import (
    DryRun,
    Metadata,
    SampleFilename,
    SensorAttrName,
    SensorCSVPath,
    SensorName,
    SubjectID,
    Timestamp,
)
from src.versa.sensor import Sensor
from src.versa.sensor_group import SensorGroup, sensor_name_to_attr_name

# ===================================== UTILS ==================================


def timestamp_str_to_datetime(timestamp_str: str) -> datetime.datetime:
    """
    Convert a timestamp string to a datetime object.

    Args:
        timestamp_str: The timestamp string

    Returns:
        The corresponding datetime object

    """
    # Get datetime from string
    dt = datetime.datetime.fromisoformat(timestamp_str)

    # Ensure that it is timezone-aware
    return datetime_to_tz_aware(dt)


# ===================================== WRITE ==================================


@dataclass
class WriteDataCallbacks:
    """Callbacks used for the write_data function."""

    set_parsed_file: Callable[[Path], None]
    finished_writing_file: Callable[[], None]
    finished_writing_sensor: Callable[[], None]


def _finished_writing_sensor_callback(
    callbacks: WriteDataCallbacks | None = None,
) -> None | Callable[[], None]:
    if callbacks is None:
        return None

    return callbacks.finished_writing_sensor


def write_data(  # noqa: PLR0913
    raw_file_path_to_data: dict[Path, SensorGroup],
    subject_id: SubjectID,
    notes: str,
    config_path: Path,
    dry_run: DryRun = DryRun.WRITE,
    callbacks: WriteDataCallbacks | None = None,
) -> Path:
    """
    Write data into the database.

    The folder structure is as follows:

    subject ID / import session timestamp / metadata.json
    subject ID / import session timestamp / raw_file_name / raw file, data

    Args:
        raw_file_path_to_data: The dict of the raw data path to parsed data
        subject_id: The ID of the patient
        notes: The notes written by the user
        dry_run: Simulates an execution of the function. Defaults to False.
        config_path: Alternative path to the config file.
        callbacks: Callbacks called during the execution of the function.
                   Defaults to None.

    Returns:
        The path to the import folder (subject ID / import session timestamp)

    """
    logger.debug(
        f"Start writing {len(raw_file_path_to_data)} files",
        subject_id=subject_id,
    )

    # Get DB path
    db_path = Config.get_db_path(config_path)

    # Create timestamp for folder
    timestamp = get_now().isoformat(timespec="seconds")
    timestamp_uri = timestamp.replace(":", "")

    # Create the root folder for import
    import_folder_path = db_path / subject_id / timestamp_uri
    if dry_run == DryRun.WRITE:
        # Only create if not a dry run
        import_folder_path.mkdir(exist_ok=False, parents=True)

    # Write the metadata
    meta_path = import_folder_path / METADATA_FILENAME
    if dry_run == DryRun.WRITE:
        with meta_path.open("w", encoding="utf-8") as f:
            obj = {
                "subject_id": subject_id,
                "notes": notes,
                "timestamp": timestamp,
            }
            json.dump(obj, f, sort_keys=True, indent=4)

    # Write data
    for raw_path, data in raw_file_path_to_data.items():
        if callbacks is not None:
            callbacks.set_parsed_file(raw_path)

        sample_folder = import_folder_path / raw_path.stem
        new_raw_path = sample_folder / RAW_FILE_FILENAME

        if dry_run == DryRun.WRITE:
            sample_folder.mkdir(exist_ok=False, parents=True)

            # Copy raw file
            shutil.copy(raw_path, new_raw_path)

            try:
                # Write data (CSVs and WAV)
                data.write_to_disk(
                    sample_folder,
                    finished_writing_sensor_callback=_finished_writing_sensor_callback(
                        callbacks,
                    ),
                )
            except Exception as e:  # noqa: BLE001
                # TODO: write test for this case
                # Ignore errors to continue import of other files
                logger.exception(e)  # pyright: ignore[reportArgumentType]

        # Finished writing file
        if callbacks is not None:
            callbacks.finished_writing_file()

    logger.info(
        f"Finished writing {len(raw_file_path_to_data)} files",
        import_folder=str(import_folder_path.resolve()),
        subject_id=subject_id,
        timestamp=timestamp,
    )

    return import_folder_path


def create_import_folder(
    subject_id: SubjectID,
    notes: str,
    config_path: Path,
    lead_off: dict[str, int] | None = None,
) -> Path:
    """
    Create and return a new import folder.

    Args:
        subject_id: The ID of the subject whose data is being imported
        notes: The user given notes related to the import
        config_path: The path to the config file used to get the path to the database
        lead_off: The device's lead-off configuration at recording time, if it
                  could be read back from the device. Omitted when unknown.

    Returns:
        The path to the import folder.

    """
    # Get DB path
    db_path = Config.get_db_path(config_path)

    # Create timestamp for folder
    timestamp = get_now().isoformat(timespec="seconds")
    timestamp_uri = timestamp.replace(":", "")

    # Create the root folder for import
    import_folder_path = db_path / subject_id / timestamp_uri
    import_folder_path.mkdir(exist_ok=False, parents=True)

    # Write the metadata
    meta_path = import_folder_path / METADATA_FILENAME
    with meta_path.open("w", encoding="utf-8") as f:
        obj = {
            "subject_id": subject_id,
            "notes": notes,
            "timestamp": timestamp,
        }
        if lead_off is not None:
            obj["lead_off"] = lead_off
        json.dump(obj, f, sort_keys=True, indent=4)

    # Write data

    logger.info(
        "Created an import folder",
        import_folder=str(import_folder_path.resolve()),
        subject_id=subject_id,
        timestamp=timestamp,
    )

    return import_folder_path


# ===================================== READ ===================================


def get_ids_info(config_path: Path) -> list[tuple[SubjectID, int]]:
    """
    Get information about the subject IDs inside the database.

    Args:
        config_path: Alternative path to the config file.

    Returns:
        The list of (subject IDs, their number of imports).

    """
    db = Config.get_db_path(config_path)

    res = []

    for subject_id_path in db.iterdir():
        if not subject_id_path.is_dir():
            continue

        # Get the number of imports
        nbr = len([d for d in subject_id_path.iterdir() if d.is_dir()])

        res.append((subject_id_path.name, nbr))

    return res


def get_imports_of_subject(
    subject_id: str,
    config_path: Path,
) -> list[tuple[Path, Timestamp, int]]:
    """
    Get information about the imports of a given subject ID.

    Args:
        subject_id: The subject's ID.
        config_path: Alternative path to the config file.

    Returns:
        A list of (import folder path, import timestamp, number of samples).

    """
    db = Config.get_db_path(config_path)

    # Get the path to the subject's folder
    subject_path = db / subject_id

    if not subject_path.exists():
        msg = f"Directory {subject_path.resolve()!s} does not exist"
        raise ValueError(msg)

    if not subject_path.exists():
        msg = f"{subject_path.resolve()!s} is not a directory"
        raise ValueError(msg)

    # Get the list of imports
    res: list[tuple[Path, Timestamp, int]] = []

    for import_folder in subject_path.iterdir():
        if not import_folder.is_dir():
            continue

        # Get the timestamp from the folder's name
        timestamp = timestamp_str_to_datetime(import_folder.name)

        # Get the number of samples in the folder
        nbr = len([d for d in import_folder.iterdir() if d.is_dir()])

        res.append((import_folder, timestamp, nbr))

    return res


def get_import_data(
    import_folder: Path,
) -> tuple[
    Metadata,
    dict[SampleFilename, dict[SensorAttrName, list[SensorCSVPath]]],
]:
    """
    Get information about a given import.

    I.e., the metadata, the samples along with the paths to the related CSV files.

    Args:
        import_folder: The path to the import folder.

    Returns:
        A tuple (metadata, dictionary of sample filenames to sensor name to the
        list of CSV files of the sensor).

    """
    if not import_folder.exists():
        msg = f"Directory {import_folder.resolve()!s} does not exist"
        raise ValueError(msg)

    if not import_folder.is_dir():
        msg = f"{import_folder.resolve()!s} is not a directory"
        raise NotADirectoryError(msg)

    # Read metadata
    metadata = _get_metadata(import_folder)

    # Get samples data
    res: dict[SampleFilename, dict[SensorName, list[SensorCSVPath]]] = {}

    for sample_folder in import_folder.iterdir():
        # Go through samples
        if not sample_folder.is_dir():
            continue

        # Create dict of sensor to CSV files
        sensor_to_csv_files: dict[SensorName, list[SensorCSVPath]] = {}

        # Go through the list of files
        for file in sample_folder.iterdir():
            # Only check CSVs
            if file.is_dir() or file.suffix != ".csv":
                continue

            # Get the name of the sensor from the file
            # Need to split for sensors with multiple files
            sensor_name_from_file = file.stem.split("_")[0]
            sensor_attr_name = sensor_name_to_attr_name(sensor_name_from_file)

            # Create the list of CSV files if needed, o.w. append
            if sensor_attr_name in sensor_to_csv_files:
                sensor_to_csv_files[sensor_attr_name].append(file)
            else:
                sensor_to_csv_files[sensor_attr_name] = [file]

        res[sample_folder.name] = sensor_to_csv_files

    return metadata, res


def get_data_for_sensor(
    sensor_name: str,
    files_for_data: list[SensorCSVPath],
) -> Sensor:
    """
    Get data for a given sensor.

    Args:
        sensor_name: the name of the sensor.
        files_for_data: the list of files to read for the given sensor.

    Returns:
        The data for the given sensor.

    """
    attr_name = sensor_name_to_attr_name(sensor_name)
    sens_data = SensorGroup.from_csv_files({attr_name: files_for_data})
    return getattr(sens_data, attr_name)


def _get_metadata(import_folder: Path) -> Metadata:
    """
    Get the metadata of a given import.

    i.e., the subject ID, the notes and the timestamp.

    Args:
        import_folder: The path to the import folder.

    Returns:
        The metadata.

    """
    meta_path = import_folder / METADATA_FILENAME

    if not meta_path.exists():
        msg = "Metadata file does not exist"
        raise FileNotFoundError(msg)

    with meta_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

        if "timestamp" not in data:
            msg = "Missing timestamp in metadata"
            raise TypeError(msg)

        # Check that all values are present
        # assert "subject_id" in data
        # assert "notes" in data
        # assert "timestamp" in data
        data["timestamp"] = timestamp_str_to_datetime(data["timestamp"])

        metadata = Metadata(**data)

    logger.debug("Read metadata", path=str(meta_path.resolve()))

    return metadata


def find_last_added(config_path: Path) -> tuple[SubjectID, Timestamp]:
    """
    Find the metadata of the last sample added to the database.

    Args:
        config_path: Alternative path to the config file.

    Returns:
        The metadata if found

    """
    last_id: SubjectID | None = None
    last_timestamp: Timestamp | None = None

    # Find db
    db = Config.get_db_path(config_path)

    # Go through folders
    for subject_id_path in db.iterdir():
        if not subject_id_path.is_dir():
            continue

        for timestamp_path in subject_id_path.iterdir():
            if not timestamp_path.is_dir():
                continue

            timestamp = timestamp_str_to_datetime(timestamp_path.name)
            subject_id = subject_id_path.name

            if last_timestamp is None or timestamp > last_timestamp:
                last_timestamp = timestamp
                last_id = subject_id

    if last_id is None or last_timestamp is None:
        msg = "No data found inside database"
        raise DataNotFoundError(msg)

    return last_id, last_timestamp
