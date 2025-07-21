import requests
from datetime import datetime

BASE_URL = "https://hrmstismo.keka.com/k/attendance/api/mytime/attendance/summary/"
TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjFBRjQzNjk5RUE0NDlDNkNCRUU3NDZFMjhDODM5NUIyMEE0MUNFMTgiLCJ4NXQiOiJHdlEybWVwRW5HeS01MGJpaklPVnNncEJ6aGciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FwcC5rZWthLmNvbSIsIm5iZiI6MTc1MjE1MTcyOSwiaWF0IjoxNzUyMTUxNzI5LCJleHAiOjE3NTIyMzgxMjksImF1ZCI6WyJrZWthaHIuYXBpIiwiaGlyby5hcGkiLCJodHRwczovL2FwcC5rZWthLmNvbS9yZXNvdXJjZXMiXSwic2NvcGUiOlsib3BlbmlkIiwia2VrYWhyLmFwaSIsImhpcm8uYXBpIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbImV4dGVybmFsIl0sImNsaWVudF9pZCI6Ijk4N2NjOTcxLWZjMjItNDQ1NC05OWY5LTE2YzA3OGZhN2ZmNiIsInN1YiI6IjljNzIwYzZjLWNiNjQtNDJkMy04OWMwLTEwNDk4YWFkMDE5OCIsImF1dGhfdGltZSI6MTc1MTk0ODkwNSwiaWRwIjoiR29vZ2xlIiwidGVuYW50X2lkIjoiMWU5NDQ2NmYtNWM3ZS00M2YyLWIyZWQtMmZkYmRjY2JjNDI2IiwidGVuYW50aWQiOiIxZTk0NDY2Zi01YzdlLTQzZjItYjJlZC0yZmRiZGNjYmM0MjYiLCJzdWJkb21haW4iOiJocm1zdGlzbW8ua2VrYS5jb20iLCJ1c2VyX2lkIjoiYmNiMTkzNGMtMjZlMi00NTlkLTkxMTktNjZkOWVhZDIwMWQ5IiwidXNlcl9pZGVudGlmaWVyIjoiYmNiMTkzNGMtMjZlMi00NTlkLTkxMTktNjZkOWVhZDIwMWQ5IiwidXNlcm5hbWUiOiJzaGFtYW50aC5rcmlzaG5hQHRpc21vdGVjaC5jb20iLCJlbWFpbCI6InNoYW1hbnRoLmtyaXNobmFAdGlzbW90ZWNoLmNvbSIsImF1dGhlbnRpY2F0aW9uX3R5cGUiOiIzIiwic2lkIjoiQTQ2Q0UxMEU4OTNCNTg4MEI1RDJBQ0JFM0Y0RjRCRjYiLCJqdGkiOiI5REFERUNERjQ3RDlEOTgyMDkxODE2NEMzOEY4OUE0NyJ9.FmPWCYvWUyLGK8GBg6DEPTHsZP_YQXTlE89u5OqsimbLIaV8mhOgZ_QtRJe0rujKwa97gTTGva8eUsYRQdBgdOCkEMtOzCQrhoSr7Nnxc_ayMJiCHGgPAPaTyUdDhsIg5Krtbg4XzyE79gAoiY60-dc4ZGtHNODKX4HtUY7zVN-o5RbSuCE10n_0vRhY3MMwfsVN5KjuUXKomB3x6VDFoJmIJuab6ZbJGZhT1BeLylS9JUl3eRi6J0PGDo2Yh0m9nkqfgK2EdbyLuYD1P7s5gRkrIUxVBIwcSxhL6TlV2OE25-5yQ2CukCAcDAFr16j3cwiwf0wHzwgrXWu77pi1fA"  # Replace with your actual token

# ✅ List of dates (in YYYY-MM-DD format) you want lastLogOfTheDay for
target_dates = {
    "2025-07-01",
    "2025-07-05",
    "2025-07-09",
    "2025-07-10",
    # Add more here
}

# ✅ Determine months from target dates
months_to_fetch = sorted({date[:7] + "-01" for date in target_dates})

def fetch_last_log_of_day():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    results = {}

    for month in months_to_fetch:
        url = f"{BASE_URL}{month}"
        print(f"Fetching for month: {month}")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json().get("data", [])

            for record in data:
                date_str = record.get("attendanceDate", "")[:10]
                if date_str in target_dates:
                    results[date_str] = {
                        "firstLog": record.get("firstLogOfTheDay", "N/A"),
                        "lastLog": record.get("lastLogOfTheDay", "N/A"),
                    }

        except requests.RequestException as e:
            print(f"Error fetching data for {month}: {e}")

    return results

# 🔍 Run and display results
if __name__ == "__main__":
    log_data = fetch_last_log_of_day()
    for date, logs in sorted(log_data.items()):
        print(f"{date} => First: {logs['firstLog']}, Last: {logs['lastLog']}")
