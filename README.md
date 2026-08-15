# EEG Task Experiment

PsychoPy-based experiment (`frontend/` + pure logic in `src2/`) that records EEG
via the VersaSens headset. On launch it starts a BLE worker (the `versasens/`
project) as a subprocess, so **two Python environments** are involved:

| Environment | Python | Used for |
|---|---|---|
| Experiment | 3.10 | `frontend/` + `src2/` (PsychoPy) |
| BLE worker | 3.13 | `versasens/` (device streaming + recording) |

---

## 1. Experiment environment (Python 3.10)

```bash
py -3.10 -m venv .venv310
.venv310\Scripts\activate
pip install -r src2/requirements.txt
```

## 2. BLE worker environment (Python 3.13, versasens)

The worker is the `versasens/` project, managed with [uv](https://docs.astral.sh/uv/):

```bash
cd versasens
uv sync
cd ..
```

This creates `versasens/.venv`. You can skip this if you only need to develop the
experiment logic without the headset (see *Notes* below).

## 3. Configure the BLE worker paths

`main.py` locates the 3.13 interpreter and hardware via environment variables,
falling back to sensible defaults. Set these to match your machine:

| Variable | Default | Meaning |
|---|---|---|
| `PYTHON313_HOME` | `C:/Users/ikaze/AppData/Local/Programs/Python/Python313` | Folder containing the Python 3.13 `python.exe` that runs the worker |
| `OPUS_LIBRARY_PATH` | same as `PYTHON313_HOME` | Folder containing the libopus DLL |
| `BLE_MARKER_PORT` | `COM3` | Serial port the marker/trigger board enumerates as |

Example (PowerShell):

```powershell
$env:PYTHON313_HOME = "C:/Path/To/Python313"
$env:BLE_MARKER_PORT = "COM4"
```

The versasens project root itself is resolved relative to the repo (`./versasens`),
so it needs no configuration.

## 4. Run the experiment

```bash
python -m frontend.main --participant P01
```

Other useful flags: `--trigger {none,parallel,serial}`, `--audio-device`,
`--audio-mono`. Experiment settings live in `src2/settings.json`.

---

## Output

All generated data is written under a single top-level `output/` folder:

```
output/
  task_data/   # per-participant session + checkpoint JSON
  eeg/         # EEG recordings from the BLE worker
  logs/        # BLE worker logs
```

The folder skeleton is tracked in git; its contents are gitignored. Sessions are
checkpointed after every trial, so a crashed run resumes from where it stopped
when you relaunch with the same `--participant`.

## Notes

- Launching the experiment starts the BLE worker subprocess unconditionally, so
  the versasens environment (step 2) and the headset/marker hardware are expected
  to be present for a full run.
- The `PYTHON313_HOME` default points at one specific machine — set the env var
  on any other machine.
