"""Module containing functions related to logging."""

import logging.config
from enum import Enum
from pathlib import Path

import colorama
import structlog
from structlog.typing import EventDict, WrappedLogger

from src.utils.paths import ROOT_PATH
from src.utils.time import get_now


class ShowColors(Enum):
    """Enum to set whether to show colors."""

    YES = 0
    NO = 1


class CallsiteConsoleRenderer(structlog.dev.ConsoleRenderer):
    """Renderer that adds callsite information."""

    def __init__(self, colors: ShowColors, **kwargs) -> None:
        """
        Create a new renderer with callsite information.

        Args:
            colors: Whether to show colors in the output
            **kwargs: Additional arguments for the ConsoleRenderer

        """
        super().__init__(colors=colors == ShowColors.YES, **kwargs)

        self._columns.insert(
            1,
            structlog.dev.Column(
                "callsite",
                structlog.dev.KeyValueColumnFormatter(
                    key_style=None,
                    value_style=colorama.Fore.YELLOW
                    if colors == ShowColors.YES
                    else "",
                    reset_style=colorama.Style.RESET_ALL
                    if colors == ShowColors.YES
                    else "",
                    value_repr=str,
                ),
            ),
        )


# Create timestamp for log filename
timestamp = get_now().strftime("%Y-%m-%d_%H-%M-%S.%f")

# Check that the log folder exists. Logs go to the shared top-level output/
# folder (sibling of this versasens/ project root), resolved absolutely from
# ROOT_PATH so it doesn't depend on the process CWD.
log_folder = ROOT_PATH.parent / "output" / "logs"
log_folder.mkdir(parents=True, exist_ok=True)
log_file = log_folder / f"{timestamp}.log"

# Setup logger config
# Processor to add a timestamp
timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=False)


# Custom processor to create the "module.func:lineno" field
def _reformat_callsite(
    _logger: WrappedLogger,
    _name: str,
    event_dict: EventDict,
) -> EventDict:
    # Needs to first get call site parameters in event dict

    module = event_dict.pop("module", None)
    func = event_dict.pop("func_name", None)
    lineno = event_dict.pop("lineno", None)

    if module and func and lineno:
        event_dict["callsite"] = f"{module}.{func}:{lineno}"
    elif module and func:
        event_dict["callsite"] = f"{module}.{func}"
    elif module:
        event_dict["callsite"] = module
    return event_dict


pre_chain = [
    # Add the log level and a timestamp to the event_dict if the log entry
    # is not from structlog.
    structlog.stdlib.add_log_level,
    # Add extra attributes of LogRecord objects to the event dictionary
    # so that values passed in the extra parameter of log methods pass
    # through to log output.
    structlog.stdlib.ExtraAdder(),
    timestamper,
    structlog.processors.CallsiteParameterAdder(
        [
            structlog.processors.CallsiteParameter.MODULE,
            structlog.processors.CallsiteParameter.FUNC_NAME,
            structlog.processors.CallsiteParameter.LINENO,
        ],
    ),
    _reformat_callsite,
]

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    CallsiteConsoleRenderer(colors=ShowColors.NO),
                ],
                "foreign_pre_chain": pre_chain,
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    CallsiteConsoleRenderer(colors=ShowColors.YES),
                ],
                "foreign_pre_chain": pre_chain,
            },
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "colored",
            },
            "file": {
                "level": "DEBUG",
                "class": "logging.handlers.WatchedFileHandler",
                "filename": log_file,
                "formatter": "plain",
            },
        },
        "loggers": {
            "versasens": {
                "handlers": ["default", "file"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    },
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        _reformat_callsite,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
    context_class=dict,
    cache_logger_on_first_use=True,
)

_logger: structlog.stdlib.BoundLogger = structlog.get_logger("versasens")
_logger.debug("Initialized logger")

logger = _logger
