import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path
from typing import Union


def run_command(args: list[str]) -> None:
    command: Union[str, list[str]] = (
        args
        if "win" in sys.platform and "darwin" not in sys.platform
        else " ".join(args)
    )
    pros = subprocess.Popen(
        command,
        cwd=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=True,
    )
    _, stderr = pros.communicate()
    if (
        stderr
        and not stderr.startswith("warning")
        and "DeprecationWarning" not in stderr
    ):
        print(stderr)
        sys.exit(1)


def update_ts_file(project_folder: str, ts_folder: str, locale: str) -> None:
    py_files = list(glob.glob(f"{project_folder}/**/*.py", recursive=True))
    ui_files = list(glob.glob(f"{project_folder}/**/*.ui", recursive=True))
    files = py_files + ui_files

    ts_file = os.path.join(ts_folder, f"{locale}.ts")

    if "win" in sys.platform and "darwin" not in sys.platform:
        args = [
            ".venv\\Scripts\\python.exe",
            "-m",
            "PyQt5.pylupdate_main",
            "-noobsolete",
            *files,
            "-ts",
            ts_file,
        ]

        try:
            # Use temporary bat-file to by-pass "command line too long"
            # error in subprocess.Popen
            file_path = str(Path(__file__).parent / "temp-update-translations.bat")
            with open(file_path, "w") as temporary_file:
                temporary_file.write(" ".join(args))
                print("Updating ts-file...")
                run_command([file_path])
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
            print("Update complete")

    else:
        args = ["pylupdate5", "-noobsolete", *files, "-ts", ts_file]
        run_command(args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "project_folder",
        type=str,
        help="folder to search for py and ui files to translate",
    )
    parser.add_argument("ts_folder", type=str, help="output folder for ts files")
    parser.add_argument(
        "lang_codes", type=str, help="language codes to update, separated by comma"
    )

    args = parser.parse_args()
    lang_codes = args.lang_codes.split(",")

    for locale in lang_codes:
        update_ts_file(args.project_folder, args.ts_folder, locale)

    sys.exit(0)
