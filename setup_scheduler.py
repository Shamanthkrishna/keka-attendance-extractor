"""
setup_scheduler.py
------------------
One-time setup script.

What it does:
  1. Drops KekaServerAutoStart.bat into the Windows Startup folder
     → server.py starts at every user login (no admin rights needed).
  2. Creates Task Scheduler task "KekaServerOnWake"
     → restarts server.py automatically when the PC wakes from sleep.

The Chrome extension (background.js) handles daily token extraction at 18:30.
No extra Task Scheduler jobs or special Chrome flags are required.

Run once:
    python setup_scheduler.py

To undo everything:
    python setup_scheduler.py --remove
"""

import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
PYTHON_EXE = sys.executable
SERVER_SCRIPT = BASE_DIR / "server.py"
SERVER_BAT = BASE_DIR / "start_server.bat"

TASK_WAKE = "KekaServerOnWake"


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
    startup_folder = (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )
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
        print(f"  The server will start automatically at every login.")
    except Exception as e:
        print(f"  ERROR: {e}")


def create_server_wake_task() -> None:
    """
    Create a Task Scheduler task that restarts the Flask server whenever
    the PC wakes from sleep (System event log, Power-Troubleshooter, Event ID 1).
    No admin rights required — task runs as the current user.
    """
    # XPath filter: System event log, Microsoft-Windows-Power-Troubleshooter, EventID 1 = wake
    event_query = (
        r"*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]"
    )
    # The task action: run start_server.bat (kills stale instance, then starts fresh)
    action = f'"{SERVER_BAT}"'

    print(f"Creating task '{TASK_WAKE}' (restart server on wake from sleep)...")
    cmd = [
        "schtasks", "/Create", "/F",
        "/TN", TASK_WAKE,
        "/TR", action,
        "/SC", "ONEVENT",
        "/EC", "System",
        "/MO", event_query,
    ]
    result = run(cmd, check=False)
    if result.returncode == 0:
        print(f"  Task '{TASK_WAKE}' created successfully.")
    else:
        print(f"  ERROR creating '{TASK_WAKE}':\n  {result.stderr.strip()}")
        print(f"  You can add it manually in taskschd.msc: trigger = On event, System log,")
        print(f"  Provider: Microsoft-Windows-Power-Troubleshooter, Event ID: 1")


def main() -> None:
    if "--remove" in sys.argv:
        print("Removing Keka Attendance Extractor automation...")
        startup_folder = (
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        )
        for fname in ("KekaServerAutoStart.bat", "KekaChrome.bat"):
            p = startup_folder / fname
            if p.exists():
                p.unlink()
                print(f"  Removed: {p}")
            else:
                print(f"  {fname} not found in Startup folder (skipping).")
        delete_task(TASK_WAKE)
        # Also clean up old tasks if they exist from previous setup
        delete_task("KekaAttendanceDaily")
        return

    print("Setting up Keka Attendance Extractor automation")
    print(f"  Python   : {PYTHON_EXE}")
    print(f"  Server   : {SERVER_SCRIPT}")
    print()

    create_server_startup_shortcut()
    print()
    create_server_wake_task()

    print()
    print("Done!")
    print()
    print("Next steps:")
    print("  1. Double-click start_server.bat to start the server right now.")
    print("  2. In Chrome, go to chrome://extensions/ and load the ChromeExtension/ folder.")
    print("  3. Open hrmstismo.keka.com and log in.")
    print("  4. Click the extension icon to test — or wait for the 18:30 automatic trigger.")
    print()
    print("To undo: python setup_scheduler.py --remove")


if __name__ == "__main__":
    main()
