import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

logger = logging.getLogger("uvicorn.error")

DATABASE_URL = settings.DATABASE_URL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALLBACK_DB_PATH = os.path.join(BASE_DIR, "hotel_fallback.db").replace("\\", "/")

# Tự động chuẩn hóa chuỗi kết nối Cloud PostgreSQL (Render / Supabase / Neon / Heroku cấp postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Tự động phát hiện môi trường Cloud (Render/Linux) hoặc khi không thể kết nối SQL Server localhost
is_cloud = bool(os.getenv("RENDER") or os.getenv("PORT") or sys.platform != "win32" or settings.ENVIRONMENT == "production")

# Nếu chạy trên Cloud mà DATABASE_URL vẫn trỏ vào localhost/SQLEXPRESS cục bộ -> tự động dùng SQLite dự phòng
if is_cloud and ("localhost" in DATABASE_URL or "SQLEXPRESS" in DATABASE_URL or "127.0.0.1" in DATABASE_URL):
    logger.warning("Phát hiện môi trường Cloud nhưng DATABASE_URL vẫn trỏ về localhost SQL Server. Kích hoạt SQLite dự phòng...")
    DATABASE_URL = f"sqlite:///{FALLBACK_DB_PATH}"

# Nếu cấu hình Remote SQL Server trên Linux qua pyodbc mà không có driver -> tự động chuyển sang pymssql
if is_cloud and "mssql+pyodbc" in DATABASE_URL:
    logger.info("Chuyển đổi driver mssql+pyodbc sang mssql+pymssql để tương thích môi trường Linux Cloud...")
    DATABASE_URL = DATABASE_URL.replace("mssql+pyodbc://", "mssql+pymssql://")
    if "?" in DATABASE_URL:
        base_part = DATABASE_URL.split("?")[0]
        DATABASE_URL = f"{base_part}?charset=utf8"

# Cấu hình engine linh hoạt cho MSSQL, PostgreSQL hoặc SQLite
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "pyodbc" in DATABASE_URL:
    connect_args["timeout"] = 3
elif "pymssql" in DATABASE_URL:
    connect_args["timeout"] = 5
    connect_args["charset"] = "utf8"

try:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=False
    )
    # Thử kết nối nhanh
    with engine.connect() as conn:
        logger.info(f"Kết nối cơ sở dữ liệu thành công: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'Local SQL Server'}")
except Exception as e:
    logger.warning(f"Không thể kết nối CSDL chính ({e}). Chuyển sang dùng SQLite dự phòng...")
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

