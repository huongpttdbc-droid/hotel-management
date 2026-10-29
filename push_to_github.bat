@echo off
chcp 65001 > nul
echo ========================================================
echo   ĐẨY DỰ ÁN KHÁCH SẠN LÊN GITHUB
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
echo 3. Dang thuc hien Push ma nguon da sua len GitHub...
echo [CHU Y] Neu trinh duyet mo tab GitHub, ban chi can bam 'Authorize' de hoan tat!
echo.
git push origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo   [THANH CONG] MA NGUON MOI DA LEN GITHUB!
    echo   Render se tu dong cap nhat va het sach loi trong 1-2 phut!
    echo ========================================================
) else (
    echo ========================================================
    echo   [THONG BAO] Chua hoan tat push. Vui long kiem tra xac thuc.
    echo ========================================================
)
pause
