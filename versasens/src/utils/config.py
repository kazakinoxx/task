"""Module containing functions related to the management of the configuration file."""

import configparser
from collections.abc import Callable
from configparser import ConfigParser
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypedDict, TypeVar

from src.utils.constants import (
    DEFAULT_ADS_GAIN,
    DEFAULT_ADS_V_REF,
    DEFAULT_DB_PATH,
    DEFAULT_PLOT_X_AXIS_LENGTH,
)
from src.utils.logger import logger


class SensorParseConfig(TypedDict):
    """Dict containing parameters for the sensor parsing function."""

    ads_vref: int
    ads_gain: int


class _ConfigFieldNames(StrEnum):
    DATABASE_PATH = "DatabasePath"
    PLOT_X_AXIS_LENGTH = "PlotXAxisLength"
    ADS_V_REF = "ADSVRef"
    ADS_GAIN = "ADSGain"


@dataclass
class Config:
    """Class representing the configuration file."""

    db_path: Path
    """Path to the database root folder."""

    plot_x_axis_length: float
    """Length in seconds of the x axis during plotting."""

    ads_vref: int
    """The V_REF for the ADS sensor."""

    ads_gain: int
    """The GAIN for the ADS sensor."""

    @staticmethod
    def get_db_path(config_path: Path) -> Path:
        """
        Get the path to the database root folder from the config file.

        Args:
            config_path: Alternative path to the config file

        Returns:
            The path to the database root folder.

        """
        config = get_or_create_config(config_path)
        return config.db_path

    @staticmethod
    def get_plot_x_axis_length(config_path: Path) -> float:
        """
        Get the length of the X axis during plotting from the config file.

        Args:
            config_path: The path to the config file.

        Returns:
            The length of the X axis during plotting.

        """
        config = get_or_create_config(config_path)
        return config.plot_x_axis_length

    @staticmethod
    def get_sensor_parse_config(config_path: Path) -> SensorParseConfig:
        """
        Get the config parameters for the sensor parsing functions.

        Args:
            config_path: The path to the config file.

        Returns:
            The sensor parsing config.

        """
        config = get_or_create_config(config_path)
        return {"ads_gain": config.ads_gain, "ads_vref": config.ads_vref}


def _write_config(
    config_file_path: Path,
    db_path: Path,
    plot_x_axis_length: float,
    ads_vref: int,
    ads_gain: int,
) -> None:
    # Create database folder
    db_path.mkdir(exist_ok=True, parents=True)

    # Create config parser
    config = ConfigParser()
    config["Config"] = {
        _ConfigFieldNames.DATABASE_PATH: str(db_path),
        _ConfigFieldNames.PLOT_X_AXIS_LENGTH: str(plot_x_axis_length),
        _ConfigFieldNames.ADS_V_REF: str(ads_vref),
        _ConfigFieldNames.ADS_GAIN: str(ads_gain),
    }

    # Write the config file
    with config_file_path.open("w", encoding="utf-8") as f:
        config.write(f)

    logger.debug("Written config file", path=str(config_file_path.resolve()))


T = TypeVar("T")


def _get_updated_field(
    update_val: T | None,
    default_val: T,
    get_config_val: Callable[[], T],
) -> T:
    if update_val is not None:
        # Given a new value
        return update_val

    # Check if in config
    try:
        return get_config_val()
    except KeyError:
        pass

    return default_val


def update_config(
    config_file_path: Path,
    db_path: Path | None = None,
    plot_x_axis_length: float | None = None,
    ads_vref: int | None = None,
    ads_gain: int | None = None,
) -> None:
    """
    Update the config file with the given arguments.

    Args:
        db_path: (optional) Path to the database root folder.
        plot_x_axis_length: (optional) Length of the X axis during plotting.
        config_file_path: (optional) Path to the config file.
        ads_vref: (optional) V_REF value for the ADS sensor.
        ads_gain: (optional) GAIN value for the ADS sensor.

    Returns:
        The updated config file object.

    """
    # If config exists, read it
    config = ConfigParser()
    if config_file_path.exists():
        config.read(config_file_path, encoding="utf-8")

    # Get new db path
    new_db_path = _get_updated_field(
        db_path,
        DEFAULT_DB_PATH,
        lambda: Path(config["Config"][_ConfigFieldNames.DATABASE_PATH]),
    )

    # Get plot axis length
    new_plot_x_axis_length = _get_updated_field(
        plot_x_axis_length,
        DEFAULT_PLOT_X_AXIS_LENGTH,
        lambda: float(config["Config"][_ConfigFieldNames.PLOT_X_AXIS_LENGTH]),
    )

    # Get ADS vars
    new_ads_v_ref = _get_updated_field(
        ads_vref,
        DEFAULT_ADS_V_REF,
        lambda: int(config["Config"][_ConfigFieldNames.ADS_V_REF]),
    )

    new_ads_gain = _get_updated_field(
        ads_gain,
        DEFAULT_ADS_GAIN,
        lambda: int(config["Config"][_ConfigFieldNames.ADS_GAIN]),
    )

    # Write the new config file
    _write_config(
        config_file_path,
        db_path=new_db_path,
        plot_x_axis_length=new_plot_x_axis_length,
        ads_vref=new_ads_v_ref,
        ads_gain=new_ads_gain,
    )

    logger.info(
        "Updated config file",
        db_path=db_path,
        plot_x_axis_length=plot_x_axis_length,
        ads_v_ref=new_ads_v_ref,
        ads_gain=new_ads_gain,
    )


def _create_default_config(config_path: Path) -> None:
    _write_config(
        config_path,
        db_path=DEFAULT_DB_PATH,
        plot_x_axis_length=DEFAULT_PLOT_X_AXIS_LENGTH,
        ads_gain=DEFAULT_ADS_GAIN,
        ads_vref=DEFAULT_ADS_V_REF,
    )


def get_or_create_config(config_path: Path) -> Config:
    """
    Read the config file or create it if it doesn't already exist.

    Args:
        config_path: Path to the config file.

    Returns:
        The config object.

    """
    # Create the config file if it doesn't exist
    if not config_path.exists():
        _create_default_config(config_path)
        logger.info("Created config file", path=str(config_path.resolve()))

    # Read the config file
    config_parser = ConfigParser()
    try:
        config_parser.read(config_path)

        logger.debug(
            "Read config file",
            path=str(config_path.resolve()),
        )
    except configparser.Error:
        _create_default_config(config_path)
        logger.info("Created config file", path=str(config_path.resolve()))

        config_parser.read(config_path)

    # Get database path
    if _ConfigFieldNames.DATABASE_PATH not in config_parser["Config"]:
        update_config(config_file_path=config_path, db_path=DEFAULT_DB_PATH)

    # Get plot x axis length
    if _ConfigFieldNames.PLOT_X_AXIS_LENGTH not in config_parser["Config"]:
        update_config(
            config_file_path=config_path,
            plot_x_axis_length=DEFAULT_PLOT_X_AXIS_LENGTH,
        )

    # Get ads v_ref
    if _ConfigFieldNames.ADS_V_REF not in config_parser["Config"]:
        update_config(
            config_file_path=config_path,
            ads_vref=DEFAULT_ADS_V_REF,
        )

    # Get ads gain
    if _ConfigFieldNames.ADS_GAIN not in config_parser["Config"]:
        update_config(
            config_file_path=config_path,
            ads_gain=DEFAULT_ADS_GAIN,
        )

    # Read again to get all changes
    config_parser.read(config_path)

    # Create config object
    return Config(
        db_path=Path(config_parser["Config"][_ConfigFieldNames.DATABASE_PATH]),
        plot_x_axis_length=float(
            config_parser["Config"][_ConfigFieldNames.PLOT_X_AXIS_LENGTH],
        ),
        ads_gain=int(config_parser["Config"][_ConfigFieldNames.ADS_GAIN]),
        ads_vref=int(config_parser["Config"][_ConfigFieldNames.ADS_V_REF]),
    )
