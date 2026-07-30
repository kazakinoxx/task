import BLEController
import os


python313_path = r"C:/Users/ikaze/AppData/Local/Programs/Python/Python313/python.exe"
project_root = r"C:/Users/ikaze/Documents/EEGproj/versasens-gui-main"
env = os.environ.copy()
env["OPUS_LIBRARY_PATH"] = r"C:/Users/ikaze/AppData/Local/Programs/Python/Python313"

ble_controller = BLEController.BLEController(
    python313_path=python313_path,
    project_root=project_root,
    opus_lib_path=env["OPUS_LIBRARY_PATH"]
)

ble_controller.start()
ble_controller._send_command("connect")
