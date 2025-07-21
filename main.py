import os
import requests
import csv
import datetime
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from threading import Event
import subprocess
import sys

log_box_ready = Event()

# ---------------------------------------
# Constants and Directory Setup
# ---------------------------------------

# Base URL to fetch attendance data
BASE_URL = "https://hrmstismo.keka.com/k/attendance/api/mytime/attendance/summary/"

# Get the current script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define subdirectories for logs, extracted CSVs, and final reports
LOG_DIR = os.path.join(BASE_DIR, "Logs")
EXTRACTED_DIR = os.path.join(BASE_DIR, "Extracted")
REPORT_DIR = os.path.join(BASE_DIR, "Report")

# Create the directories if they don't exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXTRACTED_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Define file paths
LOG_FILE = os.path.join(LOG_DIR, f"attendance_log_{datetime.date.today()}.txt")
EXTRACTED_FILE = os.path.join(EXTRACTED_DIR, "attendance_data.csv")
TRANSFORMED_FILE = os.path.join(REPORT_DIR, "transformed_data.csv")

# ---------------------------------------
# Logging Function
# ---------------------------------------

# Logs a message with a timestamp to the log file and prints to console 
def log_message(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    final_message = f"{timestamp} {message}\n"

    with open(LOG_FILE, "a") as log:
        log.write(f"{timestamp} {message}\n")
    
    # Print to console
    print(final_message.strip())

    try:
        log_box.configure(state='normal')
        log_box.insert(tk.END, final_message)
        log_box.configure(state='disabled')
        log_box.see(tk.END)
        log_box.update_idletasks()
    except Exception as e:
        pass


# ---------------------------------------
# Open Report Folder
# ---------------------------------------
def open_report_folder():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, 'report')

    if not os.path.exists(report_path):
        log_message("Report folder does not exist.")
        return

    try:
        if sys.platform.startswith('darwin'):  # macOS
            subprocess.call(['open', report_path])
        elif os.name == 'nt':  # Windows
            os.startfile(report_path)
        elif os.name == 'posix':  # Linux
            subprocess.call(['xdg-open', report_path])
    except Exception as e:
        log_message(f"Failed to open report folder: {e}")

# ---------------------------------------
# Validate Token
# ---------------------------------------

# Validate the token before using it for extraction

def validate_token(token):
    test_url = BASE_URL  # A safe endpoint for validation
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(test_url, headers=headers)
        if response.status_code == 200:
            log_message("Token validation successful.")
            return True
        else:
            log_message(f"Token validation failed. Status Code: {response.status_code}")
            return False
    except Exception as e:
        log_message(f"Token validation error: {e}")
        return False

# ---------------------------------------
# API Request to Fetch Attendance Data
# ---------------------------------------

# Makes a GET request to the given URL using Bearer token for authorization
def fetch_attendance_data(url, token):
    log_message("Fetching Attendance Data")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        log_message(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers)
        log_message(f"Response Code: {response.status_code}")
        response.raise_for_status()  # Raise error for HTTP codes 4xx or 5xx
        log_message("Data fetched successfully")
        return response.json()
    except requests.exceptions.RequestException as e:
        log_message(f"Error fetching data: {e}")
        return None

# ---------------------------------------
# Load Previously Extracted Attendance
# ---------------------------------------

# Loads the existing extracted CSV and returns a set of (Employee ID, Date) for deduplication
def load_existing_data():
    existing_records = set()
    if os.path.exists(EXTRACTED_FILE):
        df = pd.read_csv(EXTRACTED_FILE)
        for _, row in df.iterrows():
            key = (str(row["Employee ID"]), row["Date"][:10])  # Date is in ISO; truncate to YYYY-MM-DD
            existing_records.add(key)
    return existing_records

# ---------------------------------------
# Extract Useful Data from API Response
# ---------------------------------------

# Parses and filters raw API data to extract relevant attendance records
def extract_attendance_data(data, existing_records):
    log_message("Extracting Attendance Data")
    extracted_data = []
    for record in data.get("data", []):
        if record.get("dayType") == 0 and record.get("attendanceDayStatus") == 1:
            employee_id = str(record.get("employeeId"))
            attendance_date = record.get("attendanceDate")
            # REMOVE this condition inside extract_attendance_data():
            # if (employee_id, attendance_date[:10]) in existing_records:
            #     continue
            in_time = record.get("firstLogOfTheDay", "0")
            out_time = record.get("lastLogOfTheDay", "0")

            extracted_data.append([employee_id, attendance_date, in_time, out_time])
    return extracted_data

# ---------------------------------------
# Save Extracted Data to CSV (Append Mode)
# ---------------------------------------

# Appends new records to CSV file. Writes header only if file is created newly.
def save_to_csv(data, filename):
    if not data:
        log_message("No new data to save.")
        return
    log_message(f"Saving data to {filename}")
    new_df = pd.DataFrame(data, columns=["Employee ID", "Date", "Login Time", "Logout Time"])

    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        # Truncate time for comparison
        new_df["Date"] = new_df["Date"].str[:10]
        existing_df["Date"] = existing_df["Date"].str[:10]

        # Combine and drop duplicates
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=["Employee ID", "Date"], keep="last", inplace=True)
    else:
        combined_df = new_df

    combined_df.to_csv(filename, index=False)
    # file_exists = os.path.exists(filename)
    # with open(filename, "a", newline="") as file:
    #     writer = csv.writer(file)
    #     if not file_exists:
    #         writer.writerow(["Employee ID", "Date", "Login Time", "Logout Time"])
    #     writer.writerows(data)

# ---------------------------------------
# Generate Last 6 Months’ Date Strings
# ---------------------------------------

# Returns list of YYYY-MM-01 strings for last 6 months to fetch monthly summaries
def get_last_six_months():
    today = datetime.date.today()
    months = []
    for i in range(6):
        month = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        today = month
        months.append(month.strftime("%Y-%m-01"))
    return months

# ---------------------------------------
# Transform Extracted Data into Final Report
# ---------------------------------------

# Transforms the raw attendance CSV into a readable report with formatted times, duration, etc.
def transform_data():
    log_message("Starting Transformation Process")
    df = pd.read_csv(EXTRACTED_FILE)

    # Remove rows with missing login/logout values
    df = df[(df["Login Time"] != "N/A") & (df["Logout Time"] != "N/A")]

    # Format date, time, and compute working hours
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%d-%m-%Y")
    df["Day"] = pd.to_datetime(df["Date"], format="%d-%m-%Y").dt.day_name()
    df["Login Time"] = pd.to_datetime(df["Login Time"], format="%Y-%m-%dT%H:%M:%S").dt.strftime("%H:%M:%S")
    df["Logout Time"] = pd.to_datetime(df["Logout Time"], format="%Y-%m-%dT%H:%M:%S").dt.strftime("%H:%M:%S")

    # Calculate total working hours (duration between logout and login)
    df["Total Working Hours"] = (
        pd.to_datetime(df["Logout Time"], format="%H:%M:%S") -
        pd.to_datetime(df["Login Time"], format="%H:%M:%S")
    ).astype(str).str.replace("0 days ", "", regex=False)

    # Final column order
    df = df[["Employee ID", "Date", "Day", "Login Time", "Logout Time", "Total Working Hours"]]

    if os.path.exists(TRANSFORMED_FILE):
        df_old = pd.read_csv(TRANSFORMED_FILE)
        combined_df = pd.concat([df_old, df], ignore_index=True)

        # Remove any duplicate rows
        combined_df.drop_duplicates(subset=["Date"], keep="last", inplace=True)

    else:
        combined_df = df

    # Sort by Date descending
    combined_df["Date"] = pd.to_datetime(combined_df["Date"], format="%d-%m-%Y")
    combined_df.sort_values(by="Date", ascending=False, inplace=True)
    combined_df["Date"] = combined_df["Date"].dt.strftime("%d-%m-%Y")

    # Save updated combined report
    combined_df.to_csv(TRANSFORMED_FILE, index=False)
    log_message(f"Saving Transformed Data to {TRANSFORMED_FILE}")
    log_message("Transformation Process Completed")

# ---------------------------------------
# Main Processing Logic
# ---------------------------------------

# Core function to coordinate fetch → extract → append → transform steps
def main(token):
    extracted_data = []
    existing_records = load_existing_data()

    # Fetch latest attendance summary (for current day/week)
    fetched_data = fetch_attendance_data(BASE_URL, token)
    if fetched_data:
        extracted_data.extend(extract_attendance_data(fetched_data, existing_records))

    # Fetch past 6 months of attendance history
    for month in get_last_six_months():
        monthly_url = f"{BASE_URL}{month}"
        data = fetch_attendance_data(monthly_url, token)
        if data:
            extracted_data.extend(extract_attendance_data(data, existing_records))

    # Save newly fetched data and transform
    save_to_csv(extracted_data, EXTRACTED_FILE)
    transform_data()

# ---------------------------------------
# GUI Layer (Token Input & Trigger)
# ---------------------------------------

# GUI button handler to run extraction after getting token
def run_script():
    token = token_entry.get().strip()
    if not token:
        messagebox.showerror("Error", "Please enter the Bearer Token")
        return
    log_message("Validating token...")
    if validate_token(token):
        log_message("Starting attendance data extraction...")
        main(token)
        log_message("Process Completed!")
        messagebox.showinfo("Success", "Attendance data extraction completed successfully!")
    else:
        messagebox.showerror("Invalid Token", "The provided token is invalid or expired.")



def start_gui(disable_input=False):
    global root, token_entry, log_box
    # GUI Window Setup
    root = tk.Tk()
    root.iconbitmap("system_cloud.ico")  # .ico format only for Windows
    root.title("Attendance Data Extractor")
    root.geometry("600x400")

        # Token entry UI
    if not disable_input:
        ttk.Label(root, text="Enter Bearer Token:").pack(pady=10)
        token_entry = ttk.Entry(root, width=50, show="*")
        token_entry.pack(pady=5)
        token_entry.bind("<Return>", lambda event: run_script())


        # Start button
        ttk.Button(root, text="Start Extraction", command=run_script).pack(pady=20)

    #Display Log Output
    log_frame = tk.Frame(root)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    log_scrollbar = tk.Scrollbar(log_frame)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    log_box = tk.Text(log_frame, height=6, yscrollcommand=log_scrollbar.set, state='disabled', wrap='none')
    log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Signal that log_box is ready
    log_box_ready.set()

    log_scrollbar.config(command=log_box.yview)
    # Button to open report folder
    report_button = tk.Button(root, text="Open Report Folder", command=open_report_folder)
    report_button.pack(pady=(5, 10))


    # Start the GUI event loop
    root.mainloop()
    
if __name__ == "__main__":
    start_gui()


    