import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

logger = logging.getLogger("uvicorn.error")

import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

# Nạp file .env ở máy local
load_dotenv()

logger = logging.getLogger("uvicorn.error")

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SUPABASE_DB_URL")
    or os.getenv("SUPABASE_DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRESQL_URL")
    or settings.DATABASE_URL
).strip()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALLBACK_DB_PATH = os.path.join(BASE_DIR, "hotel_fallback.db").replace("\\", "/")

# Tự động chuẩn hóa chuỗi kết nối Cloud PostgreSQL (Render / Supabase / Neon / Heroku cấp postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Nếu là Supabase mà chưa có tham số sslmode -> tự động bổ sung sslmode=require để đảm bảo bảo mật SSL
if "supabase" in DATABASE_URL.lower() and "sslmode" not in DATABASE_URL.lower():
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"

# Tự động phát hiện môi trường Cloud (Render/Linux) hoặc khi không thể kết nối SQL Server localhost
is_cloud = bool(os.getenv("RENDER") or os.getenv("PORT") or sys.platform != "win32" or settings.ENVIRONMENT == "production")

# Nếu chạy trên Cloud mà DATABASE_URL vẫn trỏ vào localhost/SQLEXPRESS cục bộ -> VĂNG LỖI CẢNH BÁO
if is_cloud and ("localhost" in DATABASE_URL or "SQLEXPRESS" in DATABASE_URL or "127.0.0.1" in DATABASE_URL):
    logger.error("CRITICAL: Bạn đang chạy trên Cloud nhưng chưa cấu hình biến môi trường DATABASE_URL cho Supabase!")
    raise RuntimeError(
        "CRITICAL ERROR: Thiếu biến môi trường DATABASE_URL trên Render! "
        "App không thể kết nối tới SQL Server localhost từ Cloud. "
        "Vui lòng vào Render Dashboard > Environment và thêm biến DATABASE_URL trỏ tới Supabase."
    )

# Nếu cấu hình Remote SQL Server trên Linux qua pyodbc mà không có driver -> tự động chuyển sang pymssql
if is_cloud and "mssql+pyodbc" in DATABASE_URL:
    logger.info("Chuyển đổi driver mssql+pyodbc sang mssql+pymssql để tương thích môi trường Linux Cloud...")
    DATABASE_URL = DATABASE_URL.replace("mssql+pyodbc://", "mssql+pymssql://")
    if "?" in DATABASE_URL:
        base_part = DATABASE_URL.split("?")[0]
        DATABASE_URL = f"{base_part}?charset=utf8"

# Cấu hình engine linh hoạt cho MSSQL, PostgreSQL hoặc SQLite
connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False
}

if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "pyodbc" in DATABASE_URL:
    connect_args["timeout"] = 3
    engine_kwargs["pool_recycle"] = 300
elif "pymssql" in DATABASE_URL:
    connect_args["timeout"] = 5
    connect_args["charset"] = "utf8"
    engine_kwargs["pool_recycle"] = 300
elif "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL:
    connect_args["connect_timeout"] = 10
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine_kwargs["connect_args"] = connect_args

try:
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    # Thử kết nối nhanh
    with engine.connect() as conn:
        logger.info(f"Kết nối cơ sở dữ liệu thành công: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'Local SQL Server'}")
except Exception as e:
    target_clean = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    # Trên Cloud hoặc khi đã chỉ định PostgreSQL/Supabase: Văng lỗi ngay, không âm thầm fallback sang SQLite
    if is_cloud or "postgres" in DATABASE_URL.lower() or "supabase" in DATABASE_URL.lower():
        logger.error(f"CRITICAL ERROR: Không thể kết nối cơ sở dữ liệu ({target_clean}). Chi tiết: {e}")
        raise RuntimeError(
            f"CRITICAL: Không thể kết nối Database ({target_clean}). "
            f"Vui lòng kiểm tra lại biến môi trường DATABASE_URL trên Render! Chi tiết lỗi: {e}"
        )
    else:
        logger.warning(f"Không thể kết nối CSDL chính ({e}). Chế độ Local -> Chuyển sang SQLite dự phòng...")
        DATABASE_URL = f"sqlite:///{FALLBACK_DB_PATH}"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

