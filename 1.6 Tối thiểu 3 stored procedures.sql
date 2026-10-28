USE QuanLyKhachSan;
GO

/* =========================================================
   FILE: 04_stored_procedure.sql
   Mô tả: Ít nhất 3 Stored Procedures + 1 Function
   Yêu cầu:
   - ≥ 3 procedure
   - Ít nhất 1 procedure có tham số OUTPUT
   - TRY...CATCH, kiểm tra trùng lịch và sức chứa
   - Có procedure gọi function của chính mình
   - Test thành công và thất bại
   ========================================================= */

-- =========================================================
-- 1. FUNCTION: Tính số giờ thuê (dùng trong procedure)
-- =========================================================
IF OBJECT_ID('dbo.fn_TinhSoGioThue', 'FN') IS NOT NULL
    DROP FUNCTION dbo.fn_TinhSoGioThue;
GO

CREATE FUNCTION dbo.fn_TinhSoGioThue
(
    @GioNhan DATETIME,
    @GioTra  DATETIME
)
RETURNS INT
AS
BEGIN
    IF @GioTra IS NULL OR @GioNhan IS NULL OR @GioTra <= @GioNhan
        RETURN 0;

    -- Làm tròn lên nếu có phút lẻ
    RETURN CEILING(DATEDIFF(MINUTE, @GioNhan, @GioTra) / 60.0);
END;
GO

-- =========================================================
-- 2. PROCEDURE 1: sp_KiemTraPhongTrong
--    - Kiểm tra phòng có trống trong khoảng thời gian
--    - Có OUTPUT parameter
--    - Gọi function fn_TinhSoGioThue
-- =========================================================
IF OBJECT_ID('dbo.sp_KiemTraPhongTrong', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_KiemTraPhongTrong;
GO

CREATE PROCEDURE dbo.sp_KiemTraPhongTrong
    @MaPhong          VARCHAR(10),
    @GioNhan          DATETIME,
    @GioTra           DATETIME,
    @SoNguoiDuKien    TINYINT,
    @KetQua           NVARCHAR(200) OUTPUT,   -- OUTPUT
    @SoGioThue        INT OUTPUT              -- OUTPUT (gọi function)
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        -- Kiểm tra tham số đầu vào
        IF @MaPhong IS NULL OR @GioNhan IS NULL OR @GioTra IS NULL OR @SoNguoiDuKien IS NULL
        BEGIN
            SET @KetQua = N'Thiếu tham số bắt buộc.';
            SET @SoGioThue = 0;
            RETURN;
        END;

        IF @GioTra <= @GioNhan
        BEGIN
            SET @KetQua = N'Giờ trả phải sau giờ nhận.';
            SET @SoGioThue = 0;
            RETURN;
        END;

        -- Gọi function của chính mình
        SET @SoGioThue = dbo.fn_TinhSoGioThue(@GioNhan, @GioTra);

        -- Kiểm tra phòng tồn tại
        IF NOT EXISTS (SELECT 1 FROM Phong WHERE MaPhong = @MaPhong)
        BEGIN
            SET @KetQua = N'Phòng không tồn tại.';
            RETURN;
        END;

        -- Kiểm tra sức chứa
        DECLARE @SucChua TINYINT;
        SELECT @SucChua = lp.SucChua
        FROM Phong p
        INNER JOIN LoaiPhong lp ON p.MaLoaiPhong = lp.MaLoaiPhong
        WHERE p.MaPhong = @MaPhong;

        IF @SoNguoiDuKien > @SucChua
        BEGIN
            SET @KetQua = N'Số người dự kiến (' + CAST(@SoNguoiDuKien AS NVARCHAR(5))
                        + N') vượt quá sức chứa phòng (' + CAST(@SucChua AS NVARCHAR(5)) + N').';
            RETURN;
        END;

        -- Kiểm tra trùng lịch (overlap)
        -- Hai khoảng thời gian overlap nếu: GioNhan < @GioTra AND (GioTra IS NULL OR GioTra > @GioNhan)
        -- Chỉ xét phiếu chưa hủy / chưa hoàn tất
        IF EXISTS (
            SELECT 1
            FROM ChiTietPhieuThue ct
            INNER JOIN PhieuThue pt ON ct.MaPhieuThue = pt.MaPhieuThue
            WHERE ct.MaPhong = @MaPhong
              AND pt.TrangThai IN (N'Đã đặt', N'Đang thuê')
              AND ct.GioNhan < @GioTra
              AND (ct.GioTra IS NULL OR ct.GioTra > @GioNhan)
        )
        BEGIN
            SET @KetQua = N'Phòng đã có lịch thuê trùng trong khoảng thời gian này.';
            RETURN;
        END;

        -- Thành công
        SET @KetQua = N'Phòng trống và đủ sức chứa. Số giờ thuê ước tính: '
                    + CAST(@SoGioThue AS NVARCHAR(10));
    END TRY
    BEGIN CATCH
        SET @KetQua = N'Lỗi hệ thống: ' + ERROR_MESSAGE();
        SET @SoGioThue = 0;
    END CATCH
END;
GO

-- =========================================================
-- 3. PROCEDURE 2: sp_DatPhong
--    - Đặt phòng (tạo phiếu thuê + chi tiết)
--    - TRY...CATCH
--    - Kiểm tra trùng lịch + sức chứa (gọi sp_KiemTraPhongTrong)
--    - Có OUTPUT
-- =========================================================
IF OBJECT_ID('dbo.sp_DatPhong', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_DatPhong;
GO

CREATE PROCEDURE dbo.sp_DatPhong
    @MaKH             VARCHAR(10),
    @MaNV             VARCHAR(10),
    @MaPhong          VARCHAR(10),
    @HinhThucThue     NVARCHAR(20),
    @SoNguoiDuKien    TINYINT,
    @GioNhan          DATETIME,
    @GioTra           DATETIME,                 -- Bắt buộc truyền (có thể đặt xa nếu chưa biết)
    @GhiChu           NVARCHAR(500) = NULL,
    @MaPhieuThueMoi   VARCHAR(12) OUTPUT,       -- OUTPUT
    @ThongBao         NVARCHAR(300) OUTPUT      -- OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT OFF;   -- Cho phép xử lý lỗi thủ công

    DECLARE @KetQuaKiemTra NVARCHAR(200);
    DECLARE @SoGio         INT;
    DECLARE @STT           INT = 1;
    DECLARE @MaPhieu       VARCHAR(12);
    DECLARE @MaxNum        INT;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 1. Kiểm tra khách hàng & nhân viên tồn tại
        IF NOT EXISTS (SELECT 1 FROM KhachHang WHERE MaKH = @MaKH)
        BEGIN
            SET @ThongBao = N'Khách hàng không tồn tại.';
            SET @MaPhieuThueMoi = NULL;
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        IF NOT EXISTS (SELECT 1 FROM NhanVien WHERE MaNV = @MaNV)
        BEGIN
            SET @ThongBao = N'Nhân viên không tồn tại.';
            SET @MaPhieuThueMoi = NULL;
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        -- 2. Kiểm tra hình thức thuê hợp lệ
        IF @HinhThucThue NOT IN (N'Theo giờ', N'Qua đêm', N'Theo ngày')
        BEGIN
            SET @ThongBao = N'Hình thức thuê không hợp lệ. Chỉ chấp nhận: Theo giờ, Qua đêm, Theo ngày.';
            SET @MaPhieuThueMoi = NULL;
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        -- 3. Kiểm tra giờ hợp lệ
        IF @GioNhan IS NULL OR @GioTra IS NULL OR @GioTra <= @GioNhan
        BEGIN
            SET @ThongBao = N'Giờ nhận/trả không hợp lệ.';
            SET @MaPhieuThueMoi = NULL;
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        -- 4. Gọi procedure kiểm tra phòng trống + sức chứa + trùng lịch
        EXEC dbo.sp_KiemTraPhongTrong
            @MaPhong       = @MaPhong,
            @GioNhan       = @GioNhan,
            @GioTra        = @GioTra,
            @SoNguoiDuKien = @SoNguoiDuKien,
            @KetQua        = @KetQuaKiemTra OUTPUT,
            @SoGioThue     = @SoGio OUTPUT;

        IF @KetQuaKiemTra NOT LIKE N'Phòng trống%'
        BEGIN
            SET @ThongBao = @KetQuaKiemTra;
            SET @MaPhieuThueMoi = NULL;
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        -- 5. Tạo mã phiếu thuê mới an toàn (PT + 4 chữ số)
        SELECT @MaxNum = ISNULL(MAX(
            CASE 
                WHEN MaPhieuThue LIKE 'PT[0-9][0-9][0-9][0-9]' 
                THEN CAST(SUBSTRING(MaPhieuThue, 3, 4) AS INT)
                ELSE 0 
            END
        ), 0)
        FROM PhieuThue;

        SET @MaPhieu = 'PT' + RIGHT('0000' + CAST(@MaxNum + 1 AS VARCHAR(4)), 4);

        -- 6. Insert PhieuThue
        INSERT INTO PhieuThue (MaPhieuThue, NgayLap, TrangThai, MaKH, MaNV)
        VALUES (@MaPhieu, GETDATE(), N'Đã đặt', @MaKH, @MaNV);

        -- 7. Insert ChiTietPhieuThue
        INSERT INTO ChiTietPhieuThue
            (MaPhieuThue, STT, MaPhong, HinhThucThue, SoNguoiDuKien,
             KhachDatCoOPhongNay, GioNhan, GioTra, GhiChu)
        VALUES
            (@MaPhieu, @STT, @MaPhong, @HinhThucThue, @SoNguoiDuKien,
             1, @GioNhan, @GioTra, @GhiChu);

        -- 8. Cập nhật tình trạng phòng nếu đang trong thời gian thuê
        IF @GioNhan <= GETDATE() AND @GioTra > GETDATE()
        BEGIN
            UPDATE Phong
            SET TinhTrang = N'Đang thuê'
            WHERE MaPhong = @MaPhong;
        END;

        COMMIT TRANSACTION;

        SET @MaPhieuThueMoi = @MaPhieu;
        SET @ThongBao = N'Đặt phòng thành công. Mã phiếu: ' + @MaPhieu
                      + N'. Số giờ thuê ước tính: ' + CAST(@SoGio AS NVARCHAR(10));
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @MaPhieuThueMoi = NULL;
        SET @ThongBao = N'Lỗi khi đặt phòng: ' + ERROR_MESSAGE();
    END CATCH
END;
GO

-- =========================================================
-- 4. PROCEDURE 3: sp_ThemDichVu
--    - Thêm dịch vụ vào chi tiết phiếu thuê
--    - TRY...CATCH
--    - Có OUTPUT
-- =========================================================
IF OBJECT_ID('dbo.sp_ThemDichVu', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_ThemDichVu;
GO

CREATE PROCEDURE dbo.sp_ThemDichVu
    @MaPhieuThue   VARCHAR(12),
    @STT           INT,
    @MaDichVu      VARCHAR(10),
    @SoLuong       INT = 1,
    @GioBD         DATETIME = NULL,
    @ThongBao      NVARCHAR(300) OUTPUT   -- OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT OFF;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Kiểm tra phiếu + chi tiết tồn tại và còn hiệu lực
        IF NOT EXISTS (
            SELECT 1
            FROM ChiTietPhieuThue ct
            INNER JOIN PhieuThue pt ON ct.MaPhieuThue = pt.MaPhieuThue
            WHERE ct.MaPhieuThue = @MaPhieuThue
              AND ct.STT = @STT
              AND pt.TrangThai IN (N'Đã đặt', N'Đang thuê')
        )
        BEGIN
            SET @ThongBao = N'Phiếu thuê / chi tiết không tồn tại hoặc đã hoàn tất/hủy.';
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        -- Kiểm tra dịch vụ tồn tại
        IF NOT EXISTS (SELECT 1 FROM DichVu WHERE MaDichVu = @MaDichVu)
        BEGIN
            SET @ThongBao = N'Dịch vụ không tồn tại.';
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        IF @SoLuong IS NULL OR @SoLuong <= 0
        BEGIN
            SET @ThongBao = N'Số lượng phải lớn hơn 0.';
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        -- Mặc định giờ bắt đầu = giờ nhận phòng nếu không truyền
        IF @GioBD IS NULL
        BEGIN
            SELECT @GioBD = GioNhan
            FROM ChiTietPhieuThue
            WHERE MaPhieuThue = @MaPhieuThue AND STT = @STT;
        END;

        -- Insert (cho phép nhiều lần dùng cùng dịch vụ nếu khác GioBD)
        INSERT INTO DungDichVu (MaPhieuThue, STT, MaDichVu, GioBD, GioKT, SoLuong)
        VALUES (@MaPhieuThue, @STT, @MaDichVu, @GioBD, NULL, @SoLuong);

        COMMIT TRANSACTION;

        SET @ThongBao = N'Thêm dịch vụ thành công.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @ThongBao = N'Lỗi khi thêm dịch vụ: ' + ERROR_MESSAGE();
    END CATCH
END;
GO

-- =========================================================
-- 5. PROCEDURE 4: sp_HuyPhieuThue
--    - Hủy phiếu thuê
--    - TRY...CATCH + OUTPUT
-- =========================================================
IF OBJECT_ID('dbo.sp_HuyPhieuThue', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_HuyPhieuThue;
GO

CREATE PROCEDURE dbo.sp_HuyPhieuThue
    @MaPhieuThue   VARCHAR(12),
    @MaNV          VARCHAR(10),          -- Nhân viên thực hiện hủy
    @ThongBao      NVARCHAR(300) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT OFF;

    BEGIN TRY
        BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM PhieuThue WHERE MaPhieuThue = @MaPhieuThue)
        BEGIN
            SET @ThongBao = N'Phiếu thuê không tồn tại.';
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        DECLARE @TrangThaiHienTai NVARCHAR(20);
        SELECT @TrangThaiHienTai = TrangThai
        FROM PhieuThue
        WHERE MaPhieuThue = @MaPhieuThue;

        IF @TrangThaiHienTai IN (N'Hoàn tất', N'Đã hủy')
        BEGIN
            SET @ThongBao = N'Không thể hủy phiếu ở trạng thái: ' + @TrangThaiHienTai;
            ROLLBACK TRANSACTION;
            RETURN;
        END;

        -- Cập nhật trạng thái
        UPDATE PhieuThue
        SET TrangThai = N'Đã hủy'
        WHERE MaPhieuThue = @MaPhieuThue;

        -- Trả phòng về trạng thái Trống
        UPDATE Phong
        SET TinhTrang = N'Trống'
        WHERE MaPhong IN (
            SELECT MaPhong
            FROM ChiTietPhieuThue
            WHERE MaPhieuThue = @MaPhieuThue
        )
        AND TinhTrang = N'Đang thuê';

        COMMIT TRANSACTION;

        SET @ThongBao = N'Hủy phiếu thuê thành công.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @ThongBao = N'Lỗi khi hủy phiếu: ' + ERROR_MESSAGE();
    END CATCH
END;
GO

-- =========================================================
-- PHẦN TEST (Thành công + Thất bại)
-- Chạy tuần tự để kiểm tra
-- =========================================================

PRINT N'========== TEST 1: sp_KiemTraPhongTrong - THÀNH CÔNG ==========';
DECLARE @KQ NVARCHAR(200), @SG INT;
EXEC dbo.sp_KiemTraPhongTrong
    @MaPhong       = 'P15',
    @GioNhan       = '2027-01-15 14:00',
    @GioTra        = '2027-01-17 12:00',
    @SoNguoiDuKien = 2,
    @KetQua        = @KQ OUTPUT,
    @SoGioThue     = @SG OUTPUT;
PRINT @KQ;
PRINT N'Số giờ: ' + CAST(ISNULL(@SG, 0) AS NVARCHAR(10));
GO

PRINT N'========== TEST 2: sp_KiemTraPhongTrong - THẤT BẠI (vượt sức chứa) ==========';
DECLARE @KQ2 NVARCHAR(200), @SG2 INT;
EXEC dbo.sp_KiemTraPhongTrong
    @MaPhong       = 'P01',          -- LP01 sức chứa = 2
    @GioNhan       = '2027-02-01 14:00',
    @GioTra        = '2027-02-02 12:00',
    @SoNguoiDuKien = 5,              -- > 2
    @KetQua        = @KQ2 OUTPUT,
    @SoGioThue     = @SG2 OUTPUT;
PRINT @KQ2;
GO

PRINT N'========== TEST 3: sp_KiemTraPhongTrong - THẤT BẠI (trùng lịch) ==========';
-- Dùng khoảng thời gian có dữ liệu mẫu (khoảng tháng 7/2026)
DECLARE @KQ3 NVARCHAR(200), @SG3 INT;
EXEC dbo.sp_KiemTraPhongTrong
    @MaPhong       = 'P01',
    @GioNhan       = '2026-07-01 14:00',
    @GioTra        = '2026-07-03 12:00',
    @SoNguoiDuKien = 1,
    @KetQua        = @KQ3 OUTPUT,
    @SoGioThue     = @SG3 OUTPUT;
PRINT @KQ3;
GO

PRINT N'========== TEST 4: sp_DatPhong - THÀNH CÔNG ==========';
DECLARE @MaPT VARCHAR(12), @TB NVARCHAR(300);
EXEC dbo.sp_DatPhong
    @MaKH           = 'KH001',
    @MaNV           = 'NV01',
    @MaPhong        = 'P20',
    @HinhThucThue   = N'Theo ngày',
    @SoNguoiDuKien  = 2,
    @GioNhan        = '2027-03-01 14:00',
    @GioTra         = '2027-03-03 12:00',
    @GhiChu         = N'Test đặt phòng thành công',
    @MaPhieuThueMoi = @MaPT OUTPUT,
    @ThongBao       = @TB OUTPUT;
PRINT @TB;
PRINT N'Mã phiếu mới: ' + ISNULL(@MaPT, N'NULL');
GO

PRINT N'========== TEST 5: sp_DatPhong - THẤT BẠI (khách không tồn tại) ==========';
DECLARE @MaPT2 VARCHAR(12), @TB2 NVARCHAR(300);
EXEC dbo.sp_DatPhong
    @MaKH           = 'KH999',          -- không tồn tại
    @MaNV           = 'NV01',
    @MaPhong        = 'P21',
    @HinhThucThue   = N'Theo giờ',
    @SoNguoiDuKien  = 1,
    @GioNhan        = '2027-03-10 10:00',
    @GioTra         = '2027-03-10 15:00',
    @MaPhieuThueMoi = @MaPT2 OUTPUT,
    @ThongBao       = @TB2 OUTPUT;
PRINT @TB2;
GO

PRINT N'========== TEST 6: sp_ThemDichVu - THÀNH CÔNG ==========';
DECLARE @TB3 NVARCHAR(300);
DECLARE @MaPTTest VARCHAR(12), @STTTest INT;

SELECT TOP 1 @MaPTTest = ct.MaPhieuThue, @STTTest = ct.STT
FROM ChiTietPhieuThue ct
INNER JOIN PhieuThue pt ON ct.MaPhieuThue = pt.MaPhieuThue
WHERE pt.TrangThai IN (N'Đã đặt', N'Đang thuê')
ORDER BY ct.MaPhieuThue DESC;

IF @MaPTTest IS NOT NULL
BEGIN
    EXEC dbo.sp_ThemDichVu
        @MaPhieuThue = @MaPTTest,
        @STT         = @STTTest,
        @MaDichVu    = 'DV05',      -- Nước suối
        @SoLuong     = 2,
        @ThongBao    = @TB3 OUTPUT;
    PRINT N'Phiếu ' + @MaPTTest + N': ' + @TB3;
END
ELSE
    PRINT N'Không tìm thấy phiếu để test thêm dịch vụ.';
GO

PRINT N'========== TEST 7: sp_ThemDichVu - THẤT BẠI (dịch vụ không tồn tại) ==========';
DECLARE @TB4 NVARCHAR(300);
DECLARE @MaPTTest2 VARCHAR(12), @STTTest2 INT;

SELECT TOP 1 @MaPTTest2 = ct.MaPhieuThue, @STTTest2 = ct.STT
FROM ChiTietPhieuThue ct
INNER JOIN PhieuThue pt ON ct.MaPhieuThue = pt.MaPhieuThue
WHERE pt.TrangThai IN (N'Đã đặt', N'Đang thuê')
ORDER BY ct.MaPhieuThue DESC;

IF @MaPTTest2 IS NOT NULL
BEGIN
    EXEC dbo.sp_ThemDichVu
        @MaPhieuThue = @MaPTTest2,
        @STT         = @STTTest2,
        @MaDichVu    = 'DV99',      -- không tồn tại
        @SoLuong     = 1,
        @ThongBao    = @TB4 OUTPUT;
    PRINT @TB4;
END
GO

PRINT N'========== TEST 8: sp_HuyPhieuThue ==========';
DECLARE @TB5 NVARCHAR(300);
DECLARE @MaPTHuy VARCHAR(12);

-- Ưu tiên hủy phiếu vừa tạo ở TEST 4 (nếu còn)
SELECT TOP 1 @MaPTHuy = MaPhieuThue
FROM PhieuThue
WHERE TrangThai = N'Đã đặt'
ORDER BY NgayLap DESC;

IF @MaPTHuy IS NOT NULL
BEGIN
    EXEC dbo.sp_HuyPhieuThue
        @MaPhieuThue = @MaPTHuy,
        @MaNV        = 'NV01',
        @ThongBao    = @TB5 OUTPUT;
    PRINT N'Hủy phiếu ' + @MaPTHuy + N': ' + @TB5;
END
ELSE
    PRINT N'Không có phiếu Đã đặt để hủy.';

-- Test hủy phiếu đã hoàn tất (thất bại)
DECLARE @TB6 NVARCHAR(300);
DECLARE @MaPTHoanTat VARCHAR(12);

SELECT TOP 1 @MaPTHoanTat = MaPhieuThue
FROM PhieuThue
WHERE TrangThai = N'Hoàn tất';

IF @MaPTHoanTat IS NOT NULL
BEGIN
    EXEC dbo.sp_HuyPhieuThue
        @MaPhieuThue = @MaPTHoanTat,
        @MaNV        = 'NV01',
        @ThongBao    = @TB6 OUTPUT;
    PRINT N'Hủy phiếu hoàn tất ' + @MaPTHoanTat + N': ' + @TB6;
END
GO

PRINT N'========== KẾT THÚC TEST ==========';
PRINT N'File 04_stored_procedure.sql đã được sửa và sẵn sàng bàn giao.';
GO