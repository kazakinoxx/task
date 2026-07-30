import subprocess
import json
import time
import os
import threading
import queue  

python313_path = r"C:/Users/ikaze/AppData/Local/Programs/Python/Python313/python.exe"
project_root = r"C:/Users/ikaze/Documents/EEGproj/versasens-gui-main"

# Optionally set the opus library path
env = os.environ.copy()
env["OPUS_LIBRARY_PATH"] = r"C:/Users/ikaze/AppData/Local/Programs/Python/Python313"


def _send_ble_command(action, **kwargs):
    cmd = {"action": action, **kwargs}
    proc.stdin.write(json.dumps(cmd) + "\n")
    proc.stdin.flush()

    q = queue.Queue()

    def read_stdout():
        try:
            line = proc.stdout.readline()
            q.put(line)
        except Exception:
            q.put(None)

    t = threading.Thread(target=read_stdout)
    t.daemon = True
    t.start()
    t.join(timeout=10000)         

    if t.is_alive():
        raise RuntimeError("Timeout: worker did not respond")
    response_line = q.get()
    if response_line is None:
        stderr_data = proc.stderr.read()
        raise RuntimeError(f"Worker produced no output. stderr: {stderr_data}")
    return json.loads(response_line)

def connect_device():
    proc = subprocess.Popen(
        [python313_path, "-m", "src.connect"],
        cwd=project_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env
        )

    time.sleep(1)  # give worker time to start

    try:
        result = send_ble_command("connect")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        proc.terminate()