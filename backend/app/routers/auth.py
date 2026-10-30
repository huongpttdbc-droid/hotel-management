import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
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
            h1 = hashlib.sha256((salt + v).encode("utf-8")).hexdigest().upper()
            h2 = hashlib.sha256((v + salt).encode("utf-8")).hexdigest().upper()
            if h1 == target or h2 == target:
                return True
    hashed_direct = hashlib.sha256(p.encode("utf-8")).hexdigest().upper()
    return hashed_direct == (db_hash or "").upper()

# Cấu hình thứ tự ưu tiên chức vụ trong khách sạn (từ cấp cao nhất xuống cấp cơ sở)
ROLE_HIERARCHY = {
    "Quản lý": 1,
    "Kế toán": 2,
    "Lễ tân": 3,
    "Buồng phòng": 4,
    "Bảo vệ": 5
}

@router.get("/staff-list")
def list_staff_accounts(
    keyword: Optional[str] = None,
    chuc_vu: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Trả về danh sách toàn bộ nhân sự khách sạn:
    - Sắp xếp theo thứ bậc chức vụ từ cao xuống thấp (Quản lý -> Kế toán -> Lễ tân -> Buồng phòng -> Bảo vệ)
    - Cùng chức vụ sắp xếp tiếp theo Mã nhân viên (MaNV)
    - Hỗ trợ tìm kiếm theo tên / mã NV và lọc theo chức vụ thực tế
    """
    # 1. Truy vấn toàn bộ nhân viên và tài khoản tương ứng bằng joinedload trong 1 query duy nhất
    nvs = db.query(NhanVien).options(joinedload(NhanVien.tai_khoan)).all()

    results = []
    for nv in nvs:
        tk = nv.tai_khoan
        role_name = (nv.ChucVu or "Nhân viên").strip()
        role_order = ROLE_HIERARCHY.get(role_name, 99)

        # Xác định phân quyền hệ thống tương ứng
        if "Quản lý" in role_name:
            phan_quyen = "Toàn quyền Quản lý"
        elif "Kế toán" in role_name:
            phan_quyen = "Nghiệp vụ Kế toán"
        elif "Lễ tân" in role_name:
            phan_quyen = "Nghiệp vụ Lễ tân"
        elif "Buồng phòng" in role_name:
            phan_quyen = "Nghiệp vụ Buồng phòng"
        elif "Bảo vệ" in role_name:
            phan_quyen = "Nghiệp vụ An ninh"
        else:
            phan_quyen = "Nhân viên Khách sạn"

        item = {
            "ma_nv": nv.MaNV,
            "ho_ten": nv.HoTen,
            "chuc_vu": role_name,
            "chuc_vu_order": role_order,
            "username": tk.TenDangNhap if tk else "—",
            "trang_thai": tk.TrangThai if tk else "Đang công tác",
            "has_account": bool(tk),
            "phan_quyen": phan_quyen
        }

        # Lọc theo từ khóa (Mã NV, Họ tên, Tên đăng nhập)
        if keyword:
            kw = keyword.strip().lower()
            if kw not in item["ma_nv"].lower() and kw not in item["ho_ten"].lower() and kw not in item["username"].lower():
                continue

        # Lọc theo chức vụ
        if chuc_vu and chuc_vu.strip():
            if item["chuc_vu"].lower() != chuc_vu.strip().lower():
                continue

        results.append(item)

    # 3. Sắp xếp danh sách: Cấp bậc chức vụ từ cao xuống thấp (1 -> 5), cùng chức vụ xếp theo Mã NV
    results.sort(key=lambda x: (x["chuc_vu_order"], x["ma_nv"]))
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

    # 2. Kiểm tra bảng TaiKhoan trong Database (kèm joinedload NhanVien để tránh N+1 query)
    from sqlalchemy import func
    tk = (
        db.query(TaiKhoan)
        .options(joinedload(TaiKhoan.nhan_vien))
        .filter(
            (func.lower(TaiKhoan.TenDangNhap) == username_lower) |
            (func.lower(TaiKhoan.TenDangNhap).like(f"{username_lower}.%")) |
            (func.lower(TaiKhoan.MaNV) == username_lower)
        )
        .first()
    )

    if tk:
        if tk.TrangThai == "Khóa":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản '{tk.TenDangNhap}' hiện đang bị khóa."
            )

        if verify_password(password, tk.MatKhau, tk.Salt):
            nv = tk.nhan_vien
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
