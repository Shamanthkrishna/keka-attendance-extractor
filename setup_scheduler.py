"""
setup_scheduler.py
------------------
One-time setup script that registers two Windows Task Scheduler tasks:

  1. "KekaServerAutoStart"  — starts server.py at every user login (background).
  2. "KekaAttendanceDaily"  — runs auto_extract.py every weekday at 6:30 PM.

Run once as a normal user (no admin rights needed for user-scoped tasks):
    python setup_scheduler.py

To remove the tasks later:
    python setup_scheduler.py --remove
"""

import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
PYTHON_EXE = sys.executable          # the Python that is running this script
SERVER_SCRIPT = BASE_DIR / "server.py"
EXTRACT_SCRIPT = BASE_DIR / "auto_extract.py"

TASK_SERVER = "KekaServerAutoStart"
TASK_EXTRACT = "KekaAttendanceDaily"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def delete_task(name: str) -> None:
    result = run(["schtasks", "/Delete", "/TN", name, "/F"], check=False)
    if result.returncode == 0:
        print(f"  Removed task: {name}")
    else:
        print(f"  Task '{name}' did not exist (or could not be removed).")


def create_server_startup_shortcut() -> None:
    """
    Drop a .bat file into the user's Startup folder so the server starts
    at every login — no admin rights required.
    """
    import shutil

    startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_bat = startup_folder / "KekaServerAutoStart.bat"

    bat_content = (
        f'@echo off\n'
        f'cd /d "{BASE_DIR}"\n'
        f'for /f "tokens=5" %%a in (\'netstat -aon ^| findstr ":5000 "\') do taskkill /F /PID %%a >nul 2>&1\n'
        f'start "" /min "{PYTHON_EXE}" "{SERVER_SCRIPT}"\n'
    )

    print(f"Adding server auto-start to Startup folder: {startup_bat}")
    try:
        startup_bat.write_text(bat_content, encoding="utf-8")
        print(f"  Created: {startup_bat}")
        print(f"  The server will start automatically at your next login.")
    except Exception as e:
        print(f"  ERROR: {e}")


def create_extract_task(hour: int = 18, minute: int = 30) -> None:
    """Run auto_extract.py every weekday at the given time (default 18:30)."""
    time_str = f"{hour:02d}:{minute:02d}"
    print(f"Creating task '{TASK_EXTRACT}' (daily extraction at {time_str} Mon-Fri)...")

    # schtasks /SC WEEKLY with /D MON,TUE,WED,THU,FRI
    cmd = [
        "schtasks", "/Create", "/F",
        "/TN", TASK_EXTRACT,
        "/TR", f'"{PYTHON_EXE}" "{EXTRACT_SCRIPT}"',
        "/SC", "WEEKLY",
        "/D", "MON,TUE,WED,THU,FRI",
        "/ST", time_str,
    ]
    result = run(cmd, check=False)
    if result.returncode == 0:
        print(f"  Task '{TASK_EXTRACT}' created successfully.")
    else:
        print(f"  ERROR creating '{TASK_EXTRACT}':\n  {result.stderr.strip()}")


def main() -> None:
    if "--remove" in sys.argv:
        print("Removing scheduled tasks...")
        # Remove Startup folder shortcut
        startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        startup_bat = startup_folder / "KekaServerAutoStart.bat"
        if startup_bat.exists():
            startup_bat.unlink()
            print(f"  Removed: {startup_bat}")
        else:
            print(f"  Startup shortcut did not exist.")
        delete_task(TASK_EXTRACT)
        return

    print("Setting up Windows Task Scheduler tasks for Keka Attendance Extractor")
    print(f"  Python: {PYTHON_EXE}")
    print(f"  Server script: {SERVER_SCRIPT}")
    print(f"  Extractor script: {EXTRACT_SCRIPT}")
    print()

    create_server_startup_shortcut()
    create_extract_task()

    print()
    print("Done. You can verify tasks in Task Scheduler (taskschd.msc).")
    print("To run the extractor manually at any time:")
    print(f'  python "{EXTRACT_SCRIPT}"')


if __name__ == "__main__":
    main()
