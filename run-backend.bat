@echo off
echo Starting SIH26183 backend...
cd /d "%~dp0backend"
if not exist .env copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
