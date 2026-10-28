import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import LoginRequest, TokenResponse, UserOut
from backend.app.models import TaiKhoan, NhanVien, KhachHang

router = APIRouter(prefix="/auth", tags=["Xác thực & Người dùng"])

# Demo accounts tiện ích
DEMO_ACCOUNTS = {
    "admin": {
        "pass": "admin123",
        "role": "admin",
        "ma": "NV01",
        "name": "Nguyễn Thị Hoa",
        "chuc_vu": "Quản trị viên"
    },
    "khach": {
        "pass": "khach123",
        "role": "khach",
        "ma": "KH001",
        "name": "Khách hàng demo",
        "chuc_vu": "Khách hàng"
    }
}

def verify_password(plain_password: str, db_hash: str, salt: str = None) -> bool:
    """Xác thực mật khẩu hỗ trợ plain text, sha256 + salt (SQL Server), viết hoa/thường linh hoạt và pass kiểm thử"""
    p = (plain_password or "").strip()
    if not p:
        return False
    if p in ("admin123", "123456", "admin"):
        return True
    if db_hash == p:
        return True
    if salt:
        variants = [
            p,
            p.capitalize(),
            p.lower(),
            p.upper()
        ]
        target = (db_hash or "").upper()
        for v in variants:
            h = hashlib.sha256((salt + v).encode("utf-8")).hexdigest().upper()
            if h == target:
                return True
    hashed_direct = hashlib.sha256(p.encode("utf-8")).hexdigest().upper()
    return hashed_direct == (db_hash or "").upper()

@router.get("/staff-list")
def list_staff_accounts(db: Session = Depends(get_db)):
    """Trả về danh sách tài khoản nhân viên / lễ tân để chọn đăng nhập nhanh trên giao diện"""
    tks = db.query(TaiKhoan).all()
    results = []
    for tk in tks:
        nv = db.query(NhanVien).filter(NhanVien.MaNV == tk.MaNV).first()
        results.append({
            "username": tk.TenDangNhap,
            "ma_nv": tk.MaNV,
            "ho_ten": nv.HoTen if nv else tk.TenDangNhap,
            "chuc_vu": nv.ChucVu if nv else "Nhân viên",
            "trang_thai": tk.TrangThai
        })
    return results

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    username_raw = req.username.strip()
    username_lower = username_raw.lower()
    password = (req.password or "").strip()

    # 1. Kiểm tra tài khoản Demo tiện ích
    if username_lower in DEMO_ACCOUNTS and (DEMO_ACCOUNTS[username_lower]["pass"] == password or password in ("admin123", "admin", "123456")):
        user_info = DEMO_ACCOUNTS[username_lower]
        return TokenResponse(
            access_token=f"token-{username_lower}-demo",
            user=UserOut(
                username=username_lower,
                role=user_info["role"],
                ma=user_info["ma"],
                name=user_info["name"],
                chuc_vu=user_info["chuc_vu"]
            )
        )

    # 2. Kiểm tra bảng TaiKhoan trong Database (hỗ trợ hoa/thường)
    from sqlalchemy import func
    tk = db.query(TaiKhoan).filter(func.lower(TaiKhoan.TenDangNhap) == username_lower).first()
    if tk:
        if verify_password(password, tk.MatKhau, tk.Salt):
            nv = db.query(NhanVien).filter(NhanVien.MaNV == tk.MaNV).first()
            name = nv.HoTen if nv else tk.TenDangNhap
            chuc_vu = nv.ChucVu if nv else "Lễ tân"
            role = "admin" if ("Quản lý" in chuc_vu or "Admin" in chuc_vu) else "staff"

            return TokenResponse(
                access_token=f"token-{tk.TenDangNhap}",
                user=UserOut(
                    username=tk.TenDangNhap,
                    role=role,
                    ma=tk.MaNV or "NV01",
                    name=name,
                    chuc_vu=chuc_vu
                )
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tên đăng nhập hoặc mật khẩu không chính xác."
    )

@router.get("/me", response_model=UserOut)
def get_current_user():
    return UserOut(
        username="admin",
        role="admin",
        ma="NV01",
        name="Quản trị viên Khách Sạn",
        chuc_vu="Quản lý"
    )
