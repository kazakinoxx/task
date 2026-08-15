# """Module containing utility functions for tests."""

# from pathlib import Path

# from src.utils.paths import ROOT_PATH
# from src.versa.raw_data import RawData, WriteLocation
# from src.versa.sensor_group import SensorGroup


# def _split_raw_file_into_samples(raw_file_path: Path) -> list[bytes]:
#     all_bytes = raw_file_path.read_bytes()
#     chunks: list[bytes] = []

#     with RawData.from_bytes(all_bytes, WriteLocation.TO_MEMORY) as raw_data:
#         data = SensorGroup()

#         last_start = 0

#         while not data.add_data_single_read(raw_data):
#             cur_pos = raw_data.tell()
#             chunks.append(all_bytes[last_start:cur_pos])
#             last_start = cur_pos

#     return chunks


# TEST_FILES_FOLDER_PATH = ROOT_PATH / "tests" / "test_files"

# TEST_FILE_1_PATH = TEST_FILES_FOLDER_PATH / "file1.TXT"
# TEST_FILE_2_PATH = TEST_FILES_FOLDER_PATH / "file2.TXT"

# TEST_FILES = [TEST_FILE_1_PATH, TEST_FILE_2_PATH]

# TEST_FILES_CHUNKS = [_split_raw_file_into_samples(f) for f in TEST_FILES]

# PARSED_TEST_FILES = {p: SensorGroup.parse_raw_file(p) for p in TEST_FILES}

# TEST_FILES_CHUNKS_AND_PARSED = [
#     (_split_raw_file_into_samples(f), SensorGroup.parse_raw_file(f)) for f in TEST_FILES
# ]

# TEST_FILES_PATH_CHUNKS_AND_PARSED = [
#     (f, _split_raw_file_into_samples(f), SensorGroup.parse_raw_file(f))
#     for f in TEST_FILES
# ]
