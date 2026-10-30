import os
import sys
import logging
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

# Nạp file .env ở máy local nếu có
load_dotenv()

logger = logging.getLogger("uvicorn.error")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALLBACK_DB_PATH = os.path.join(BASE_DIR, "hotel_fallback.db").replace("\\", "/")


def clean_and_normalize_database_url(raw_url: str):
    """
    Chuẩn hóa và làm sạch chuỗi kết nối Database theo chuẩn URI:
    1. Ghi log chẩn đoán an toàn (tuyệt đối không lộ username/password/host).
    2. Bóc tách dấu nháy thừa (' / "), tiền tố copy nhầm (DATABASE_URL=, export, psql), ký tự ngắt dòng.
    3. Bảo toàn nguyên vẹn chuỗi kết nối SQL Server & SQLite cục bộ khi chạy local.
    4. Kiểm tra protocol: nếu thiếu scheme (postgresql:// hoặc postgres://), báo lỗi cấu hình rõ ràng, không tự ý đoán.
    5. Sử dụng urllib.parse.urlsplit để phân tích chuẩn URI.
    6. Sử dụng urllib.parse.unquote để giải mã username/password đã URL-encode đúng một lần.
    7. Sử dụng sqlalchemy.engine.URL.create() để tạo đối tượng URL hợp lệ với driver postgresql+psycopg2.
    8. Bảo toàn và đảm bảo tham số sslmode=require khi kết nối Supabase Cloud.
    """
    if not raw_url:
        return raw_url

    # 1. Ghi log chẩn đoán an toàn
    has_quotes = raw_url.startswith(('"', "'")) or raw_url.endswith(('"', "'"))
    has_newlines = "\n" in raw_url or "\r" in raw_url
    has_prefix = any(raw_url.lstrip().startswith(p) for p in ("DATABASE_URL=", "DATABASE_URL:", "export ", "psql "))
    raw_scheme = raw_url.split("://")[0].strip("\"' ") if "://" in raw_url else "none"

    logger.info(
        f"[DB Diagnostic] Kiểm tra cấu hình DATABASE_URL: "
        f"scheme='{raw_scheme}', "
        f"has_quotes={has_quotes}, "
        f"has_prefix={has_prefix}, "
        f"has_newlines={has_newlines}"
    )

    # 2. Làm sạch dấu nháy và khoảng trắng thừa ở 2 đầu
    url = raw_url.strip()
    for prefix in ("export ", "DATABASE_URL=", "DATABASE_URL:", "psql "):
        if url.startswith(prefix):
            url = url[len(prefix):].strip()

    while (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()

    url = url.strip("\"' \t\r\n;")

    # 3. Nếu là SQLite hoặc SQL Server local -> Giữ nguyên vẹn
    if any(k in url.lower() for k in ("sqlite", "mssql", "sqlserver", "trusted_connection")):
        return url

    # 4. Kiểm tra protocol: Không tự động thêm protocol nếu thiếu -> Báo lỗi cấu hình rõ ràng
    if not (url.startswith("postgresql://") or url.startswith("postgres://") or url.startswith("postgresql+psycopg2://")):
        raise ValueError(
            "Cấu hình DATABASE_URL không hợp lệ: thiếu scheme 'postgresql://' hoặc 'postgres://'. "
            "Vui lòng kiểm tra lại biến môi trường DATABASE_URL trên Render (đảm bảo dán đúng chuỗi URI đầy đủ từ Supabase)."
        )

    # 5. Dùng urllib.parse.urlsplit để phân tích chuẩn URI
    parse_target = url
    if parse_target.startswith("postgres://"):
        parse_target = "postgresql://" + parse_target[len("postgres://"):]
    elif parse_target.startswith("postgresql+psycopg2://"):
        parse_target = "postgresql://" + parse_target[len("postgresql+psycopg2://"):]

    split_res = urllib.parse.urlsplit(parse_target)

    # 6. Dùng urllib.parse.unquote để giải mã username/password đã URL-encode đúng một lần
    raw_user = urllib.parse.unquote(split_res.username) if split_res.username else None
    raw_pass = urllib.parse.unquote(split_res.password) if split_res.password else None

    # Cảnh báo an toàn nếu người dùng quên thay thế placeholder
    if raw_pass and ("YOUR-PASSWORD" in raw_pass.upper() or "YOUR_PASSWORD" in raw_pass.upper()):
        logger.warning(
            "CẢNH BÁO: Phát hiện placeholder [YOUR-PASSWORD] chưa được thay thế trong DATABASE_URL! "
            "Vui lòng thay thế bằng mật khẩu Supabase thật của bạn."
        )

    # 7. Query parameters & sslmode=require
    query_params = dict(urllib.parse.parse_qsl(split_res.query, keep_blank_values=True))
    host_str = split_res.hostname or ""
    if "supabase" in host_str.lower() or "supabase" in url.lower():
        if "sslmode" not in query_params:
            query_params["sslmode"] = "require"

    database_name = split_res.path.lstrip("/") if split_res.path else "postgres"

    # 8. Dùng sqlalchemy.engine.URL.create() để tạo đối tượng URL chuẩn xác
    url_obj = URL.create(
        drivername="postgresql+psycopg2",
        username=raw_user,
        password=raw_pass,
        host=split_res.hostname,
        port=split_res.port,
        database=database_name or None,
        query=query_params
    )

    return url_obj


def get_masked_url(target) -> str:
    """Ẩn mật khẩu khi ghi log hoặc hiển thị thông báo lỗi để đảm bảo an toàn thông tin."""
    if isinstance(target, URL):
        return target.render_as_string(hide_password=True)
    try:
        return make_url(target).render_as_string(hide_password=True)
    except Exception:
        target_str = str(target)
        if "@" in target_str:
            proto = target_str.split("://")[0] if "://" in target_str else ""
            host = target_str.split("@")[-1]
            return f"{proto}://***@{host}"
        return target_str


# Đọc DATABASE_URL từ biến môi trường (ưu tiên Render) hoặc cấu hình settings
RAW_DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SUPABASE_DB_URL")
    or os.getenv("SUPABASE_DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRESQL_URL")
    or settings.DATABASE_URL
    or ""
)

# Chuẩn hóa URL
normalized_target = clean_and_normalize_database_url(RAW_DATABASE_URL)

if isinstance(normalized_target, URL):
    TARGET_ENGINE_URL = normalized_target
    DATABASE_URL = normalized_target.render_as_string(hide_password=False)
else:
    TARGET_ENGINE_URL = normalized_target
    DATABASE_URL = str(normalized_target)

MASKED_DATABASE_URL = get_masked_url(TARGET_ENGINE_URL)

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
    TARGET_ENGINE_URL = DATABASE_URL
    MASKED_DATABASE_URL = get_masked_url(TARGET_ENGINE_URL)

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
    engine = create_engine(TARGET_ENGINE_URL, **engine_kwargs)
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
        TARGET_ENGINE_URL = DATABASE_URL
        MASKED_DATABASE_URL = DATABASE_URL
        engine = create_engine(TARGET_ENGINE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
