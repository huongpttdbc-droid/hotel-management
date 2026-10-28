<?php
// C:\xampp\htdocs\QuanLyKhachSan\fix_font.php
header('Content-Type: text/html; charset=utf-8');
require_once __DIR__ . '/config/database.php';

try {
    $conn->beginTransaction();

    $sql = "
        -- 1. Tạm thời tắt CHECK constraint của các bảng để tránh lỗi cập nhật
        ALTER TABLE Phong NOCHECK CONSTRAINT CK_Phong_TinhTrang;
        ALTER TABLE PhieuThue NOCHECK CONSTRAINT CK_PhieuThue_TrangThai;
        ALTER TABLE HoaDon NOCHECK CONSTRAINT CK_HoaDon_TrangThai;

        -- 2. Sửa danh mục Loại Phòng
        UPDATE LoaiPhong SET TenLoai = N'Đơn', MoTa = N'Phòng 1 giường đơn 1m2, phù hợp 1-2 khách' WHERE MaLoaiPhong = 'LP01';
        UPDATE LoaiPhong SET TenLoai = N'Đôi', MoTa = N'Phòng 1 giường đôi, có ban công' WHERE MaLoaiPhong = 'LP02';
        UPDATE LoaiPhong SET TenLoai = N'Gia đình', MoTa = N'Phòng 2 giường, phù hợp gia đình nhỏ' WHERE MaLoaiPhong = 'LP03';
        UPDATE LoaiPhong SET TenLoai = N'VIP', MoTa = N'Phòng cao cấp, view thành phố' WHERE MaLoaiPhong = 'LP04';
        UPDATE LoaiPhong SET TenLoai = N'Suite', MoTa = N'Phòng suite rộng, có phòng khách riêng' WHERE MaLoaiPhong = 'LP05';

        -- 3. Sửa Trạng Thái Phòng chuẩn
        UPDATE Phong SET TinhTrang = N'Trống' WHERE MaPhong NOT IN ('P02', 'P03', 'P04', 'P05', 'P06', 'P07', 'P08', 'P09', 'P29', 'P30');
        UPDATE Phong SET TinhTrang = N'Đang thuê' WHERE MaPhong IN ('P02', 'P03', 'P04', 'P07', 'P08', 'P09');
        UPDATE Phong SET TinhTrang = N'Đang dọn' WHERE MaPhong IN ('P05', 'P06');
        UPDATE Phong SET TinhTrang = N'Bảo trì' WHERE MaPhong IN ('P29', 'P30');

        -- 4. Sửa Hạng Khách Hàng
        UPDATE LoaiKhachHang SET TenLoai = N'Thường' WHERE MaLoaiKH = 'LKH01';
        UPDATE LoaiKhachHang SET TenLoai = N'Thân thiết' WHERE MaLoaiKH = 'LKH02';
        UPDATE LoaiKhachHang SET TenLoai = N'VIP' WHERE MaLoaiKH = 'LKH03';
        UPDATE LoaiKhachHang SET TenLoai = N'Doanh nghiệp' WHERE MaLoaiKH = 'LKH04';

        -- 5. Sửa Trạng Thái Phiếu Thuê & Hóa Đơn
        UPDATE PhieuThue SET TrangThai = N'Đang thuê' WHERE MaPhieuThue IN ('PT0037', 'PT0038', 'PT0039');
        UPDATE PhieuThue SET TrangThai = N'Đã đặt' WHERE MaPhieuThue IN ('PT0040', 'PT0041', 'PT0042');
        UPDATE PhieuThue SET TrangThai = N'Đã hủy' WHERE MaPhieuThue IN ('PT0008', 'PT0017', 'PT0026');
        UPDATE PhieuThue SET TrangThai = N'Hoàn tất' WHERE TrangThai NOT IN (N'Đang thuê', N'Đã đặt', N'Đã hủy');

        UPDATE HoaDon SET TrangThai = N'Chưa thanh toán' WHERE MaHD IN ('HD0034', 'HD0035', 'HD0036');
        UPDATE HoaDon SET TrangThai = N'Đã thanh toán' WHERE MaHD NOT IN ('HD0034', 'HD0035', 'HD0036');

        -- 6. Bật lại CHECK constraint cho các bảng
        ALTER TABLE Phong CHECK CONSTRAINT CK_Phong_TinhTrang;
        ALTER TABLE PhieuThue CHECK CONSTRAINT CK_PhieuThue_TrangThai;
        ALTER TABLE HoaDon CHECK CONSTRAINT CK_HoaDon_TrangThai;

        -- 7. Sửa Danh Mục Dịch Vụ
        UPDATE DichVu SET TenDichVu = N'Giặt ủi thường', MoTa = N'Giặt sấy và ủi, trả đồ sau 24 giờ', DonViTinh = N'kg' WHERE MaDichVu = 'DV01';
        UPDATE DichVu SET TenDichVu = N'Giặt ủi nhanh', MoTa = N'Trả đồ trong vòng 4 giờ', DonViTinh = N'kg' WHERE MaDichVu = 'DV02';
        UPDATE DichVu SET TenDichVu = N'Ủi quần áo', MoTa = N'Ủi riêng, không giặt', DonViTinh = N'món' WHERE MaDichVu = 'DV03';
        UPDATE DichVu SET TenDichVu = N'Giặt khô', MoTa = N'Áo vest, váy, áo dài, đồ len', DonViTinh = N'món' WHERE MaDichVu = 'DV04';
        UPDATE DichVu SET TenDichVu = N'Nước suối 500ml', MoTa = N'Minibar trong phòng', DonViTinh = N'chai' WHERE MaDichVu = 'DV05';
        UPDATE DichVu SET TenDichVu = N'Nước ngọt lon', MoTa = N'Coca-Cola, Pepsi, 7Up - minibar', DonViTinh = N'lon' WHERE MaDichVu = 'DV06';
        UPDATE DichVu SET TenDichVu = N'Bia lon', MoTa = N'Bia Tiger/Heineken - minibar', DonViTinh = N'lon' WHERE MaDichVu = 'DV07';
        UPDATE DichVu SET TenDichVu = N'Cà phê phin sữa đá', MoTa = N'Phục vụ tại phòng', DonViTinh = N'ly' WHERE MaDichVu = 'DV08';
        UPDATE DichVu SET TenDichVu = N'Trà thảo mộc', MoTa = N'Trà hoa cúc, trà gừng; ấm 2-3 người', DonViTinh = N'ấm' WHERE MaDichVu = 'DV09';
        UPDATE DichVu SET TenDichVu = N'Snack minibar', MoTa = N'Bánh, hạt, snack các loại', DonViTinh = N'gói' WHERE MaDichVu = 'DV10';
        UPDATE DichVu SET TenDichVu = N'Buffet sáng người lớn', MoTa = N'Phục vụ 6:30-9:30 tại nhà hàng', DonViTinh = N'suất' WHERE MaDichVu = 'DV11';
        UPDATE DichVu SET TenDichVu = N'Buffet sáng trẻ em', MoTa = N'Trẻ em dưới 12 tuổi', DonViTinh = N'suất' WHERE MaDichVu = 'DV12';
        UPDATE DichVu SET TenDichVu = N'Phở bò phục vụ tại phòng', MoTa = N'Phục vụ trong 20 phút', DonViTinh = N'tô' WHERE MaDichVu = 'DV13';

        -- 8. Sửa Tên Khách Hàng mẫu
        UPDATE KhachHang SET HoTen = N'Nguyễn Quốc Hải' WHERE MaKH = 'KH001';
        UPDATE KhachHang SET HoTen = N'Trần Văn Bình' WHERE MaKH = 'KH002';
        UPDATE KhachHang SET HoTen = N'Lê Thị Châu' WHERE MaKH = 'KH003';
        UPDATE KhachHang SET HoTen = N'Phạm Quốc Dũng' WHERE MaKH = 'KH004';
        UPDATE KhachHang SET HoTen = N'Hoàng Thu Giang' WHERE MaKH = 'KH005';
        UPDATE KhachHang SET HoTen = N'Vũ Minh Khánh' WHERE MaKH = 'KH006';
        UPDATE KhachHang SET HoTen = N'Đặng Gia Linh' WHERE MaKH = 'KH007';
        UPDATE KhachHang SET HoTen = N'Bùi Thu Giang' WHERE MaKH = 'KH008';
        UPDATE KhachHang SET HoTen = N'Đỗ Quốc Hải' WHERE MaKH = 'KH009';
        UPDATE KhachHang SET HoTen = N'Ngô Gia Linh' WHERE MaKH = 'KH010';
    ";

    $conn->exec($sql);
    $conn->commit();

    echo "<h2 style='color:green; font-family:sans-serif;'>SUCCESS: ĐÃ SỬA TOÀN BỘ FONT TIẾNG VIỆT THÀNH CÔNG!</h2>";
    echo "<p><a href='admin/dashboard.php' style='font-size:18px; font-weight:bold;'>👉 Bấm vào đây để quay lại trang Admin Dashboard</a></p>";
} catch (Exception $e) {
    if ($conn->inTransaction()) {
        $conn->rollBack();
    }
    echo "<h2 style='color:red;'>LỖI XỬ LÝ: " . $e->getMessage() . "</h2>";
}
?>