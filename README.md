# Keka Attendance Extractor

Automatically extracts your daily attendance data from the Keka HRMS portal and saves it as a formatted CSV report — no manual token copying or browser extension clicks required.

---

## How It Works

```
Windows Startup  →  server.py  (Flask server on port 5000, always running)

Task Scheduler   →  auto_extract.py  (runs every weekday at 6:30 PM)
                        │
                        ├─ [Token cache valid?]  →  skip browser, use cached token
                        │
                        └─ [Token expired?]
                                │
                                ├─ Launch Chrome silently using your saved profile
                                ├─ GAuth session still active → already logged in
                                ├─ Extract access_token from localStorage
                                ├─ Cache token with JWT expiry
                                └─ Run pipeline → Extracted/attendance_data.csv
                                                → Report/transformed_data.csv  (auto-opens)
```

The Chrome extension (`ChromeExtension/`) is the **legacy approach** — it still works if you prefer manual extraction, but the automated pipeline above replaces the need for it entirely.

---

## Project Structure

```
├── auto_extract.py          # Main automation script (Playwright-based)
├── main.py                  # Core pipeline: fetch → parse → save → transform
├── server.py                # Flask server that receives tokens from the Chrome extension
├── setup_scheduler.py       # One-time setup: registers Task Scheduler + Startup tasks
├── start_server.bat         # Starts the Flask server (also placed in Windows Startup)
│
├── ChromeExtension/         # Legacy Chrome extension (manual trigger)
│   ├── manifest.json
│   ├── background.js
│   └── content.js
│
├── Extracted/
│   └── attendance_data.csv  # Raw attendance records (cumulative)
│
├── Report/
│   └── transformed_data.csv # Formatted report with working hours (auto-opens after extraction)
│
└── Logs/
    └── attendance_log_YYYY-MM-DD.txt  # Daily rotating logs
```

---

## Prerequisites

- **Python 3.10+** (project uses 3.14)
- **Google Chrome** installed
- You must have logged into `hrmstismo.keka.com` via GAuth at least once in your default Chrome profile

---

## First-Time Setup

### 1. Install dependencies

```powershell
pip install flask flask-cors waitress pandas requests playwright
playwright install chromium
```

### 2. Register automation tasks (no admin rights needed)

```powershell
python setup_scheduler.py
```

This does two things:
- Drops `KekaServerAutoStart.bat` into your Windows **Startup folder** so `server.py` starts automatically at every login
- Creates a **Task Scheduler** job (`KekaAttendanceDaily`) that runs `auto_extract.py` every weekday at 6:30 PM

### 3. Seed your Chrome session

Open `https://hrmstismo.keka.com` in your normal Google Chrome and log in via **Sign in with Google (GAuth)**. This saves the session cookies to your Chrome profile so the automation can reuse them silently.

### 4. Run once manually to verify

```powershell
python auto_extract.py
```

On success, `Report/transformed_data.csv` will open automatically.

---

## Daily Usage (after setup)

Nothing. The extractor runs itself every weekday at 6:30 PM.

- **Token still valid** → extraction completes in seconds with no browser visible
- **Token expired** → Chrome opens visibly, you complete GAuth once (~10 seconds), Chrome closes, extraction continues automatically
- **Report** → `Report/transformed_data.csv` opens after every successful run

---

## Manual Extraction (anytime)

```powershell
python auto_extract.py
```

---

## Legacy: Chrome Extension (manual)

If you want to trigger extraction manually from the browser:

1. Ensure the Flask server is running: double-click `start_server.bat`
2. Open `https://hrmstismo.keka.com` in Chrome (must be logged in)
3. Load the extension in Chrome:
   - Go to `chrome://extensions/`
   - Enable **Developer mode**
   - Click **Load unpacked** → select the `ChromeExtension/` folder
4. Click the extension icon while on the Keka page

The extension reads the Bearer token from localStorage and POSTs it to the local Flask server, which then runs the extraction pipeline.

---

## Removing the Automation

```powershell
python setup_scheduler.py --remove
```

This deletes the Startup folder shortcut and the Task Scheduler job.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Token not found in localStorage` | Log into Keka manually in Chrome first, then rerun |
| `Address already in use` on port 5000 | The updated `start_server.bat` kills stale instances automatically |
| Playwright can't find Chrome | Ensure Google Chrome is installed; `channel="chrome"` in `auto_extract.py` requires the full Chrome, not just Chromium |
| GAuth keeps expiring | Normal — Google OAuth sessions last a few weeks. Browser opens automatically when needed |
| Report not updating | Check `Logs/attendance_log_YYYY-MM-DD.txt` for error details |

---

## Configuration

Edit these constants at the top of `auto_extract.py` if needed:

| Constant | Default | Description |
|---|---|---|
| `KEKA_URL` | `https://hrmstismo.keka.com` | Your organisation's Keka URL |
| `TOKEN_STORAGE_KEY` | `access_token` | localStorage key for the Bearer token |
| `CHROME_USER_DATA` | `%LOCALAPPDATA%\Google\Chrome\User Data` | Chrome profile directory |
| `CHROME_PROFILE` | `Default` | Profile folder name inside User Data |

To change the daily extraction time, re-run:

```powershell
python setup_scheduler.py
```

And edit `create_extract_task(hour=18, minute=30)` in `setup_scheduler.py` before running.
