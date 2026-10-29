"""
backend/app/migrate_to_cloud.py
Script chuyển toàn bộ dữ liệu từ SQL Server Local (localhost\\SQLEXPRESS01) sang Cloud Database (Supabase PostgreSQL).
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, text
from backend.app.database import Base
import backend.app.models

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

LOCAL_SQL_SERVER = "mssql+pyodbc://localhost\\SQLEXPRESS01/QuanLyKhachSan?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Trusted_Connection=yes"
FALLBACK_SQLITE = os.path.join(BASE_DIR, "hotel_fallback.db").replace("\\", "/")

def get_source_engine():
    try:
        engine = create_engine(LOCAL_SQL_SERVER, connect_args={"timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("   -> CSDL Nguồn: Microsoft SQL Server (localhost\\SQLEXPRESS01)", flush=True)
            return engine
    except Exception as e:
        print(f"   -> Không kết nối được SQL Server ({e}), dùng SQLite fallback...", flush=True)
        return create_engine(f"sqlite:///{FALLBACK_SQLITE}", connect_args={"check_same_thread": False})

def main():
    if len(sys.argv) < 2:
        print("Cú pháp: python backend/app/migrate_to_cloud.py \"<TARGET_DATABASE_URL>\"", flush=True)
        sys.exit(1)

    target_url = sys.argv[1].strip()
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif target_url.startswith("postgresql://") and "+psycopg2" not in target_url:
        target_url = target_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    source_engine = get_source_engine()

    print(f"1. CSDL Nguồn: {source_engine.url.render_as_string(hide_password=True)}", flush=True)
    print(f"2. CSDL Đích: {target_url.split('@')[-1] if '@' in target_url else target_url}", flush=True)

    target_engine = create_engine(target_url, pool_pre_ping=True)
    with target_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("   -> Kết nối Cloud Database thành công!", flush=True)

    print("\n3. Đang tự động kiểm tra và tạo cấu trúc bảng...", flush=True)
    Base.metadata.create_all(bind=target_engine)
    print("   -> Cấu trúc bảng đã sẵn sàng!", flush=True)

    table_order = [
        "LoaiKhachHang", "KhachHang", "KhachHang_SDT",
        "NhanVien", "TaiKhoan",
        "LoaiPhong", "Phong",
        "PhieuThue", "ChiTietPhieuThue",
        "DichVu", "DungDichVu",
        "HoaDon", "ThanhToan"
    ]

    is_postgres = "postgres" in target_url.lower()

    print("\n4. Làm sạch dữ liệu cũ theo thứ tự ngược...", flush=True)
    with target_engine.begin() as clean_conn:
        for t in reversed(table_order):
            tbl_name = f'"{t}"' if is_postgres else t
            clean_conn.execute(text(f"DELETE FROM {tbl_name}"))

    print("\n5. Bắt đầu sao chép dữ liệu từng bảng:", flush=True)
    total_copied = 0

    for tbl in table_order:
        try:
            # Đọc từ source
            with source_engine.connect() as src_conn:
                q_src = f'SELECT * FROM "{tbl}"' if "sqlite" in str(source_engine.url) else f"SELECT * FROM {tbl}"
                rows = src_conn.execute(text(q_src)).mappings().all()

            if not rows:
                print(f"   - {tbl:18s}: 0 bản ghi", flush=True)
                continue

            # Lấy danh sách cột được định nghĩa trong ORM model
            model_cols = set(Base.metadata.tables[tbl].columns.keys())
            src_keys = list(rows[0].keys())
            valid_cols = [c for c in src_keys if c in model_cols]

            tbl_name = f'"{tbl}"' if is_postgres else tbl
            col_str = ", ".join([f'"{c}"' if is_postgres else c for c in valid_cols])
            val_str = ", ".join([f":{c}" for c in valid_cols])
            insert_stmt = text(f"INSERT INTO {tbl_name} ({col_str}) VALUES ({val_str})")

            payloads = [{c: r[c] for c in valid_cols} for r in rows]

            with target_engine.begin() as tgt_conn:
                tgt_conn.execute(insert_stmt, payloads)

            print(f"   - {tbl:18s}: Đã đồng bộ {len(rows)} bản ghi.", flush=True)
            total_copied += len(rows)

        except Exception as te:
            print(f"   - [Lỗi] {tbl:18s}: {te}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(f"HOÀN TẤT ĐỒNG BỘ: Đã sao chép thành công {total_copied} bản ghi lên Supabase!", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
