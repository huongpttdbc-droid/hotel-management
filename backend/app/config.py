import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "QuanLyKhachSan API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Kết nối trực tiếp vào SQL Server cục bộ hoặc Cloud qua DATABASE_URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mssql+pyodbc://localhost\\SQLEXPRESS01/QuanLyKhachSan?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Trusted_Connection=yes"
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "hotel-management-secret-key-2026")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", 8000))

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
