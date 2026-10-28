USE QuanLyKhachSan;
GO

/*=============================================================================
  05_function.sql
  Yêu cầu 1.7: Tối thiểu 2 User-Defined Functions
  - ≥ 1 Scalar Function
  - ≥ 1 Table-Valued Function
  - Có ví dụ dùng trong SELECT
  - Có ví dụ dùng trong Procedure
=============================================================================*/

/*-----------------------------------------------------------------------------
  1. SCALAR FUNCTION
  fn_TinhThoiGianThue: Tính thời gian thuê (số giờ) giữa giờ nhận và giờ trả
-----------------------------------------------------------------------------*/
CREATE OR ALTER FUNCTION dbo.fn_TinhThoiGianThue
(
    @GioNhan DATETIME,
    @GioTra  DATETIME
)
RETURNS INT
AS
BEGIN
    -- Nếu thiếu dữ liệu hoặc giờ trả ≤ giờ nhận → trả về NULL
    IF @GioNhan IS NULL OR @GioTra IS NULL OR @GioTra <= @GioNhan
        RETURN NULL;

    -- Tính số giờ (làm tròn lên nếu có phút lẻ)
    RETURN CEILING(DATEDIFF(MINUTE, @GioNhan, @GioTra) / 60.0);
END;
GO

/*-----------------------------------------------------------------------------
  2. SCALAR FUNCTION
  fn_TinhTienPhongTheoHinhThuc: Tính tiền phòng theo hình thức thuê
-----------------------------------------------------------------------------*/
CREATE OR ALTER FUNCTION dbo.fn_TinhTienPhongTheoHinhThuc
(
    @MaPhong        VARCHAR(10),
    @HinhThucThue   NVARCHAR(20),
    @GioNhan        DATETIME,
    @GioTra         DATETIME
)
RETURNS DECIMAL(14,0)
AS
BEGIN
    DECLARE @DonGia DECIMAL(12,0) = 0;
    DECLARE @SoDonVi DECIMAL(10,2) = 0;
    DECLARE @TienPhong DECIMAL(14,0) = 0;

    -- Lấy đơn giá theo loại phòng
    SELECT 
        @DonGia = CASE @HinhThucThue
                      WHEN N'Theo giờ'  THEN lp.DonGiaTheoGio
                      WHEN N'Qua đêm'   THEN lp.DonGiaQuaDem
                      WHEN N'Theo ngày' THEN lp.DonGiaTheoNgay
                      ELSE 0
                  END
    FROM Phong p
    INNER JOIN LoaiPhong lp ON p.MaLoaiPhong = lp.MaLoaiPhong
    WHERE p.MaPhong = @MaPhong;

    IF @DonGia = 0 OR @GioNhan IS NULL OR @GioTra IS NULL OR @GioTra <= @GioNhan
        RETURN 0;

    -- Tính số đơn vị
    IF @HinhThucThue = N'Theo giờ'
        SET @SoDonVi = CEILING(DATEDIFF(MINUTE, @GioNhan, @GioTra) / 60.0);
    ELSE IF @HinhThucThue = N'Qua đêm'
        SET @SoDonVi = 1;
    ELSE IF @HinhThucThue = N'Theo ngày'
        SET @SoDonVi = CEILING(DATEDIFF(HOUR, @GioNhan, @GioTra) / 24.0);

    SET @TienPhong = @DonGia * @SoDonVi;

    RETURN @TienPhong;
END;
GO

/*-----------------------------------------------------------------------------
  3. TABLE-VALUED FUNCTION (Inline)
  fn_DanhSachPhongTrong: Trả về danh sách phòng đang trống
-----------------------------------------------------------------------------*/
CREATE OR ALTER FUNCTION dbo.fn_DanhSachPhongTrong()
RETURNS TABLE
AS
RETURN
(
    SELECT 
        p.MaPhong,
        p.SoPhong,
        p.Tang,
        p.TinhTrang,
        lp.MaLoaiPhong,
        lp.TenLoai,
        lp.SucChua,
        lp.DonGiaTheoGio,
        lp.DonGiaQuaDem,
        lp.DonGiaTheoNgay
    FROM Phong p
    INNER JOIN LoaiPhong lp ON p.MaLoaiPhong = lp.MaLoaiPhong
    WHERE p.TinhTrang = N'Trống'
);
GO

/*-----------------------------------------------------------------------------
  4. TABLE-VALUED FUNCTION (Multi-statement)
  fn_LichSuThueCuaKhach: Trả về lịch sử thuê phòng của 1 khách hàng
-----------------------------------------------------------------------------*/
CREATE OR ALTER FUNCTION dbo.fn_LichSuThueCuaKhach
(
    @MaKH VARCHAR(10)
)
RETURNS @KetQua TABLE
(
    MaPhieuThue      VARCHAR(12),
    NgayLap          DATETIME,
    TrangThai        NVARCHAR(20),
    SoPhong          VARCHAR(10),
    HinhThucThue     NVARCHAR(20),
    GioNhan          DATETIME,
    GioTra           DATETIME,
    ThoiGianThueGio  INT,               -- dùng scalar function
    TienPhongUocTinh DECIMAL(14,0)
)
AS
BEGIN
    INSERT INTO @KetQua
    SELECT 
        pt.MaPhieuThue,
        pt.NgayLap,
        pt.TrangThai,
        p.SoPhong,
        ct.HinhThucThue,
        ct.GioNhan,
        ct.GioTra,
        dbo.fn_TinhThoiGianThue(ct.GioNhan, ct.GioTra),   -- gọi scalar
        dbo.fn_TinhTienPhongTheoHinhThuc(ct.MaPhong, ct.HinhThucThue, ct.GioNhan, ct.GioTra)
    FROM PhieuThue pt
    INNER JOIN ChiTietPhieuThue ct ON pt.MaPhieuThue = ct.MaPhieuThue
    INNER JOIN Phong p ON ct.MaPhong = p.MaPhong
    WHERE pt.MaKH = @MaKH;

    RETURN;
END;
GO

/*=============================================================================
  VÍ DỤ SỬ DỤNG TRONG SELECT
=============================================================================*/

-- 1. Dùng Scalar Function tính thời gian thuê
PRINT N'=== Ví dụ 1: Thời gian thuê (số giờ) ===';
SELECT 
    MaPhieuThue,
    MaPhong,
    HinhThucThue,
    GioNhan,
    GioTra,
    dbo.fn_TinhThoiGianThue(GioNhan, GioTra) AS SoGioThue
FROM ChiTietPhieuThue
WHERE GioTra IS NOT NULL
ORDER BY SoGioThue DESC;
GO

-- 2. Dùng Scalar Function tính tiền phòng
PRINT N'=== Ví dụ 2: Tính tiền phòng ước tính ===';
SELECT 
    ct.MaPhieuThue,
    ct.MaPhong,
    ct.HinhThucThue,
    ct.GioNhan,
    ct.GioTra,
    dbo.fn_TinhTienPhongTheoHinhThuc(ct.MaPhong, ct.HinhThucThue, ct.GioNhan, ct.GioTra) AS TienPhongUocTinh
FROM ChiTietPhieuThue ct
WHERE ct.GioTra IS NOT NULL;
GO

-- 3. Dùng Table-Valued Function (Inline)
PRINT N'=== Ví dụ 3: Danh sách phòng trống ===';
SELECT * FROM dbo.fn_DanhSachPhongTrong();
GO

-- 4. Dùng Table-Valued Function (Multi-statement) + Scalar
PRINT N'=== Ví dụ 4: Lịch sử thuê của khách KH001 ===';
SELECT * FROM dbo.fn_LichSuThueCuaKhach('KH001');
GO

/*=============================================================================
  VÍ DỤ SỬ DỤNG TRONG STORED PROCEDURE
=============================================================================*/

CREATE OR ALTER PROCEDURE dbo.usp_BaoCaoKhachHangVaPhongTrong
    @MaKH VARCHAR(10) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Phần 1: Lịch sử thuê của khách (dùng TVF + Scalar bên trong)
    IF @MaKH IS NOT NULL
    BEGIN
        PRINT N'--- Lịch sử thuê phòng của khách ---';
        SELECT * FROM dbo.fn_LichSuThueCuaKhach(@MaKH);
    END

    -- Phần 2: Các chi tiết thuê có thời gian thuê > trung bình (dùng Scalar)
    PRINT N'--- Chi tiết thuê có thời gian > trung bình hệ thống ---';
    SELECT 
        ct.MaPhieuThue,
        ct.MaPhong,
        ct.HinhThucThue,
        ct.GioNhan,
        ct.GioTra,
        dbo.fn_TinhThoiGianThue(ct.GioNhan, ct.GioTra) AS SoGioThue
    FROM ChiTietPhieuThue ct
    WHERE ct.GioTra IS NOT NULL
      AND dbo.fn_TinhThoiGianThue(ct.GioNhan, ct.GioTra) > (
            SELECT AVG(CAST(dbo.fn_TinhThoiGianThue(GioNhan, GioTra) AS FLOAT))
            FROM ChiTietPhieuThue
            WHERE GioTra IS NOT NULL
        );

    -- Phần 3: Danh sách phòng trống (dùng TVF)
    PRINT N'--- Danh sách phòng đang trống ---';
    SELECT * FROM dbo.fn_DanhSachPhongTrong()
    ORDER BY Tang, SoPhong;
END;
GO

-- Chạy thử procedure
PRINT N'=== Chạy procedure với khách KH008 ===';
EXEC dbo.usp_BaoCaoKhachHangVaPhongTrong @MaKH = 'KH008';
GO

PRINT N'=== Chạy procedure không truyền MaKH ===';
EXEC dbo.usp_BaoCaoKhachHangVaPhongTrong;
GO