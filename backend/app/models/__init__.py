from sqlalchemy import (
    Column, String, Unicode, Integer, SmallInteger, Numeric, Date, DateTime, Boolean, ForeignKey, ForeignKeyConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

class LoaiKhachHang(Base):
    __tablename__ = "LoaiKhachHang"
    
    MaLoaiKH = Column(String(10), primary_key=True)
    TenLoai = Column(Unicode(50), nullable=False, unique=True)
    PhanTramUuDai = Column(Numeric(5, 2, asdecimal=False), default=0.0)

    khach_hangs = relationship("KhachHang", back_populates="loai_khach_hang")


class KhachHang(Base):
    __tablename__ = "KhachHang"
    
    MaKH = Column(String(10), primary_key=True)
    HoTen = Column(Unicode(100), nullable=False)
    NgaySinh = Column(Date, nullable=False)
    CCCD = Column(String(12), nullable=False, unique=True)
    DiaChi = Column(Unicode(200), nullable=True)
    MaLoaiKH = Column(String(10), ForeignKey("LoaiKhachHang.MaLoaiKH"), nullable=False, default="LKH01")

    loai_khach_hang = relationship("LoaiKhachHang", back_populates="khach_hangs")
    so_dien_thoai = relationship("KhachHangSDT", back_populates="khach_hang")
    phieu_thues = relationship("PhieuThue", back_populates="khach_hang")


class KhachHangSDT(Base):
    __tablename__ = "KhachHang_SDT"
    
    MaKH = Column(String(10), ForeignKey("KhachHang.MaKH"), primary_key=True)
    SDT = Column(String(15), primary_key=True)

    khach_hang = relationship("KhachHang", back_populates="so_dien_thoai")


class NhanVien(Base):
    __tablename__ = "NhanVien"
    
    MaNV = Column(String(10), primary_key=True)
    HoTen = Column(Unicode(100), nullable=False)
    ChucVu = Column(Unicode(50), nullable=False)

    tai_khoan = relationship("TaiKhoan", back_populates="nhan_vien", uselist=False)


class TaiKhoan(Base):
    __tablename__ = "TaiKhoan"
    
    TenDangNhap = Column(String(50), primary_key=True)
    MatKhau = Column(String(255), nullable=False)
    Salt = Column(String(32), nullable=False)
    TrangThai = Column(Unicode(20), nullable=False, default="Hoạt động")
    MaNV = Column(String(10), ForeignKey("NhanVien.MaNV"), nullable=False, unique=True)

    nhan_vien = relationship("NhanVien", back_populates="tai_khoan")


class LoaiPhong(Base):
    __tablename__ = "LoaiPhong"
    
    MaLoaiPhong = Column(String(10), primary_key=True)
    TenLoai = Column(Unicode(50), nullable=False, unique=True)
    SucChua = Column(SmallInteger, nullable=False)
    DonGiaTheoGio = Column(Numeric(12, 0, asdecimal=False), default=0)
    DonGiaQuaDem = Column(Numeric(12, 0, asdecimal=False), default=0)
    DonGiaTheoNgay = Column(Numeric(12, 0, asdecimal=False), default=0)
    MoTa = Column(Unicode(500), nullable=True)

    phongs = relationship("Phong", back_populates="loai_phong")


class Phong(Base):
    __tablename__ = "Phong"
    
    MaPhong = Column(String(10), primary_key=True)
    SoPhong = Column(String(10), nullable=False, unique=True)
    Tang = Column(SmallInteger, nullable=False)
    TinhTrang = Column(Unicode(20), nullable=False, default="Trống")
    MaLoaiPhong = Column(String(10), ForeignKey("LoaiPhong.MaLoaiPhong"), nullable=False)

    loai_phong = relationship("LoaiPhong", back_populates="phongs")


class PhieuThue(Base):
    __tablename__ = "PhieuThue"
    
    MaPhieuThue = Column(String(12), primary_key=True)
    NgayLap = Column(DateTime, nullable=False)
    TrangThai = Column(Unicode(20), nullable=False, default="Đã đặt")
    MaKH = Column(String(10), ForeignKey("KhachHang.MaKH"), nullable=False)
    MaNV = Column(String(10), ForeignKey("NhanVien.MaNV"), nullable=False)

    khach_hang = relationship("KhachHang", back_populates="phieu_thues")
    chi_tiet = relationship("ChiTietPhieuThue", back_populates="phieu_thue")
    hoa_don = relationship("HoaDon", back_populates="phieu_thue", uselist=False)


class ChiTietPhieuThue(Base):
    __tablename__ = "ChiTietPhieuThue"
    
    MaPhieuThue = Column(String(12), ForeignKey("PhieuThue.MaPhieuThue"), primary_key=True)
    STT = Column(Integer, primary_key=True)
    MaPhong = Column(String(10), ForeignKey("Phong.MaPhong"), nullable=False)
    HinhThucThue = Column(Unicode(20), nullable=False)
    DonGiaApDung = Column(Numeric(12, 0, asdecimal=False), nullable=False)
    SoNguoiDuKien = Column(SmallInteger, default=1)
    KhachDatCoOPhongNay = Column(Boolean, default=True)
    GioNhan = Column(DateTime, nullable=False)
    GioTraDuKien = Column(DateTime, nullable=False)
    GioTra = Column(DateTime, nullable=True)
    GhiChu = Column(Unicode(500), nullable=True)

    phieu_thue = relationship("PhieuThue", back_populates="chi_tiet")
    phong = relationship("Phong")


class DichVu(Base):
    __tablename__ = "DichVu"
    
    MaDichVu = Column(String(10), primary_key=True)
    TenDichVu = Column(Unicode(100), nullable=False, unique=True)
    MoTa = Column(Unicode(500), nullable=True)
    DonViTinh = Column(Unicode(20), nullable=False)
    DonGia = Column(Numeric(12, 0, asdecimal=False), nullable=False)


class DungDichVu(Base):
    __tablename__ = "DungDichVu"
    
    MaPhieuThue = Column(String(12), primary_key=True)
    STT = Column(Integer, primary_key=True)
    MaDichVu = Column(String(10), ForeignKey("DichVu.MaDichVu"), primary_key=True)
    GioBD = Column(DateTime, primary_key=True)
    GioKT = Column(DateTime, nullable=True)
    SoLuong = Column(Integer, default=1)
    DonGiaApDung = Column(Numeric(12, 0, asdecimal=False), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["MaPhieuThue", "STT"],
            ["ChiTietPhieuThue.MaPhieuThue", "ChiTietPhieuThue.STT"],
        ),
    )

    dich_vu = relationship("DichVu")


class HoaDon(Base):
    __tablename__ = "HoaDon"
    
    MaHD = Column(String(12), primary_key=True)
    MaPhieuThue = Column(String(12), ForeignKey("PhieuThue.MaPhieuThue"), nullable=False, unique=True)
    MaNV = Column(String(10), ForeignKey("NhanVien.MaNV"), nullable=False)
    NgayLap = Column(DateTime, nullable=False)
    TienPhong = Column(Numeric(14, 0, asdecimal=False), default=0)
    TienDichVu = Column(Numeric(14, 0, asdecimal=False), default=0)
    TienPhuThu = Column(Numeric(14, 0, asdecimal=False), default=0)
    UuDai = Column(Numeric(14, 0, asdecimal=False), default=0)
    TyLeVAT = Column(Numeric(5, 2, asdecimal=False), default=10)
    TrangThai = Column(Unicode(20), default="Chưa thanh toán")

    phieu_thue = relationship("PhieuThue", back_populates="hoa_don")


class ThanhToan(Base):
    __tablename__ = "ThanhToan"

    MaThanhToan = Column(String(10), primary_key=True)
    MaPhieuThue = Column(String(12), ForeignKey("PhieuThue.MaPhieuThue"), nullable=False)
    MaNV = Column(String(10), ForeignKey("NhanVien.MaNV"), nullable=False)
    NgayGioThanhToan = Column(DateTime, nullable=False)
    PhuongThuc = Column(Unicode(20), nullable=False, default="Tiền mặt")
    SoTien = Column(Numeric(14, 0, asdecimal=False), nullable=False)
    LoaiKhoan = Column(Unicode(20), nullable=False, default="Thanh toán")

    phieu_thue = relationship("PhieuThue")
    nhan_vien = relationship("NhanVien")
