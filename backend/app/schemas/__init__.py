from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# --- Auth Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    username: str
    role: str
    name: str
    ma: str
    chuc_vu: Optional[str] = "Lễ tân"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# --- Room Schemas ---
class LoaiPhongOut(BaseModel):
    MaLoaiPhong: str
    TenLoai: str
    SucChua: int
    DonGiaTheoGio: float
    DonGiaQuaDem: float
    DonGiaTheoNgay: float
    MoTa: Optional[str] = None

    class Config:
        from_attributes = True

class PhongOut(BaseModel):
    MaPhong: str
    SoPhong: str
    Tang: int
    TinhTrang: str
    MaLoaiPhong: str
    TenLoaiPhong: Optional[str] = None
    SucChua: Optional[int] = None
    DonGiaTheoNgay: Optional[float] = None
    KhachHienTai: Optional[str] = None
    MaPhieuThue: Optional[str] = None

    class Config:
        from_attributes = True

class PhongStatusUpdate(BaseModel):
    TinhTrang: str = Field(..., description="Trống, Đang thuê, Đang dọn, Bảo trì")

# --- Customer Schemas ---
class KhachHangOut(BaseModel):
    MaKH: str
    HoTen: str
    NgaySinh: date
    CCCD: str
    DiaChi: Optional[str] = None
    MaLoaiKH: str
    TenLoaiKH: Optional[str] = None
    PhanTramUuDai: Optional[float] = None
    SDT: Optional[str] = None

    class Config:
        from_attributes = True

class KhachHangCreate(BaseModel):
    MaKH: Optional[str] = None
    HoTen: str
    NgaySinh: date
    CCCD: str
    DiaChi: Optional[str] = None
    SDT: Optional[str] = None
    MaLoaiKH: Optional[str] = "LKH01"

# --- Rental Schemas ---
class ChiTietPhieuThueOut(BaseModel):
    STT: int
    MaPhong: str
    SoPhong: Optional[str] = None
    HinhThucThue: str
    DonGiaApDung: float
    SoNguoiDuKien: int
    GioNhan: datetime
    GioTraDuKien: datetime
    GioTra: Optional[datetime] = None

    class Config:
        from_attributes = True

class PhieuThueOut(BaseModel):
    MaPhieuThue: str
    NgayLap: datetime
    TrangThai: str
    MaKH: str
    TenKhachHang: Optional[str] = None
    MaNV: str
    ChiTiet: List[ChiTietPhieuThueOut] = []

    class Config:
        from_attributes = True

class PhieuThueCreate(BaseModel):
    MaKH: str
    MaPhong: str
    HinhThucThue: str = "Theo ngày"  # 'Theo giờ', 'Qua đêm', 'Theo ngày'
    SoNguoiDuKien: int = 1
    GioNhan: Optional[datetime] = None
    GioTraDuKien: Optional[datetime] = None
    GhiChu: Optional[str] = None
    MaNV: Optional[str] = "NV01"

# --- Service Schemas ---
class DichVuOut(BaseModel):
    MaDichVu: str
    TenDichVu: str
    DonViTinh: str
    DonGia: float
    MoTa: Optional[str] = None

    class Config:
        from_attributes = True

class DungDichVuCreate(BaseModel):
    MaPhieuThue: str
    STT: int = 1
    MaDichVu: str
    SoLuong: int = 1

class ChiTietDichVuHoaDon(BaseModel):
    TenDichVu: str
    DonViTinh: Optional[str] = None
    DonGia: float
    SoLuong: int
    ThanhTien: float

# --- Invoice & Stats Schemas ---
class HoaDonOut(BaseModel):
    MaHD: str
    MaPhieuThue: str
    MaNV: str
    NgayLap: datetime
    TienPhong: float
    TienDichVu: float
    TienPhuThu: float
    UuDai: float
    TyLeVAT: float
    TongTien: float
    TrangThai: str

    # Thông tin chi tiết mở rộng phục vụ xuất/in hóa đơn
    TenKhachHang: Optional[str] = None
    SoDienThoai: Optional[str] = None
    CCCD: Optional[str] = None
    DiaChi: Optional[str] = None
    TenLoaiKH: Optional[str] = None
    PhanTramUuDai: Optional[float] = None
    SoPhong: Optional[str] = None
    TenLoaiPhong: Optional[str] = None
    HinhThucThue: Optional[str] = None
    DonGiaApDung: Optional[float] = None
    GioNhan: Optional[datetime] = None
    GioTra: Optional[datetime] = None
    ThoiGianThue: Optional[str] = None
    NhanVienLap: Optional[str] = None
    ChiTietDichVu: List[ChiTietDichVuHoaDon] = []

    class Config:
        from_attributes = True

class ThongKeSummary(BaseModel):
    tong_phong: int
    phong_trong: int
    phong_dang_thue: int
    phong_dang_don: int
    phong_bao_tri: int
    tong_khach_hang: int
    doanh_thu_thang: float

