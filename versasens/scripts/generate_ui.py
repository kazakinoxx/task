"""Uses pyside6-uic to generate files from Qt XML file."""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_FOLDER = ROOT / "ui"
GENERATED_FOLDER = ROOT / "src" / "generated" / "ui"


def collect_ui_files(root: Path) -> list[Path]:
    """Recursively collect all UI files under the given root directory."""
    return [p for p in root.rglob("*.ui") if p.is_file()]


def convert_ui_file(ui_file: Path) -> str:
    """Convert a single .ui file to .py using pyside6-uic."""
    new_path = GENERATED_FOLDER / ui_file.relative_to(UI_FOLDER)
    new_path = new_path.with_suffix(".py")
    new_path.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(  # noqa: S602
        ["uv", "run", "pyside6-uic", "-o", str(new_path), str(ui_file)],  # noqa: S607
        shell=True,
        check=True,
    )
    return " ".join(proc.args)


def main() -> None:  # noqa: D103
    ui_files = collect_ui_files(UI_FOLDER)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(convert_ui_file, f): f for f in ui_files}

        for future in as_completed(futures):
            res = future.result()
            print(res)  # noqa: T201


if __name__ == "__main__":
    main()
