# GUI Changes vs. the Original VersaSens GUI

This document lists everything changed in this GUI
(`versasens-gui-main_headset_check_electrode`) relative to the upstream original
(`originals/versasens-gui-main`). It is GUI-only; the firmware side is described
separately in the handoff document.

The changes fall into four groups, added in this order:
- **A — Condition marker / experiment sync:** decode the experiment condition and
  the `0x7777` marker records embedded in the data.
- **B — Electrode lead-off:** show electrode-contact status and run a
  pre-recording check.
- **C — Runtime lead-off threshold:** set the comparator threshold from the GUI
  and record it in the metadata.
- **D — On-demand check (Variant B) + readable CSV:** run an electrode check
  during a recording over the live connection, mark the perturbed window, and
  emit human-readable per-channel contact columns.

No new third-party dependencies were added (`pyproject.toml` is unchanged);
everything uses the existing `bleak` / `pyqtgraph` / `PySide6` stack.

---

## File-by-file summary

| File | Group | Added | What changed |
|---|---|---|---|
| `src/versa/sensors/marker.py` *(new)* | A | 89 | Parser + plot for the `0x7777` condition/check markers |
| `src/generated/sensors_info.py` | A | +4 | Register the new `Marker` sensor |
| `src/versa/sensors/ads.py` | A,C,D | +224 | `condition_id`, per-channel `*_connected` columns, legacy-CSV loader |
| `src/versa/sensor.py` | A | +11 | `exact_x_range_links()` hook for the condition strip |
| `src/qt/utils/plot_dialog.py` | A | +42 | Exact numerical X-range linking (condition strip alignment) |
| `src/qt/main_window.py` | A | +35 | Disconnect BLE clients on shutdown (macOS crash fix) |
| `src/qt/lead_off/` *(new dir)* | B,D | 4 files | Head diagram, live status dialog, threshold settings dialog |
| `src/versa/ble.py` | B,C,D | +276 | Lead-off check, threshold get/set, live-connection command channel |
| `src/utils/constants.py` | B,C,D | +74 | Command bytes, threshold table, marker command codes |
| `src/qt/stream/stream_dialog.py` | B,C,D | +219 | Lead-off buttons, live check, threshold, metadata capture |
| `src/utils/typedefs.py` | C | +5 | `Metadata.lead_off` field |
| `src/versa/db.py` | C | +5 | Write `lead_off` into `metadata.json` |
| `src/versa/process.py` | C | +5 | Thread `lead_off` through the parse pipeline |
| `src/qt/utils/data_import_dialog.py` | C | +15 | Carry `lead_off` into the import worker |
| `marker_gui/` *(new dir)* | — | 3 files | Standalone USB condition-sender tool (companion, not imported) |

---

## Group A — Condition marker & sample labelling

### `src/versa/sensors/marker.py` (new)
A new `Marker(Sensor)` with header `b"\x77\x77"`. `parse_file()` decodes the
3-byte payload (`command`, `transition_sequence`); `plot_graphics()` step-plots
`command` over time with tick labels **0/1** = condition, **2** = ping,
**3** = check-window start, **4** = check-window end. Because sensors are
discovered by header, this is all that is needed for the `0x7777` markers to be
parsed and written to `Condition Marker.csv`.

### `src/generated/sensors_info.py`
Registers `Marker` (import, `SENSOR_CLASSES` entry, `marker` field on
`SensorGroupBase`). This routes `0x7777` records to the new parser.

### `src/versa/sensors/ads.py` (condition part)
- New `condition_id_list` decoded from `loff_stat_x` bit 2.
- `parse_file()` reads the appended lead-off bytes; it reads exactly
  `length - 1 - CHANNEL_BYTES` trailing bytes so it stays aligned for both old
  firmware (no lead-off bytes) and new firmware (2 bytes).
- `plot_graphics()` adds a `0/1` condition step-strip below the 8 channels,
  X-linked to the channels so the condition change lines up in time with the EEG.

### `src/versa/sensor.py` + `src/qt/utils/plot_dialog.py`
`Sensor.exact_x_range_links()` (default empty) plus plumbing in `PlotDialog` so a
follower plot receives the master's **numerical** X range directly. Native
pyqtgraph X-linking maps scene coordinates, which jitters when the follower (the
condition strip, spanning two columns) has a different pixel width.

### `src/qt/main_window.py`
An async `closeEvent` calls `ble_disconnect_all()` once on shutdown (guarded by
`_ble_cleanup_done`), avoiding a macOS/CoreBluetooth crash when a characteristic
callback is delivered after the event loop closes.

---

## Group B — Electrode lead-off

### `src/qt/lead_off/` (new directory)
- `headset_widget.py` — a head diagram colouring each electrode green/red/grey
  (connected / off / no-data), with the electrode labels CH1=Fp1 … CH8=O2, REF,
  BIAS.
- `lead_off_dialog.py` — polls the live ADS sensor (~200 ms) or shows a fixed
  snapshot from a pre-recording electrode check.
- (`loff_settings_dialog.py` is added in Group C.)

### `src/versa/ble.py` (lead-off check)
`ble_run_lead_off_check(address)` connects, subscribes to the command
characteristic, writes the check command, and awaits the 4-byte indication
`[0x10, statp, statn, rld]`. A shared `_command_exchange()` helper factors out the
connect → subscribe → write → await-indication skeleton reused by all the short
command exchanges.

### `src/qt/stream/stream_dialog.py` (buttons)
Two buttons next to start/stop: **"Lead-off status"** (live dialog) and
**"Check electrodes"** (`_run_electrode_check`).

---

## Group C — Runtime lead-off threshold

### `src/utils/constants.py`
`BLE_CMD_SET_LOFF_CFG = 0x11`, `BLE_CMD_GET_LOFF_CFG = 0x12`,
`LOFF_CFG_RESPONSE_LEN`, the status codes, `LOFF_THRESHOLDS` (8 steps 95%/5% …
70%/30%). The disambiguation rule is documented: replies are told apart by the
**(first byte, length)** pair, never either alone.

### `src/versa/ble.py` (threshold)
`LeadOffConfig` dataclass, `ble_get_loff_config()` / `ble_set_loff_config()`. The
reply always carries the values read back from the device (including on error),
so the returned config is authoritative.

### `src/qt/lead_off/loff_settings_dialog.py` (new)
A threshold combobox + "Apply" + "Read from device". On open it GETs the current
value from the device (never a remembered value) and shows the status text.

### Metadata pipeline (`typedefs.py`, `db.py`, `process.py`, `data_import_dialog.py`)
`Metadata` gains a **defaulted** `lead_off: dict | None` field (so old
`metadata.json` files still load). At recording start the stream dialog reads the
active config from the device and threads it through
`ParseConfig` → `create_import_folder` → `metadata.json` (`lead_off` block).

---

## Group D — On-demand check (Variant B) + readable CSV

### `src/utils/constants.py`
`BLE_CMD_LEAD_OFF_CHECK_LIVE = 0x13`, and the check-window marker command codes
(3 = start, 4 = end).

### `src/versa/ble.py` (live command channel)
During streaming, `ble_start_stream` now **also subscribes to the command
characteristic** (the device allows a single central, so a check mid-recording
must reuse the live connection). Its indication handler routes: the 4-byte
lead-off result to the caller, and the 13-byte `0x7777` markers into `raw_data`
so STREAM recordings capture the check-window markers. Two new optional
`BLEStreamConfig` callbacks (`client_ready_callback`, `command_result_callback`)
wire this up without changing the default behaviour.

### `src/qt/stream/stream_dialog.py` (live check)
"Check electrodes" now branches: **idle** → the accurate `0x10` check over its own
connection; **while streaming** → `_live_electrode_check()` sends `0x13` over the
live connection and awaits the result. A third button, **"Lead-off settings"**,
opens the threshold dialog.

### `src/versa/sensors/ads.py` (readable CSV columns + backward compatibility)
The cryptic raw lead-off bytes were replaced with decoded, human-readable
per-channel columns:
```
ch1_connected_list … ch8_connected_list,   (1 = connected, 0 = off / high-Z)
ref_connected_list, bias_connected_list,
condition_id_list
```
`parse_file()` decodes the lead-off bits into these; `latest_lead_off()` (the live
electrode dialog) is rebuilt from them. **Backward compatibility:** `from_csv_files`
was overridden so recordings made with the older `loff_statp_list` /
`loff_stat_x_list` columns still load — those raw bytes are decoded into the
current columns automatically.

> **Note on this build's meaning:** the per-channel `*_connected` columns read 1
> (connected) for every channel *except during a check window*, because the
> lead-off resistors are disconnected during normal recording (this is the
> firmware's Variant B behaviour). The real measurement appears only between a
> `command 3` and `command 4` marker.

### `src/versa/sensors/marker.py`
Plot tick labels extended to include the check-window codes (3 = start,
4 = end); Add-Samples import of a recording shows the window automatically.

---

## Companion tool — `marker_gui/` (new, standalone, not part of the app)

`marker_gui/` is a small set of standalone **tkinter** desktop tools that send the
experiment-condition commands to the board over its **USB CDC serial port**. This
is what flips the live 0/1 condition — the `loff_stat_x` bit-2 field that ends up
in every EEG sample and in the `condition_id_list` CSV column. The tools are
**never imported** by the PySide6 GUI and talk over **USB** while the main GUI uses
**BLE**, so both can run at the same time (USB drives the condition, BLE records
the EEG that carries the resulting `condition_id`).

**Requirements:** `pyserial` (tkinter ships with CPython). This is *not* a
dependency of the main GUI, so install it separately.

### `versa_marker_gui.py` — full marker tool (send **and** verify)
Three buttons — **Condition 0** (`0x00`), **Condition 1** (`0x01`), **USB Ping**
(`0x02`).

**What it sends:** exactly **one raw command byte** per click — `0x00`, `0x01`, or
`0x02`. There is no header or framing on the outgoing side; the whole command is a
single byte. `0x00`/`0x01` change the experiment condition; `0x02` is a ping
(marks a timestamp without changing the condition).

**How it sends it:** over the board's **USB CDC-ACM serial port** using `pyserial`.
On a button click it (1) records the host send time keyed by the command byte,
then (2) writes the byte and flushes:
```python
self.pending[code] = time.perf_counter()      # remember when it was sent
self.ser.write(bytes([code])); self.ser.flush()
```
The serial port is opened at 115200 baud, but USB CDC ignores the baud rate — the
byte is delivered as a USB packet regardless.

**What comes back / how it verifies:** a background reader thread reads the
firmware's echo, resynchronises on the `0x77 0x77` header, and unpacks the 13-byte
`0x7777` marker frame (`header, seconds, ms, len, command_sequence, command,
transition_sequence`). It matches the echo to the send by the **command** field,
computes `rtt = now − send_time`, and logs:
```
-> Condition 1 (0x01)
<- Condition 1 ack  dev_ts=12446 ms  seq=5  trans=3  rtt=1.234 ms
```
where `dev_ts` = `seconds*1000 + ms` (device timestamp, ms), `seq` =
command_sequence, `trans` = transition_sequence, `rtt` = host-measured USB
round-trip. This is the tool used to change the condition and confirm it reached
the device. Run with `python marker_gui/versa_marker_gui.py`.

### `usb_condition_sender.py` — minimal sender (send-only)
Two buttons — **Condition 0** / **Condition 1** — write the command byte and do
**not** parse the echo; a background thread just drains the incoming bytes so the
serial buffer never fills. No timestamp or latency display. Use it when you only
need to flip the condition and don't need the round-trip readout.

### `usb_ble_condition_test.py`
A non-interactive script (not a GUI) that drives condition commands and validates
the responses; useful for automated testing rather than day-to-day marking.

### Interface (both GUI tools)
- **Port** dropdown + **Refresh** — pick the board's USB CDC serial port
  (auto-selects a `usbmodem…` port when one is present).
- **Connect / Disconnect** — open/close the serial port (USB CDC ignores the baud
  rate; it is set only because pyserial requires a value).
- **Condition buttons** — send the corresponding command byte on click.
- **Log** area — one timestamped line per action: `-> …` for a sent command, and
  (in `versa_marker_gui.py`) `<- …` for the parsed echo with device timestamp and
  RTT.

### How it works
Each button writes exactly one byte over USB CDC-ACM. On the device, the USB RX
interrupt captures an acquisition-relative timestamp, builds a 13-byte `0x7777`
marker record (stored to SD and/or sent over BLE, and echoed back over USB), and —
for conditions 0/1 — flips the condition that every subsequent EEG sample carries.
`versa_marker_gui.py` parses that echo for the timestamp/latency readout;
`usb_condition_sender.py` discards it.

---

## Output format summary

- **`ADS1298.csv`:** `idx_list, time_list, ch1_list…ch8_list` (voltages),
  `ch1_connected_list…ch8_connected_list, ref_connected_list, bias_connected_list`
  (contact, 1 = connected), `condition_id_list`.
- **`Condition Marker.csv`:** `idx_list, time_list, command_list,
  transition_sequence_list` (command 0/1 = condition, 2 = ping, 3/4 = check
  window). Order by `time_list`, not `idx_list` (two independent sequence
  counters share the idx field).
- The two files align on the shared `time_list` (ms). Old recordings with the
  previous column layout still load.
