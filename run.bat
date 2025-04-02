@echo off
start /B python app.py
timeout /t 12 /nobreak >nul
streamlit run streamlit/app2.py
