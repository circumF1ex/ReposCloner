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

echo Installing web dependencies...
python -m pip install -r requirements-web.txt

echo Starting ReposCloner web console at http://localhost:8501 ...
echo Close this window to stop the server.
start "" http://localhost:8501
python -m streamlit run web.py

pause
