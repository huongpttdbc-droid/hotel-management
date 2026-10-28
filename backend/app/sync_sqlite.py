import sys
import os
import pyodbc
import sqlite3

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

print("Đang đồng bộ dữ liệu từ SQL Server (localhost\\SQLEXPRESS01) sang SQLite fallback...")

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS01;"
    "DATABASE=QuanLyKhachSan;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

try:
    mssql_conn = pyodbc.connect(conn_str)
    cursor = mssql_conn.cursor()

    sqlite_path = os.path.join(os.path.dirname(__file__), "..", "..", "hotel_fallback.db")
    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cur = sqlite_conn.cursor()

    # Danh sách bảng cần sync theo thứ tự
    tables = [
        "LoaiKhachHang", "KhachHang", "KhachHang_SDT", "KhachHang_Email",
        "NhanVien", "NhanVien_SDT", "NhanVien_Email", "TaiKhoan",
        "LoaiPhong", "Phong", "PhieuThue", "ChiTietPhieuThue",
        "KhachDiCung", "OCung", "DichVu", "DungDichVu", "ThanhToan", "HoaDon"
    ]

    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            cols = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            # Tạo bảng trong SQLite
            col_defs = ", ".join([f'"{col}" TEXT' for col in cols])
            sqlite_cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs})')

            # Chèn dữ liệu
            placeholders = ", ".join(["?"] * len(cols))
            for row in rows:
                converted_row = [str(val) if val is not None else None for val in row]
                sqlite_cur.execute(f'INSERT INTO "{table}" VALUES ({placeholders})', converted_row)

            print(f" - Đã đồng bộ bảng {table}: {len(rows)} bản ghi.")
        except Exception as te:
            print(f" - Bỏ qua bảng {table}: {te}")

    sqlite_conn.commit()
    sqlite_conn.close()
    mssql_conn.close()
    print("HOÀN TẤT ĐỒNG BỘ: hotel_fallback.db đã sẵn sàng cho Cloud / Render!")
except Exception as e:
    print("Lỗi đồng bộ:", e)
