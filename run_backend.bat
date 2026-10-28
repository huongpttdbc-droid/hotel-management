@echo off
chcp 65001 > nul
echo ========================================================
echo  KHOI DONG BACKEND PYTHON FASTAPI - QUAN LY KHACH SAN
echo ========================================================
echo.
echo Dang kich hoat moi truong ao (.venv)...
call .\venv\Scripts\activate
echo Dang chay Uvicorn Server tai http://127.0.0.1:8000 ...
echo Swagger UI Docs: http://127.0.0.1:8000/docs
echo.
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause

