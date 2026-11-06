@echo off
rem Chay nhanh UpScale: bam doi vao file nay hoac go run.bat trong thu muc du an.
rem Thu .venv truoc, neu thieu thu vien thi tim ban Python khac da cai customtkinter va Pillow.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set "PY="

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import customtkinter, PIL" >nul 2>&1
    if not errorlevel 1 set "PY=.venv\Scripts\python.exe"
)

if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 (
        for %%V in (3.11 3.12 3.13 3.14) do (
            if not defined PY (
                py -%%V -c "import customtkinter, PIL" >nul 2>&1
                if not errorlevel 1 set "PY=py -%%V"
            )
        )
    )
)

if not defined PY (
    python -c "import customtkinter, PIL" >nul 2>&1
    if not errorlevel 1 set "PY=python"
)

if not defined PY (
    echo Khong tim thay Python co du customtkinter va Pillow.
    echo Cai bang lenh: python -m pip install -r requirements.txt
    pause
    exit /b 1
)

%PY% run.py
if errorlevel 1 (
    echo.
    echo UpScale thoat voi loi. Xem logs\app.log de biet chi tiet.
    pause
)
endlocal
