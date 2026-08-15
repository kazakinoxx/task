"""Generates a file containing the imports and constants needed to use the sensors."""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import NamedTuple

from jinja2 import Environment, FileSystemLoader

import src.versa.sensors

# Get the path to the import folder
# This is done this way to help the IDE to detect changes if this folder moves
from src.versa.sensor import Sensor

SENSORS_MODULE = src.versa.sensors
SENSORS_MODULE_IMPORT_PATH = SENSORS_MODULE.__name__
SENSORS_MODULE_PATH = Path(SENSORS_MODULE.__path__[0])

BASE_SENSOR_CLASS = Sensor
BASE_SENSOR_CLASS_MODULE = Sensor.__module__
BASE_SENSOR_CLASS_NAME = BASE_SENSOR_CLASS.__name__

ROOT = Path(__file__).resolve().parent.parent
GENERATED_FILE = ROOT / "src" / "generated" / "sensors_info.py"
SCRIPTS_FOLDER = Path(__file__).resolve().parent
TEMPLATE_NAME = "sensors_info.py.jinja"


class _SensorClassInfo(NamedTuple):
    module_path: str
    class_name: str
    attribute_name: str


def find_sensor_classes() -> list[_SensorClassInfo]:
    """Find all sensor classes inside of the sensors module."""
    res: list[_SensorClassInfo] = []

    # Get every module in the sensors directory
    for sens_module_info in pkgutil.iter_modules([SENSORS_MODULE_PATH]):
        # Get the module corresponding to the sensor
        sens_module_path = f"{SENSORS_MODULE_IMPORT_PATH}.{sens_module_info.name}"
        sens_module = importlib.import_module(sens_module_path)

        # Now get the classes inside of the module
        for class_name, class_obj in inspect.getmembers(sens_module, inspect.isclass):
            # Skip imported classes. Their module is different than the sensors module
            if class_obj.__module__ != sens_module_path:
                continue

            # Just to make sure, skip the base class
            if class_obj is BASE_SENSOR_CLASS:
                continue

            # Only get subclasses of the Sensor class
            if issubclass(class_obj, BASE_SENSOR_CLASS):
                # Get the attribute name
                attr_name = class_obj.attr_name()

                res.append(
                    _SensorClassInfo(
                        module_path=sens_module_path,
                        class_name=class_name,
                        attribute_name=attr_name,
                    ),
                )
                print(f"Found sensor {class_name} in module {sens_module_path}")  # noqa: T201

    return res


def generate() -> None:
    """Generate the python file."""
    classes_info = find_sensor_classes()

    jinja_env = Environment(
        loader=FileSystemLoader(SCRIPTS_FOLDER),
        keep_trailing_newline=True,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = jinja_env.get_template(TEMPLATE_NAME)

    output = template.render(
        base_sensor_class_module=BASE_SENSOR_CLASS_MODULE,
        base_sensor_class_name=BASE_SENSOR_CLASS_NAME,
        classes_info=classes_info,
    )

    GENERATED_FILE.write_text(output)
    print(f"Generated {GENERATED_FILE}.")  # noqa: T201


if __name__ == "__main__":
    generate()
