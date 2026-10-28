@echo off
chcp 65001 > nul
echo ========================================================
echo   ĐẨY DỰ ÁN KHÁCH SẠN LÊN GITHUB
echo   Repository: https://github.com/huongpttdbc-droid/hotel-management.git
echo ========================================================
echo.
set "PATH=C:\Users\PHAM HUONG\AppData\Local\Programs\Git\cmd;%PATH%"

echo 1. Kiểm tra cấu hình Remote...
git remote set-url origin https://huongpttdbc-droid@github.com/huongpttdbc-droid/hotel-management.git
git remote -v

echo.
echo 2. Chuyển nhánh main...
git branch -M main

echo.
echo 3. Đang thực hiện Push mã nguồn lên GitHub...
echo [LƯU Ý] Trình duyệt hoặc cửa sổ GitHub sẽ tự động mở lên để bạn xác thực tài khoản huongpttdbc-droid.
echo.
git push -u origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo   THÀNH CÔNG! MÃ NGUỒN ĐÃ ĐƯỢC ĐẨY LÊN GITHUB HOÀN TẤT!
    echo ========================================================
) else (
    echo ========================================================
    echo   CÓ LỖI XẢY RA HOẶC BẠN ĐÃ HỦY XÁC THỰC.
    echo ========================================================
)
pause

