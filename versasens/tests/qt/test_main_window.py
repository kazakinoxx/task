import random
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytestqt.qtbot import QtBot

from src.qt.main_window import MainWindow
from src.utils.time import get_now
from src.versa.db import timestamp_str_to_datetime, write_data
from src.versa.sensor_group import SensorGroup

# ====================================== Fixtures ======================================


@pytest.fixture
def main_window(config_with_path: Path, qtbot: QtBot) -> MainWindow:
    window = MainWindow(config_file_path=config_with_path)
    qtbot.addWidget(window)
    return window


# ====================================== __init__ ======================================


class TestInit:
    def test_works(self, config_with_path: Path, qtbot: QtBot):
        main_window = MainWindow(config_file_path=config_with_path)
        qtbot.addWidget(main_window)

    def test_works_with_no_config(self, tmp_path: Path, qtbot: QtBot):
        config_path = tmp_path / "config.json"

        # Check that it doesn't exist
        assert not config_path.exists()

        # Call init
        main_window = MainWindow(config_file_path=config_path)
        qtbot.addWidget(main_window)

        # Check that it was created
        assert config_path.exists()

    def test_correctly_initialized_empty(self, config_with_path: Path, qtbot: QtBot):
        main_window = MainWindow(config_file_path=config_with_path)
        qtbot.addWidget(main_window)

        # Check correct config path
        assert main_window.config_file_path == config_with_path

        # Check no subject_id or timestamp as db is empty
        assert main_window.subject_id is None
        assert main_window.timestamp is None

        # Check timer not running as db is empty
        assert not main_window.ago_timer.isActive()

    def test_last_added_called(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        magic_mock: MagicMock,
    ):
        # Patch _update_last_added
        monkeypatch.setattr(MainWindow, "_update_last_added", magic_mock)

        # Call init
        main_window = MainWindow(config_file_path=config_with_path)
        qtbot.addWidget(main_window)

        # Check was called
        magic_mock.assert_called()

    def test_update_ago_text_called(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        magic_mock: MagicMock,
        test_files_parsed_dict: dict[Path, SensorGroup],
        subject_id: str,
        notes: str,
    ):
        # Patch _update_last_added
        monkeypatch.setattr(MainWindow, "_update_ago_text", magic_mock)

        # Add data
        write_data(
            test_files_parsed_dict,
            subject_id,
            notes,
            config_path=config_with_path,
        )

        # Call init
        main_window = MainWindow(config_file_path=config_with_path)
        qtbot.addWidget(main_window)

        # Check was called
        magic_mock.assert_called()

    @pytest.mark.parametrize(
        ("fct_name", "button_name"),
        [
            ("_add_button_clicked", "add_button"),
            ("_settings_button_clicked", "settings_button"),
            ("_view_button_clicked", "view_button"),
            ("_stream_button_clicked", "stream_button"),
        ],
    )
    def test_buttons_initialized(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        magic_mock: MagicMock,
        fct_name: str,
        button_name: str,
    ):
        # Patch _update_last_added
        monkeypatch.setattr(MainWindow, fct_name, magic_mock)

        # Call init
        main_window = MainWindow(config_file_path=config_with_path)
        qtbot.addWidget(main_window)

        # Click button
        getattr(main_window, button_name).click()

        # Check was called
        magic_mock.assert_called()


# ================================= _update_last_added =================================


class TestUpdateLastAdded:
    def test_no_samples(self, main_window: MainWindow):
        # Run function
        main_window._update_last_added()

        # Check that text is correct
        assert main_window.last_id_text.text() == "No samples"
        assert main_window.time_ago_text.text() == ""

    def test_finds_last_added(
        self,
        main_window: MainWindow,
        test_files_parsed_dict: dict[Path, SensorGroup],
        subject_id: str,
        notes: str,
    ):
        # Import data
        import_folder = write_data(
            test_files_parsed_dict,
            subject_id,
            notes,
            config_path=main_window.config_file_path,
        )

        # Get timestamp
        timestamp_dt = timestamp_str_to_datetime(import_folder.name)
        timestamp_str = timestamp_dt.strftime("%d.%m.%y at %H:%M:%S")

        # Run function
        main_window._update_last_added()

        # Check that text is correct
        assert main_window.last_id_text.text() == f"ID {subject_id} - {timestamp_str}"
        assert main_window.time_ago_text.text() != ""

    def test_timer_only_if_found(
        self,
        main_window: MainWindow,
        test_files_parsed_dict: dict[Path, SensorGroup],
        subject_id: str,
        notes: str,
    ):
        # Run function without samples
        main_window._update_last_added()

        # Check the timer is not running
        assert not main_window.ago_timer.isActive()

        # Import data
        write_data(
            test_files_parsed_dict,
            subject_id,
            notes,
            config_path=main_window.config_file_path,
        )

        # Re-run function
        main_window._update_last_added()

        # Check the timer is running
        assert main_window.ago_timer.isActive()


# ================================== _update_ago_text ==================================


class TestUpdateAgoText:
    def test_works(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        magic_mock: MagicMock,
    ):
        # Create window
        main_window = MainWindow(config_file_path=config_with_path)
        qtbot.addWidget(main_window)

        # Replace the setText by the callback
        monkeypatch.setattr(main_window.time_ago_text, "setText", magic_mock)

        # Manually call fct
        main_window.timestamp = get_now()
        main_window._update_ago_text()

        # Check that the ago text was updated
        magic_mock.assert_called_once()

    def test_does_nothing_if_no_timestamp(
        self,
        main_window: MainWindow,
        monkeypatch: pytest.MonkeyPatch,
        magic_mock: MagicMock,
    ):
        main_window.timestamp = None

        # Replace the setText by the callback
        monkeypatch.setattr(main_window.time_ago_text, "setText", magic_mock)

        # Check that the ago text was not updated
        magic_mock.assert_not_called()

    def test_works_if_zero(self, main_window: MainWindow):
        timestamp = get_now()
        main_window.timestamp = timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=timestamp):
            main_window._update_ago_text()

            assert main_window.time_ago_text.text() == "(0 seconds ago)"

    def test_works_if_seconds(self, main_window: MainWindow):
        rnd_seconds = random.randint(2, 59)

        now_timestamp = get_now()
        stored_timestamp = now_timestamp - timedelta(seconds=rnd_seconds)

        main_window.timestamp = stored_timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=now_timestamp):
            main_window._update_ago_text()

            assert main_window.time_ago_text.text() == f"({rnd_seconds} seconds ago)"

    def test_works_if_minutes(self, main_window: MainWindow):
        rnd_seconds = random.randint(2, 59)
        rnd_minutes = random.randint(2, 59)

        now_timestamp = get_now()
        stored_timestamp = now_timestamp - timedelta(
            minutes=rnd_minutes,
            seconds=rnd_seconds,
        )

        main_window.timestamp = stored_timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=now_timestamp):
            main_window._update_ago_text()

            exp = f"({rnd_minutes} minutes and {rnd_seconds} seconds ago)"
            assert main_window.time_ago_text.text() == exp

    def test_works_if_hours(self, main_window: MainWindow):
        rnd_seconds = random.randint(2, 59)
        rnd_minutes = random.randint(2, 59)
        rnd_hours = random.randint(2, 23)

        now_timestamp = get_now()
        stored_timestamp = now_timestamp - timedelta(
            hours=rnd_hours,
            minutes=rnd_minutes,
            seconds=rnd_seconds,
        )

        main_window.timestamp = stored_timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=now_timestamp):
            main_window._update_ago_text()

            exp = (
                f"({rnd_hours} hours, {rnd_minutes} minutes and "
                f"{rnd_seconds} seconds ago)"
            )
            assert main_window.time_ago_text.text() == exp

    def test_works_if_days(self, main_window: MainWindow):
        rnd_days = random.randint(2, 27)
        rnd_seconds = random.randint(2, 59)
        rnd_minutes = random.randint(2, 59)
        rnd_hours = random.randint(2, 23)

        now_timestamp = get_now()
        stored_timestamp = now_timestamp - timedelta(
            days=rnd_days,
            hours=rnd_hours,
            minutes=rnd_minutes,
            seconds=rnd_seconds,
        )

        main_window.timestamp = stored_timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=now_timestamp):
            main_window._update_ago_text()

            exp = (
                f"({rnd_days} days, {rnd_hours} hours, {rnd_minutes} minutes and "
                f"{rnd_seconds} seconds ago)"
            )
            assert main_window.time_ago_text.text() == exp

    def test_works_if_months(self, main_window: MainWindow):
        rnd_days = random.randint(32, 364)
        rnd_seconds = random.randint(2, 59)
        rnd_minutes = random.randint(2, 59)
        rnd_hours = random.randint(2, 23)

        now_timestamp = get_now()
        stored_timestamp = now_timestamp - timedelta(
            days=rnd_days,
            hours=rnd_hours,
            minutes=rnd_minutes,
            seconds=rnd_seconds,
        )

        main_window.timestamp = stored_timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=now_timestamp):
            main_window._update_ago_text()

            exp = (
                f"({rnd_days} days, {rnd_hours} hours, {rnd_minutes} minutes and "
                f"{rnd_seconds} seconds ago)"
            )
            assert main_window.time_ago_text.text() == exp

    def test_works_if_years(self, main_window: MainWindow):
        rnd_days = random.randint(366, 365 * 10)
        rnd_seconds = random.randint(2, 59)
        rnd_minutes = random.randint(2, 59)
        rnd_hours = random.randint(2, 23)

        now_timestamp = get_now()
        stored_timestamp = now_timestamp - timedelta(
            days=rnd_days,
            hours=rnd_hours,
            minutes=rnd_minutes,
            seconds=rnd_seconds,
        )

        main_window.timestamp = stored_timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=now_timestamp):
            main_window._update_ago_text()

            exp = (
                f"({rnd_days} days, {rnd_hours} hours, {rnd_minutes} minutes and "
                f"{rnd_seconds} seconds ago)"
            )
            assert main_window.time_ago_text.text() == exp

    def test_singular(self, main_window: MainWindow):
        now_timestamp = get_now()
        stored_timestamp = now_timestamp - timedelta(
            days=1,
            hours=1,
            minutes=1,
            seconds=1,
        )

        main_window.timestamp = stored_timestamp

        # Replace the get_now function
        with patch("src.qt.main_window.get_now", return_value=now_timestamp):
            main_window._update_ago_text()

            exp = "(1 day, 1 hour, 1 minute and 1 second ago)"
            assert main_window.time_ago_text.text() == exp


# ================================= _X_button_clicked ==================================


class TestButtonClicked:
    @pytest.mark.parametrize(
        ("dialog_name", "handler_name"),
        [
            ("AddSamplesDialog", "_add_button_clicked"),
            ("SettingsDialog", "_settings_button_clicked"),
            ("ViewImportedDataDialog", "_view_button_clicked"),
            ("StreamDialog", "_stream_button_clicked"),
        ],
    )
    def test_click_opens_dialog(
        self,
        main_window: MainWindow,
        magic_mock: MagicMock,
        dialog_name: str,
        handler_name: str,
    ):
        # Need to replace the dialog
        with patch(f"src.qt.main_window.{dialog_name}", return_value=magic_mock):
            getattr(main_window, handler_name)()

            # Check that exec was called
            magic_mock.exec.assert_called_once()

    @pytest.mark.parametrize(
        ("dialog_name", "handler_name"),
        [
            ("AddSamplesDialog", "_add_button_clicked"),
            ("SettingsDialog", "_settings_button_clicked"),
            ("StreamDialog", "_stream_button_clicked"),
        ],
    )
    def test_click_updates_last_added(
        self,
        main_window: MainWindow,
        dialog_name: str,
        handler_name: str,
        monkeypatch: pytest.MonkeyPatch,
    ):
        mock_dialog = MagicMock()
        mock_update = MagicMock()

        # Replace _update_last_added
        monkeypatch.setattr(main_window, "_update_last_added", mock_update)

        # Need to replace the dialog
        with patch(f"src.qt.main_window.{dialog_name}", return_value=mock_dialog):
            getattr(main_window, handler_name)()

            # Check that _update_last_added was called
            mock_update.assert_called_once()
