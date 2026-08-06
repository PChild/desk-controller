@echo off
curl -s http://desk.local/api/stow >nul 2>&1
timeout /t 2 /nobreak >nul
rundll32.exe powrprof.dll,SetSuspendState 0,1,0