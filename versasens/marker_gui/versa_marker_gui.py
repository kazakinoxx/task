#!/usr/bin/env python3
"""
VersaSens event-marker GUI.

A very small tkinter desktop app with three buttons - Condition 0, Condition 1,
USB Ping -
that each send a single command byte to the VersaSens board over its USB
CDC-ACM serial port:

    Condition 0 -> 0x00
    Condition 1 -> 0x01
    USB Ping    -> 0x02

The firmware captures an acquisition-relative timestamp the instant the byte's
RX interrupt fires, stores a 13-byte marker record (on the SD card and/or over
BLE) and echoes that same record back over USB. This GUI parses the echo to show
the device-side timestamp and the host-measured round-trip latency.

Echo / record frame (13 bytes, little-endian, matches the firmware's
condition_marker_frame):
    uint16 header = 0x7777
    uint32 seconds
    uint16 milliseconds
    uint8  len = 4
    uint8  command_sequence
    uint8  command            (0, 1, or 2)
    uint16 transition_sequence

The device timestamp is seconds * 1000 + milliseconds (ms resolution).

Requires: pyserial  (pip install pyserial). tkinter ships with CPython.
"""

import struct
import threading
import time
import tkinter as tk
from tkinter import ttk

import serial
import serial.tools.list_ports

HEADER = 0x7777
CMD = {"Condition 0": 0x00, "Condition 1": 0x01, "USB Ping": 0x02}
NAME = {v: k for k, v in CMD.items()}
# header, seconds, milliseconds, len, command_sequence, command, transition_sequence
FRAME_FMT = "<HIHBBBH"
FRAME_LEN = struct.calcsize(FRAME_FMT)   # 13 bytes


class MarkerGUI:
    def __init__(self, root):
        self.root = root
        self.ser = None
        self.reader = None
        self.reader_stop = threading.Event()
        self.pending = {}        # command byte -> host send time (perf_counter)
        self.pending_lock = threading.Lock()

        root.title("VersaSens Marker")
        root.resizable(False, False)

        # --- connection row ---
        conn = ttk.Frame(root, padding=10)
        conn.grid(row=0, column=0, sticky="ew")

        ttk.Label(conn, text="Port:").grid(row=0, column=0, padx=(0, 4))
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(conn, textvariable=self.port_var,
                                     width=28, state="readonly")
        self.port_box.grid(row=0, column=1, padx=4)

        ttk.Button(conn, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=4)
        self.connect_btn = ttk.Button(conn, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=4)

        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(conn, textvariable=self.status_var, foreground="#888").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

        # --- buttons ---
        btns = ttk.Frame(root, padding=10)
        btns.grid(row=1, column=0)
        big = ("Segoe UI", 16, "bold")
        for i, name in enumerate(("Condition 0", "Condition 1", "USB Ping")):
            b = tk.Button(btns, text=name, width=10, height=2, font=big,
                          command=lambda n=name: self.send(n))
            b.grid(row=0, column=i, padx=8, pady=4)

        # --- log ---
        logf = ttk.Frame(root, padding=(10, 0, 10, 10))
        logf.grid(row=2, column=0, sticky="nsew")
        self.log = tk.Text(logf, width=64, height=14, state="disabled",
                           font=("Consolas", 9))
        self.log.grid(row=0, column=0)
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log["yscrollcommand"] = sb.set

        self.refresh_ports()

    # ----- logging -----
    def log_line(self, text):
        self.log["state"] = "normal"
        self.log.insert("end", time.strftime("%H:%M:%S ") + text + "\n")
        self.log.see("end")
        self.log["state"] = "disabled"

    # ----- ports / connection -----
    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        values = [f"{p.device} - {p.description}" for p in ports]
        self.port_box["values"] = values
        if values and not self.port_var.get():
            self.port_box.current(0)

    def toggle_connection(self):
        if self.ser is None:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        sel = self.port_var.get()
        if not sel:
            self.log_line("No port selected.")
            return
        dev = sel.split(" - ")[0]
        try:
            # CDC-ACM ignores baud rate; timeout keeps the reader responsive.
            self.ser = serial.Serial(dev, 115200, timeout=0.1)
        except serial.SerialException as e:
            self.log_line(f"Open failed: {e}")
            self.ser = None
            return

        self.reader_stop.clear()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

        self.connect_btn["text"] = "Disconnect"
        self.status_var.set(f"Connected to {dev}")
        self.log_line(f"Connected to {dev}")

    def disconnect(self):
        self.reader_stop.set()
        if self.reader:
            self.reader.join(timeout=1.0)
            self.reader = None
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        self.connect_btn["text"] = "Connect"
        self.status_var.set("Disconnected")
        self.log_line("Disconnected")

    # ----- send / receive -----
    def send(self, name):
        if self.ser is None:
            self.log_line("Not connected.")
            return
        code = CMD[name]
        with self.pending_lock:
            self.pending[code] = time.perf_counter()
        try:
            self.ser.write(bytes([code]))
            self.ser.flush()
        except serial.SerialException as e:
            self.log_line(f"Write failed: {e}")
            self.disconnect()
            return
        self.log_line(f"-> {name} (0x{code:02x})")

    def _read_loop(self):
        buf = bytearray()
        while not self.reader_stop.is_set():
            try:
                # Read one frame's worth at a time; with timeout=0.1 this keeps
                # the reader responsive without adding artificial RTT.
                chunk = self.ser.read(FRAME_LEN)
            except Exception:
                break
            if not chunk:
                continue
            buf.extend(chunk)
            # Resync to header and parse complete frames.
            while len(buf) >= FRAME_LEN:
                if buf[0] != 0x77 or buf[1] != 0x77:
                    buf.pop(0)
                    continue
                (_header, seconds, ms, _len, cmd_seq, cmd,
                 trans_seq) = struct.unpack(FRAME_FMT, buf[:FRAME_LEN])
                del buf[:FRAME_LEN]
                device_ms = seconds * 1000 + ms
                self._handle_ack(device_ms, cmd, cmd_seq, trans_seq)

    def _handle_ack(self, device_ms, cmd, cmd_seq, trans_seq):
        now = time.perf_counter()
        with self.pending_lock:
            t0 = self.pending.pop(cmd, None)
        name = NAME.get(cmd, f"0x{cmd:02x}")
        detail = f"dev_ts={device_ms} ms  seq={cmd_seq}  trans={trans_seq}"
        if t0 is not None:
            rtt_ms = (now - t0) * 1000.0
            line = f"<- {name} ack  {detail}  rtt={rtt_ms:.3f} ms"
        else:
            line = f"<- {name} ack  {detail}"
        # marshal back onto the Tk thread
        self.root.after(0, self.log_line, line)


def main():
    root = tk.Tk()
    app = MarkerGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.disconnect(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
