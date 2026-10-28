USE QuanLyKhachSan;
GO

-- 1. Lọc danh sách khách hàng thuộc loại VIP (LKH03)
SELECT * 
FROM KhachHang 
WHERE MaLoaiKH = 'LKH03';
GO

-- 2. Xem chi tiết phiếu thuê gồm mã phiếu, tên khách hàng, số phòng, hình thức thuê
SELECT pt.MaPhieuThue, kh.HoTen, p.SoPhong, ct.HinhThucThue, pt.TrangThai
FROM PhieuThue pt
INNER JOIN KhachHang kh ON pt.MaKH = kh.MaKH
INNER JOIN ChiTietPhieuThue ct ON pt.MaPhieuThue = ct.MaPhieuThue
INNER JOIN Phong p ON ct.MaPhong = p.MaPhong;
GO

-- 3. Liệt kê tất cả khách hàng và tìm khách hàng chưa có phiếu thuê nào
SELECT kh.MaKH, kh.HoTen, pt.MaPhieuThue
FROM KhachHang kh
LEFT JOIN PhieuThue pt ON kh.MaKH = pt.MaKH
WHERE pt.MaPhieuThue IS NULL;
GO

-- 4. Liệt kê thông tin chi tiết phiếu thuê và đơn giá theo ngày của loại phòng tương ứng
SELECT ct.MaPhieuThue, ct.MaPhong, lp.TenLoai, lp.DonGiaTheoNgay
FROM ChiTietPhieuThue ct
RIGHT JOIN Phong p ON ct.MaPhong = p.MaPhong
RIGHT JOIN LoaiPhong lp ON p.MaLoaiPhong = lp.MaLoaiPhong;
GO

-- 5. Liệt kê toàn bộ các phòng và tìm phòng chưa từng được thuê
SELECT p.MaPhong, p.SoPhong, ct.MaPhieuThue
FROM Phong p
FULL JOIN ChiTietPhieuThue ct ON p.MaPhong = ct.MaPhong
WHERE ct.MaPhieuThue IS NULL;
GO

-- 6. Thống kê tổng doanh thu thanh toán theo từng tháng, chỉ lấy tháng có tổng tiền lớn hơn 0
SELECT MONTH(h.NgayLap) AS Thang, SUM(t.SoTien) AS TongDoanhThu
FROM HoaDon h
JOIN ThanhToan t ON h.MaPhieuThue = t.MaPhieuThue
WHERE h.TrangThai = N'Đã thanh toán' AND t.LoaiKhoan = N'Thanh toán'
GROUP BY MONTH(h.NgayLap)
HAVING SUM(t.SoTien) > 0;
GO

-- 7. Tìm các chi tiết phiếu thuê có thời gian thuê theo giờ lớn hơn thời gian thuê trung bình toàn hệ thống
SELECT MaPhieuThue, MaPhong, HinhThucThue
FROM ChiTietPhieuThue
WHERE DATEDIFF(HOUR, GioNhan, GioTra) > (
    SELECT AVG(DATEDIFF(HOUR, GioNhan, GioTra)) 
    FROM ChiTietPhieuThue 
    WHERE GioTra IS NOT NULL
);
GO

-- 8. Liệt kê thông tin khách hàng đang có phiếu thuê với trạng thái 'Đang thuê'
SELECT MaKH, HoTen, DiaChi
FROM KhachHang
WHERE EXISTS (
    SELECT 1 
    FROM PhieuThue pt 
    WHERE pt.MaKH = KhachHang.MaKH 
      AND pt.TrangThai = N'Đang thuê'
);
GO

-- 9. UNION: Gộp danh sách mã khách hàng thuộc loại LKH02 và LKH03
SELECT MaKH, HoTen, MaLoaiKH FROM KhachHang WHERE MaLoaiKH = 'LKH02'
UNION
SELECT MaKH, HoTen, MaLoaiKH FROM KhachHang WHERE MaLoaiKH = 'LKH03';
GO

-- 10. INTERSECT: Lấy thông tin nhân viên vừa có SĐT vừa có Email
SELECT MaNV, HoTen, ChucVu 
FROM NhanVien 
WHERE MaNV IN (
    SELECT MaNV FROM NhanVien_SDT
    INTERSECT
    SELECT MaNV FROM NhanVien_Email
);
GO

-- 11. EXCEPT: Lấy thông tin nhân viên chưa từng lập phiếu thuê nào
SELECT MaNV, HoTen, ChucVu 
FROM NhanVien 
WHERE MaNV IN (
    SELECT MaNV FROM NhanVien
    EXCEPT
    SELECT MaNV FROM PhieuThue
);
GO

-- 12. Lấy top 20 phần trăm dịch vụ có đơn giá từ 10000 đến 200000 và tên chứa chữ 'nước'
SELECT TOP 20 PERCENT MaDichVu, TenDichVu, DonGia
FROM DichVu
WHERE DonGia BETWEEN 10000 AND 200000 
  AND TenDichVu LIKE N'%nước%';
GO