@echo off
chcp 65001 >nul
setlocal

REM Skip Streamlit first-run email prompt (create once, reused afterwards)
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
    echo [general] > "%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "" >> "%USERPROFILE%\.streamlit\credentials.toml"
)

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_HEADLESS=true

REM Web console needs Python 3.8+ (streamlit>=1.30.0)
for /f "tokens=1,2" %%a in ('py -c "import sys; print(sys.version_info[0], sys.version_info[1])" 2^>nul') do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)

if not defined PYMAJOR (
    echo Python launcher 'py' not found. Install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

set NEED_UPDATE=0
if %PYMAJOR% LSS 3 set NEED_UPDATE=1
if %PYMAJOR%==3 if %PYMINOR% LSS 8 set NEED_UPDATE=1

if %NEED_UPDATE%==0 goto :launch

echo Web console requires Python 3.8+ for streamlit, but detected Python %PYMAJOR%.%PYMINOR%.
echo Download a newer Python here: https://www.python.org/downloads/
echo Launch cancelled. Web console was not started.
pause
exit /b 1

:launch
echo Installing web dependencies...
py -m pip install -r requirements-web.txt
if errorlevel 1 (
    echo Failed to install web dependencies. Launch cancelled.
    pause
    exit /b 1
)

echo Starting ReposCloner web console at http://localhost:8501 ...
echo Close this window to stop the server.
start "" http://localhost:8501
py -m streamlit run web.py

pause
