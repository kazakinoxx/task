from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot

from src.qt.settings_dialog import SettingsDialog
from src.utils.config import Config

if TYPE_CHECKING:
    from PySide6.QtCore import QUrl

# ====================================== Fixtures ======================================


@pytest.fixture
def settings_dialog(config_with_path: Path, qtbot: QtBot) -> SettingsDialog:
    window = SettingsDialog(config_path=config_with_path)
    qtbot.addWidget(window)
    return window


# ====================================== __init__ ======================================


class TestInit:
    def test_works(self, config_with_path: Path, qtbot: QtBot):
        dialog = SettingsDialog(config_path=config_with_path)
        qtbot.addWidget(dialog)

    def test_initialized_variables(self, config_with_path: Path, qtbot: QtBot):
        dialog = SettingsDialog(config_path=config_with_path)
        qtbot.addWidget(dialog)

        # Check config path set
        assert dialog.config_path is not None
        assert dialog.config_path == config_with_path

    @pytest.mark.parametrize(
        ("fct_name", "button_name"),
        [
            ("_open_config_file", "open_button"),
            ("_change_db_path", "db_button"),
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
        monkeypatch.setattr(SettingsDialog, fct_name, magic_mock)

        # Call init
        dialog = SettingsDialog(config_path=config_with_path)
        qtbot.addWidget(dialog)

        # Click button
        getattr(dialog, button_name).click()

        # Check was called
        magic_mock.assert_called()

    def test_updates_the_db_path_text(self, config_with_path: Path, qtbot: QtBot):
        dialog = SettingsDialog(config_path=config_with_path)
        qtbot.addWidget(dialog)

        # Check that the db path text was given
        assert dialog.db_lineedit.text() != ""


# ================================== _refresh_config ===================================


class TestRefreshConfig:
    def test_creates_config_if_not_exists(self, tmp_path: Path, qtbot: QtBot):
        config_path = tmp_path / "config.json"

        # Check it doesn't exist
        assert not config_path.exists()

        # Call init
        dialog = SettingsDialog(config_path=config_path)
        qtbot.addWidget(dialog)

        # Call fct
        dialog._refresh_config()

        # Check it now exists
        assert config_path.exists()

    def test_updates_db_path_text(self, settings_dialog: SettingsDialog):
        # Call fct
        settings_dialog._refresh_config()

        # Check text updated
        assert settings_dialog.db_lineedit.text() != ""


# ================================== _change_db_path ===================================


class TestChangeDbPath:
    def test_updates_db_path(self, settings_dialog: SettingsDialog, tmp_path: Path):
        # Patch QFileDialog.getExistingDirectory
        with patch(
            "src.qt.settings_dialog.QFileDialog.getExistingDirectory",
            return_value=tmp_path,
        ):
            settings_dialog._change_db_path()

        # Check db path text
        assert settings_dialog.db_lineedit.text() == str(tmp_path)

        # Check config file updated
        res_db_path = Config.get_db_path(settings_dialog.config_path)
        assert res_db_path == tmp_path

    def test_updates_db_path_text(
        self,
        settings_dialog: SettingsDialog,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Patch QFileDialog.getExistingDirectory
        monkeypatch.setattr(
            QFileDialog,
            "getExistingDirectory",
            lambda *_args, **_kwargs: tmp_path,
        )

        settings_dialog._change_db_path()

        # Check db path text
        assert settings_dialog.db_lineedit.text() == str(tmp_path)

    def test_works_if_no_config(
        self,
        settings_dialog: SettingsDialog,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        new_config_path = tmp_path / "new_config.json"
        new_db_path = tmp_path / "new_db"

        # Change config path
        settings_dialog.config_path = new_config_path
        assert not new_config_path.exists()

        # Patch QFileDialog.getExistingDirectory
        monkeypatch.setattr(
            QFileDialog,
            "getExistingDirectory",
            lambda *_args, **_kwargs: new_db_path,
        )

        settings_dialog._change_db_path()

        # Check db path text
        assert settings_dialog.db_lineedit.text() == str(new_db_path)

        # Check config file updated
        res_db_path = Config.get_db_path(new_config_path)
        assert res_db_path == new_db_path


# ================================= _open_config_file ==================================


class TestOpenConfigFile:
    def test_shows_error_if_not_exists(
        self,
        settings_dialog: SettingsDialog,
        tmp_path: Path,
        magic_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ):
        new_config_path = tmp_path / "new_config.json"

        # Change config path
        settings_dialog.config_path = new_config_path
        assert not new_config_path.exists()

        # Patch QMessageBox.critical
        monkeypatch.setattr(QMessageBox, "critical", magic_mock)

        # Call function
        settings_dialog._open_config_file()

        # Check was called
        magic_mock.assert_called_once()

        # Check error message
        error_msg: str = magic_mock.call_args[0][2]
        assert "doesn't exist" in error_msg

    def test_shows_error_if_not_a_file(
        self,
        settings_dialog: SettingsDialog,
        tmp_path: Path,
        magic_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ):
        new_config_path = tmp_path / "new_config"
        new_config_path.mkdir()

        # Change config path
        settings_dialog.config_path = new_config_path
        assert not new_config_path.is_file()

        # Patch QMessageBox.critical
        monkeypatch.setattr(QMessageBox, "critical", magic_mock)

        # Call function
        settings_dialog._open_config_file()

        # Check was called
        magic_mock.assert_called_once()

        # Check error message
        error_msg: str = magic_mock.call_args[0][2]
        assert "is not a file" in error_msg

    def test_works(
        self,
        settings_dialog: SettingsDialog,
        magic_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Patch QDesktopServices.openUrl
        monkeypatch.setattr(QDesktopServices, "openUrl", magic_mock)

        # Call function
        settings_dialog._open_config_file()

        # Check was called
        magic_mock.assert_called_once()

        # Check given correct path
        qurl: QUrl = magic_mock.call_args[0][0]
        # Remove first slash
        qurl_path = Path(qurl.toLocalFile())

        assert qurl_path == settings_dialog.config_path
