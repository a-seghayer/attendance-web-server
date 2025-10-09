# PreStaff — Attendance & HR Web Server

Backend service for PreStaff, a lightweight Attendance & HR system. Built with Flask, it powers:

- Attendance processing (Excel to rich reports)
- Overtime and leave requests
- Employees directory and search
- Users and permissions (admin panel)

Note: Dashboard statistics endpoints have been removed to reduce resource usage and simplify operations.

## API Overview
- `GET /api/health` — Health check.
- Attendance processing:
  - `POST /api/process` — Uploads an Excel file and options, returns a ZIP with `Summary_*.xlsx` and `Daily_*.xlsx` reports.
- Employees:
  - `POST /api/employees/search` — Advanced employee search (by ID/name and more).
- Users and admin:
  - Endpoints for listing, creating, and updating users and their service permissions.

Examples and full details live in `app_firebase.py` and related modules.

Form fields for `/api/process`:
- `file` (required): uploaded Excel file.
- `sheet` (optional): worksheet name.
- `target_days` (required): e.g., `26`.
- `holidays` (optional): comma-separated dates `YYYY-MM-DD`.
- `special_days` (optional): comma-separated dates `YYYY-MM-DD` to ignore absences.
- `cutoff_hour` (optional): default `7`.
- `format` (optional): `auto` | `legacy` | `timecard`.
- `allow_negative` (optional): `1` to allow negative overtime.

## Installation
1. Open a terminal in this folder:
   `attendance_tool/web_server/`
2. Create a virtual environment (recommended):
   - Windows PowerShell:
     ```powershell
     py -3 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

Note: The server imports `attendance_processor.py` from the parent folder; no extra install is required for it.

## Local Development
```powershell
python app.py
```
This starts the server at `http://localhost:5000`.

## Use from the Website
Frontend pages live in `My website/`:
- `dashboard.html` — main hub (statistics disabled by design).
- `attendance-processor.html` — attendance processing UI.
- `overtime.html` — overtime and leave requests.
- `employees.html` — employees directory.

Ensure the backend base URL is configured in local storage or page settings as `http://localhost:5000` when running locally.

Basic cURL example (attendance):
```bash
curl -X POST "http://localhost:5000/api/process" \
  -F "file=@path/to/attendance.xlsx" \
  -F "target_days=26" \
  -o result.zip
```

## Configuration
- Firebase: place `serviceAccountKey.json` in `attendance_tool/web_server/`, or set the `FIREBASE_CREDENTIALS` environment variable to the JSON content.
- Environment variables can be added as needed for deployment.

## Security
- CORS is enabled via `flask-cors` to allow calls from the static frontend.
- Temporary files are handled per-request; results are streamed back as a ZIP.
- Do NOT expose this server publicly without authentication, rate limits, and proper hardening.

## Deployment
- Containerize or host on a PaaS (e.g., Render/Heroku) with environment variables for Firebase credentials.
- Configure HTTPS, logging, and monitoring for production.

## License
MIT — see `LICENSE` (add if missing).

## Author
Built by Anas Seghayer.
