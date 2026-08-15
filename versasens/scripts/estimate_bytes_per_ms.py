from pathlib import Path

import tqdm

from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor_group import SensorGroup

ROOT = Path(__file__).resolve().parent.parent
TEST_FILES_FOLDER = ROOT / "tests" / "test_files"


MAX_MS = 10 * 60 * 60 * 1000


def _get_all_test_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []

    res: list[Path] = []

    for file in root.iterdir():
        if file.is_dir():
            rec_files = _get_all_test_files(file)
            res.extend(rec_files)
        else:
            res.append(file)

    return res


def main():
    ratios: list[float] = []

    # Go through the test files
    test_files = _get_all_test_files(TEST_FILES_FOLDER)

    with tqdm.tqdm(total=len(test_files)) as pbar:
        for i, file_path in enumerate(test_files):
            pbar.update()
            # Get the file size
            size_bytes = file_path.stat().st_size

            # Get the timestamp of the first sample and the last sample
            start_time_ms: int | None = None
            end_time_ms: int | None = None

            # Parse the file
            with RawData.from_file(file_path, WriteLocation.TO_MEMORY) as raw_data:
                try:
                    sensors = SensorGroup().add_raw_data(
                        raw_data, {"ads_gain": 12, "ads_vref": 4},
                    )
                except Exception:
                    continue

            # Go through each sensor and get timestamps
            for sensor in sensors._get_all_sensors():
                if len(sensor.time_list) == 0:
                    continue

                sens_start = sensor.time_list[0]
                if start_time_ms is None:
                    start_time_ms = sens_start
                else:
                    start_time_ms = min(start_time_ms, sens_start)

                sens_end = sensor.time_list[-1]
                if end_time_ms is None:
                    end_time_ms = sens_end
                else:
                    end_time_ms = max(end_time_ms, sens_end)

            # Check that we have found times
            if start_time_ms is None or end_time_ms is None:
                continue

            # Compute overall time in seconds
            time_ms = end_time_ms - start_time_ms

            if time_ms == 0:
                continue

            # Compute ratio
            bytes_per_ms = size_bytes / time_ms

            pbar.write(
                f"File {file_path.name} has {bytes_per_ms} bytes per millisecond"
            )

            ratios.append(bytes_per_ms)

    print(f"The maximum bytes per millisecond is: {max(ratios)}")

    max_size = max(ratios) * MAX_MS
    max_size_kb = max_size / 1000.0
    max_size_mb = max_size_kb / 1000.0
    max_size_gb = max_size_mb / 1000.0
    print(f"The maximum file size is {max_size} B")
    print(f"The maximum file size is {max_size_kb} kB")
    print(f"The maximum file size is {max_size_mb} MB")
    print(f"The maximum file size is {max_size_gb} GB")


if __name__ == "__main__":
    main()
