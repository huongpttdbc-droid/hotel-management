"""
backend/app/migrate_to_cloud.py
Script hỗ trợ chuyển toàn bộ dữ liệu từ SQL Server Local (hoặc SQLite fallback) sang Cloud Database (Supabase / Render Postgres / Neon / Aiven / Azure SQL).

Cách dùng:
    python backend/app/migrate_to_cloud.py "<TARGET_DATABASE_URL>"

Ví dụ:
    python backend/app/migrate_to_cloud.py "postgresql://postgres.xxx:mypassword@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
    python backend/app/migrate_to_cloud.py "postgres://hotel_user:pass@dpg-xxx-a.singapore-postgres.render.com/hotel_db"
"""

import os
import sys

# Đảm bảo đường dẫn gốc của project luôn có trong sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, text
from backend.app.database import engine as source_engine, Base
import backend.app.models  # Nạp các model để lấy danh sách bảng

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    if len(sys.argv) < 2:
        print("=" * 70)
        print("HƯỚNG DẪN ĐỒNG BỘ DỮ LIỆU LÊN CLOUD DATABASE")
        print("=" * 70)
        print("Cú pháp: python backend/app/migrate_to_cloud.py \"<TARGET_DATABASE_URL>\"\n")
        print("Ví dụ PostgreSQL (Supabase / Neon / Render):")
        print("  python backend/app/migrate_to_cloud.py \"postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres\"\n")
        print("Ví dụ SQL Server Cloud (Azure SQL / Aiven MSSQL):")
        print("  python backend/app/migrate_to_cloud.py \"mssql+pymssql://user:pass@server.database.windows.net:1433/hoteldb\"\n")
        sys.exit(1)

    target_url = sys.argv[1].strip()
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif target_url.startswith("postgresql://") and "+psycopg2" not in target_url:
        target_url = target_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    print(f"1. Đang kết nối tới CSDL Nguồn (Source): {source_engine.url.render_as_string(hide_password=True)}")
    print(f"2. Đang kết nối tới CSDL Đích (Target Cloud): {target_url.split('@')[-1] if '@' in target_url else target_url}")

    try:
        target_engine = create_engine(target_url, pool_pre_ping=True)
        with target_engine.connect() as conn:
            print("   -> Kết nối Cloud Database thành công!")
    except Exception as e:
        print(f"   [LỖI] Không thể kết nối tới Cloud Database: {e}")
        sys.exit(1)

    print("\n3. Đang tự động tạo cấu trúc bảng (Schema & Tables) trên Cloud Database...")
    try:
        Base.metadata.create_all(bind=target_engine)
        print("   -> Đã khởi tạo cấu trúc toàn bộ 18 bảng thành công!")
    except Exception as e:
        print(f"   [CẢNH BÁO] Lỗi khi tạo bảng: {e}")

    # Thứ tự sao chép bảng theo thứ tự quan hệ khóa ngoại (Foreign Keys)
    table_order = [
        "LoaiKhachHang", "KhachHang", "KhachHang_SDT", "KhachHang_Email",
        "NhanVien", "NhanVien_SDT", "NhanVien_Email", "TaiKhoan",
        "LoaiPhong", "Phong", "PhieuThue", "ChiTietPhieuThue",
        "KhachDiCung", "OCung", "DichVu", "DungDichVu", "ThanhToan", "HoaDon"
    ]

    print("\n4. Bắt đầu sao chép dữ liệu từng bảng:")
    total_copied = 0

    with source_engine.connect() as src_conn:
        for tbl in table_order:
            try:
                # Đọc dữ liệu từ nguồn
                rows = src_conn.execute(text(f'SELECT * FROM "{tbl}"' if "sqlite" in str(source_engine.url) else f"SELECT * FROM {tbl}")).mappings().all()
                if not rows:
                    print(f"   - {tbl:20s}: 0 bản ghi (trống)")
                    continue

                # Ghi vào đích
                with target_engine.begin() as tgt_conn:
                    # Xóa dữ liệu cũ nếu có
                    tgt_conn.execute(text(f'DELETE FROM "{tbl}"' if "postgres" in target_url else f"DELETE FROM {tbl}"))
                    
                    cols = list(rows[0].keys())
                    col_names = ", ".join([f'"{c}"' if "postgres" in target_url else c for c in cols])
                    val_placeholders = ", ".join([f":{c}" for c in cols])
                    
                    insert_stmt = text(f'INSERT INTO {"\"" + tbl + "\"" if "postgres" in target_url else tbl} ({col_names}) VALUES ({val_placeholders})')
                    tgt_conn.execute(insert_stmt, [dict(r) for r in rows])

                print(f"   - {tbl:20s}: Đã đồng bộ {len(rows)} bản ghi.")
                total_copied += len(rows)
            except Exception as te:
                print(f"   - [Bỏ qua/Lỗi] {tbl:16s}: {te}")

    print("\n" + "=" * 70)
    print(f"HOÀN TẤT ĐỒNG BỘ: Đã sao chép thành công {total_copied} bản ghi lên Cloud Database!")
    print("Bây giờ bạn chỉ cần copy chuỗi kết nối dán vào biến môi trường DATABASE_URL trên Render:")
    print(f"DATABASE_URL = {target_url}")
    print("=" * 70)

if __name__ == "__main__":
    main()
