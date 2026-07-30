
import subprocess
import json
import threading
import queue
import os
import time
import sys
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

    def start(self) -> None:
        """Launch the worker subprocess and start the reader thread."""
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
        # Give worker time to start
        time.sleep(1)
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        self._started = True

    def _reader_loop(self) -> None:
        """Read stdout lines from the worker and put them into the queue."""
        if self.proc is None:
            return
        for line in self.proc.stdout:
            try:
                resp = json.loads(line.strip())
                self._response_queue.put(resp)
            except json.JSONDecodeError:
                # Optionally log
                pass

    def _send_command(self, action: str, timeout: float = 15.0, **kwargs) -> Dict[str, Any]:
        """Send a JSON command to the worker and wait for a response."""
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

    def disconnect(self, timeout: float = 10.0) -> Dict[str, Any]:
        return self._send_command("disconnect", timeout=timeout)

    def start_recording(self, timeout: float = 5.0) -> Dict[str, Any]:
        print("Starting BLE recording...")
        return self._send_command("start_record", timeout=timeout)

    def stop_recording(self, timeout: float = 5.0) -> Dict[str, Any]:
        return self._send_command("stop_record", timeout=timeout)

    def close(self) -> None:
        """Terminate the worker process."""
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait()
        self._started = False