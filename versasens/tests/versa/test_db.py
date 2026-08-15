import datetime
import json
import pathlib
import random
import tempfile
from itertools import permutations
from random import shuffle
from time import sleep

import pytest

from src.utils.config import update_config
from src.utils.constants import LOCAL_TIMEZONE
from src.utils.exceptions import DataNotFoundError, UnknownSensorError
from src.utils.time import get_now
from src.versa.db import (
    METADATA_FILENAME,
    _get_metadata,
    find_last_added,
    get_data_for_sensor,
    get_ids_info,
    get_import_data,
    get_imports_of_subject,
    timestamp_str_to_datetime,
    write_data,
)
from src.versa.sensor import DryRun
from src.versa.sensor_group import SensorGroup

# =================================== UTILS ====================================


@pytest.fixture
def write_data_to_db_factory(
    tmp_path_factory,
    random_text_factory,
    test_files_parsed_dict,
):
    def _write_data_to_db(
        nbr_subject_ids: int = 1,
        nbr_imports_for_id: list[int] | None = None,
    ) -> tuple[pathlib.Path, list[tuple[str, int]], pathlib.Path, list[pathlib.Path]]:
        assert nbr_subject_ids > 0

        tmp_path = tmp_path_factory.mktemp("test_db")

        # Initialize nbr_imports_for_id
        if nbr_imports_for_id is None:
            nbr_imports_for_id = [1] * nbr_subject_ids

        # Create the config file
        config_path = tmp_path / "config.ini"
        db_path = tmp_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Get subject IDs
        subject_ids = [
            random_text_factory(prefix="subject_") for _ in range(nbr_subject_ids)
        ]
        notes_lst = [
            random_text_factory(prefix="notes_") for _ in range(nbr_subject_ids)
        ]

        for sid, notes, nbr_imports in zip(
            subject_ids,
            notes_lst,
            nbr_imports_for_id,
            strict=True,
        ):
            for _ in range(nbr_imports):
                start = get_now()
                write_data(test_files_parsed_dict, sid, notes, config_path=config_path)

                time_delta = get_now() - start
                if time_delta < datetime.timedelta(seconds=1):
                    sleep(time_delta.total_seconds())

        # Get expected info
        exp_ids_info = [
            (sid, nbr) for sid, nbr in zip(subject_ids, nbr_imports_for_id, strict=True)
        ]

        # Get paths to subject IDs
        subject_ids_paths = [db_path / sid for sid in subject_ids]

        return config_path, exp_ids_info, db_path, subject_ids_paths

    return _write_data_to_db


# ========================= timestamp_str_to_datetime ==========================


def test_timestamp_str_to_datetime():
    res_1 = timestamp_str_to_datetime("2025-10-25T152923")
    exp_1 = datetime.datetime(2025, 10, 25, 15, 29, 23, tzinfo=LOCAL_TIMEZONE)
    assert res_1 == exp_1

    res_2 = timestamp_str_to_datetime("2025-11-03T133018")
    exp_2 = datetime.datetime(2025, 11, 3, 13, 30, 18, tzinfo=LOCAL_TIMEZONE)
    assert res_2 == exp_2

    assert res_1 != res_2


# ================================= write_data =================================


def test_write_data(
    config_with_path_and_db,
    subject_id,
    notes,
    test_files_parsed_dict: dict[pathlib.Path, SensorGroup],
):
    config_path, db_path = config_with_path_and_db

    # Write data
    folder = write_data(
        test_files_parsed_dict,
        subject_id,
        notes,
        config_path=config_path,
    )

    # Check results
    assert folder.exists()
    assert folder.parent == db_path / subject_id
    assert (folder / METADATA_FILENAME).exists()

    # Check test files
    for file in test_files_parsed_dict:
        filename = file.stem
        assert (folder / filename).exists()
        assert len(list((folder / filename).iterdir())) > 0


def test_write_data_dry_run(
    config_with_path_and_db,
    subject_id,
    notes,
    test_files_parsed_dict: dict[pathlib.Path, SensorGroup],
):
    config_path, db_path = config_with_path_and_db

    # Write data
    folder = write_data(
        test_files_parsed_dict,
        subject_id,
        notes,
        config_path=config_path,
        dry_run=DryRun.NO_WRITES,
    )

    # Check that nothing was written
    assert not folder.exists()
    assert len(list(db_path.iterdir())) == 0


# ================================ get_ids_info ================================


def test_get_ids_info(write_data_to_db_factory):
    config_path, exp_ids_info, _, _ = write_data_to_db_factory(
        nbr_subject_ids=2,
        nbr_imports_for_id=[1, 2],
    )

    # Get ids info
    ids_info = get_ids_info(config_path)

    # Check results
    assert set(ids_info) == set(exp_ids_info)


def test_get_ids_info_ignores_files_in_id_folder(write_data_to_db_factory):
    config_path, exp_ids_info, _, subject_ids_paths = write_data_to_db_factory(
        nbr_subject_ids=1,
        nbr_imports_for_id=[1],
    )

    # Get import folder
    import_folder = subject_ids_paths[0].iterdir().__next__()

    # Add a dummy file inside the subject's folder.
    dummy_file = import_folder.parent / "dummy.txt"
    dummy_file.touch()
    assert dummy_file.exists()

    # Get ids info
    ids_info = get_ids_info(config_path)

    # Check results
    assert set(ids_info) == set(exp_ids_info)


def test_get_ids_info_ignores_files_in_db_folder(write_data_to_db_factory):
    config_path, exp_ids_info, db_path, _ = write_data_to_db_factory(
        nbr_subject_ids=1,
        nbr_imports_for_id=[1],
    )

    # Add a dummy file inside the subject's folder.
    dummy_file = db_path / "dummy.txt"
    dummy_file.touch()
    assert dummy_file.exists()

    # Get ids info
    ids_info = get_ids_info(config_path)

    # Check results
    assert set(ids_info) == set(exp_ids_info)


# =========================== get_imports_of_subject ===========================


def test_get_imports_of_subject(
    test_files_paths,
    test_files_parsed_dict,
    config_with_path,
    random_text_factory,
):
    config_path = config_with_path

    nbr_subject_ids = random.randint(1, 5)
    nbr_imports_for_id = random.choices(range(1, 3), k=nbr_subject_ids)
    nbr_files = len(test_files_paths)

    assert len(nbr_imports_for_id) == nbr_subject_ids

    # Get subject IDs
    subject_ids = [
        random_text_factory(prefix="subject_") for _ in range(nbr_subject_ids)
    ]
    notes_lst = [random_text_factory(prefix="notes_") for _ in range(nbr_subject_ids)]

    for subject_id, notes, nbr_imports in zip(
        subject_ids,
        notes_lst,
        nbr_imports_for_id,
        strict=False,
    ):
        # Import each subject ID
        for _ in range(nbr_imports):
            # Import multiple times for each subject
            import_path = write_data(
                test_files_parsed_dict,
                subject_id,
                notes,
                config_path=config_path,
            )

            # Get timestamp from the import path
            start = timestamp_str_to_datetime(import_path.name)

            # Wait if one second not yet elapsed
            time_delta = get_now() - start
            if time_delta < datetime.timedelta(seconds=1):
                sleep(time_delta.total_seconds())

        # Get the imports
        imports_info = get_imports_of_subject(
            subject_id,
            config_path,
        )

        # Check has gotten the right number of imports
        assert len(imports_info) == nbr_imports

        # Check that each import has the correct number of files
        for import_info in imports_info:
            assert import_info[2] == nbr_files

        # Check that the timestamps correspond with the folder's name
        for import_info in imports_info:
            assert import_info[1] == timestamp_str_to_datetime(import_info[0].name)


def test_get_imports_of_subject_no_error_if_has_files(
    test_files_parsed_dict,
    test_files_paths,
    config_with_path_and_db,
    subject_id,
    notes,
):
    config_path, db_path = config_with_path_and_db

    # Import multiple times for each subject
    write_data(test_files_parsed_dict, subject_id, notes, config_path=config_path)

    # Add a dummy file inside the subject's folder
    subject_id_folder = db_path / subject_id
    assert subject_id_folder.exists()

    dummy_file = subject_id_folder / "dummy.txt"
    dummy_file.touch()
    assert dummy_file.exists()

    # Get the imports
    imports_info = get_imports_of_subject(
        subject_id,
        config_path,
    )

    # Check has gotten the right number of imports
    assert len(imports_info) == 1

    # Check that each import has the correct number of files
    for import_info in imports_info:
        assert import_info[2] == len(test_files_paths)

    # Check that the timestamps correspond with the folder's name
    for import_info in imports_info:
        assert import_info[1] == timestamp_str_to_datetime(import_info[0].name)


def test_get_imports_of_subject_error_if_doesnt_exist():
    with tempfile.TemporaryDirectory() as temp_folder:
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        with pytest.raises(ValueError, match="does not exist"):
            # Get the imports of a dummy path
            get_imports_of_subject(
                "ABCD",
                config_path,
            )


def test_get_imports_of_subject_error_if_not_a_folder():
    with tempfile.TemporaryDirectory() as temp_folder:
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Dummy file
        dummy_file = db_path / "dummy"
        dummy_file.touch()

        with pytest.raises(NotADirectoryError):
            # Get the imports of a dummy file
            get_imports_of_subject(
                "dummy",
                config_path,
            )


# ============================== get_import_data ===============================


def test_get_import_data(test_files_paths, test_files_parsed_dict):
    nbr_imports = random.randint(2, 5)
    nbr_files = len(test_files_paths)
    test_filenames_stems = [f.stem for f in test_files_paths]

    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Set values
        subject_id = "test_subject"
        notes = "Some notes about subject"

        # Import multiple times
        for _ in range(nbr_imports):
            # Import multiple times for each subject
            import_path = write_data(
                test_files_parsed_dict,
                subject_id,
                notes,
                config_path=config_path,
            )

            # Get info of import
            metadata, info = get_import_data(import_path)

            # Check metadata
            assert metadata.subject_id == subject_id
            assert metadata.notes == notes
            assert metadata.timestamp == timestamp_str_to_datetime(
                import_path.name,
            )

            # Check read correct number of files
            assert len(info) == nbr_files

            # Check sample filenames are correct
            for sample_filename, data_dict in info.items():
                assert sample_filename in test_filenames_stems

                # Check that the lists are not empty
                assert len(data_dict) > 0

                # Check that each sensor has at least one csv file
                for csvs in data_dict.values():
                    assert len(csvs) > 0

            # Get timestamp from the import path
            start = timestamp_str_to_datetime(import_path.name)

            # Wait if one second not yet elapsed
            time_delta = get_now() - start
            if time_delta < datetime.timedelta(seconds=1):
                sleep(time_delta.total_seconds())


def test_get_import_data_error_if_no_folder():
    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Dummy path
        dummy_import_path = pathlib.Path(temp_folder) / "dummy"
        assert not dummy_import_path.exists()

        with pytest.raises(ValueError, match="does not exist"):
            get_import_data(dummy_import_path)


def test_get_import_data_error_if_not_a_folder():
    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Dummy path
        dummy_import_path = pathlib.Path(temp_folder) / "dummy"
        dummy_import_path.touch()
        assert dummy_import_path.exists()
        assert not dummy_import_path.is_dir()

        with pytest.raises(NotADirectoryError, match="is not a directory"):
            get_import_data(dummy_import_path)


# ============================ get_data_for_sensor =============================


def test_get_data_for_sensor(test_files_parsed_dict, test_files_paths):
    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Set values
        subject_id = "test_subject"
        notes = "Some notes about subject"

        # Import multiple times for each subject
        import_path = write_data(
            test_files_parsed_dict,
            subject_id,
            notes,
            config_path=config_path,
        )

        # Get info of import to get CSV files
        _, info = get_import_data(import_path)

        for sample_filename, sensor_to_csvs in info.items():
            # Get the source file's path
            source_file_path = next(
                f for f in test_files_paths if f.stem == sample_filename
            )

            # Get the data of the file
            sample_data = test_files_parsed_dict[source_file_path]

            for sensor_name, csvs in sensor_to_csvs.items():
                data = get_data_for_sensor(sensor_name, csvs)

                # Check is the same data
                assert data == sample_data._get_sensor(sensor_name)


def test_get_data_for_sensor_empty_if_no_files():
    res = get_data_for_sensor("ads", [])
    assert res.is_empty()


def test_get_data_for_sensor_error_if_wrong_name():
    with pytest.raises(UnknownSensorError):
        get_data_for_sensor("ABCD", [])


def test_get_data_for_sensor_error_if_nonexisting_file():
    with tempfile.TemporaryDirectory() as temp_folder:
        dummy_file = pathlib.Path(temp_folder) / "dummy.CSV"

        with pytest.raises(FileNotFoundError):
            get_data_for_sensor("ads", [dummy_file])


# =============================== _get_metadata ================================


def test_get_metadata(test_files_parsed_dict):
    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Set values
        subject_id = "test_subject"
        notes = "Some notes about subject"

        # Import multiple times for each subject
        import_path = write_data(
            test_files_parsed_dict,
            subject_id,
            notes,
            config_path=config_path,
        )

        # Get info of import to get CSV files
        metadata = _get_metadata(import_path)

        # Check metadata
        assert metadata.subject_id == subject_id
        assert metadata.notes == notes
        assert metadata.timestamp == timestamp_str_to_datetime(
            import_path.name,
        )


def test_get_metadata_error_no_metadata_file():
    with tempfile.TemporaryDirectory() as temp_folder:
        dummy_metadata_file = pathlib.Path(temp_folder) / METADATA_FILENAME
        assert not dummy_metadata_file.exists()

        with pytest.raises(FileNotFoundError):
            _get_metadata(dummy_metadata_file)


def test_get_metadata_error_missing_values():
    with tempfile.TemporaryDirectory() as temp_folder:
        metadata_file = pathlib.Path(temp_folder) / METADATA_FILENAME

        subject_id = "test_subject"
        notes = "Some notes about subject"
        timestamp = get_now()

        fields = [
            ("subject_id", subject_id),
            ("notes", notes),
            ("timestamp", timestamp.isoformat()),
        ]

        for k in [1, 2]:
            for perms in permutations(fields, k):
                data = dict(perms)

                with metadata_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f)

                with pytest.raises(TypeError):
                    _get_metadata(pathlib.Path(temp_folder))


# ============================== find_last_added ===============================


def test_find_last_added(test_files_parsed_dict):
    nbr_subject_ids = random.randint(1, 5)
    nbr_imports_for_id = random.choices(range(1, 3), k=nbr_subject_ids)

    assert len(nbr_imports_for_id) == nbr_subject_ids

    # Get subject IDs
    subject_ids = [f"test_subject_{i}" for i in range(nbr_subject_ids)]
    notes_lst = [f"Some notes about subject {i}" for i in range(nbr_subject_ids)]

    # Shuffle the order of imports
    imports_args = []

    for subject_id, notes, nbr_imports in zip(
        subject_ids,
        notes_lst,
        nbr_imports_for_id,
        strict=False,
    ):
        imports_args.extend([(subject_id, notes)] * nbr_imports)

    shuffle(imports_args)

    # Get the ID of the last import
    exp_id = imports_args[-1][0]

    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        import_path: pathlib.Path | None = None

        # Import the data
        for subject_id, notes in imports_args:
            # Import multiple times for each subject
            import_path = write_data(
                test_files_parsed_dict,
                subject_id,
                notes,
                config_path=config_path,
            )

            # Get timestamp from the import path
            start = timestamp_str_to_datetime(import_path.name)

            # Wait if one second not yet elapsed
            time_delta = get_now() - start
            if time_delta < datetime.timedelta(seconds=1):
                sleep(time_delta.total_seconds())

        # Get last added timestamp
        assert import_path is not None
        exp_timestamp = timestamp_str_to_datetime(import_path.name)

        # Get last added
        res_id, res_timestamp = find_last_added(config_path)

        # Compare results
        assert res_id == exp_id
        assert exp_timestamp == res_timestamp


def test_find_last_added_error_if_no_data():
    with tempfile.TemporaryDirectory() as temp_folder:
        # Create config
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        with pytest.raises(DataNotFoundError):
            find_last_added(config_path)


def test_find_last_added_no_error_if_file_in_root(test_files_parsed_dict):
    # Set variables
    subject_id = "test_subject"
    notes = "Some notes about subject"

    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Import multiple times for each subject
        import_path = write_data(
            test_files_parsed_dict,
            subject_id,
            notes,
            config_path=config_path,
        )

        # Add a file in the root
        dummy_file = db_path / "dummy.txt"
        dummy_file.touch()
        assert dummy_file.exists()

        # Get last added timestamp
        exp_timestamp = timestamp_str_to_datetime(import_path.name)

        # Get last added
        res_id, res_timestamp = find_last_added(config_path)

        # Compare results
        assert res_id == subject_id
        assert exp_timestamp == res_timestamp


def test_find_last_added_no_error_if_file_in_subject_folder(test_files_parsed_dict):
    # Set variables
    subject_id = "test_subject"
    notes = "Some notes about subject"

    with tempfile.TemporaryDirectory() as temp_folder:
        # Create the config file
        config_path = pathlib.Path(temp_folder) / "config.ini"
        db_path = pathlib.Path(temp_folder) / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Import multiple times for each subject
        import_path = write_data(
            test_files_parsed_dict,
            subject_id,
            notes,
            config_path=config_path,
        )

        # Add a file in the subject's folder
        dummy_file = import_path.parent / "dummy.txt"
        dummy_file.touch()
        assert dummy_file.exists()

        # Get last added timestamp
        exp_timestamp = timestamp_str_to_datetime(import_path.name)

        # Get last added
        res_id, res_timestamp = find_last_added(config_path)

        # Compare results
        assert res_id == subject_id
        assert exp_timestamp == res_timestamp
