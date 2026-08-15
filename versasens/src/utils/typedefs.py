"""Type definitions used across the project."""

import dataclasses
import datetime
from enum import Enum
from pathlib import Path

SensorHeader = bytes
"""Header of a sensor"""

SubjectID = str
"""The ID of a subject"""

Timestamp = datetime.datetime
"""The timestamp of the import"""

SampleFilename = str
"""The filename of the sample file/folder"""

SensorName = str
"""The name of the sensor"""

SensorAttrName = str
"""The attribute name of the sensor"""

SensorCSVPath = Path
"""Path to the sensor's CSV file."""


@dataclasses.dataclass
class Metadata:
    """Class representing the metadata stored for each sample."""

    subject_id: SubjectID
    notes: str
    timestamp: Timestamp

    lead_off: dict[str, int] | None = None
    """The device's lead-off configuration when the recording was made, read
    back from the device rather than remembered by the GUI. Defaults to None so
    that recordings made before this was captured still load."""


class DryRun(Enum):
    """Enum to set whether to perform a dry run."""

    NO_WRITES = 1
    WRITE = 2


class DeleteFiles(Enum):
    """Enum to set whether to delete files after processing."""

    YES = 1
    NO = 2


class ShouldUpdateGraph(Enum):
    """Enum to set whether to update the correponding graph."""

    YES = 1
    NO = 2


class ClearSensorDataOnClose(Enum):
    """Enum to set whether to clear the sensor's data on dialog close."""

    YES = 1
    NO = 2


class WriteBehaviour(Enum):
    """Enum to set whether to overwrite or append if data is already present."""

    OVERWRITE = 1
    APPEND = 2


class PlotPause(Enum):
    """Enum to set whether the plotting is paused or running."""

    PAUSED = 1
    RUNNING = 2
