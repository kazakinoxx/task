"""Module containing constants for the project."""

import datetime
from pathlib import Path

# ==================================== BLE =====================================

BLE_CHARACTERISTIC_UUID = "E11D2E01-04AB-4DA5-B66A-EECB738F90F3"
"""UUID of the BLE characteristic for data streaming"""

BLE_CMD_CHARACTERISTIC_UUID = "E11D2E03-04AB-4DA5-B66A-EECB738F90F3"
"""UUID of the BLE command characteristic (write + indicate)"""

BLE_CMD_LEAD_OFF_CHECK = 0x10
"""Command byte that asks the device to run a one-shot electrode lead-off check.
The device indicates back 4 bytes: [BLE_CMD_LEAD_OFF_CHECK, statp, statn, rld].
Idle-only: it powers down the RLD amplifier for an accurate RLD reading."""

BLE_CMD_LEAD_OFF_CHECK_LIVE = 0x13
"""Command byte for a lead-off check while a recording is running. Briefly
connects the P/N lead-off resistors and reads their status, bracketing the
perturbed ~500 ms window with CONDITION marker records (commands 3 and 4). The
result is the same 4-byte frame as BLE_CMD_LEAD_OFF_CHECK; the RLD byte is
best-effort because the amplifier keeps driving mid-recording."""

BLE_LEAD_OFF_CHECK_TIMEOUT: float = 6
"""Timeout in seconds to wait for the lead-off check result."""

MARKER_CMD_CHECK_START = 3
"""Marker command value written just before a live lead-off check window."""

MARKER_CMD_CHECK_END = 4
"""Marker command value written just after a live lead-off check window."""

BLE_CMD_SET_LOFF_CFG = 0x11
"""Command byte that sets the lead-off comparator threshold.
Written as 3 bytes: [BLE_CMD_SET_LOFF_CFG, comp_th, reserved]."""

BLE_CMD_GET_LOFF_CFG = 0x12
"""Command byte that reads back the device's lead-off configuration.
Written as 1 byte."""

LOFF_CFG_RESPONSE_LEN = 5
"""Length of a lead-off config indication:
[cmd, status, comp_th, reserved, raw_loff].

Replies on the command characteristic are told apart by the
(first byte, length) pair, never by either one alone: the device's generic
command ack is `value + 0xA0` truncated to 8 bits, so a command of 0x71 acks
as 0x11 and collides with BLE_CMD_SET_LOFF_CFG."""

LOFF_CFG_STATUS_OK = 0
LOFF_CFG_STATUS_NOT_IDLE = 1
LOFF_CFG_STATUS_BAD_PARAM = 2
LOFF_CFG_STATUS_IO_ERROR = 3

LOFF_CFG_STATUS_TEXT = {
    LOFF_CFG_STATUS_OK: "OK",
    LOFF_CFG_STATUS_NOT_IDLE: (
        "The device is recording or streaming. Stop it and try again."
    ),
    LOFF_CFG_STATUS_BAD_PARAM: "The device rejected the value.",
    LOFF_CFG_STATUS_IO_ERROR: "The device could not reach the ADS1298.",
}
"""Human-readable text for each lead-off config status byte."""

LOFF_THRESHOLDS: list[tuple[int, str]] = [
    (0, "95% / 5%"),
    (1, "92.5% / 7.5%"),
    (2, "90% / 10%"),
    (3, "87.5% / 12.5%"),
    (4, "85% / 15%"),
    (5, "80% / 20%"),
    (6, "75% / 25%"),
    (7, "70% / 30%"),
]
"""Selectable lead-off comparator thresholds (LOFF.COMP_TH[2:0]), as
(register value, label) pairs. The label is the positive / negative comparator
trip point as a percentage of the supply. Lower percentages detect a poor
contact sooner; 95% / 5% (the power-on default) is the least sensitive."""

BLE_LOFF_CFG_TIMEOUT: float = 6
"""Timeout in seconds to wait for a lead-off config reply."""

BLE_DEVICE_NAME = "VersaSens"
"""Device name of the VersaSens BLE device"""

BLE_FIND_DEVICES_TIMEOUT: float = 5
"""Timeout to find VersaSens devices in seconds"""

BLE_CONNECTION_TIMEOUT: float = 10
"""Timeout to connect to a BLE device in seconds"""

BLE_MAX_CONNECTION_ATTEMPTS: int = 4
"""Number of max retry attempts when a device disconnected by itself"""

# ================================== PLOTTING ==================================

# Plotting constants
PLOT_REFRESH_RATE = 1000 // 30
"""Refresh rate in milliseconds of the plots"""

DELETE_STALE_DATA_MS = 5 * 1000

DEFAULT_PLOT_X_AXIS_LENGTH = 5.0
"""Size of the time window shown in the plot in seconds
(how many seconds to show)"""

COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]
"""List of colors for plotting"""

# =================================== CONFIG ===================================

DEFAULT_DB_PATH_STR = "db"
"""Default path for the database"""

DEFAULT_DB_PATH = Path(DEFAULT_DB_PATH_STR)
"""Default path for the database"""

DEFAULT_ADS_V_REF = 4
DEFAULT_ADS_GAIN = 12

# ===================================== DB =====================================

METADATA_FILENAME = "metadata.json"
RAW_FILE_FILENAME = "raw_data.txt"

# ==================================== TIME ====================================

LOCAL_TIMEZONE = datetime.datetime.now(tz=datetime.UTC).astimezone().tzinfo

# ====================================== CACHING =======================================

RAW_EST_BYTES_PER_MS = 46
"""Estimated number of bytes per millisecond for raw files"""
