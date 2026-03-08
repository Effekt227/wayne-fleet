@echo off
title Wayne Fleet
cd /d "C:\Users\Anna S\Wayne Fleet"
echo Spoustim Wayne Fleet...
start "" http://localhost:8501
streamlit run app.py --server.port 8501 --server.headless false
