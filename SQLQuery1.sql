/* ============================================================================
   QuanLyKhachSan - Tạo CSDL + Dữ liệu mẫu (Bản hoàn chỉnh đã sửa lỗi)
   ============================================================================ */

USE master;
GO

-- Đặt @Reset = 1 để tự động xóa và tái tạo CSDL sạch sẽ từ đầu
DECLARE @Reset BIT = 1;

IF DB_ID(N'QuanLyKhachSan') IS NOT NULL
BEGIN
    IF @Reset = 1
    BEGIN
        ALTER DATABASE QuanLyKhachSan SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
        DROP DATABASE QuanLyKhachSan;
    END
    ELSE
    BEGIN
        RAISERROR(N'Database QuanLyKhachSan đã tồn tại. Đặt @Reset = 1 ở đầu script nếu muốn xóa và tạo lại.', 16, 1);
        SET NOEXEC ON;
    END
END
GO

IF DB_ID(N'QuanLyKhachSan') IS NULL
    CREATE DATABASE QuanLyKhachSan;
GO

USE QuanLyKhachSan;
GO

/* ============================================================================
   HÀM HỖ TRỢ KIỂM TRA ĐỦ 18 TUỔI
   ============================================================================ */
CREATE FUNCTION dbo.fn_KiemTraDu18Tuoi (@NgaySinh DATE)
RETURNS BIT
AS
BEGIN
    DECLARE @HopLe BIT = 0;
    IF @NgaySinh <= DATEADD(YEAR, -18, GETDATE())
        SET @HopLe = 1;
    RETURN @HopLe;
END;
GO

/* ============================================================================
   1. TẠO BẢNG
   ============================================================================ */

CREATE TABLE LoaiKhachHang (
    MaLoaiKH       VARCHAR(10)   NOT NULL,
    TenLoai        NVARCHAR(50)  NOT NULL,
    PhanTramUuDai  DECIMAL(5,2)  NOT NULL
        CONSTRAINT DF_LoaiKhachHang_PhanTramUuDai DEFAULT 0,
    CONSTRAINT PK_LoaiKhachHang PRIMARY KEY (MaLoaiKH),
    CONSTRAINT UQ_LoaiKhachHang_TenLoai UNIQUE (TenLoai),
    CONSTRAINT CK_LoaiKhachHang_PhanTramUuDai
        CHECK (PhanTramUuDai >= 0 AND PhanTramUuDai <= 100)
);
GO

CREATE TABLE KhachHang (
    MaKH       VARCHAR(10)    NOT NULL,
    HoTen      NVARCHAR(100)  NOT NULL,
    NgaySinh   DATE           NOT NULL,
    CCCD       CHAR(12)       NOT NULL,
    DiaChi     NVARCHAR(200)  NULL,
    MaLoaiKH   VARCHAR(10)    NOT NULL
        CONSTRAINT DF_KhachHang_MaLoaiKH DEFAULT 'LKH01',
    CONSTRAINT PK_KhachHang PRIMARY KEY (MaKH),
    CONSTRAINT UQ_KhachHang_CCCD UNIQUE (CCCD),
    CONSTRAINT CK_KhachHang_NgaySinh CHECK (dbo.fn_KiemTraDu18Tuoi(NgaySinh) = 1),
    CONSTRAINT CK_KhachHang_CCCD
        CHECK (CCCD LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CONSTRAINT FK_KhachHang_LoaiKhachHang
        FOREIGN KEY (MaLoaiKH) REFERENCES LoaiKhachHang (MaLoaiKH)
);
GO

CREATE TABLE KhachHang_SDT (
    MaKH  VARCHAR(10)  NOT NULL,
    SDT   VARCHAR(15)  NOT NULL,
    CONSTRAINT PK_KhachHang_SDT PRIMARY KEY (MaKH, SDT),
    CONSTRAINT FK_KhachHang_SDT_KhachHang
        FOREIGN KEY (MaKH) REFERENCES KhachHang (MaKH),
    CONSTRAINT CK_KhachHang_SDT_SDT
        CHECK (SDT NOT LIKE '%[^0-9]%' AND LEN(SDT) BETWEEN 10 AND 11)
);
GO

CREATE TABLE KhachHang_Email (
    MaKH   VARCHAR(10)   NOT NULL,
    Email  VARCHAR(100)  NOT NULL,
    CONSTRAINT PK_KhachHang_Email PRIMARY KEY (MaKH, Email),
    CONSTRAINT FK_KhachHang_Email_KhachHang
        FOREIGN KEY (MaKH) REFERENCES KhachHang (MaKH),
    CONSTRAINT CK_KhachHang_Email_Email
        CHECK (Email LIKE '_%@_%._%' AND Email NOT LIKE '% %')
);
GO

CREATE TABLE NhanVien (
    MaNV    VARCHAR(10)    NOT NULL,
    HoTen   NVARCHAR(100)  NOT NULL,
    ChucVu  NVARCHAR(50)   NOT NULL,
    CONSTRAINT PK_NhanVien PRIMARY KEY (MaNV),
    CONSTRAINT CK_NhanVien_ChucVu
        CHECK (ChucVu IN (N'Lễ tân', N'Quản lý', N'Kế toán', N'Buồng phòng', N'Bảo vệ'))
);
GO

CREATE TABLE NhanVien_SDT (
    MaNV  VARCHAR(10)  NOT NULL,
    SDT   VARCHAR(15)  NOT NULL,
    CONSTRAINT PK_NhanVien_SDT PRIMARY KEY (MaNV, SDT),
    CONSTRAINT FK_NhanVien_SDT_NhanVien
        FOREIGN KEY (MaNV) REFERENCES NhanVien (MaNV),
    CONSTRAINT CK_NhanVien_SDT_SDT
        CHECK (SDT NOT LIKE '%[^0-9]%' AND LEN(SDT) BETWEEN 10 AND 11)
);
GO

CREATE TABLE NhanVien_Email (
    MaNV   VARCHAR(10)   NOT NULL,
    Email  VARCHAR(100)  NOT NULL,
    CONSTRAINT PK_NhanVien_Email PRIMARY KEY (MaNV, Email),
    CONSTRAINT FK_NhanVien_Email_NhanVien
        FOREIGN KEY (MaNV) REFERENCES NhanVien (MaNV),
    CONSTRAINT CK_NhanVien_Email_Email
        CHECK (Email LIKE '_%@_%._%' AND Email NOT LIKE '% %')
);
GO

CREATE TABLE TaiKhoan (
    TenDangNhap  VARCHAR(50)   NOT NULL,
    MatKhau      VARCHAR(255)  NOT NULL,
    Salt         VARCHAR(32)   NOT NULL,
    TrangThai    NVARCHAR(20)  NOT NULL
        CONSTRAINT DF_TaiKhoan_TrangThai DEFAULT N'Hoạt động',
    MaNV         VARCHAR(10)   NOT NULL,
    CONSTRAINT PK_TaiKhoan PRIMARY KEY (TenDangNhap),
    CONSTRAINT UQ_TaiKhoan_MaNV UNIQUE (MaNV),
    CONSTRAINT CK_TaiKhoan_TrangThai CHECK (TrangThai IN (N'Hoạt động', N'Khóa')),
    CONSTRAINT FK_TaiKhoan_NhanVien
        FOREIGN KEY (MaNV) REFERENCES NhanVien (MaNV)
);
GO

CREATE TABLE LoaiPhong (
    MaLoaiPhong     VARCHAR(10)    NOT NULL,
    TenLoai         NVARCHAR(50)   NOT NULL,
    SucChua         TINYINT        NOT NULL,
    DonGiaTheoGio   DECIMAL(12,0)  NOT NULL
        CONSTRAINT DF_LoaiPhong_DonGiaTheoGio DEFAULT 0,
    DonGiaQuaDem    DECIMAL(12,0)  NOT NULL
        CONSTRAINT DF_LoaiPhong_DonGiaQuaDem DEFAULT 0,
    DonGiaTheoNgay  DECIMAL(12,0)  NOT NULL
        CONSTRAINT DF_LoaiPhong_DonGiaTheoNgay DEFAULT 0,
    MoTa            NVARCHAR(500)  NULL,
    CONSTRAINT PK_LoaiPhong PRIMARY KEY (MaLoaiPhong),
    CONSTRAINT UQ_LoaiPhong_TenLoai UNIQUE (TenLoai),
    CONSTRAINT CK_LoaiPhong_SucChua CHECK (SucChua > 0),
    CONSTRAINT CK_LoaiPhong_DonGiaTheoGio CHECK (DonGiaTheoGio >= 0),
    CONSTRAINT CK_LoaiPhong_DonGiaQuaDem CHECK (DonGiaQuaDem >= 0),
    CONSTRAINT CK_LoaiPhong_DonGiaTheoNgay CHECK (DonGiaTheoNgay >= 0)
);
GO

CREATE TABLE Phong (
    MaPhong      VARCHAR(10)   NOT NULL,
    SoPhong      VARCHAR(10)   NOT NULL,
    Tang         TINYINT       NOT NULL,
    TinhTrang    NVARCHAR(20)  NOT NULL
        CONSTRAINT DF_Phong_TinhTrang DEFAULT N'Trống',
    MaLoaiPhong  VARCHAR(10)   NOT NULL,
    CONSTRAINT PK_Phong PRIMARY KEY (MaPhong),
    CONSTRAINT UQ_Phong_SoPhong UNIQUE (SoPhong),
    CONSTRAINT CK_Phong_Tang CHECK (Tang >= 1),
    CONSTRAINT CK_Phong_TinhTrang
        CHECK (TinhTrang IN (N'Trống', N'Đang thuê', N'Đang dọn', N'Bảo trì')),
    CONSTRAINT FK_Phong_LoaiPhong
        FOREIGN KEY (MaLoaiPhong) REFERENCES LoaiPhong (MaLoaiPhong)
);
GO

CREATE TABLE PhieuThue (
    MaPhieuThue  VARCHAR(12)   NOT NULL,
    NgayLap      DATETIME      NOT NULL
        CONSTRAINT DF_PhieuThue_NgayLap DEFAULT GETDATE(),
    TrangThai    NVARCHAR(20)  NOT NULL
        CONSTRAINT DF_PhieuThue_TrangThai DEFAULT N'Đã đặt',
    MaKH         VARCHAR(10)   NOT NULL,
    MaNV         VARCHAR(10)   NOT NULL,
    CONSTRAINT PK_PhieuThue PRIMARY KEY (MaPhieuThue),
    CONSTRAINT CK_PhieuThue_TrangThai
        CHECK (TrangThai IN (N'Đã đặt', N'Đang thuê', N'Hoàn tất', N'Đã hủy')),
    CONSTRAINT FK_PhieuThue_KhachHang
        FOREIGN KEY (MaKH) REFERENCES KhachHang (MaKH),
    CONSTRAINT FK_PhieuThue_NhanVien
        FOREIGN KEY (MaNV) REFERENCES NhanVien (MaNV)
);
GO

CREATE TABLE ChiTietPhieuThue (
    MaPhieuThue          VARCHAR(12)    NOT NULL,
    STT                  INT            NOT NULL,
    MaPhong              VARCHAR(10)    NOT NULL,
    HinhThucThue         NVARCHAR(20)   NOT NULL,
    DonGiaApDung         DECIMAL(12,0)  NOT NULL,
    SoNguoiDuKien        TINYINT        NOT NULL
        CONSTRAINT DF_ChiTietPhieuThue_SoNguoiDuKien DEFAULT 1,
    KhachDatCoOPhongNay  BIT            NOT NULL
        CONSTRAINT DF_ChiTietPhieuThue_KhachDatCoOPhongNay DEFAULT 1,
    GioNhan              DATETIME       NOT NULL,
    GioTraDuKien         DATETIME       NOT NULL,
    GioTra               DATETIME       NULL,
    GhiChu               NVARCHAR(500)  NULL,
    CONSTRAINT PK_ChiTietPhieuThue PRIMARY KEY (MaPhieuThue, STT),
    CONSTRAINT CK_ChiTietPhieuThue_STT CHECK (STT > 0),
    CONSTRAINT CK_ChiTietPhieuThue_HinhThucThue
        CHECK (HinhThucThue IN (N'Theo giờ', N'Qua đêm', N'Theo ngày')),
    CONSTRAINT CK_ChiTietPhieuThue_DonGiaApDung CHECK (DonGiaApDung >= 0),
    CONSTRAINT CK_ChiTietPhieuThue_SoNguoiDuKien CHECK (SoNguoiDuKien > 0),
    CONSTRAINT CK_ChiTietPhieuThue_GioTraDuKien CHECK (GioTraDuKien > GioNhan),
    CONSTRAINT CK_ChiTietPhieuThue_GioTra CHECK (GioTra > GioNhan),
    CONSTRAINT FK_ChiTietPhieuThue_PhieuThue
        FOREIGN KEY (MaPhieuThue) REFERENCES PhieuThue (MaPhieuThue),
    CONSTRAINT FK_ChiTietPhieuThue_Phong
        FOREIGN KEY (MaPhong) REFERENCES Phong (MaPhong)
);
GO

CREATE TABLE KhachDiCung (
    CCCD    CHAR(12)       NOT NULL,
    HoTen   NVARCHAR(100)  NOT NULL,
    DiaChi  NVARCHAR(200)  NULL,
    CONSTRAINT PK_KhachDiCung PRIMARY KEY (CCCD),
    CONSTRAINT CK_KhachDiCung_CCCD
        CHECK (CCCD LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]')
);
GO

CREATE TABLE OCung (
    MaPhieuThue  VARCHAR(12)  NOT NULL,
    STT          INT          NOT NULL,
    CCCD         CHAR(12)     NOT NULL,
    CONSTRAINT PK_OCung PRIMARY KEY (MaPhieuThue, STT, CCCD),
    CONSTRAINT FK_OCung_ChiTietPhieuThue
        FOREIGN KEY (MaPhieuThue, STT)
        REFERENCES ChiTietPhieuThue (MaPhieuThue, STT),
    CONSTRAINT FK_OCung_KhachDiCung
        FOREIGN KEY (CCCD) REFERENCES KhachDiCung (CCCD)
);
GO

CREATE TABLE DichVu (
    MaDichVu    VARCHAR(10)    NOT NULL,
    TenDichVu   NVARCHAR(100)  NOT NULL,
    MoTa        NVARCHAR(500)  NULL,
    DonViTinh   NVARCHAR(20)   NOT NULL,
    DonGia      DECIMAL(12,0)  NOT NULL,
    CONSTRAINT PK_DichVu PRIMARY KEY (MaDichVu),
    CONSTRAINT UQ_DichVu_TenDichVu UNIQUE (TenDichVu),
    CONSTRAINT CK_DichVu_DonGia CHECK (DonGia >= 0)
);
GO

CREATE TABLE DungDichVu (
    MaPhieuThue   VARCHAR(12)    NOT NULL,
    STT           INT            NOT NULL,
    MaDichVu      VARCHAR(10)    NOT NULL,
    GioBD         DATETIME       NOT NULL,
    GioKT         DATETIME       NULL,
    SoLuong       INT            NOT NULL
        CONSTRAINT DF_DungDichVu_SoLuong DEFAULT 1,
    DonGiaApDung  DECIMAL(12,0)  NOT NULL,
    CONSTRAINT PK_DungDichVu PRIMARY KEY (MaPhieuThue, STT, MaDichVu, GioBD),
    CONSTRAINT CK_DungDichVu_GioKT CHECK (GioKT > GioBD),
    CONSTRAINT CK_DungDichVu_SoLuong CHECK (SoLuong > 0),
    CONSTRAINT CK_DungDichVu_DonGiaApDung CHECK (DonGiaApDung >= 0),
    CONSTRAINT FK_DungDichVu_ChiTietPhieuThue
        FOREIGN KEY (MaPhieuThue, STT)
        REFERENCES ChiTietPhieuThue (MaPhieuThue, STT),
    CONSTRAINT FK_DungDichVu_DichVu
        FOREIGN KEY (MaDichVu) REFERENCES DichVu (MaDichVu)
);
GO

CREATE TABLE ThanhToan (
    MaThanhToan       VARCHAR(12)    NOT NULL,
    MaPhieuThue       VARCHAR(12)    NOT NULL,
    MaNV              VARCHAR(10)    NOT NULL,
    NgayGioThanhToan  DATETIME       NOT NULL
        CONSTRAINT DF_ThanhToan_NgayGioThanhToan DEFAULT GETDATE(),
    PhuongThuc        NVARCHAR(20)   NOT NULL,
    SoTien            DECIMAL(14,0)  NOT NULL,
    LoaiKhoan         NVARCHAR(30)   NOT NULL,
    CONSTRAINT PK_ThanhToan PRIMARY KEY (MaThanhToan),
    CONSTRAINT CK_ThanhToan_PhuongThuc
        CHECK (PhuongThuc IN (N'Tiền mặt', N'Chuyển khoản', N'Thẻ')),
    CONSTRAINT CK_ThanhToan_SoTien CHECK (SoTien > 0),
    CONSTRAINT CK_ThanhToan_LoaiKhoan
        CHECK (LoaiKhoan IN (N'Đặt cọc', N'Thanh toán', N'Hoàn tiền')),
    CONSTRAINT FK_ThanhToan_PhieuThue
        FOREIGN KEY (MaPhieuThue) REFERENCES PhieuThue (MaPhieuThue),
    CONSTRAINT FK_ThanhToan_NhanVien
        FOREIGN KEY (MaNV) REFERENCES NhanVien (MaNV)
);
GO

CREATE TABLE HoaDon (
    MaHD         VARCHAR(12)    NOT NULL,
    MaPhieuThue  VARCHAR(12)    NOT NULL,
    MaNV         VARCHAR(10)    NOT NULL,
    NgayLap      DATETIME       NOT NULL
        CONSTRAINT DF_HoaDon_NgayLap DEFAULT GETDATE(),
    TienPhong    DECIMAL(14,0)  NOT NULL
        CONSTRAINT DF_HoaDon_TienPhong DEFAULT 0,
    TienDichVu   DECIMAL(14,0)  NOT NULL
        CONSTRAINT DF_HoaDon_TienDichVu DEFAULT 0,
    TienPhuThu   DECIMAL(14,0)  NOT NULL
        CONSTRAINT DF_HoaDon_TienPhuThu DEFAULT 0,
    UuDai        DECIMAL(14,0)  NOT NULL
        CONSTRAINT DF_HoaDon_UuDai DEFAULT 0,
    TyLeVAT      DECIMAL(5,2)   NOT NULL
        CONSTRAINT DF_HoaDon_TyLeVAT DEFAULT 10,
    TienVAT      AS CAST(ROUND((TienPhong + TienDichVu + TienPhuThu - UuDai) * TyLeVAT / 100.0, 0) AS DECIMAL(14,0)),
    TongTien     AS (TienPhong + TienDichVu + TienPhuThu - UuDai
                     + CAST(ROUND((TienPhong + TienDichVu + TienPhuThu - UuDai) * TyLeVAT / 100.0, 0) AS DECIMAL(14,0))),
    TrangThai    NVARCHAR(20)   NOT NULL
        CONSTRAINT DF_HoaDon_TrangThai DEFAULT N'Chưa thanh toán',
    CONSTRAINT PK_HoaDon PRIMARY KEY (MaHD),
    CONSTRAINT UQ_HoaDon_MaPhieuThue UNIQUE (MaPhieuThue),
    CONSTRAINT CK_HoaDon_TienPhong CHECK (TienPhong >= 0),
    CONSTRAINT CK_HoaDon_TienDichVu CHECK (TienDichVu >= 0),
    CONSTRAINT CK_HoaDon_TienPhuThu CHECK (TienPhuThu >= 0),
    CONSTRAINT CK_HoaDon_UuDai CHECK (UuDai >= 0),
    CONSTRAINT CK_HoaDon_UuDai_HopLe CHECK (UuDai <= TienPhong + TienDichVu + TienPhuThu),
    CONSTRAINT CK_HoaDon_TyLeVAT CHECK (TyLeVAT >= 0 AND TyLeVAT <= 99.99),
    CONSTRAINT CK_HoaDon_TrangThai
        CHECK (TrangThai IN (N'Chưa thanh toán', N'Đã thanh toán', N'Đã hủy')),
    CONSTRAINT FK_HoaDon_PhieuThue
        FOREIGN KEY (MaPhieuThue) REFERENCES PhieuThue (MaPhieuThue),
    CONSTRAINT FK_HoaDon_NhanVien
        FOREIGN KEY (MaNV) REFERENCES NhanVien (MaNV)
);
GO

/* ============================================================================
   2. TẠO INDEX CHO CÁC KHÓA NGOẠI
   ============================================================================ */

CREATE INDEX IX_KhachHang_MaLoaiKH ON KhachHang (MaLoaiKH);
CREATE INDEX IX_Phong_MaLoaiPhong ON Phong (MaLoaiPhong);
CREATE INDEX IX_PhieuThue_MaKH ON PhieuThue (MaKH);
CREATE INDEX IX_PhieuThue_MaNV ON PhieuThue (MaNV);
CREATE INDEX IX_ChiTietPhieuThue_MaPhong ON ChiTietPhieuThue (MaPhong, GioNhan) INCLUDE (GioTra, GioTraDuKien);
CREATE INDEX IX_OCung_CCCD ON OCung (CCCD);
CREATE INDEX IX_DungDichVu_MaDichVu ON DungDichVu (MaDichVu);
CREATE INDEX IX_ThanhToan_MaPhieuThue ON ThanhToan (MaPhieuThue);
CREATE INDEX IX_ThanhToan_MaNV ON ThanhToan (MaNV);
CREATE INDEX IX_HoaDon_MaNV ON HoaDon (MaNV);
GO

/* ============================================================================
   3. DỮ LIỆU MẪU
   ============================================================================ */

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Today DATETIME = CAST(CAST(GETDATE() AS DATE) AS DATETIME);

IF OBJECT_ID('tempdb..#N')     IS NOT NULL DROP TABLE #N;
IF OBJECT_ID('tempdb..#TK')    IS NOT NULL DROP TABLE #TK;
IF OBJECT_ID('tempdb..#Phieu') IS NOT NULL DROP TABLE #Phieu;
IF OBJECT_ID('tempdb..#HD0')   IS NOT NULL DROP TABLE #HD0;

BEGIN TRY
BEGIN TRANSACTION;

SELECT TOP (100) CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS INT) AS n
INTO #N
FROM sys.all_objects;

INSERT INTO LoaiKhachHang (MaLoaiKH, TenLoai, PhanTramUuDai) VALUES
('LKH01', N'Thường', 0),
('LKH02', N'Thân thiết', 5),
('LKH03', N'VIP', 10),
('LKH04', N'Doanh nghiệp', 7.5);

INSERT INTO NhanVien (MaNV, HoTen, ChucVu) VALUES
('NV01', N'Nguyễn Thị Hoa',    N'Lễ tân'),
('NV02', N'Trần Văn Nam',      N'Lễ tân'),
('NV03', N'Lê Thị Mai',        N'Lễ tân'),
('NV04', N'Phạm Quốc Huy',     N'Lễ tân'),
('NV05', N'Hoàng Thị Thu',     N'Lễ tân'),
('NV06', N'Vũ Minh Đức',       N'Lễ tân'),
('NV07', N'Hoàng Minh Tuấn',   N'Quản lý'),
('NV08', N'Vũ Thị Lan',        N'Quản lý'),
('NV09', N'Đặng Thu Hà',       N'Kế toán'),
('NV10', N'Bùi Văn Long',      N'Kế toán'),
('NV11', N'Ngô Thị Thanh',     N'Buồng phòng'),
('NV12', N'Trịnh Thị Hương',   N'Buồng phòng'),
('NV13', N'Lý Thị Nhung',      N'Buồng phòng'),
('NV14', N'Phan Thị Lụa',      N'Buồng phòng'),
('NV15', N'Đoàn Thị Hiền',     N'Buồng phòng'),
('NV16', N'Dương Thị Bích',    N'Buồng phòng'),
('NV17', N'Đỗ Văn Hùng',       N'Bảo vệ'),
('NV18', N'Mai Văn Thắng',     N'Bảo vệ'),
('NV19', N'Tạ Quang Vinh',     N'Bảo vệ'),
('NV20', N'Lưu Đức Anh',       N'Bảo vệ');

INSERT INTO NhanVien_SDT (MaNV, SDT) VALUES
('NV01', '0912345601'), ('NV02', '0987654302'), ('NV03', '0903456703'), ('NV04', '0978123404'),
('NV05', '0936789505'), ('NV06', '0965432106'), ('NV07', '0913777807'), ('NV08', '0982246808'),
('NV09', '0905112209'), ('NV10', '0977889910'), ('NV11', '0348123411'), ('NV12', '0367456212'),
('NV13', '0389765313'), ('NV14', '0332198414'), ('NV15', '0356874515'), ('NV16', '0378965216'),
('NV17', '0393214717'), ('NV18', '0345678918'), ('NV19', '0362587419'), ('NV20', '0386471920');

SELECT v.TenDangNhap, v.MatKhauMau, v.TrangThai, v.MaNV,
       REPLACE(CONVERT(VARCHAR(36), NEWID()), '-', '') AS Salt
INTO #TK
FROM (VALUES
    ('hoa.nt',  'Hoa@2026',  N'Hoạt động', 'NV01'),
    ('nam.tv',  'Nam@2026',  N'Hoạt động', 'NV02'),
    ('mai.lt',  'Mai@2026',  N'Hoạt động', 'NV03'),
    ('huy.pq',  'Huy@2026',  N'Hoạt động', 'NV04'),
    ('thu.ht',  'Thu@2026',  N'Hoạt động', 'NV05'),
    ('duc.vm',  'Duc@2026',  N'Hoạt động', 'NV06'),
    ('tuan.hm', 'Tuan@2026', N'Hoạt động', 'NV07'),
    ('lan.vt',  'Lan@2026',  N'Hoạt động', 'NV08'),
    ('ha.dt',   'Ha@2026',   N'Hoạt động', 'NV09'),
    ('long.bv', 'Long@2026', N'Khóa',      'NV10')
) v (TenDangNhap, MatKhauMau, TrangThai, MaNV);

INSERT INTO TaiKhoan (TenDangNhap, MatKhau, Salt, TrangThai, MaNV)
SELECT TenDangNhap,
       CONVERT(VARCHAR(64), HASHBYTES('SHA2_256', Salt + MatKhauMau), 2),
       Salt, TrangThai, MaNV
FROM #TK;

INSERT INTO NhanVien_Email (MaNV, Email)
SELECT MaNV, TenDangNhap + '@khachsan.vn'
FROM TaiKhoan;

INSERT INTO LoaiPhong (MaLoaiPhong, TenLoai, SucChua, DonGiaTheoGio, DonGiaQuaDem, DonGiaTheoNgay, MoTa) VALUES
('LP01', N'Đơn',      2,  80000, 250000,  350000, N'Phòng 1 giường đơn 1m2, phù hợp 1-2 khách'),
('LP02', N'Đôi',      3, 100000, 300000,  450000, N'Phòng 1 giường đôi, có ban công'),
('LP03', N'Gia đình', 4, 150000, 450000,  650000, N'Phòng 2 giường, phù hợp gia đình nhỏ'),
('LP04', N'VIP',      4, 200000, 600000,  900000, N'Phòng cao cấp, view thành phố'),
('LP05', N'Suite',    6, 300000, 900000, 1300000, N'Phòng suite rộng, có phòng khách riêng');

INSERT INTO DichVu (MaDichVu, TenDichVu, MoTa, DonViTinh, DonGia) VALUES
('DV01', N'Giặt ủi thường',              N'Giặt sấy và ủi, trả đồ sau 24 giờ',                 N'kg',     35000),
('DV02', N'Giặt ủi nhanh',               N'Trả đồ trong vòng 4 giờ',                           N'kg',     60000),
('DV03', N'Ủi quần áo',                  N'Ủi riêng, không giặt',                              N'món',    15000),
('DV04', N'Giặt khô',                    N'Áo vest, váy, áo dài, đồ len',                      N'món',    80000),
('DV05', N'Nước suối 500ml',             N'Minibar trong phòng',                               N'chai',   15000),
('DV06', N'Nước ngọt lon',               N'Coca-Cola, Pepsi, 7Up - minibar',                   N'lon',    20000),
('DV07', N'Bia lon',                     N'Bia Tiger/Heineken - minibar',                      N'lon',    35000),
('DV08', N'Cà phê phin sữa đá',          N'Phục vụ tại phòng',                                 N'ly',     35000),
('DV09', N'Trà thảo mộc',                N'Trà hoa cúc, trà gừng; ấm 2-3 người',               N'ấm',     60000),
('DV10', N'Snack minibar',               N'Bánh, hạt, snack các loại',                         N'gói',    25000),
('DV11', N'Buffet sáng người lớn',       N'Phục vụ 6:30-9:30 tại nhà hàng',                    N'suất',  120000),
('DV12', N'Buffet sáng trẻ em',          N'Trẻ em dưới 12 tuổi',                               N'suất',   60000),
('DV13', N'Phở bò phục vụ tại phòng',    N'Phục vụ trong 20 phút',                             N'tô',     75000),
('DV14', N'Cơm phần phục vụ tại phòng',  N'Cơm, canh, món mặn, tráng miệng',                   N'phần',  110000),
('DV15', N'Mì Ý sốt bò bằm',             N'Phục vụ tại phòng hoặc nhà hàng',                   N'đĩa',   130000),
('DV16', N'Đưa đón sân bay Nội Bài',     N'Xe 4 chỗ, đặt trước ít nhất 3 giờ',                 N'chuyến',350000),
('DV17', N'Taxi nội thành',              N'Xe 4 chỗ, quanh khu vực trung tâm',                 N'chuyến',150000),
('DV18', N'Thuê xe máy',                 N'Xe tay ga, kèm mũ bảo hiểm; giữ CCCD gốc',          N'ngày',  150000),
('DV19', N'Gửi hành lý',                 N'Gửi sau giờ trả phòng, tối đa 24 giờ',              N'kiện',   30000),
('DV20', N'Giường phụ',                  N'Thêm giường phụ trong phòng',                       N'đêm',   200000),
('DV21', N'Nôi em bé',                   N'Dành cho trẻ dưới 2 tuổi',                          N'đêm',    50000),
('DV22', N'Massage toàn thân',           N'Liệu trình 60 phút, tính theo giờ',                 N'giờ',   300000),
('DV23', N'Xông hơi',                    N'Phòng xông hơi khô, tính theo giờ',                 N'giờ',   150000),
('DV24', N'Phòng họp',                   N'Sức chứa 15 người, có máy chiếu',                   N'giờ',   400000),
('DV25', N'Thuê xe đạp',                 N'Xe đạp thành phố, tính theo giờ',                   N'giờ',    20000),
('DV26', N'Thuê xe 7 chỗ có tài xế',     N'Đi tham quan, tối đa 10 giờ/ngày',                  N'ngày', 1500000),
('DV27', N'Tour tham quan trong ngày',   N'Xe, hướng dẫn viên, vé tham quan',                  N'người', 450000),
('DV28', N'Đặt vé tàu xe',               N'Phí dịch vụ đặt vé tàu, xe khách, máy bay',         N'vé',     50000),
('DV29', N'In ấn, photo tài liệu',       N'Khổ A4, đen trắng',                                 N'trang',   2000),
('DV30', N'Đĩa trái cây theo mùa',       N'Phục vụ tại phòng',                                 N'đĩa',   120000),
('DV31', N'Rượu vang đỏ',                N'Vang nhập khẩu, kèm ly và đồ khui',                 N'chai',  650000),
('DV32', N'Trang trí phòng sinh nhật',   N'Bóng, hoa, bánh nhỏ; đặt trước 1 ngày',             N'set',   500000);

INSERT INTO KhachHang (MaKH, HoTen, NgaySinh, CCCD, DiaChi, MaLoaiKH)
SELECT 'KH' + RIGHT('000' + CAST(a.n AS VARCHAR(3)), 3),
       ho.v + N' ' + dem.v + N' ' + ten.v,
       ns.v,
       '079'
         + CASE WHEN dem.v = N'Thị' THEN '1' ELSE '0' END
         + RIGHT('0' + CAST(YEAR(ns.v) % 100 AS VARCHAR(2)), 2)
         + RIGHT('000000' + CAST(a.n AS VARCHAR(6)), 6),
       CASE WHEN a.n % 7 = 0 THEN NULL
            ELSE N'Số ' + CAST(a.n AS NVARCHAR(3)) + N' ' + st.v + N', ' + ci.v END,
       CASE WHEN a.n % 10 BETWEEN 1 AND 5 THEN 'LKH01'
            WHEN a.n % 10 IN (6, 7, 0)    THEN 'LKH02'
            WHEN a.n % 10 = 8             THEN 'LKH03'
            ELSE 'LKH04' END
FROM #N a
CROSS APPLY (SELECT DATEADD(DAY, a.n * 300, CAST('19650101' AS DATE)) AS v) ns
JOIN (VALUES (1,N'Nguyễn'),(2,N'Trần'),(3,N'Lê'),(4,N'Phạm'),(5,N'Hoàng'),
             (6,N'Vũ'),(7,N'Đặng'),(8,N'Bùi'),(9,N'Đỗ'),(10,N'Ngô')) ho(i, v)
     ON ho.i = (a.n - 1) % 10 + 1
JOIN (VALUES (1,N'Văn'),(2,N'Thị'),(3,N'Minh'),(4,N'Quốc'),(5,N'Thu'),(6,N'Gia')) dem(i, v)
     ON dem.i = (a.n + 2) % 6 + 1
JOIN (VALUES (1,N'Anh'),(2,N'Bình'),(3,N'Châu'),(4,N'Dũng'),(5,N'Giang'),(6,N'Hải'),
             (7,N'Khánh'),(8,N'Linh'),(9,N'Phúc'),(10,N'Quang'),(11,N'Trang'),(12,N'Việt')) ten(i, v)
     ON ten.i = (a.n * 5) % 12 + 1
JOIN (VALUES (1,N'Lê Lợi'),(2,N'Nguyễn Huệ'),(3,N'Trần Hưng Đạo'),(4,N'Hai Bà Trưng'),
             (5,N'Điện Biên Phủ'),(6,N'Lý Thường Kiệt'),(7,N'Phạm Ngũ Lão'),(8,N'Võ Thị Sáu')) st(i, v)
     ON st.i = a.n % 8 + 1
JOIN (VALUES (1,N'Hà Nội'),(2,N'TP. Hồ Chí Minh'),(3,N'Đà Nẵng'),(4,N'Hải Phòng'),
             (5,N'Cần Thơ'),(6,N'Huế'),(7,N'Nha Trang'),(8,N'Vũng Tàu')) ci(i, v)
     ON ci.i = (a.n * 3) % 8 + 1
WHERE a.n <= 40;

INSERT INTO KhachHang_SDT (MaKH, SDT)
SELECT 'KH' + RIGHT('000' + CAST(a.n AS VARCHAR(3)), 3),
       '090' + CAST(1000000 + a.n AS VARCHAR(7))
FROM #N a WHERE a.n <= 40
UNION ALL
SELECT 'KH' + RIGHT('000' + CAST(a.n AS VARCHAR(3)), 3),
       '091' + CAST(2000000 + a.n AS VARCHAR(7))
FROM #N a WHERE a.n <= 40 AND a.n % 4 = 0;

INSERT INTO KhachHang_Email (MaKH, Email)
SELECT 'KH' + RIGHT('000' + CAST(a.n AS VARCHAR(3)), 3),
       'kh' + RIGHT('000' + CAST(a.n AS VARCHAR(3)), 3) + '@gmail.com'
FROM #N a WHERE a.n <= 40 AND a.n % 3 <> 0
UNION ALL
SELECT 'KH' + RIGHT('000' + CAST(a.n AS VARCHAR(3)), 3),
       'kh' + RIGHT('000' + CAST(a.n AS VARCHAR(3)), 3) + '@congty.vn'
FROM #N a WHERE a.n <= 40 AND a.n % 10 = 9;

INSERT INTO Phong (MaPhong, SoPhong, Tang, MaLoaiPhong)
SELECT 'P' + RIGHT('00' + CAST(a.n AS VARCHAR(2)), 2),
       CAST(((a.n - 1) / 5 + 1) * 100 + (a.n - 1) % 5 + 1 AS VARCHAR(10)),
       (a.n - 1) / 5 + 1,
       'LP0' + CAST((a.n - 1) % 5 + 1 AS VARCHAR(1))
FROM #N a WHERE a.n <= 30;

SELECT a.n AS n,
       'PT' + RIGHT('0000' + CAST(a.n AS VARCHAR(4)), 4) AS MaPhieuThue,
       d.Ngay AS Ngay,
       DATEADD(HOUR, 8, CASE WHEN a.n <= 39 THEN d.Ngay
                             ELSE DATEADD(DAY, a.n - 43, @Today) END) AS NgayLap,
       CASE WHEN a.n IN (8, 17, 26)   THEN N'Đã hủy'
            WHEN a.n BETWEEN 37 AND 39 THEN N'Đang thuê'
            WHEN a.n BETWEEN 40 AND 42 THEN N'Đã đặt'
            ELSE N'Hoàn tất' END AS TrangThai,
       'KH' + RIGHT('000' + CAST((a.n * 7) % 30 + 1 AS VARCHAR(3)), 3) AS MaKH,
       'NV0' + CAST(a.n % 6 + 1 AS VARCHAR(1)) AS MaNV
INTO #Phieu
FROM #N a
CROSS APPLY (SELECT CASE WHEN a.n <= 36 THEN DATEADD(DAY, -120 + 3 * (a.n - 1), @Today)
                         WHEN a.n <= 39 THEN DATEADD(DAY, a.n - 40, @Today)
                         ELSE DATEADD(DAY, 2 * (a.n - 39), @Today) END AS Ngay) d
WHERE a.n <= 42;

INSERT INTO PhieuThue (MaPhieuThue, NgayLap, TrangThai, MaKH, MaNV)
SELECT MaPhieuThue, NgayLap, TrangThai, MaKH, MaNV
FROM #Phieu;

INSERT INTO ChiTietPhieuThue
    (MaPhieuThue, STT, MaPhong, HinhThucThue, DonGiaApDung, SoNguoiDuKien, KhachDatCoOPhongNay,
     GioNhan, GioTraDuKien, GioTra, GhiChu)
SELECT x.MaPhieuThue, x.STT, x.MaPhong,
       CASE x.k WHEN 0 THEN N'Theo giờ' WHEN 1 THEN N'Qua đêm' ELSE N'Theo ngày' END,
       CASE x.k WHEN 0 THEN lp.DonGiaTheoGio WHEN 1 THEN lp.DonGiaQuaDem ELSE lp.DonGiaTheoNgay END,
       x.SoNguoi, x.KhachCo, x.GioNhan, x.GioTraDuKien,
       CASE WHEN x.TrangThai = N'Hoàn tất' THEN x.GioTraDuKien END,
       x.GhiChu
FROM (
    SELECT p.MaPhieuThue, p.TrangThai, s.STT, kk.k,
           'P' + RIGHT('00' + CAST(CASE s.STT WHEN 1 THEN (p.n - 1) % 30 + 1
                                              ELSE (p.n + 14) % 30 + 1 END AS VARCHAR(2)), 2) AS MaPhong,
           1 + p.n % 2 AS SoNguoi,
           CAST(CASE s.STT WHEN 1 THEN 1 ELSE 0 END AS BIT) AS KhachCo,
           CASE kk.k WHEN 1 THEN DATEADD(HOUR, 21, p.Ngay)
                     ELSE DATEADD(HOUR, 14, p.Ngay) END AS GioNhan,
           CASE kk.k WHEN 0 THEN DATEADD(HOUR, 17, p.Ngay)
                     WHEN 1 THEN DATEADD(HOUR, 36, p.Ngay)
                     ELSE DATEADD(HOUR, 12 + 24 * CASE WHEN p.TrangThai = N'Đang thuê' THEN 4
                                                       ELSE 1 + p.n % 3 END, p.Ngay) END AS GioTraDuKien,
           CASE WHEN p.n % 5 = 0  THEN N'Khách yêu cầu phòng tầng cao'
                WHEN p.n % 11 = 0 THEN N'Nhận phòng sớm' END AS GhiChu
    FROM #Phieu p
    JOIN (VALUES (1), (2)) s(STT) ON s.STT = 1 OR p.n % 3 = 0
    CROSS APPLY (SELECT CASE WHEN p.TrangThai = N'Đang thuê' THEN 2
                             ELSE (p.n + s.STT) % 3 END AS k) kk
) x
JOIN Phong ph ON ph.MaPhong = x.MaPhong
JOIN LoaiPhong lp ON lp.MaLoaiPhong = ph.MaLoaiPhong;

INSERT INTO KhachDiCung (CCCD, HoTen, DiaChi)
SELECT '001'
         + CASE WHEN dem.v = N'Thị' THEN '1' ELSE '0' END
         + RIGHT('00' + CAST(70 + a.n % 25 AS VARCHAR(2)), 2)
         + RIGHT('000000' + CAST(300000 + a.n AS VARCHAR(6)), 6),
       ho.v + N' ' + dem.v + N' ' + ten.v,
       CASE WHEN a.n % 5 = 0 THEN NULL
            ELSE N'Số ' + CAST(a.n + 50 AS NVARCHAR(3)) + N' ' + st.v + N', ' + ci.v END
FROM #N a
JOIN (VALUES (1,N'Nguyễn'),(2,N'Trần'),(3,N'Lê'),(4,N'Phạm'),(5,N'Hoàng'),
             (6,N'Vũ'),(7,N'Đặng'),(8,N'Bùi'),(9,N'Đỗ'),(10,N'Ngô')) ho(i, v)
     ON ho.i = (a.n + 3) % 10 + 1
JOIN (VALUES (1,N'Văn'),(2,N'Thị'),(3,N'Minh'),(4,N'Quốc'),(5,N'Thu'),(6,N'Gia')) dem(i, v)
     ON dem.i = a.n % 6 + 1
JOIN (VALUES (1,N'Anh'),(2,N'Bình'),(3,N'Châu'),(4,N'Dũng'),(5,N'Giang'),(6,N'Hải'),
             (7,N'Khánh'),(8,N'Linh'),(9,N'Phúc'),(10,N'Quang'),(11,N'Trang'),(12,N'Việt')) ten(i, v)
     ON ten.i = (a.n * 7) % 12 + 1
JOIN (VALUES (1,N'Lê Lợi'),(2,N'Nguyễn Huệ'),(3,N'Trần Hưng Đạo'),(4,N'Hai Bà Trưng'),
             (5,N'Điện Biên Phủ'),(6,N'Lý Thường Kiệt'),(7,N'Phạm Ngũ Lão'),(8,N'Võ Thị Sáu')) st(i, v)
     ON st.i = (a.n + 3) % 8 + 1
JOIN (VALUES (1,N'Hà Nội'),(2,N'TP. Hồ Chí Minh'),(3,N'Đà Nẵng'),(4,N'Hải Phòng'),
             (5,N'Cần Thơ'),(6,N'Huế'),(7,N'Nha Trang'),(8,N'Vũng Tàu')) ci(i, v)
     ON ci.i = (a.n * 5) % 8 + 1
WHERE a.n <= 40;

INSERT INTO OCung (MaPhieuThue, STT, CCCD)
SELECT x.MaPhieuThue, x.STT, kd.CCCD
FROM (
    SELECT ct.MaPhieuThue, ct.STT,
           ct.SoNguoiDuKien - CAST(ct.KhachDatCoOPhongNay AS INT) AS SoKhach,
           ROW_NUMBER() OVER (ORDER BY ct.MaPhieuThue, ct.STT) AS rn
    FROM ChiTietPhieuThue ct
    JOIN #Phieu p ON p.MaPhieuThue = ct.MaPhieuThue
    WHERE p.TrangThai IN (N'Hoàn tất', N'Đang thuê')
) x
JOIN #N c ON c.n <= x.SoKhach
JOIN (SELECT CCCD, ROW_NUMBER() OVER (ORDER BY CCCD) AS k FROM KhachDiCung) kd
     ON kd.k = (x.rn * 3 + c.n) % 40 + 1;

INSERT INTO DungDichVu (MaPhieuThue, STT, MaDichVu, GioBD, GioKT, SoLuong, DonGiaApDung)
SELECT ct.MaPhieuThue, ct.STT, dv.MaDichVu,
       DATEADD(MINUTE, CASE sl.n WHEN 1 THEN 30 ELSE 90 END, ct.GioNhan),
       CASE WHEN dv.DonViTinh = N'giờ'
            THEN DATEADD(MINUTE, CASE sl.n WHEN 1 THEN 90 ELSE 150 END, ct.GioNhan) END,
       CASE WHEN dv.DonViTinh IN (N'giờ', N'ngày', N'đêm', N'set') THEN 1
            ELSE 1 + p.n % 3 END,
       dv.DonGia
FROM ChiTietPhieuThue ct
JOIN #Phieu p ON p.MaPhieuThue = ct.MaPhieuThue
JOIN (VALUES (1), (2)) sl(n) ON sl.n = 1 OR p.n % 2 = 0
JOIN DichVu dv ON dv.MaDichVu =
     'DV' + RIGHT('00' + CAST(CASE sl.n WHEN 1 THEN (p.n + ct.STT) % 20 + 1
                                        ELSE (p.n * 3 + ct.STT + 7) % 32 + 1 END AS VARCHAR(2)), 2)
WHERE p.TrangThai IN (N'Hoàn tất', N'Đang thuê');

SELECT p.n, p.MaPhieuThue, p.MaKH, p.MaNV,
       CAST(tp.TienPhong AS DECIMAL(14,0)) AS TienPhong,
       CAST(ISNULL(dv.TienDV, 0) AS DECIMAL(14,0)) AS TienDichVu,
       CAST(CASE WHEN p.n % 5 = 0 THEN 50000
                 WHEN p.n % 7 = 0 THEN 100000 ELSE 0 END AS DECIMAL(14,0)) AS TienPhuThu,
       lk.PhanTramUuDai,
       tg.GioTraCuoi,
       CAST(100000 + 50000 * (p.n % 3) AS DECIMAL(14,0)) AS Coc
INTO #HD0
FROM #Phieu p
JOIN (SELECT ct.MaPhieuThue,
             SUM(ct.DonGiaApDung *
                 CASE ct.HinhThucThue
                      WHEN N'Theo giờ' THEN CEILING(DATEDIFF(MINUTE, ct.GioNhan, ct.GioTra) / 60.0)
                      WHEN N'Qua đêm'  THEN 1
                      ELSE CEILING(DATEDIFF(HOUR, ct.GioNhan, ct.GioTra) / 24.0)
                 END) AS TienPhong
      FROM ChiTietPhieuThue ct
      WHERE ct.GioTra IS NOT NULL
      GROUP BY ct.MaPhieuThue) tp ON tp.MaPhieuThue = p.MaPhieuThue
LEFT JOIN (SELECT d.MaPhieuThue, SUM(d.SoLuong * d.DonGiaApDung) AS TienDV
           FROM DungDichVu d
           GROUP BY d.MaPhieuThue) dv ON dv.MaPhieuThue = p.MaPhieuThue
JOIN (SELECT MaPhieuThue, MAX(GioTra) AS GioTraCuoi
      FROM ChiTietPhieuThue
      GROUP BY MaPhieuThue) tg ON tg.MaPhieuThue = p.MaPhieuThue
JOIN KhachHang kh ON kh.MaKH = p.MaKH
JOIN LoaiKhachHang lk ON lk.MaLoaiKH = kh.MaLoaiKH
WHERE p.TrangThai = N'Hoàn tất';

INSERT INTO ThanhToan (MaThanhToan, MaPhieuThue, MaNV, NgayGioThanhToan, PhuongThuc, SoTien, LoaiKhoan)
SELECT 'TTC' + RIGHT('0000' + CAST(p.n AS VARCHAR(4)), 4), p.MaPhieuThue, p.MaNV,
       DATEADD(MINUTE, 10, p.NgayLap),
       CASE p.n % 3 WHEN 0 THEN N'Tiền mặt' WHEN 1 THEN N'Chuyển khoản' ELSE N'Thẻ' END,
       100000 + 50000 * (p.n % 3),
       N'Đặt cọc'
FROM #Phieu p;

INSERT INTO ThanhToan (MaThanhToan, MaPhieuThue, MaNV, NgayGioThanhToan, PhuongThuc, SoTien, LoaiKhoan)
SELECT 'TTH' + RIGHT('0000' + CAST(p.n AS VARCHAR(4)), 4), p.MaPhieuThue, p.MaNV,
       DATEADD(DAY, 1, p.NgayLap),
       CASE p.n % 3 WHEN 0 THEN N'Tiền mặt' WHEN 1 THEN N'Chuyển khoản' ELSE N'Thẻ' END,
       100000 + 50000 * (p.n % 3),
       N'Hoàn tiền'
FROM #Phieu p
WHERE p.TrangThai = N'Đã hủy';

INSERT INTO HoaDon (MaHD, MaPhieuThue, MaNV, NgayLap, TienPhong, TienDichVu, TienPhuThu, UuDai, TyLeVAT, TrangThai)
SELECT 'HD' + RIGHT('0000' + CAST(h.n AS VARCHAR(4)), 4), h.MaPhieuThue, h.MaNV,
       DATEADD(MINUTE, 15, h.GioTraCuoi),
       h.TienPhong, h.TienDichVu, h.TienPhuThu,
       CAST(ROUND((h.TienPhong + h.TienDichVu + h.TienPhuThu) * h.PhanTramUuDai / 100.0, 0) AS DECIMAL(14,0)),
       10,
       N'Chưa thanh toán'
FROM #HD0 h;

INSERT INTO ThanhToan (MaThanhToan, MaPhieuThue, MaNV, NgayGioThanhToan, PhuongThuc, SoTien, LoaiKhoan)
SELECT 'TTT' + RIGHT('0000' + CAST(h.n AS VARCHAR(4)), 4), h.MaPhieuThue, h.MaNV,
       DATEADD(MINUTE, 30, h.GioTraCuoi),
       CASE (h.n + 1) % 3 WHEN 0 THEN N'Tiền mặt' WHEN 1 THEN N'Chuyển khoản' ELSE N'Thẻ' END,
       CASE WHEN h.n IN (34, 35, 36) THEN ROUND((hd.TongTien - h.Coc) / 2.0, 0)
            ELSE hd.TongTien - h.Coc END,
       N'Thanh toán'
FROM #HD0 h
JOIN HoaDon hd ON hd.MaPhieuThue = h.MaPhieuThue;

UPDATE HoaDon SET TrangThai = N'Đã thanh toán'
WHERE MaPhieuThue IN (SELECT MaPhieuThue FROM #HD0 WHERE n NOT IN (34, 35, 36));

UPDATE ph SET TinhTrang = N'Đang thuê'
FROM Phong ph
JOIN ChiTietPhieuThue ct ON ct.MaPhong = ph.MaPhong
JOIN PhieuThue p ON p.MaPhieuThue = ct.MaPhieuThue
WHERE p.TrangThai = N'Đang thuê';

UPDATE Phong SET TinhTrang = N'Đang dọn' WHERE MaPhong IN ('P05', 'P06');
UPDATE Phong SET TinhTrang = N'Bảo trì'  WHERE MaPhong IN ('P29', 'P30');

COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

IF OBJECT_ID('tempdb..#N')     IS NOT NULL DROP TABLE #N;
IF OBJECT_ID('tempdb..#TK')    IS NOT NULL DROP TABLE #TK;
IF OBJECT_ID('tempdb..#Phieu') IS NOT NULL DROP TABLE #Phieu;
IF OBJECT_ID('tempdb..#HD0')   IS NOT NULL DROP TABLE #HD0;
GO

/* ============================================================================
   4. TRIGGER NGHIỆP VỤ
   ============================================================================ */

CREATE TRIGGER TR_ChiTietPhieuThue_KiemTra
ON ChiTietPhieuThue
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT 1
               FROM inserted i
               JOIN Phong ph ON ph.MaPhong = i.MaPhong
               JOIN LoaiPhong lp ON lp.MaLoaiPhong = ph.MaLoaiPhong
               WHERE i.SoNguoiDuKien > lp.SucChua)
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 50001, N'Số người dự kiến vượt quá sức chứa của loại phòng.', 1;
    END;

    IF EXISTS (SELECT 1
               FROM inserted i
               JOIN PhieuThue pt1 ON pt1.MaPhieuThue = i.MaPhieuThue
               JOIN ChiTietPhieuThue c ON c.MaPhong = i.MaPhong
                    AND (c.MaPhieuThue <> i.MaPhieuThue OR c.STT <> i.STT)
               JOIN PhieuThue pt2 ON pt2.MaPhieuThue = c.MaPhieuThue
               WHERE pt1.TrangThai <> N'Đã hủy'
                 AND pt2.TrangThai <> N'Đã hủy'
                 AND i.GioNhan < ISNULL(c.GioTra, c.GioTraDuKien)
                 AND c.GioNhan < ISNULL(i.GioTra, i.GioTraDuKien))
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 50002, N'Phòng đã có phiếu thuê khác trong khoảng thời gian này.', 1;
    END;
END;
GO

CREATE TRIGGER TR_PhieuThue_TrangThai
ON PhieuThue
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT UPDATE(TrangThai) RETURN;

    IF EXISTS (SELECT 1
               FROM inserted i
               JOIN deleted d ON d.MaPhieuThue = i.MaPhieuThue
               JOIN ChiTietPhieuThue ct ON ct.MaPhieuThue = i.MaPhieuThue
               WHERE i.TrangThai = N'Hoàn tất' AND d.TrangThai <> N'Hoàn tất'
                 AND ct.GioTra IS NULL)
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 50003, N'Không thể hoàn tất phiếu thuê khi còn phòng chưa có giờ trả.', 1;
    END;

    IF EXISTS (SELECT 1
               FROM inserted i
               JOIN deleted d ON d.MaPhieuThue = i.MaPhieuThue
               JOIN ChiTietPhieuThue ct ON ct.MaPhieuThue = i.MaPhieuThue
               JOIN Phong ph ON ph.MaPhong = ct.MaPhong
               WHERE i.TrangThai = N'Đang thuê' AND d.TrangThai <> N'Đang thuê'
                 AND ph.TinhTrang <> N'Trống')
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 50004, N'Không thể nhận phòng: có phòng chưa ở trạng thái Trống (đang thuê, đang dọn hoặc bảo trì).', 1;
    END;

    UPDATE ph SET TinhTrang = N'Đang thuê'
    FROM Phong ph
    JOIN ChiTietPhieuThue ct ON ct.MaPhong = ph.MaPhong
    JOIN inserted i ON i.MaPhieuThue = ct.MaPhieuThue
    JOIN deleted d ON d.MaPhieuThue = i.MaPhieuThue
    WHERE i.TrangThai = N'Đang thuê' AND d.TrangThai <> N'Đang thuê';

    UPDATE ph SET TinhTrang = N'Đang dọn'
    FROM Phong ph
    JOIN ChiTietPhieuThue ct ON ct.MaPhong = ph.MaPhong
    JOIN inserted i ON i.MaPhieuThue = ct.MaPhieuThue
    JOIN deleted d ON d.MaPhieuThue = i.MaPhieuThue
    WHERE i.TrangThai IN (N'Hoàn tất', N'Đã hủy') AND d.TrangThai = N'Đang thuê'
      AND ph.TinhTrang = N'Đang thuê';
END;
GO

CREATE TRIGGER TR_ThanhToan_KiemTra
ON ThanhToan
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT 1
               FROM HoaDon hd
               CROSS APPLY (SELECT ISNULL(SUM(CASE t.LoaiKhoan WHEN N'Hoàn tiền' THEN -t.SoTien
                                                               ELSE t.SoTien END), 0) AS DaThu
                            FROM ThanhToan t
                            WHERE t.MaPhieuThue = hd.MaPhieuThue) x
               WHERE hd.TrangThai <> N'Đã hủy'
                 AND hd.MaPhieuThue IN (SELECT MaPhieuThue FROM inserted)
                 AND x.DaThu > hd.TongTien)
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 50005, N'Tổng số tiền đã thu vượt quá tổng tiền hóa đơn.', 1;
    END;
END;
GO

CREATE TRIGGER TR_HoaDon_KiemTra
ON HoaDon
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT 1
               FROM inserted i
               CROSS APPLY (SELECT ISNULL(SUM(CASE t.LoaiKhoan WHEN N'Hoàn tiền' THEN -t.SoTien
                                                               ELSE t.SoTien END), 0) AS DaThu
                            FROM ThanhToan t
                            WHERE t.MaPhieuThue = i.MaPhieuThue) x
               WHERE i.TrangThai <> N'Đã hủy'
                 AND (x.DaThu > i.TongTien
                      OR (i.TrangThai = N'Đã thanh toán' AND x.DaThu <> i.TongTien)))
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 50006, N'Số tiền đã thu không khớp với tổng tiền hóa đơn.', 1;
    END;
END;
GO

/* ============================================================================
   5. KIỂM TRA TÍNH TOÀN VẸN CỦA DỮ LIỆU MẪU
   ============================================================================ */

SELECT N'Phòng bị đặt trùng thời gian' AS KiemTra, COUNT(*) AS SoViPham
FROM ChiTietPhieuThue a
JOIN PhieuThue pa ON pa.MaPhieuThue = a.MaPhieuThue AND pa.TrangThai <> N'Đã hủy'
JOIN ChiTietPhieuThue b ON b.MaPhong = a.MaPhong
     AND (b.MaPhieuThue > a.MaPhieuThue OR (b.MaPhieuThue = a.MaPhieuThue AND b.STT > a.STT))
JOIN PhieuThue pb ON pb.MaPhieuThue = b.MaPhieuThue AND pb.TrangThai <> N'Đã hủy'
WHERE a.GioNhan < ISNULL(b.GioTra, b.GioTraDuKien)
  AND b.GioNhan < ISNULL(a.GioTra, a.GioTraDuKien)
UNION ALL
SELECT N'Số người dự kiến vượt sức chứa', COUNT(*)
FROM ChiTietPhieuThue ct
JOIN Phong ph ON ph.MaPhong = ct.MaPhong
JOIN LoaiPhong lp ON lp.MaLoaiPhong = ph.MaLoaiPhong
WHERE ct.SoNguoiDuKien > lp.SucChua
UNION ALL
SELECT N'Phiếu hoàn tất còn phòng chưa có giờ trả', COUNT(*)
FROM PhieuThue p
JOIN ChiTietPhieuThue ct ON ct.MaPhieuThue = p.MaPhieuThue
WHERE p.TrangThai = N'Hoàn tất' AND ct.GioTra IS NULL
UNION ALL
SELECT N'Phiếu đang thuê nhưng phòng chưa ở trạng thái Đang thuê', COUNT(*)
FROM PhieuThue p
JOIN ChiTietPhieuThue ct ON ct.MaPhieuThue = p.MaPhieuThue
JOIN Phong ph ON ph.MaPhong = ct.MaPhong
WHERE p.TrangThai = N'Đang thuê' AND ph.TinhTrang <> N'Đang thuê'
UNION ALL
SELECT N'Phiếu đang thuê đã quá giờ trả dự kiến', COUNT(*)
FROM PhieuThue p
JOIN ChiTietPhieuThue ct ON ct.MaPhieuThue = p.MaPhieuThue
WHERE p.TrangThai = N'Đang thuê' AND ct.GioTra IS NULL AND ct.GioTraDuKien < GETDATE()
UNION ALL
SELECT N'Hóa đơn có số đã thu không khớp', COUNT(*)
FROM HoaDon hd
CROSS APPLY (SELECT ISNULL(SUM(CASE t.LoaiKhoan WHEN N'Hoàn tiền' THEN -t.SoTien ELSE t.SoTien END), 0) AS DaThu
             FROM ThanhToan t WHERE t.MaPhieuThue = hd.MaPhieuThue) x
WHERE x.DaThu > hd.TongTien
   OR (hd.TrangThai = N'Đã thanh toán' AND x.DaThu <> hd.TongTien)
UNION ALL
SELECT N'Mốc đã xảy ra nhưng nằm ở tương lai',
       (SELECT COUNT(*) FROM PhieuThue WHERE NgayLap > GETDATE())
     + (SELECT COUNT(*) FROM ThanhToan WHERE NgayGioThanhToan > GETDATE())
     + (SELECT COUNT(*) FROM HoaDon WHERE NgayLap > GETDATE())
     + (SELECT COUNT(*) FROM ChiTietPhieuThue WHERE GioTra > GETDATE());
GO

/* ============================================================================
   6. TRUY VẤN XEM TOÀN BỘ CÁC BẢNG DỮ LIỆU
   ============================================================================ */

SELECT * FROM LoaiKhachHang;
SELECT * FROM KhachHang;
SELECT * FROM KhachHang_SDT;
SELECT * FROM KhachHang_Email;
SELECT * FROM NhanVien;
SELECT * FROM NhanVien_SDT;
SELECT * FROM NhanVien_Email;
SELECT * FROM TaiKhoan;
SELECT * FROM LoaiPhong;
SELECT * FROM Phong;
SELECT * FROM PhieuThue;
SELECT * FROM ChiTietPhieuThue;
SELECT * FROM KhachDiCung;
SELECT * FROM OCung;
SELECT * FROM DichVu;
SELECT * FROM DungDichVu;
SELECT * FROM ThanhToan;
SELECT * FROM HoaDon;
GO

SET NOEXEC OFF;
GO