import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from backend.app.config import settings
from backend.app.routers import auth, phong, khach_hang, phieu_thue, dich_vu, hoa_don, thong_ke

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API Hệ Thống Quản Lý Khách Sạn (kết nối SQL Server & sẵn sàng deploy lên Render / Railway / Netlify)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cấu hình CORS mở cho mọi nguồn (Frontend Render, Netlify, Localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn các Routers API
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(phong.router, prefix=settings.API_V1_STR)
app.include_router(khach_hang.router, prefix=settings.API_V1_STR)
app.include_router(phieu_thue.router, prefix=settings.API_V1_STR)
app.include_router(dich_vu.router, prefix=settings.API_V1_STR)
app.include_router(hoa_don.router, prefix=settings.API_V1_STR)
app.include_router(thong_ke.router, prefix=settings.API_V1_STR)

from backend.app.database import DATABASE_URL, engine

@app.on_event("startup")
def on_startup():
    try:
        from backend.app.database import Base
        import backend.app.models  # Nạp toàn bộ models để tạo bảng tự động nếu là DB mới
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("Startup metadata create_all notice:", e)

@app.get("/api/health")
def health_check():
    url_lower = DATABASE_URL.lower()
    is_sqlite = "sqlite" in url_lower
    is_postgres = "postgres" in url_lower
    is_mssql = "mssql" in url_lower

    if is_sqlite:
        db_type = "SQLite Fallback (hotel_fallback.db)"
        server_info = "Local SQLite"
    elif is_postgres:
        db_type = "PostgreSQL (Cloud / Supabase / Neon / Render)"
        server_info = DATABASE_URL.split("@")[-1].split("?")[0] if "@" in DATABASE_URL else "PostgreSQL Cloud"
    elif is_mssql:
        db_type = "Microsoft SQL Server"
        server_info = DATABASE_URL.split("@")[-1].split("?")[0] if "@" in DATABASE_URL else "Local SQL Server"
    else:
        db_type = "Database Engine"
        server_info = DATABASE_URL.split("@")[-1].split("?")[0] if "@" in DATABASE_URL else "Unknown"

    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": {
            "type": db_type,
            "server": server_info,
            "is_sqlite_fallback": is_sqlite
        }
    }

# Phục vụ thư mục Frontend (HTML, CSS, JS, Ảnh) trực tiếp tại máy và Render
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# Handler Serverless cho Netlify Functions / AWS Lambda
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
