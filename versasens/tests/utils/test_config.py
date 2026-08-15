import pathlib
import random
from configparser import ConfigParser

import pytest

from src.utils.config import (
    Config,
    _ConfigFieldNames,
    _create_default_config,
    get_or_create_config,
    update_config,
)
from src.utils.constants import (
    DEFAULT_ADS_GAIN,
    DEFAULT_ADS_V_REF,
    DEFAULT_DB_PATH_STR,
    DEFAULT_PLOT_X_AXIS_LENGTH,
)


@pytest.fixture
def config_path(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "config.ini"


@pytest.fixture
def db_path(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "db"


@pytest.fixture
def plot_x_axis_length(random_float: int) -> int:
    return random_float


@pytest.fixture
def ads_vref(random_int: int) -> int:
    return random_int


@pytest.fixture
def ads_gain(random_int: int) -> int:
    return random_int


# ======================== get_or_create_config ========================


class TestGetOrCreateConfig:
    def test_works(self, config_path: pathlib.Path):
        get_or_create_config(config_path)

        # Check values
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        # Category check
        assert "Config" in config

        # Database path
        assert _ConfigFieldNames.DATABASE_PATH in config["Config"]
        assert config["Config"][_ConfigFieldNames.DATABASE_PATH] == DEFAULT_DB_PATH_STR

        # Plot X axis length
        assert _ConfigFieldNames.PLOT_X_AXIS_LENGTH in config["Config"]
        assert config["Config"][_ConfigFieldNames.PLOT_X_AXIS_LENGTH] == str(
            DEFAULT_PLOT_X_AXIS_LENGTH,
        )

        # ADS V_REF
        assert _ConfigFieldNames.ADS_V_REF in config["Config"]
        assert config["Config"][_ConfigFieldNames.ADS_V_REF] == str(DEFAULT_ADS_V_REF)

        # ADS GAIN
        assert _ConfigFieldNames.ADS_GAIN in config["Config"]
        assert config["Config"][_ConfigFieldNames.ADS_GAIN] == str(DEFAULT_ADS_GAIN)

    def test_config_already_exists(self, config_path: pathlib.Path):
        get_or_create_config(config_path)
        get_or_create_config(config_path)

    def test_creates_config_if_not_exists(self, config_path: pathlib.Path):
        assert not config_path.exists()

        get_or_create_config(config_path)

        assert config_path.exists()

    def test_creates_default_config_if_no_header(
        self,
        config_path: pathlib.Path,
        random_int: int,
    ):
        # Create base config
        get_or_create_config(config_path)

        # Change gain to random value
        update_config(config_path, ads_gain=random_int)

        # Remove the [Config] line
        lines = config_path.read_text().split("\n")
        new_lines = [line for line in lines if "[Config]" not in line]
        new_text = "\n".join(new_lines)
        config_path.write_text(new_text)

        # Recreate config
        config = get_or_create_config(config_path)

        # Check that gain has the overwritten default value
        assert config.ads_gain == DEFAULT_ADS_GAIN

    def test_works_when_missing_values(self, config_path: pathlib.Path):
        for i in range(len(_ConfigFieldNames)):
            # Create a default config
            _create_default_config(config_path)

            # Remove a random line
            lines = config_path.read_text().split("\n")
            var_lines = [
                line for line in lines if "[Config]" not in line and "=" in line
            ]
            new_lines = ["[Config]"]
            var_lines.pop(i)
            new_lines.extend(var_lines)
            config_path.write_text("\n".join(new_lines))

            # Call fn
            config = get_or_create_config(config_path)

            # Check values are there
            assert config.db_path == pathlib.Path(DEFAULT_DB_PATH_STR)
            assert config.plot_x_axis_length == DEFAULT_PLOT_X_AXIS_LENGTH
            assert config.ads_vref == DEFAULT_ADS_V_REF
            assert config.ads_gain == DEFAULT_ADS_GAIN


# ======================== update_config ========================


class TestUpdateConfig:
    def test_no_args(self, config_path: pathlib.Path):
        update_config(config_path)

        # Check values
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        assert config["Config"]["DatabasePath"] == DEFAULT_DB_PATH_STR

    def test_preexisting_no_args(self, config_path: pathlib.Path):
        # Create the config file
        get_or_create_config(config_path)

        # Check that it was created
        assert config_path.exists()

        # Update config
        update_config(config_path)

        # Check values
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        assert config["Config"]["DatabasePath"] == DEFAULT_DB_PATH_STR

    @pytest.mark.parametrize(
        "arg_name",
        [
            "db_path",
            "plot_x_axis_length",
            "ads_vref",
            "ads_gain",
        ],
    )
    def test_works(
        self,
        config_path: pathlib.Path,
        arg_name: str,
        request,
    ):
        arg_val = request.getfixturevalue(arg_name)

        update_config(**{arg_name: arg_val, "config_file_path": config_path})

        # Check values
        config = get_or_create_config(config_path)

        assert getattr(config, arg_name) == arg_val

    def test_preexisting_with_db_path(
        self,
        config_path: pathlib.Path,
        db_path: pathlib.Path,
    ):
        # Create the config file
        get_or_create_config(config_path)

        # Check that it was created
        assert config_path.exists()

        # Update config
        update_config(config_path, db_path=db_path)

        # Check values
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        assert config["Config"]["DatabasePath"] == str(db_path)


# ======================== get_db_path ========================


class TestGetDbPath:
    def test_works(self, config_path: pathlib.Path, db_path: pathlib.Path):
        # Update config
        update_config(config_path, db_path=db_path)

        # Check values
        assert Config.get_db_path(config_path) == db_path


# ======================== get_plot_x_axis_length ========================


class TestGetPlotXAxisLength:
    def test_works(self, config_path: pathlib.Path, plot_x_axis_length: int):
        # Update config
        update_config(config_path, plot_x_axis_length=plot_x_axis_length)

        # Check values
        assert Config.get_plot_x_axis_length(config_path) == plot_x_axis_length

    def test_default_value(self, config_path: pathlib.Path):
        # Create default config without setting plot_x_axis_length
        get_or_create_config(config_path)

        # Check default value
        assert Config.get_plot_x_axis_length(config_path) == DEFAULT_PLOT_X_AXIS_LENGTH


# ======================== get_sensor_parse_config ========================


class TestGetSensorParseConfig:
    def test_works(self, config_path: pathlib.Path, ads_vref: int, ads_gain: int):
        # Update config
        update_config(config_path, ads_vref=ads_vref, ads_gain=ads_gain)

        # Check values
        parse_config = Config.get_sensor_parse_config(config_path)

        assert parse_config["ads_vref"] == ads_vref
        assert parse_config["ads_gain"] == ads_gain

    def test_default_values(self, config_path: pathlib.Path):
        # Create default config
        get_or_create_config(config_path)

        # Check default values
        parse_config = Config.get_sensor_parse_config(config_path)

        assert parse_config["ads_vref"] == DEFAULT_ADS_V_REF
        assert parse_config["ads_gain"] == DEFAULT_ADS_GAIN
