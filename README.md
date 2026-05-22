# Keka Attendance Extractor

Automatically extracts your daily attendance data from the Keka HRMS portal and saves it as a formatted CSV report — no new browser window, no login required after first setup.

---

# Keka Attendance Extractor

Automatically extracts your daily attendance data from the Keka HRMS portal and saves it as a formatted CSV report — no new browser window, no login required after first setup.

---

## How It Works

### Primary path — Chrome Extension Alarm (recommended)

```
Chrome Extension (background.js)
    │  chrome.alarms fires every weekday at 18:30
    │
    ├─ Find open Keka tab (you are already logged in)
    ├─ Inject content.js → read access_token from localStorage
    ├─ POST token to Flask server on localhost:5000
    └─ Flask server → main.py → attendance_data.csv + transformed_data.csv
```

The extension self-schedules — no Task Scheduler needed. The Flask server must be running (starts automatically at login via Windows Startup).

### Secondary / manual path — CDP script

```
python auto_extract.py
    │
    ├─ [Token cache valid?]  →  done instantly, no browser needed
    └─ [Token expired?]  →  connect to Chrome via --remote-debugging-port=9222
                              read token from open Keka tab → cache → pipeline
```

Requires Chrome to be launched via `start_chrome.bat`.



## Project Structure

```
├── auto_extract.py          # Main automation script (CDP-based, no new window)
├── main.py                  # Core pipeline: fetch → parse → save → transform
├── server.py                # Flask server (for legacy Chrome extension)
├── setup_scheduler.py       # One-time setup: Startup folder + Task Scheduler
├── start_server.bat         # Starts Flask server (placed in Windows Startup)
├── start_chrome.bat         # Launches Chrome with --remote-debugging-port=9222 (placed in Windows Startup)
│
├── ChromeExtension/         # Legacy Chrome extension (manual trigger, still works)
│   ├── manifest.json
│   ├── background.js
│   └── content.js
│
├── Extracted/
│   └── attendance_data.csv  # Raw attendance records (cumulative)
│
├── Report/
│   └── transformed_data.csv # Formatted report with working hours (auto-opens)
│
└── Logs/
    └── attendance_log_YYYY-MM-DD.txt  # Daily rotating logs
```

---

## Prerequisites

- **Python 3.10+** (project uses 3.14)
- **Google Chrome** installed
- Chrome must be running with `--remote-debugging-port=9222` — `start_chrome.bat` handles this automatically

---

## First-Time Setup

### 1. Install dependencies

```powershell
pip install flask flask-cors waitress pandas requests playwright
playwright install chromium
```

### 2. Register the Flask server auto-start (no admin rights needed)

```powershell
python setup_scheduler.py
```

This places `KekaServerAutoStart.bat` in your Windows **Startup folder** so the Flask server starts at every login.

### 3. Start the Flask server now (for the current session)

Double-click `start_server.bat` (or run `python server.py`). It must be running for the extension to work.

### 4. Load the Chrome extension

1. Go to `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `ChromeExtension/` folder
4. The extension is now active — it schedules itself automatically for 18:30 daily

### 5. Open Keka and log in

Go to `https://hrmstismo.keka.com` in Chrome and log in via GAuth as normal. Keep this tab open — the extension will find it at 18:30.

### 6. Test immediately

Click the extension icon while on the Keka page to trigger an extraction on demand. Check `Report/transformed_data.csv` for the result.



## Daily Usage (after setup)

Nothing. The Chrome extension fires automatically every weekday at 18:30 and:

1. Finds your open Keka tab
2. Reads the Bearer token from localStorage
3. POSTs it to the Flask server
4. The server runs the extraction pipeline

**Requirements at 18:30:**
- Chrome must be open with a Keka tab (you're already logged in to use Keka anyway)
- Flask server must be running (auto-starts at login via Windows Startup)

---

## Manual Extraction (anytime)

**Via extension button:** Click the extension icon while on the Keka page.

**Via CLI (requires Chrome with --remote-debugging-port=9222):**
```powershell
python auto_extract.py
```

---

## Legacy: Chrome Extension Manual Trigger

The extension icon always works as a manual trigger. Click it while on `hrmstismo.keka.com` to extract immediately without waiting for the 18:30 alarm.



## Removing the Automation

```powershell
python setup_scheduler.py --remove
```

This deletes the Startup folder shortcut and the Task Scheduler job.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Extension doesn't trigger at 18:30 | Make sure the extension is loaded in Chrome and Chrome is open with a Keka tab |
| `No Keka tab was found` notification | Open `hrmstismo.keka.com` in Chrome and log in — the extension will retry next trigger |
| `Token not found in localStorage` | Refresh the Keka tab (session may have expired) and click the extension icon to retry |
| `Address already in use` on port 5000 | `start_server.bat` kills stale instances automatically — double-click it to restart |
| `Cannot reach Chrome on localhost:9222` | Only relevant for `auto_extract.py` CLI path. Close Chrome, run `start_chrome.bat`, open Keka, retry |
| Report not updating | Check `Logs/attendance_log_YYYY-MM-DD.txt` for error details |

---

## Configuration

To change the daily trigger time, edit these constants at the top of `ChromeExtension/background.js`:

```js
const TRIGGER_HOUR = 18;    // 18 = 6 PM
const TRIGGER_MINUTE = 30;
```

After editing, go to `chrome://extensions/`, click the refresh icon on the extension, then reload a Keka tab to re-register the alarm.

For the CDP fallback (`auto_extract.py`), edit these constants in that file:

| Constant | Default | Description |
|---|---|---|
| `KEKA_URL` | `https://hrmstismo.keka.com` | Your organisation's Keka URL |
| `TOKEN_STORAGE_KEY` | `access_token` | localStorage key for the Bearer token |
| `CDP_URL` | `http://localhost:9222` | CDP endpoint for the running Chrome instance |

