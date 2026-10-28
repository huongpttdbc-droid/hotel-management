# Backend Python FastAPI - Hệ Thống Quản Lý Khách Sạn 🏨

Hệ thống API RESTful hoàn chỉnh xây dựng bằng **Python 3.12 (FastAPI)**, kết nối trực tiếp với cơ sở dữ liệu **Microsoft SQL Server (`QuanLyKhachSan`)**, hỗ trợ tiếng Việt Unicode chuẩn và sẵn sàng triển khai lên **Render**, **Railway**, hoặc **Netlify**.

---

## 1. Tính năng cốt lõi của Backend

- **Xác thực & Người dùng (`/api/auth`)**: Đăng nhập tài khoản Admin/Khách hàng (hỗ trợ sẵn tài khoản demo `admin / admin123`, `khach / khach123` và tra cứu bảng `TaiKhoan` trong CSDL).
- **Quản lý Sơ đồ phòng (`/api/phong`)**:
  - Tra cứu 30 phòng theo tầng và loại phòng.
  - Cập nhật trạng thái phòng (`Trống`, `Đang thuê`, `Đang dọn`, `Bảo trì`).
  - Tự động hiển thị tên khách hàng đang thuê phòng.
- **Quản lý Khách hàng (`/api/khach-hang`)**:
  - Tìm kiếm khách hàng theo Tên, CCCD hoặc SĐT.
  - Thêm mới khách hàng (ràng buộc tự động: tuổi $\ge 18$, CCCD 12 số, tự sinh mã KH).
- **Quản lý Đặt & Thuê phòng (`/api/phieu-thue`)**:
  - Lập phiếu thuê, tính đơn giá phòng theo ngày/giờ/đêm.
  - Nhận phòng, tự động chuyển trạng thái phòng sang `Đang thuê`.
  - Trả phòng, ghi nhận giờ trả thực tế và chuyển phòng sang `Đang dọn`.
- **Dịch vụ khách sạn (`/api/dich-vu`)**: Danh mục 32 dịch vụ, ghi nhận dịch vụ phát sinh theo phiếu thuê.
- **Hóa đơn & Thanh toán (`/api/hoa-don`)**:
  - Tự động tính tiền phòng + tiền dịch vụ - ưu đãi khách hàng + 10% VAT.
  - Cập nhật trạng thái `Đã thanh toán`.
- **Báo cáo Thống kê (`/api/thong-ke`)**: Thống kê số lượng phòng theo trạng thái, số khách hàng, tổng doanh thu thực tế.

---

## 2. Hướng dẫn chạy tại máy (Local Development)

### Cách 1: Chạy nhanh bằng file Batch
Bấm đúp chuột vào file:
```
run_backend.bat
```

### Cách 2: Chạy bằng Terminal
```powershell
# 1. Kích hoạt môi trường ảo
.\venv\Scripts\activate

# 2. Khởi động server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Giao diện Swagger UI (Test API trực quan)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Giao diện ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Kiểm tra trạng thái**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 3. Cấu hình Cơ sở dữ liệu

File `.env` tại thư mục gốc:
```ini
DATABASE_URL=mssql+pyodbc://localhost\SQLEXPRESS01/QuanLyKhachSan?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Trusted_Connection=yes
SECRET_KEY=hotel-management-secret-key-2026
ENVIRONMENT=development
PORT=8000
```
*Lưu ý*: Dự án đã được tạo sẵn bản cơ sở dữ liệu `hotel_fallback.db` đồng bộ toàn bộ 18 bảng dữ liệu từ SQL Server sang SQLite. Khi deploy lên Cloud nếu không có SQL Server bên ngoài, backend sẽ tự động chuyển sang CSDL này giúp website chạy ổn định 24/7 mà không bao giờ bị lỗi kết nối!

---

## 4. Hướng dẫn Triển khai lên Render (Khuyến nghị)

Dự án đã có sẵn file `render.yaml` và `Procfile`:
1. Đẩy mã nguồn lên kho lưu trữ **GitHub** (hoặc GitLab).
2. Đăng nhập vào [render.com](https://render.com) (tài khoản GitHub).
3. Chọn **New +** $\rightarrow$ **Web Service** $\rightarrow$ chọn repository dự án.
4. Render sẽ tự động nhận diện cấu hình:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
5. Nhấn **Create Web Service**, đợi 1-2 phút bạn sẽ có đường link API công khai dạng `https://quanlykhachsan-api.onrender.com/docs`.

---

## 5. Triển khai lên Netlify (Tùy chọn)

Dự án đã có sẵn cấu hình `netlify.toml` và adapter Serverless `netlify/functions/api.py` (sử dụng thư viện `mangum`).
- Lệnh deploy Netlify: `netlify deploy --prod` hoặc liên kết trực tiếp GitHub với Netlify.

