import subprocess
import json
import threading
import queue
import os
import time
import sys
import serial  # <-- ensure pyserial is installed
import serial.tools.list_ports
from typing import Optional, Dict, Any

class BLEController:
    def __init__(self, python313_path: str, project_root: str, opus_lib_path: str):
        self.python313_path = python313_path
        self.project_root = project_root
        self.env = os.environ.copy()
        self.env["OPUS_LIBRARY_PATH"] = opus_lib_path
        self.env["PYTHONUNBUFFERED"] = "1"
        self.proc: Optional[subprocess.Popen] = None
        self._response_queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._started = False
        # Tracks whether an EEG recording is currently in progress, so close()
        # can stop (and thereby save) it if the experiment ends before the
        # normal stop_recording() call (e.g. a crash or the window being closed).
        self._recording = False

        # ---- Serial marker port ----
        self.marker_ser: Optional[serial.Serial] = None
        self.marker_port: Optional[str] = None

    # ---------- BLE worker methods ----------
    def start(self) -> None:
        """Launch the BLE worker subprocess and start the reader thread."""
        if self._started:
            return
        self.proc = subprocess.Popen(
            [self.python313_path, "-m", "src.connect"],
            cwd=self.project_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=self.env,
        )

        def stderr_reader():
            for line in iter(self.proc.stderr.readline, ''):
                sys.stderr.write(f"[BLE worker] {line}")
                sys.stderr.flush()

        threading.Thread(target=stderr_reader, daemon=True).start()
        time.sleep(1)  # give worker time to start
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        self._started = True

    def _reader_loop(self) -> None:
        if self.proc is None:
            return
        for line in self.proc.stdout:
            try:
                resp = json.loads(line.strip())
                self._response_queue.put(resp)
            except json.JSONDecodeError:
                pass

    def _send_command(self, action: str, timeout: float = 15.0, **kwargs) -> Dict[str, Any]:
        if not self._started:
            raise RuntimeError("BLE controller not started. Call start() first.")
        cmd = {"action": action, **kwargs}
        with self._lock:
            self.proc.stdin.write(json.dumps(cmd) + "\n")
            self.proc.stdin.flush()
        try:
            resp = self._response_queue.get(timeout=timeout)
            return resp
        except queue.Empty:
            raise TimeoutError(f"No response from BLE worker for command '{action}'")

    def connect(self, timeout: float = 15.0) -> Dict[str, Any]:
        return self._send_command("connect", timeout=timeout)

    def disconnect(self, timeout: float = 60.0) -> Dict[str, Any]:
        # Disconnect triggers the raw->CSV import on the worker, which runs
        # synchronously before responding, so allow a generous timeout for the
        # parse of large recordings.
        resp = self._send_command("disconnect", timeout=timeout)
        self._recording = False
        return resp

    def start_recording(self, timeout: float = 5.0) -> Dict[str, Any]:
        print("Starting BLE recording...")
        resp = self._send_command("start_record", timeout=timeout)
        self._recording = True
        return resp

    def stop_recording(self, timeout: float = 5.0) -> Dict[str, Any]:
        resp = self._send_command("stop_record", timeout=timeout)
        self._recording = False
        return resp

    def lead_off_check(self, timeout: float = 5.0) -> Dict[str, Any]:
        print("Performing lead-off check...")
        return self._send_command("lead_off_check", timeout=timeout)

    def set_subject(self, subject_id: str, notes: str = "", timeout: float = 5.0) -> dict:
        return self._send_command("set_subject", timeout=timeout, subject_id=subject_id, notes=notes)

    def close(self) -> None:
        """Terminate the BLE worker and close the marker serial port.

        If a recording is still in progress -- i.e. the experiment ended before
        final_calibration ran its stop/disconnect, as happens on a crash or when
        the window is closed early -- disconnect first so the worker flushes the
        recording to disk AND runs the raw->CSV import, instead of losing it all
        when the process is terminated. (stop_record alone only flips a flag; the
        save + CSV export happen on disconnect.) Best-effort: cleanup must never
        raise.
        """
        if self._started and self._recording and self.proc and self.proc.poll() is None:
            try:
                self.disconnect()   # stop_stream saves the binary + imports -> CSV
            except Exception:
                sys.stderr.write("[BLEController] Failed to save recording on shutdown\n")
                sys.stderr.flush()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait()
        self._started = False
        self.close_marker_port()   # ensure marker port is closed

    # ---------- Serial marker methods ----------
    def find_marker_port(self) -> Optional[str]:
        """
        Find the first USB serial port that matches a VersaSens marker device.
        Returns the device path (e.g., 'COM3') or None if not found.
        """
        for port in serial.tools.list_ports.comports():
            # Look for typical CDC-ACM description or vendor-specific string
            desc = port.description.lower()
            print(f"Checking port {port.device}: {desc}")
            if "cdc-acm" in desc or "versasens" in desc:
                return port.device
        return None

    def open_marker_port(self, port: Optional[str] = None, baudrate: int = 115200) -> None:
        """
        Open the marker serial port. If port is None, try to auto‑detect.
        """
        if port is None:
            port = self.find_marker_port()
            if port is None:
                raise RuntimeError("No marker port found automatically. Please specify a port.")
        if self.marker_ser is not None and self.marker_ser.is_open:
            if self.marker_port == port:
                return  # already open
            else:
                self.close_marker_port()
        try:
            self.marker_ser = serial.Serial(port, baudrate, timeout=0.1)
            self.marker_port = port
            time.sleep(2)  # let the device settle
            print(f"Marker port opened on {port}")
        except serial.SerialException as e:
            raise RuntimeError(f"Failed to open marker port {port}: {e}")
    

    def close_marker_port(self) -> None:
        """Close the marker serial port if open."""
        if self.marker_ser is not None and self.marker_ser.is_open:
            self.marker_ser.close()
            print("Marker port closed")
        self.marker_ser = None
        self.marker_port = None

    def send_marker(self, condition: int) -> None:
        """
        Send a single‑byte marker to the VersaSens device over USB serial.
        :param condition: 0 for Condition 0, 1 for Condition 1
        """
        if condition not in (0, 1):
            raise ValueError("condition must be 0 or 1")
        if self.marker_ser is None or not self.marker_ser.is_open:
            raise RuntimeError("Marker port not open. Call open_marker_port() first.")
        try:
            self.marker_ser.write(bytes([0x00 if condition == 0 else 0x01]))
            self.marker_ser.flush()
        except serial.SerialException as e:
            raise RuntimeError(f"Marker send failed: {e}")

    def send_start(self) -> None:
        # condition must be 1 (for start) or 2 (for stop) – but you want only 1? Then it's the same.
        print("starting marker")
        self.marker_ser.write(bytes([0x01]))
        self.marker_ser.flush()
        time.sleep(10 / 1000.0)
        self.marker_ser.write(bytes([0x00]))   # send 0
        self.marker_ser.flush()

    def send_stop(self) -> None:
        # condition must be 1 (for start) or 2 (for stop) – but you want only 1? Then it's the same.
        print("stopping marker")
        self.marker_ser.write(bytes([0x01]))
        self.marker_ser.flush()
        time.sleep(50 / 1000.0)
        self.marker_ser.write(bytes([0x00]))   # send 0
        self.marker_ser.flush()