@echo off
REM Start backend with env from project root. Use "npm run backend" for reliable env loading.
REM Backend always runs on PORT from .env (default 8000).
cd /d "%~dp0"
set ROOT=%~dp0..
cd /d "%ROOT%"
node scripts\run-backend.js
