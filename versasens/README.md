# VersaSens GUI

This project uses the [uv](https://github.com/astral-sh/uv) python project manager and Qt as a graphics framework.

Only Windows is currently supported.

## How to use

Details on how to use the program can be found in [HOW_TO_USE.md](HOW_TO_USE.md)

## Install dependencies

### Install uv

Run this command in PowerShell.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Sync dependencies

Install dependencies with `uv` using:

```bash
uv sync --locked --all-extras --dev
```

### DLL dependencies

This project requires the `libopus` and `vlc` DLLs as dependencies. They are found in the [dlls](dlls) folder and are automatically imported if not already present in the system.

## Run app

Launch app using uv.

```bash
uv run app.py
```

## Build app

Build the app and create an executable using PyInstaller.

```bash
uv run pyinstaller --clean build.spec 
```

Or create a development executable (shows the terminal) using:

```bash
uv run pyinstaller --clean build.spec -- --debug
```

The executable will be inside the `dist` folder.

## Run tests

Run tests using `pytest`.

```bash
uv run pytest tests
```

## Folder and files structure

Folders:

- [`dlls`](dlls): folder containing the required DLL dependencies.
- [`src`](src): folder containing source files
- [`tests`](tests): folder of test files
- [`ui`](ui): Qt UI files describing the different Qt windows, dialogs and widgets

Files:

- [`app.py`](app.py): main script launching the app
- [`generate_ui.py`](generate_ui.py): generates the code for the Qt UI (output in [`src/generated`](src/generated))

## Implement or edit sensors

The information can be found in file [SENSORS.md](SENSORS.md)

## Edit the interface

The interface is described in XML files inside the `ui` folder. These files can either
be directly modified using a text editor, or by using Qt Creator.

Qt Creator can be opened using the following command:

```bash
uv run pyside6-designer
```

Afterwards, the script `scripts/generate_ui.py` can be used to generate the python code
to create the interface.

```bash
uv run scripts/generate_ui.py
```
>>>>>>> 5f771bf (Initial commit: VersaSens EEG headset GUI (check-electrode build))
