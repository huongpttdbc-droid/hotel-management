@echo off
chcp 65001 > nul
echo ========================================================
echo   DAY DU AN KHACH SAN LEN GITHUB
echo   Repository: https://github.com/huongpttdbc-droid/hotel-management.git
echo ========================================================
echo.
set "PATH=C:\Users\PHAM HUONG\AppData\Local\Programs\Git\cmd;%PATH%"

echo 1. Kiem tra Remote origin...
git remote set-url origin https://huongpttdbc-droid@github.com/huongpttdbc-droid/hotel-management.git
git remote -v

echo.
echo 2. Nhanh hien tai:
git branch -M main

echo.
echo 3. Tu dong them file va commit thay doi...
git add .
git commit -m "chore: Dong bo ma nguon moi nhat" > nul 2>&1

echo.
echo 4. Dang dong bo voi GitHub (Pull Rebase)...
git pull --rebase origin main

echo.
echo 5. Dang Push ma nguon len GitHub...
git push origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo   [THANH CONG] MA NGUON DA DUOC DONG BO LEN GITHUB!
    echo   Render se tu dong cap nhat trong 1-2 phut.
    echo ========================================================
) else (
    echo ========================================================
    echo   [THONG BAO] Co loi xay ra khi push. Vui long kiem tra.
    echo ========================================================
)
pause
