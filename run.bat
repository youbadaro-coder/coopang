@echo off
setlocal
cd /d %~dp0

echo Checking dependencies...
pip install -r requirements.txt --quiet 2>nul

echo Starting Coupang Partners Bot...
streamlit run app.py --browser.gatherUsageStats false

pause
