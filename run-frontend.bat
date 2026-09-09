@echo off
echo Starting SIH26183 frontend...
cd /d "%~dp0frontend"
npm install
npm run dev
