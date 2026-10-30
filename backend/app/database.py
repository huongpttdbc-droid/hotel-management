import os
import sys
import logging
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

# Nạp file .env ở máy local
load_dotenv()

logger = logging.getLogger("uvicorn.error")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALLBACK_DB_PATH = os.path.join(BASE_DIR, "hotel_fallback.db").replace("\\", "/")


def clean_and_normalize_database_url(raw_url: str) -> str:
    """
    Chuẩn hóa và làm sạch triệt để chuỗi kết nối Database:
    1. Bóc tách dấu nháy đơn/kép (' / "), tiền tố thừa (psql, export, DATABASE_URL=), khoảng trắng, xuống dòng.
    2. Bảo toàn nguyên vẹn chuỗi kết nối SQL Server & SQLite cục bộ khi chạy local.
    3. Chuẩn hóa driver PostgreSQL sang postgresql+psycopg2://.
    4. Xử lý an toàn mật khẩu có ký tự đặc biệt (@, #, :, /, ?, %, [, ]) mà không gây double-encode.
    5. Kiểm tra tính hợp lệ bằng sqlalchemy.engine.make_url.
    6. Đảm bảo tham số sslmode=require khi kết nối Supabase Cloud.
    """
    if not raw_url:
        return raw_url

    url = raw_url.strip()

    # 1. Loại bỏ tiền tố terminal/bash nếu người dùng copy nhầm
    for prefix in ("export ", "DATABASE_URL=", "psql "):
        if url.startswith(prefix):
            url = url[len(prefix):].strip()

    # 2. Bóc tách triệt để dấu ngoặc kép hoặc ngoặc đơn bao quanh chuỗi
    while (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()

    # Xóa ký tự quote, dấu chấm phẩy, khoảng trắng bị lệch ở đầu/đuôi
    url = url.strip("\"' \t\r\n;")

    # 3. Nếu là SQLite hoặc SQL Server -> Giữ nguyên vẹn cấu trúc
    if "sqlite" in url or "mssql" in url or "sqlserver" in url:
        return url

    # 4. Chuẩn hóa schema/protocol sang postgresql+psycopg2
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]

    # 5. Xử lý an toàn user/password nếu có ký tự đặc biệt
    if "://" in url and "@" in url:
        proto, rest = url.split("://", 1)
        # Tách ở dấu '@' CUỐI CÙNG trước host để tránh bị nhầm lẫn nếu mật khẩu chứa ký tự '@'
        creds, host_part = rest.rsplit("@", 1)

        if ":" in creds:
            username, password = creds.split(":", 1)

            # Cảnh báo nếu người dùng quên thay thế placeholder
            if "YOUR-PASSWORD" in password.upper() or "YOUR_PASSWORD" in password.upper():
                logger.warning(
                    "CẢNH BÁO: Phát hiện placeholder [YOUR-PASSWORD] chưa thay thế trong DATABASE_URL! "
                    "Vui lòng thay thế bằng mật khẩu Supabase thật của bạn."
                )

            # Tránh double encoding: unquote trước (nếu chuỗi đã encode), sau đó encode an toàn
            decoded_password = urllib.parse.unquote(password)
            encoded_password = urllib.parse.quote(decoded_password, safe="")

            decoded_username = urllib.parse.unquote(username)
            encoded_username = urllib.parse.quote(decoded_username, safe=".-_")

            url = f"{proto}://{encoded_username}:{encoded_password}@{host_part}"

    # 6. Parse và validate bằng sqlalchemy.engine.make_url
    url_obj = make_url(url)

    # 7. Đảm bảo drivername chuẩn cho psycopg2
    if url_obj.drivername in ("postgres", "postgresql"):
        url_obj = url_obj.set(drivername="postgresql+psycopg2")

    # 8. Đảm bảo sslmode=require khi kết nối Supabase Cloud
    host_str = url_obj.host or ""
    query_params = dict(url_obj.query)
    if "supabase" in host_str.lower() or "supabase" in raw_url.lower():
        if "sslmode" not in query_params:
            query_params["sslmode"] = "require"
            url_obj = url_obj.set(query=query_params)

    return url_obj.render_as_string(hide_password=False)


def get_masked_url(url: str) -> str:
    """Ẩn mật khẩu khi ghi log hoặc hiển thị thông báo lỗi để đảm bảo an toàn thông tin."""
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        if "@" in url:
            proto = url.split("://")[0] if "://" in url else ""
            host = url.split("@")[-1]
            return f"{proto}://***@{host}"
        return url


# Đọc DATABASE_URL từ biến môi trường hoặc cấu hình settings
RAW_DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SUPABASE_DB_URL")
    or os.getenv("SUPABASE_DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRESQL_URL")
    or settings.DATABASE_URL
    or ""
)

DATABASE_URL = clean_and_normalize_database_url(RAW_DATABASE_URL)
MASKED_DATABASE_URL = get_masked_url(DATABASE_URL)

# Tự động phát hiện môi trường Cloud (Render/Linux)
is_cloud = bool(
    os.getenv("RENDER")
    or sys.platform != "win32"
    or settings.ENVIRONMENT == "production"
)

# Nếu chạy trên Cloud mà DATABASE_URL vẫn trỏ vào localhost/SQLEXPRESS cục bộ -> VĂNG LỖI CẢNH BÁO
if is_cloud and ("localhost" in DATABASE_URL or "SQLEXPRESS" in DATABASE_URL or "127.0.0.1" in DATABASE_URL):
    logger.error("CRITICAL: Bạn đang chạy trên Cloud nhưng chưa cấu hình biến môi trường DATABASE_URL cho Supabase!")
    raise RuntimeError(
        "CRITICAL ERROR: Thiếu biến môi trường DATABASE_URL trên Render! "
        "App không thể kết nối tới SQL Server localhost từ Cloud. "
        "Vui lòng vào Render Dashboard > Environment và thêm biến DATABASE_URL trỏ tới Supabase Singapore."
    )

# Nếu cấu hình Remote SQL Server trên Linux qua pyodbc mà không có driver -> tự động chuyển sang pymssql
if is_cloud and "mssql+pyodbc" in DATABASE_URL:
    logger.info("Chuyển đổi driver mssql+pyodbc sang mssql+pymssql để tương thích môi trường Linux Cloud...")
    DATABASE_URL = DATABASE_URL.replace("mssql+pyodbc://", "mssql+pymssql://")
    if "?" in DATABASE_URL:
        base_part = DATABASE_URL.split("?")[0]
        DATABASE_URL = f"{base_part}?charset=utf8"
    MASKED_DATABASE_URL = get_masked_url(DATABASE_URL)

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
    with engine.connect() as conn:
        logger.info(f"Kết nối cơ sở dữ liệu thành công: {MASKED_DATABASE_URL}")
except Exception as e:
    # Trên Cloud hoặc khi đã chỉ định PostgreSQL/Supabase: Văng lỗi rõ ràng, không âm thầm fallback sang SQLite
    if is_cloud or "postgres" in DATABASE_URL.lower() or "supabase" in DATABASE_URL.lower():
        logger.error(f"CRITICAL ERROR: Không thể kết nối cơ sở dữ liệu ({MASKED_DATABASE_URL}). Chi tiết: {e}")
        raise RuntimeError(
            f"CRITICAL: Không thể kết nối Database ({MASKED_DATABASE_URL}). "
            f"Vui lòng kiểm tra lại biến môi trường DATABASE_URL trên Render! Chi tiết lỗi: {e}"
        )
    else:
        logger.warning(f"Không thể kết nối CSDL chính ({e}). Chế độ Local -> Chuyển sang SQLite dự phòng...")
        DATABASE_URL = f"sqlite:///{FALLBACK_DB_PATH}"
        MASKED_DATABASE_URL = DATABASE_URL
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
