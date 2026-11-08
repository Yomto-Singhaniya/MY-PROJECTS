@echo off
setlocal
set "APP_ROOT=%~dp0"
if not exist "%APP_ROOT%backend\.venv\Scripts\activate.bat" (
  echo Backend virtual environment not found.
  echo Create it from the backend folder and install requirements first.
  pause
  exit /b 1
)

pushd "%APP_ROOT%backend"
call .venv\Scripts\activate.bat
start "SkyScan API" /min python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
popd
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ready = $false; for ($i = 0; $i -lt 45; $i++) { try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2; if ($response.StatusCode -eq 200) { $ready = $true; break } } catch { Start-Sleep -Seconds 1 } }; if (-not $ready) { exit 1 }"
if errorlevel 1 (
  echo SkyScan did not become ready. Check whether port 8000 is in use.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8000/app"
endlocal
