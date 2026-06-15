@echo off
REM One-click chay Image Workflow tren Windows (double-click duoc).
REM Goi run.ps1 voi ExecutionPolicy Bypass de khong vuong chinh sach script.
REM Truyen tham so: run.bat -Dev   /   run.bat -Rebuild
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo.
  echo [x] Co loi xay ra (ma loi %ERR%^). Xem thong bao ben tren.
  pause
)
endlocal
