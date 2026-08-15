"""Module containing custom exceptions."""


class DataNotFoundError(Exception):
    """Exception raised when trying to access data that doesn't exist."""


class UnknownHeaderError(Exception):
    """Exception thrown when the header is unknown."""


class UnknownSensorError(Exception):
    """Exception thrown when the given sensor is unknown."""


# ====================================== RawData =======================================


class RawDataError(Exception):
    """Base exception for all RawData-related errors."""


class RawDataConfigError(RawDataError):
    """Raised when required configuration is missing or invalid."""


class RawDataStateError(RawDataError):
    """Raised when RawData is in an invalid or unexpected state."""


class RawDataFileError(RawDataError):
    """Raised when file operations fail."""
