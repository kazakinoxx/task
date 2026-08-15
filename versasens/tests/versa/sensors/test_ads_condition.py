import struct
from unittest.mock import MagicMock

from src.generated.sensors_info import SENSOR_ATTR_NAMES
from src.versa.ble import _get_ble_notification_handler
from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor_group import SensorGroup

ADS_FMT = "<hIHBB24sBB"
MARKER_FMT = "<HIHBBBH"


def _ads_record(seconds: int, milliseconds: int, index: int, condition: int) -> bytes:
    return struct.pack(
        ADS_FMT,
        0xDDDD - 0x10000,
        seconds,
        milliseconds,
        27,
        index,
        bytes(24),
        0,
        condition << 2,
    )


def test_live_notification_parses_all_six_ads_records(sensor_parse_config) -> None:
    batch = b"".join(
        _ads_record(1, 100 + i * 8, i * 4, int(i >= 3)) for i in range(6)
    )
    data = SensorGroup()
    should_process = dict.fromkeys(SENSOR_ATTR_NAMES, False)
    should_process["ads"] = True

    with RawData(WriteLocation.TO_MEMORY) as raw_output:
        handler = _get_ble_notification_handler(
            data,
            raw_output,
            should_process,
            MagicMock(),
            sensor_parse_config,
        )
        handler(None, bytearray(batch))

    assert len(data.ads.idx_list) == 6
    assert data.ads.idx_list == [0, 4, 8, 12, 16, 20]
    assert data.ads.condition_id_list == [0, 0, 0, 1, 1, 1]


def test_target_marker_uses_standard_record_framing(sensor_parse_config) -> None:
    marker = struct.pack(
        MARKER_FMT,
        0x7777,
        12,
        345,
        4,
        9,
        1,
        23,
    )
    with RawData.from_bytes(marker, WriteLocation.TO_MEMORY) as raw_data:
        parsed = SensorGroup().add_raw_data(raw_data, sensor_parse_config)

    assert parsed.marker.time_list == [12_345]
    assert parsed.marker.idx_list == [9]
    assert parsed.marker.command_list == [1]
    assert parsed.marker.transition_sequence_list == [23]
