import pathlib
import shutil
import tempfile

import pytest

from src.utils.config import update_config
from src.utils.constants import METADATA_FILENAME, RAW_FILE_FILENAME
from src.utils.typedefs import DeleteFiles, DryRun
from src.versa.process import ParseConfig, parse_and_save_files


def test_parse_and_save_files(subject_id, notes, test_files_paths):
    with tempfile.TemporaryDirectory() as temp_dir:
        folder_path = pathlib.Path(temp_dir)

        # Create the config file
        config_path = folder_path / "config.ini"
        db_path = folder_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Copy test files
        test_files: list[pathlib.Path] = []

        for test_file_path in test_files_paths:
            dest_path = folder_path / test_file_path.name
            shutil.copy2(test_file_path, dest_path)
            test_files.append(dest_path)

        # Set variables
        parse_config = ParseConfig(
            delete_raw_files=DeleteFiles.NO,
            dry_run=DryRun.WRITE,
            config_path=config_path,
        )
        import_path = parse_and_save_files(
            test_files,
            subject_id,
            notes,
            config=parse_config,
        )

        # Check that files were written
        assert import_path.exists()
        assert import_path.is_dir()

        # Check that number of sample folders is correct
        # + 1 for metadata file
        assert len(list(import_path.iterdir())) == len(test_files) + 1

        # Check that metadata file exists
        metadata_file_path = import_path / METADATA_FILENAME
        assert metadata_file_path.exists()
        assert metadata_file_path.is_file()

        # Check samples folders
        test_file_names = {f.stem for f in test_files}

        for sample_folder in import_path.iterdir():
            if sample_folder == metadata_file_path:
                continue

            assert sample_folder.is_dir()

            # Check that folder name corresponds to a test file
            assert sample_folder.name in test_file_names

            # Check that raw file exists
            raw_file_path = sample_folder / RAW_FILE_FILENAME
            assert raw_file_path.exists()
            assert raw_file_path.is_file()

            # Check that parsed CSV files exist
            assert len(list(sample_folder.iterdir())) > 2  # raw + metadata + CSVs


def test_parse_and_save_files_with_delete(subject_id, notes, test_files_paths):
    with tempfile.TemporaryDirectory() as temp_dir:
        folder_path = pathlib.Path(temp_dir)

        # Create the config file
        config_path = folder_path / "config.ini"
        db_path = folder_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Copy test files
        test_files: list[pathlib.Path] = []

        for test_file_path in test_files_paths:
            dest_path = folder_path / test_file_path.name
            shutil.copy2(test_file_path, dest_path)
            test_files.append(dest_path)

        # Set variables
        parse_config = ParseConfig(
            delete_raw_files=DeleteFiles.YES,
            dry_run=DryRun.WRITE,
            config_path=config_path,
        )
        import_path = parse_and_save_files(
            test_files,
            subject_id,
            notes,
            config=parse_config,
        )

        # Check that files were written
        assert import_path.exists()
        assert import_path.is_dir()

        # Check that number of sample folders is correct
        # + 1 for metadata file
        assert len(list(import_path.iterdir())) == len(test_files) + 1

        # Check that metadata file exists
        metadata_file_path = import_path / METADATA_FILENAME
        assert metadata_file_path.exists()
        assert metadata_file_path.is_file()

        # Check samples folders
        test_file_names = {f.stem for f in test_files}

        for sample_folder in import_path.iterdir():
            if sample_folder == metadata_file_path:
                continue

            assert sample_folder.is_dir()

            # Check that folder name corresponds to a test file
            assert sample_folder.name in test_file_names

            # Check that raw file exists
            raw_file_path = sample_folder / RAW_FILE_FILENAME
            assert raw_file_path.exists()
            assert raw_file_path.is_file()

            # Check that parsed CSV files exist
            assert len(list(sample_folder.iterdir())) > 2  # raw + metadata + CSVs


def test_parse_and_save_files_delete_files_works(test_files_paths):
    with tempfile.TemporaryDirectory() as temp_dir:
        folder_path = pathlib.Path(temp_dir)

        # Create the config file
        config_path = folder_path / "config.ini"
        db_path = folder_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Copy test files
        test_files: list[pathlib.Path] = []

        for test_file_path in test_files_paths:
            dest_path = folder_path / test_file_path.name
            shutil.copy2(test_file_path, dest_path)
            test_files.append(dest_path)

        # Set variables
        subject_id = "test_subject"
        notes = "These are test notes."

        parse_config = ParseConfig(
            delete_raw_files=DeleteFiles.YES,
            dry_run=DryRun.WRITE,
            config_path=config_path,
        )
        parse_and_save_files(test_files, subject_id, notes, config=parse_config)

        # Check that the raw files were deleted
        for test_file in test_files:
            assert not test_file.exists()


# TODO: write tests for callbacks


def test_parse_and_save_files_set_cur_file_name_works(test_files_paths):
    with tempfile.TemporaryDirectory() as temp_dir:
        folder_path = pathlib.Path(temp_dir)

        # Create the config file
        config_path = folder_path / "config.ini"
        db_path = folder_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Copy test files
        test_files: list[pathlib.Path] = []

        for test_file_path in test_files_paths:
            dest_path = folder_path / test_file_path.name
            shutil.copy2(test_file_path, dest_path)
            test_files.append(dest_path)

        # Set variables
        subject_id = "test_subject"
        notes = "These are test notes."

        # Setup current file name tracker
        cur_file_names_received: list[str] = []

        def _set_raw_file_path(file: pathlib.Path) -> None:
            cur_file_names_received.append(file.name)

        callbacks = ParseConfig.Callbacks(
            set_raw_file_path=_set_raw_file_path,
            set_raw_data=lambda _: None,
            finished_parsing_file=lambda: None,
        )

        parse_config = ParseConfig(
            delete_raw_files=DeleteFiles.NO,
            dry_run=DryRun.NO_WRITES,
            config_path=config_path,
            callbacks=callbacks,
        )
        parse_and_save_files(test_files, subject_id, notes, config=parse_config)

        # Check that current file name callback was called correctly
        expected_file_names = [f.name for f in test_files]
        assert cur_file_names_received == expected_file_names


def test_parse_and_save_files_error_if_file_does_not_exist():
    with tempfile.TemporaryDirectory() as temp_dir:
        folder_path = pathlib.Path(temp_dir)

        # Create the config file
        config_path = folder_path / "config.ini"
        db_path = folder_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Set variables
        subject_id = "test_subject"
        notes = "These are test notes."

        # Dummy file that does not exist
        dummy_test_files: list[pathlib.Path] = [folder_path / "dummy_file.txt"]

        parse_config = ParseConfig(
            delete_raw_files=DeleteFiles.NO,
            dry_run=DryRun.NO_WRITES,
            config_path=config_path,
        )

        with pytest.raises(FileNotFoundError, match="does not exist"):
            parse_and_save_files(
                dummy_test_files,
                subject_id,
                notes,
                config=parse_config,
            )


def test_parse_and_save_files_error_if_given_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        folder_path = pathlib.Path(temp_dir)

        # Create the config file
        config_path = folder_path / "config.ini"
        db_path = folder_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Set variables
        subject_id = "test_subject"
        notes = "These are test notes."

        # Dummy file that does not exist
        dummy_dir = folder_path / "dummy_dir"
        dummy_dir.mkdir()

        dummy_test_files: list[pathlib.Path] = [dummy_dir]

        parse_config = ParseConfig(
            delete_raw_files=DeleteFiles.NO,
            dry_run=DryRun.NO_WRITES,
            config_path=config_path,
        )

        with pytest.raises(IsADirectoryError, match="is not a file"):
            parse_and_save_files(
                dummy_test_files,
                subject_id,
                notes,
                config=parse_config,
            )


def test_parse_and_save_files_nothing_if_raw_file_invalid():
    with tempfile.TemporaryDirectory() as temp_dir:
        folder_path = pathlib.Path(temp_dir)

        # Create the config file
        config_path = folder_path / "config.ini"
        db_path = folder_path / "db"
        db_path.mkdir()
        update_config(db_path=db_path, config_file_path=config_path)

        # Set variables
        subject_id = "test_subject"
        notes = "These are test notes."

        # Dummy file with incorrect data
        dummy_file = folder_path / "dummy_file.txt"
        dummy_test_files: list[pathlib.Path] = [dummy_file]

        dummy_file.write_bytes(b"This is not a valid raw file.")

        parse_config = ParseConfig(
            delete_raw_files=DeleteFiles.YES,
            dry_run=DryRun.WRITE,
            config_path=config_path,
        )
        import_folder = parse_and_save_files(
            dummy_test_files,
            subject_id,
            notes,
            config=parse_config,
        )

        # Check that nothing was imported
        assert not import_folder.exists()
