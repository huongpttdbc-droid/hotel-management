import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

logger = logging.getLogger("uvicorn.error")

DATABASE_URL = settings.DATABASE_URL

# Nếu chạy trên môi trường Cloud (Render) hoặc DATABASE_URL vẫn trỏ localhost mà không có SQL Server
if settings.ENVIRONMENT == "production" and ("localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL):
    DATABASE_URL = "sqlite:///./hotel_fallback.db"

# Cấu hình engine linh hoạt cho MSSQL, PostgreSQL hoặc SQLite
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "pyodbc" in DATABASE_URL:
    connect_args["timeout"] = 2

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
    logger.warning(f"Không thể kết nối SQL Server ({e}). Chuyển sang dùng SQLite dự phòng cho môi trường Cloud/Offline...")
    DATABASE_URL = "sqlite:///./hotel_fallback.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

