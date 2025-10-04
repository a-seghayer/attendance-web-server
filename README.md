# Attendance Processor Web Server

This is a minimal Flask backend that exposes the existing `attendance_processor.py` as a web API so it can be used from your static website page `my website/attendance.html`.

## Endpoints
- `GET /api/health` — health check.
- `POST /api/process` — accepts an Excel file and options, returns a ZIP containing the generated `Summary_*.xlsx` and `Daily_*.xlsx` reports.

Form fields for `/api/process`:
- `file` (required): uploaded Excel file.
- `sheet` (optional): worksheet name.
- `target_days` (required): e.g., `26`.
- `holidays` (optional): comma-separated dates `YYYY-MM-DD`.
- `special_days` (optional): comma-separated dates `YYYY-MM-DD` to ignore absences.
- `cutoff_hour` (optional): default `7`.
- `format` (optional): `auto` | `legacy` | `timecard`.
- `allow_negative` (optional): `1` to allow negative overtime.

## Setup
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

Note: The web server imports `attendance_processor.py` from the parent folder, so no extra install is needed for it.

## Run
```powershell
python app.py
```
This starts the server at `http://localhost:5000`.

## Use from the website
1. Open `my website/attendance.html` in your browser (or serve the `my website/` folder with any static server).
2. Ensure the "Backend server URL" is `http://localhost:5000`.
3. Choose your Excel, set options, and click Process.
4. Download the returned ZIP.

## Notes
- CORS is enabled via `flask-cors` to allow calls from a static file opened in the browser.
- The server writes temporary files per request and returns an in-memory ZIP.
- Do not expose this server to the internet without proper hardening.
