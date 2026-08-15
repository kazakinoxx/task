#!/usr/bin/env python3
"""USB-only VersaSens condition sender.

This utility sends one-byte condition commands over the USB CDC serial port:

    Condition 0 -> 0x00
    Condition 1 -> 0x01

It does not scan for or connect to BLE, and it does not wait for an ACK before
allowing another command. Firmware responses are drained quietly in a
background thread so the serial receive buffer cannot fill during a long run.

Requires pyserial. Tkinter is included with most Python distributions.
"""

import threading
import time
import tkinter as tk
from tkinter import ttk

import serial
import serial.tools.list_ports


COMMANDS = {
    "Condition 0": 0x00,
    "Condition 1": 0x01,
}


class USBConditionSender:
    def __init__(self, root):
        self.root = root
        self.serial_port = None
        self.reader_thread = None
        self.reader_stop = threading.Event()

        root.title("VersaSens USB Condition Sender")
        root.resizable(False, False)

        connection = ttk.Frame(root, padding=10)
        connection.grid(row=0, column=0, sticky="ew")

        ttk.Label(connection, text="Port:").grid(row=0, column=0, padx=(0, 4))
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(
            connection,
            textvariable=self.port_var,
            width=34,
            state="readonly",
        )
        self.port_box.grid(row=0, column=1, padx=4)

        ttk.Button(connection, text="Refresh", command=self.refresh_ports).grid(
            row=0, column=2, padx=4
        )
        self.connect_button = ttk.Button(
            connection, text="Connect", command=self.toggle_connection
        )
        self.connect_button.grid(row=0, column=3, padx=4)

        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(connection, textvariable=self.status_var).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )

        buttons = ttk.Frame(root, padding=10)
        buttons.grid(row=1, column=0)
        button_font = ("Segoe UI", 16, "bold")

        for column, name in enumerate(("Condition 0", "Condition 1")):
            button = tk.Button(
                buttons,
                text=name,
                width=14,
                height=3,
                font=button_font,
                command=lambda selected=name: self.send(selected),
            )
            button.grid(row=0, column=column, padx=10, pady=4)

        log_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        log_frame.grid(row=2, column=0, sticky="nsew")
        self.log = tk.Text(
            log_frame,
            width=62,
            height=12,
            state="disabled",
            font=("Consolas", 10),
        )
        self.log.grid(row=0, column=0)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log["yscrollcommand"] = scrollbar.set

        self.refresh_ports()

    def log_line(self, message):
        self.log["state"] = "normal"
        self.log.insert("end", time.strftime("%H:%M:%S ") + message + "\n")
        self.log.see("end")
        self.log["state"] = "disabled"

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        values = [f"{port.device} - {port.description}" for port in ports]
        previous_device = self.port_var.get().split(" - ")[0]

        self.port_box["values"] = values
        for index, value in enumerate(values):
            if value.split(" - ")[0] == previous_device:
                self.port_box.current(index)
                break
        else:
            if values:
                preferred = next(
                    (
                        index
                        for index, value in enumerate(values)
                        if "usbmodem" in value.lower()
                    ),
                    0,
                )
                self.port_box.current(preferred)
            else:
                self.port_var.set("")

    def toggle_connection(self):
        if self.serial_port is None:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        selection = self.port_var.get()
        if not selection:
            self.log_line("No serial port selected.")
            return

        device = selection.split(" - ")[0]
        try:
            # The baud rate is ignored by USB CDC-ACM, but pyserial requires it.
            self.serial_port = serial.Serial(device, 115200, timeout=0.1)
            self.serial_port.reset_input_buffer()
        except serial.SerialException as error:
            self.serial_port = None
            self.log_line(f"Open failed: {error}")
            return

        self.reader_stop.clear()
        self.reader_thread = threading.Thread(
            target=self._drain_responses,
            name="usb-response-drain",
            daemon=True,
        )
        self.reader_thread.start()

        self.connect_button["text"] = "Disconnect"
        self.status_var.set(f"Connected to {device} (USB only)")
        self.log_line(f"Connected to {device}; BLE is not used")

    def disconnect(self):
        self.reader_stop.set()
        if self.reader_thread is not None:
            self.reader_thread.join(timeout=0.5)
            self.reader_thread = None

        if self.serial_port is not None:
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None

        self.connect_button["text"] = "Connect"
        self.status_var.set("Disconnected")

    def send(self, name):
        if self.serial_port is None:
            self.log_line("Not connected.")
            return

        command = COMMANDS[name]
        try:
            self.serial_port.write(bytes([command]))
            self.serial_port.flush()
        except (serial.SerialException, OSError) as error:
            self.log_line(f"Write failed: {error}")
            self.disconnect()
            return

        self.log_line(f"-> {name} (0x{command:02x})")

    def _drain_responses(self):
        """Discard firmware ACK bytes without parsing or waiting for them."""
        while not self.reader_stop.is_set():
            port = self.serial_port
            if port is None:
                return
            try:
                port.read(port.in_waiting or 1)
            except (serial.SerialException, OSError):
                return

    def close(self):
        self.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = USBConditionSender(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
