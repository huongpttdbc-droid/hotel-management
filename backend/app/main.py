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

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}

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
