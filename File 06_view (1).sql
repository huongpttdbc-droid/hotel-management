/* ============================================================================
   QUẢN LÝ KHÁCH SẠN  |  CSDL: QuanLyKhachSan
   TẠO VIEW 
   ============================================================================ */

USE QuanLyKhachSan;
GO



CREATE OR ALTER VIEW dbo.vw_TrangThaiPhong
AS
SELECT
    ph.MaPhong,
    ph.SoPhong,
    ph.Tang,
    ph.TinhTrang,
    ph.MaLoaiPhong,
    lp.TenLoai          AS TenLoaiPhong,
    lp.SucChua,
    lp.DonGiaTheoGio,
    lp.DonGiaQuaDem,
    lp.DonGiaTheoNgay,
    lp.MoTa             AS MoTaLoaiPhong
FROM dbo.Phong AS ph
INNER JOIN dbo.LoaiPhong AS lp
        ON lp.MaLoaiPhong = ph.MaLoaiPhong;
GO


/* ----------------------------------------------------------------------------
   VIEW 2 : dbo.vw_ChiTietHoaDon
      ---------------------------------------------------------------------------- */
CREATE OR ALTER VIEW dbo.vw_ChiTietHoaDon
AS
SELECT
    -- Hóa đơn
    hd.MaHD,
    hd.NgayLap                                  AS NgayLapHoaDon,
    hd.TrangThai                                AS TrangThaiHoaDon,

    -- Phiếu thuê
    pt.MaPhieuThue,
    pt.TrangThai                                AS TrangThaiPhieuThue,

    -- Khách hàng
    kh.MaKH,
    kh.HoTen                                    AS HoTenKhachHang,
    kh.CCCD                                     AS CCCDKhachHang,
    lkh.TenLoai                                 AS HangKhachHang,
    lkh.PhanTramUuDai,

    -- Nhân viên lập hóa đơn
    nv.MaNV                                     AS MaNVLapHoaDon,
    nv.HoTen                                    AS HoTenNVLapHoaDon,

    -- Phòng
    tp.SoLuongPhong,
    tp.DanhSachSoPhong,
    tp.GioNhanDauTien,
    tp.GioTraCuoiCung,

    -- Tiền
    tp.TienPhong,
    ISNULL(dv.SoLanDungDV, 0)                   AS SoLanDungDV,
    ISNULL(dv.TienDichVu, 0)                    AS TienDichVu,
    hd.TienPhuThu,
    s1.TongTruocUuDai,
    hd.UuDai                                    AS TienUuDai,
    CAST(s3.TongThanhTien - s2.TongSauUuDai AS DECIMAL(14,0))  AS ThueVAT_10,
    s3.TongThanhTien,

    -- Thanh toán
    ISNULL(tt.TienDatCoc, 0)                    AS TienDatCoc,
    ISNULL(tt.TienThanhToanThem, 0)             AS TienThanhToanThem,
    ISNULL(tt.TongDaTra, 0)                     AS TongDaThanhToan,
    s3.TongThanhTien - ISNULL(tt.TongDaTra, 0)  AS SoTienConNo

FROM dbo.HoaDon AS hd
INNER JOIN dbo.PhieuThue AS pt
        ON pt.MaPhieuThue = hd.MaPhieuThue
INNER JOIN dbo.KhachHang AS kh
        ON kh.MaKH = pt.MaKH
INNER JOIN dbo.LoaiKhachHang AS lkh
        ON lkh.MaLoaiKH = kh.MaLoaiKH
INNER JOIN dbo.NhanVien AS nv
        ON nv.MaNV = hd.MaNV

-- Tiền phòng theo từng phiếu thuê
INNER JOIN (
    SELECT
        ct.MaPhieuThue,
        COUNT(ct.STT)                                                    AS SoLuongPhong,
        STRING_AGG(ph.SoPhong, ', ') WITHIN GROUP (ORDER BY ph.SoPhong)  AS DanhSachSoPhong,
        MIN(ct.GioNhan)                                                  AS GioNhanDauTien,
        MAX(ct.GioTra)                                                   AS GioTraCuoiCung,
        CAST(SUM(
            CASE ct.HinhThucThue
                WHEN N'Theo giờ' THEN lp.DonGiaTheoGio * CEILING(DATEDIFF(MINUTE, ct.GioNhan, ct.GioTra) / 60.0)
                WHEN N'Qua đêm'  THEN lp.DonGiaQuaDem
                ELSE                  lp.DonGiaTheoNgay * CEILING(DATEDIFF(HOUR, ct.GioNhan, ct.GioTra) / 24.0)
            END
        ) AS DECIMAL(14,0))                                              AS TienPhong
    FROM dbo.ChiTietPhieuThue AS ct
    INNER JOIN dbo.Phong AS ph
            ON ph.MaPhong = ct.MaPhong
    INNER JOIN dbo.LoaiPhong AS lp
            ON lp.MaLoaiPhong = ph.MaLoaiPhong
    WHERE ct.GioTra IS NOT NULL
    GROUP BY ct.MaPhieuThue
) AS tp
        ON tp.MaPhieuThue = hd.MaPhieuThue

-- Tiền dịch vụ theo từng phiếu thuê
LEFT JOIN (
    SELECT
        ddv.MaPhieuThue,
        COUNT(*)                                                         AS SoLanDungDV,
        CAST(SUM(ddv.SoLuong * d.DonGia) AS DECIMAL(14,0))               AS TienDichVu
    FROM dbo.DungDichVu AS ddv
    INNER JOIN dbo.DichVu AS d
            ON d.MaDichVu = ddv.MaDichVu
    GROUP BY ddv.MaPhieuThue
) AS dv
        ON dv.MaPhieuThue = hd.MaPhieuThue

-- Các khoản đã thanh toán theo từng phiếu thuê (hoàn tiền được trừ đi)
LEFT JOIN (
    SELECT
        pay.MaPhieuThue,
        CAST(SUM(CASE WHEN pay.LoaiKhoan = N'Đặt cọc'    THEN pay.SoTien ELSE 0 END) AS DECIMAL(14,0)) AS TienDatCoc,
        CAST(SUM(CASE WHEN pay.LoaiKhoan = N'Thanh toán' THEN pay.SoTien ELSE 0 END) AS DECIMAL(14,0)) AS TienThanhToanThem,
        CAST(SUM(CASE
                     WHEN pay.LoaiKhoan IN (N'Đặt cọc', N'Thanh toán') THEN  pay.SoTien
                     WHEN pay.LoaiKhoan = N'Hoàn tiền'                 THEN -pay.SoTien
                     ELSE 0
                 END) AS DECIMAL(14,0))                                                                AS TongDaTra
    FROM dbo.ThanhToan AS pay
    GROUP BY pay.MaPhieuThue
) AS tt
        ON tt.MaPhieuThue = hd.MaPhieuThue

-- Tính tiền một lần duy nhất, các cột phía trên dùng lại kết quả này
CROSS APPLY (SELECT tp.TienPhong + ISNULL(dv.TienDichVu, 0) + hd.TienPhuThu         AS TongTruocUuDai) AS s1
CROSS APPLY (SELECT s1.TongTruocUuDai - hd.UuDai                                     AS TongSauUuDai)   AS s2
CROSS APPLY (SELECT CAST(ROUND(s2.TongSauUuDai * 1.1, 0) AS DECIMAL(14,0))           AS TongThanhTien)  AS s3;
GO


/* ----------------------------------------------------------------------------
   VIEW 3 : dbo.vw_TongHopDoanhThu
   ---------------------------------------------------------------------------- */
CREATE OR ALTER VIEW dbo.vw_TongHopDoanhThu
AS
SELECT
    k.Nam,
    k.Thang,
    RIGHT('0' + CAST(k.Thang AS VARCHAR(2)), 2) + '/' + CAST(k.Nam AS VARCHAR(4))  AS KyBaoCao,

    -- Số lượng
    COUNT(c.MaHD)                                                                   AS TongSoHoaDon,
    SUM(CASE WHEN c.TrangThaiHoaDon = N'Đã thanh toán'   THEN 1 ELSE 0 END)         AS SoHoaDonDaThanhToan,
    SUM(CASE WHEN c.TrangThaiHoaDon = N'Chưa thanh toán' THEN 1 ELSE 0 END)         AS SoHoaDonChuaThanhToan,
    SUM(c.SoLuongPhong)                                                             AS TongLuotPhongThue,

    -- Doanh thu
    SUM(c.TienPhong)                                                                AS DoanhThuTienPhong,
    SUM(c.TienDichVu)                                                               AS DoanhThuDichVu,
    SUM(c.TienPhuThu)                                                               AS TongTienPhuThu,
    SUM(c.TongTruocUuDai)                                                           AS TongDoanhThuTruocUuDai,
    SUM(c.TienUuDai)                                                                AS TongTienUuDai,
    SUM(c.ThueVAT_10)                                                               AS TongThueVAT,
    SUM(c.TongThanhTien)                                                            AS TongDoanhThuSauThue,

    -- Thu tiền và công nợ
    SUM(c.TongDaThanhToan)                                                          AS TongThucThu,
    SUM(c.SoTienConNo)                                                              AS TongCongNoConLai
FROM dbo.vw_ChiTietHoaDon AS c
CROSS APPLY (SELECT YEAR(c.NgayLapHoaDon) AS Nam, MONTH(c.NgayLapHoaDon) AS Thang) AS k
WHERE c.TrangThaiHoaDon <> N'Đã hủy'
GROUP BY k.Nam, k.Thang;
GO


/* ----------------------------------------------------------------------------
   VIEW 4 : dbo.vw_PhongTrongKhaDung
      ---------------------------------------------------------------------------- */
CREATE OR ALTER VIEW dbo.vw_PhongTrongKhaDung
AS
SELECT
    ph.MaPhong,
    ph.SoPhong,
    ph.Tang,
    ph.TinhTrang,
    ph.MaLoaiPhong
FROM dbo.Phong AS ph
WHERE ph.TinhTrang = N'Trống'
WITH CHECK OPTION;
GO


/* ============================================================================
   KIỂM THỬ: SELECT * FROM từng view trên dữ liệu mẫu
   ============================================================================ */

-- 1. Trạng thái phòng 
SELECT * FROM dbo.vw_TrangThaiPhong    ORDER BY Tang, SoPhong;

-- 2. Chi tiết hóa đơn
SELECT * FROM dbo.vw_ChiTietHoaDon     ORDER BY MaHD;

-- 3. Tổng hợp doanh thu theo tháng
SELECT * FROM dbo.vw_TongHopDoanhThu   ORDER BY Nam, Thang;

-- 4. Phòng trống sẵn sàng cho đặt online
SELECT * FROM dbo.vw_PhongTrongKhaDung ORDER BY Tang, SoPhong;
GO


/* ----------------------------------------------------------------------------
   ĐỐI CHIẾU NHANH (tùy chọn)
   ---------------------------------------------------------------------------- */

-- Hai số phải bằng nhau: các INNER JOIN trong vw_ChiTietHoaDon không làm rơi hóa đơn nào
SELECT
    (SELECT COUNT(*) FROM dbo.HoaDon)           AS SoDong_BangHoaDon,
    (SELECT COUNT(*) FROM dbo.vw_ChiTietHoaDon) AS SoDong_ViewChiTietHoaDon;

-- Hóa đơn còn nợ (dữ liệu mẫu có các hóa đơn 'Chưa thanh toán')
SELECT MaHD, HoTenKhachHang, TongThanhTien, TongDaThanhToan, SoTienConNo
FROM   dbo.vw_ChiTietHoaDon
WHERE  SoTienConNo > 0
ORDER BY MaHD;
GO



