-- =============================================================================
-- SCRIPT XÓA DỮ LIỆU TEST KHÁCH HÀNG TỪ KH041 ĐẾN KH057 TRONG POSTGRESQL (SUPABASE)
-- Thứ tự xóa chuẩn: Bảng con cấp thấp nhất -> Ngược dần lên bảng cha
-- =============================================================================

DO $$
DECLARE
    v_count_ddv INT := 0;
    v_count_tt INT := 0;
    v_count_hd INT := 0;
    v_count_ctpt INT := 0;
    v_count_pt INT := 0;
    v_count_sdt INT := 0;
    v_count_email INT := 0;
    v_count_kh INT := 0;
    v_count_phong INT := 0;
BEGIN
    -- 0. Giải phóng các phòng liên quan về trạng thái 'Trống'
    WITH affected_rooms AS (
        SELECT DISTINCT ct."MaPhong"
        FROM "ChiTietPhieuThue" ct
        JOIN "PhieuThue" pt ON ct."MaPhieuThue" = pt."MaPhieuThue"
        WHERE pt."MaKH" >= 'KH041' AND pt."MaKH" <= 'KH057'
    )
    UPDATE "Phong" p
    SET "TinhTrang" = 'Trống'
    FROM affected_rooms ar
    WHERE p."MaPhong" = ar."MaPhong"
      AND p."TinhTrang" IN ('Đang thuê', 'Đang dọn');
    GET DIAGNOSTICS v_count_phong = ROW_COUNT;
    RAISE NOTICE '0. Đã cập nhật % phòng về trạng thái Trống.', v_count_phong;

    -- 1. Xóa DungDichVu (Khóa ngoại: (MaPhieuThue, STT) tham chiếu ChiTietPhieuThue)
    DELETE FROM "DungDichVu"
    WHERE "MaPhieuThue" IN (
        SELECT "MaPhieuThue" FROM "PhieuThue" WHERE "MaKH" >= 'KH041' AND "MaKH" <= 'KH057'
    );
    GET DIAGNOSTICS v_count_ddv = ROW_COUNT;
    RAISE NOTICE '1. Đã xóa % bản ghi trong DungDichVu.', v_count_ddv;

    -- 2. Xóa ThanhToan (Khóa ngoại: MaPhieuThue tham chiếu PhieuThue)
    DELETE FROM "ThanhToan"
    WHERE "MaPhieuThue" IN (
        SELECT "MaPhieuThue" FROM "PhieuThue" WHERE "MaKH" >= 'KH041' AND "MaKH" <= 'KH057'
    );
    GET DIAGNOSTICS v_count_tt = ROW_COUNT;
    RAISE NOTICE '2. Đã xóa % bản ghi trong ThanhToan.', v_count_tt;

    -- 3. Xóa HoaDon (Khóa ngoại: MaPhieuThue tham chiếu PhieuThue)
    DELETE FROM "HoaDon"
    WHERE "MaPhieuThue" IN (
        SELECT "MaPhieuThue" FROM "PhieuThue" WHERE "MaKH" >= 'KH041' AND "MaKH" <= 'KH057'
    );
    GET DIAGNOSTICS v_count_hd = ROW_COUNT;
    RAISE NOTICE '3. Đã xóa % bản ghi trong HoaDon.', v_count_hd;

    -- 4. Xóa ChiTietPhieuThue (Khóa ngoại: MaPhieuThue tham chiếu PhieuThue)
    DELETE FROM "ChiTietPhieuThue"
    WHERE "MaPhieuThue" IN (
        SELECT "MaPhieuThue" FROM "PhieuThue" WHERE "MaKH" >= 'KH041' AND "MaKH" <= 'KH057'
    );
    GET DIAGNOSTICS v_count_ctpt = ROW_COUNT;
    RAISE NOTICE '4. Đã xóa % bản ghi trong ChiTietPhieuThue.', v_count_ctpt;

    -- 5. Xóa PhieuThue (Khóa ngoại: MaKH tham chiếu KhachHang)
    DELETE FROM "PhieuThue"
    WHERE "MaKH" >= 'KH041' AND "MaKH" <= 'KH057';
    GET DIAGNOSTICS v_count_pt = ROW_COUNT;
    RAISE NOTICE '5. Đã xóa % bản ghi trong PhieuThue.', v_count_pt;

    -- 6. Xóa KhachHang_SDT (Khóa ngoại: MaKH tham chiếu KhachHang)
    DELETE FROM "KhachHang_SDT"
    WHERE "MaKH" >= 'KH041' AND "MaKH" <= 'KH057';
    GET DIAGNOSTICS v_count_sdt = ROW_COUNT;
    RAISE NOTICE '6. Đã xóa % bản ghi trong KhachHang_SDT.', v_count_sdt;

    -- 7. Xóa KhachHang_Email nếu bảng tồn tại
    IF to_regclass('public."KhachHang_Email"') IS NOT NULL THEN
        EXECUTE 'DELETE FROM "KhachHang_Email" WHERE "MaKH" >= ''KH041'' AND "MaKH" <= ''KH057'';';
        GET DIAGNOSTICS v_count_email = ROW_COUNT;
        RAISE NOTICE '7. Đã xóa % bản ghi trong KhachHang_Email.', v_count_email;
    ELSE
        RAISE NOTICE '7. Bảng KhachHang_Email không có trong PostgreSQL (bỏ qua).';
    END IF;

    -- 8. Xóa bảng cha gốc: KhachHang
    DELETE FROM "KhachHang"
    WHERE "MaKH" >= 'KH041' AND "MaKH" <= 'KH057';
    GET DIAGNOSTICS v_count_kh = ROW_COUNT;
    RAISE NOTICE '8. Đã xóa % khách hàng trong KhachHang.', v_count_kh;

    RAISE NOTICE '===> HOÀN TẤT DỌN DẸP DỮ LIỆU TEST KH041 -> KH057 THÀNH CÔNG! <===';
END $$;

