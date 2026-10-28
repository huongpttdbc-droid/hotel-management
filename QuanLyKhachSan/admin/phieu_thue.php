
<?php
require_once __DIR__ . '/includes/functions.php';
$pageTitle  = 'Đặt & Thuê Phòng';
$activePage = 'phieu_thue';
include 'includes/header.php';
 
$maNV   = 'NV01';   // nhân viên đang đăng nhập (giống hoa_don.php cũ)
$err    = '';
$reopen = false;
$action = $_SERVER['REQUEST_METHOD'] === 'POST' ? ($_POST['action'] ?? '') : '';
 
function oldv(string $k, $def = '')
{
    return esc($_POST[$k] ?? $def);
}
 
if ($action !== '') {
    try {
        switch ($action) {
 
            // ---------------- ĐẶT PHÒNG (gọi sp_DatPhong) ----------------
            case 'dat_phong':
                $maKH    = trim($_POST['ma_kh'] ?? '');
                $maPhong = trim($_POST['ma_phong'] ?? '');
                $ht      = $_POST['hinh_thuc'] ?? 'ngay';
                if (!in_array($ht, ['gio', 'dem', 'ngay'], true)) {
                    $ht = 'ngay';
                }
                $soNguoi = max(1, (int)($_POST['so_nguoi'] ?? 1));
                $tn      = strtotime($_POST['gio_nhan'] ?? '');
                $tt      = strtotime($_POST['gio_tra'] ?? '');
                $ghiChu  = trim($_POST['ghi_chu'] ?? '');
                $coc     = max(0, (int)round((float)($_POST['dat_coc'] ?? 0)));
                $pm      = pmCode($_POST['phuong_thuc'] ?? 'tm');
 
                if ($maKH === '' || $maPhong === '') {
                    throw new Exception('Vui lòng chọn khách hàng và phòng.');
                }
                if (!$tn || !$tt) {
                    throw new Exception('Vui lòng nhập giờ nhận và giờ trả.');
                }
 
                $sql = "SET NOCOUNT ON;
                    DECLARE @ht NVARCHAR(20) = CASE CAST(? AS VARCHAR(10)) WHEN 'gio' THEN N'Theo giờ' WHEN 'dem' THEN N'Qua đêm' ELSE N'Theo ngày' END;
                    DECLARE @gn DATETIME = CONVERT(DATETIME, CAST(? AS VARCHAR(30)), 126);
                    DECLARE @gt DATETIME = CONVERT(DATETIME, CAST(? AS VARCHAR(30)), 126);
                    DECLARE @gc NVARCHAR(500) = " . uSql(500) . ";
                    DECLARE @mapt VARCHAR(12), @tb NVARCHAR(300);
                    EXEC dbo.sp_DatPhong @MaKH = ?, @MaNV = ?, @MaPhong = ?, @HinhThucThue = @ht,
                         @SoNguoiDuKien = ?, @GioNhan = @gn, @GioTra = @gt, @GhiChu = @gc,
                         @MaPhieuThueMoi = @mapt OUTPUT, @ThongBao = @tb OUTPUT;
                    SELECT CASE WHEN @mapt IS NULL THEN 0 ELSE 1 END AS Ok, @mapt AS MaPhieuThue,
                           CAST(@tb AS NVARCHAR(MAX)) AS ThongBao;";
                $r = qBatch($conn, $sql, [
                    $ht, date('Y-m-d\TH:i:s', $tn), date('Y-m-d\TH:i:s', $tt),
                    uni($ghiChu === '' ? null : $ghiChu),
                    $maKH, $maNV, $maPhong, $soNguoi,
                ]);
                if (!$r) {
                    throw new Exception('Không nhận được kết quả từ thủ tục đặt phòng.');
                }
                if ((int)$r['Ok'] !== 1) {
                    $err = $r['ThongBao'];
                    $reopen = true;
                    break;
                }
                $maPT = $r['MaPhieuThue'];
                if ($coc > 0) {
                    $maTT = nextId($conn, 'ThanhToan', 'MaThanhToan', 'TTC', 4);
                    qRun($conn, "INSERT INTO dbo.ThanhToan (MaThanhToan, MaPhieuThue, MaNV, NgayGioThanhToan, PhuongThuc, SoTien, LoaiKhoan)
                                 VALUES (?, ?, ?, GETDATE(), " . pmSql() . ", ?, N'Đặt cọc')",
                        [$maTT, $maPT, $maNV, $pm, (string)$coc]);
                }
                redirectOk('phieu_thue.php', $r['ThongBao'] . ($coc > 0 ? ' Đã ghi nhận đặt cọc ' . money($coc) . '.' : ''));
                break;
 
            // ---------------- NHẬN PHÒNG ----------------
            case 'nhan_phong':
                $pt = trim($_POST['ma_phieu'] ?? '');
                $conn->beginTransaction();
                $bad = qAll($conn, "SELECT p.SoPhong FROM dbo.ChiTietPhieuThue ct
                                    JOIN dbo.Phong p ON p.MaPhong = ct.MaPhong
                                    WHERE ct.MaPhieuThue = ? AND p.TinhTrang <> N'Trống'", [$pt]);
                if ($bad) {
                    $ds = implode(', ', array_column($bad, 'SoPhong'));
                    throw new Exception("Phòng $ds chưa sẵn sàng (đang thuê / đang dọn / bảo trì).");
                }
                $n = qRun($conn, "UPDATE dbo.PhieuThue SET TrangThai = N'Đang thuê' WHERE MaPhieuThue = ? AND TrangThai = N'Đã đặt'", [$pt]);
                if ($n < 1) {
                    throw new Exception('Chỉ nhận phòng được phiếu đang ở trạng thái "Đã đặt".');
                }
                qRun($conn, "UPDATE ph SET ph.TinhTrang = N'Đang thuê'
                             FROM dbo.Phong ph JOIN dbo.ChiTietPhieuThue ct ON ct.MaPhong = ph.MaPhong
                             WHERE ct.MaPhieuThue = ?", [$pt]);
                $conn->commit();
                redirectOk('phieu_thue.php', "Đã nhận phòng cho phiếu $pt.");
                break;
 
            // ---------------- TRẢ PHÒNG + LẬP HÓA ĐƠN ----------------
            case 'tra_phong':
                $pt  = trim($_POST['ma_phieu'] ?? '');
                $phu = max(0, (int)round((float)($_POST['phu_thu'] ?? 0)));
                $conn->beginTransaction();
                $n = qRun($conn, "UPDATE dbo.PhieuThue SET TrangThai = N'Hoàn tất' WHERE MaPhieuThue = ? AND TrangThai = N'Đang thuê'", [$pt]);
                if ($n < 1) {
                    throw new Exception('Chỉ trả phòng được phiếu đang ở trạng thái "Đang thuê".');
                }
                // Dòng chưa có giờ trả -> lấy giờ hiện tại
                qRun($conn, "UPDATE dbo.ChiTietPhieuThue
                             SET GioTra = CASE WHEN GETDATE() > GioNhan THEN GETDATE() ELSE DATEADD(HOUR, 1, GioNhan) END
                             WHERE MaPhieuThue = ? AND GioTra IS NULL", [$pt]);
                // Phòng -> Đang dọn (trừ phòng còn nằm trong phiếu Đang thuê khác)
                qRun($conn, "UPDATE ph SET ph.TinhTrang = N'Đang dọn'
                             FROM dbo.Phong ph JOIN dbo.ChiTietPhieuThue ct ON ct.MaPhong = ph.MaPhong
                             WHERE ct.MaPhieuThue = ? AND ph.TinhTrang = N'Đang thuê'
                               AND NOT EXISTS (SELECT 1 FROM dbo.ChiTietPhieuThue c2
                                               JOIN dbo.PhieuThue p2 ON p2.MaPhieuThue = c2.MaPhieuThue
                                               WHERE c2.MaPhong = ph.MaPhong AND p2.TrangThai = N'Đang thuê')", [$pt]);
                $maHD = qVal($conn, "SELECT MaHD FROM dbo.HoaDon WHERE MaPhieuThue = ?", [$pt]);
                if (!$maHD) {
                    $tp  = (float)qVal($conn, "SELECT ISNULL(SUM(dbo.fn_TinhTienPhongTheoHinhThuc(MaPhong, HinhThucThue, GioNhan, GioTra)), 0)
                                               FROM dbo.ChiTietPhieuThue WHERE MaPhieuThue = ?", [$pt]);
                    $tdv = (float)qVal($conn, "SELECT ISNULL(SUM(d.SoLuong * s.DonGia), 0)
                                               FROM dbo.DungDichVu d JOIN dbo.DichVu s ON s.MaDichVu = d.MaDichVu
                                               WHERE d.MaPhieuThue = ?", [$pt]);
                    $pct = (float)qVal($conn, "SELECT lk.PhanTramUuDai FROM dbo.PhieuThue p
                                               JOIN dbo.KhachHang k ON k.MaKH = p.MaKH
                                               JOIN dbo.LoaiKhachHang lk ON lk.MaLoaiKH = k.MaLoaiKH
                                               WHERE p.MaPhieuThue = ?", [$pt]);
                    $uuDai = (int)round(($tp + $tdv + $phu) * $pct / 100);
                    $maHD  = nextId($conn, 'HoaDon', 'MaHD', 'HD', 4);
                    qRun($conn, "INSERT INTO dbo.HoaDon (MaHD, MaPhieuThue, MaNV, NgayLap, TienPhuThu, UuDai, TrangThai)
                                 VALUES (?, ?, ?, GETDATE(), ?, ?, N'Chưa thanh toán')",
                        [$maHD, $pt, $maNV, (string)$phu, (string)$uuDai]);
                }
                $conn->commit();
                redirectOk('phieu_thue.php', "Đã trả phòng phiếu $pt, lập hóa đơn $maHD. Vào mục Hóa Đơn & Thu Tiền để thu nợ.");
                break;
 
            // ---------------- HỦY PHIẾU (gọi sp_HuyPhieuThue) ----------------
            case 'huy':
                $pt = trim($_POST['ma_phieu'] ?? '');
                $r = qBatch($conn, "SET NOCOUNT ON;
                    DECLARE @tb NVARCHAR(300);
                    EXEC dbo.sp_HuyPhieuThue @MaPhieuThue = ?, @MaNV = ?, @ThongBao = @tb OUTPUT;
                    SELECT CAST(@tb AS NVARCHAR(MAX)) AS ThongBao;", [$pt, $maNV]);
                $da = (int)qVal($conn, "SELECT CASE WHEN TrangThai = N'Đã hủy' THEN 1 ELSE 0 END FROM dbo.PhieuThue WHERE MaPhieuThue = ?", [$pt]);
                if ($da !== 1) {
                    throw new Exception($r['ThongBao'] ?? 'Không hủy được phiếu.');
                }
                redirectOk('phieu_thue.php', "Đã hủy phiếu $pt.");
                break;
        }
    } catch (Throwable $e) {
        if ($conn->inTransaction()) {
            $conn->rollBack();
        }
        $err = friendlyErr($e);
        if ($action === 'dat_phong') {
            $reopen = true;
        }
    }
}
 
// ---------------- DỮ LIỆU HIỂN THỊ ----------------
$tt = $_GET['tt'] ?? '';
$q  = trim($_GET['q'] ?? '');
 
$all = qAll($conn, "
    SELECT TOP 500 pt.MaPhieuThue, " . dtc('pt.NgayLap', 'NgayLap', 120, 19) . ",
           " . ptCodeSql('pt.TrangThai') . " AS MaTT,
           pt.MaKH, " . nvc('kh.HoTen', 'HoTen') . ",
           CAST((SELECT STRING_AGG(p.SoPhong, ', ') FROM dbo.ChiTietPhieuThue ct
                 JOIN dbo.Phong p ON p.MaPhong = ct.MaPhong WHERE ct.MaPhieuThue = pt.MaPhieuThue) AS NVARCHAR(MAX)) AS DsPhong,
           (SELECT CONVERT(VARCHAR(19), MIN(ct.GioNhan), 120) FROM dbo.ChiTietPhieuThue ct WHERE ct.MaPhieuThue = pt.MaPhieuThue) AS GioNhan,
           (SELECT CONVERT(VARCHAR(19), MAX(ct.GioTra), 120) FROM dbo.ChiTietPhieuThue ct WHERE ct.MaPhieuThue = pt.MaPhieuThue) AS GioTra,
           CASE WHEN EXISTS (SELECT 1 FROM dbo.HoaDon h WHERE h.MaPhieuThue = pt.MaPhieuThue) THEN 1 ELSE 0 END AS CoHoaDon
    FROM dbo.PhieuThue pt
    JOIN dbo.KhachHang kh ON kh.MaKH = pt.MaKH
    ORDER BY pt.NgayLap DESC, pt.MaPhieuThue DESC");
 
$list = array_filter($all, function ($r) use ($tt, $q) {
    if ($tt !== '' && $r['MaTT'] !== $tt) {
        return false;
    }
    if ($q !== '') {
        $hay = $r['MaPhieuThue'] . ' ' . $r['MaKH'] . ' ' . $r['HoTen'] . ' ' . $r['DsPhong'];
        if (mb_stripos($hay, $q) === false) {
            return false;
        }
    }
    return true;
});
 
$khachs = qAll($conn, "SELECT MaKH, " . nvc('HoTen') . " FROM dbo.KhachHang ORDER BY MaKH");
$phongs = qAll($conn, "SELECT MaPhong, SoPhong, " . nvc('TenLoaiPhong') . ", SucChua, DonGiaTheoNgay, " . nvc('TinhTrang') . "
                       FROM dbo.vw_TrangThaiPhong WHERE TinhTrang <> N'Bảo trì' ORDER BY SoPhong");
 
// Chi tiết một phiếu
$xem = trim($_GET['xem'] ?? '');
$chiTiet = null;
if ($xem !== '') {
    $head = qOne($conn, "SELECT pt.MaPhieuThue, " . dtc('pt.NgayLap', 'NgayLap') . ", " . ptCodeSql('pt.TrangThai') . " AS MaTT,
                                pt.MaKH, " . nvc('kh.HoTen', 'HoTen') . ", " . nvc('nv.HoTen', 'NhanVien') . "
                         FROM dbo.PhieuThue pt JOIN dbo.KhachHang kh ON kh.MaKH = pt.MaKH
                         JOIN dbo.NhanVien nv ON nv.MaNV = pt.MaNV WHERE pt.MaPhieuThue = ?", [$xem]);
    if ($head) {
        $chiTiet = [
            'head'  => $head,
            'phong' => qAll($conn, "SELECT ct.STT, p.SoPhong, " . nvc('lp.TenLoai', 'Loai') . ", " . nvc('ct.HinhThucThue', 'HinhThuc') . ",
                                           ct.SoNguoiDuKien, " . dtc('ct.GioNhan', 'GioNhan') . ", " . dtc('ct.GioTra', 'GioTra') . ",
                                           dbo.fn_TinhTienPhongTheoHinhThuc(ct.MaPhong, ct.HinhThucThue, ct.GioNhan, ct.GioTra) AS TienPhong
                                    FROM dbo.ChiTietPhieuThue ct JOIN dbo.Phong p ON p.MaPhong = ct.MaPhong
                                    JOIN dbo.LoaiPhong lp ON lp.MaLoaiPhong = p.MaLoaiPhong
                                    WHERE ct.MaPhieuThue = ? ORDER BY ct.STT", [$xem]),
            'dv'    => qAll($conn, "SELECT " . nvc('s.TenDichVu', 'TenDichVu') . ", d.SoLuong, s.DonGia, d.SoLuong * s.DonGia AS ThanhTien, " . dtc('d.GioBD', 'GioBD') . "
                                    FROM dbo.DungDichVu d JOIN dbo.DichVu s ON s.MaDichVu = d.MaDichVu
                                    WHERE d.MaPhieuThue = ? ORDER BY d.GioBD", [$xem]),
            'tt'    => qAll($conn, "SELECT " . nvc('LoaiKhoan') . ", " . nvc('PhuongThuc') . ", SoTien, " . dtc('NgayGioThanhToan', 'Ngay') . "
                                    FROM dbo.ThanhToan WHERE MaPhieuThue = ? ORDER BY NgayGioThanhToan", [$xem]),
        ];
    }
}
 
$preChonPhong = $_POST['ma_phong'] ?? ($_GET['phong'] ?? '');
if (isset($_GET['phong'])) {
    $reopen = true;
}
$defNhan = date('Y-m-d\TH:i');
$defTra  = date('Y-m-d\T12:00', strtotime('+1 day'));
?>
 
<?php flashHtml($err); ?>
 
<?php if ($chiTiet): $h = $chiTiet['head']; ?>
    <div class="card border-0 shadow-sm mb-4">
        <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
            <span class="fw-bold">Chi tiết phiếu <?= esc($h['MaPhieuThue']) ?> <?= ptBadge($h['MaTT']) ?></span>
            <a href="phieu_thue.php" class="btn btn-sm btn-light">Đóng</a>
        </div>
        <div class="card-body">
            <p class="mb-2">Khách: <strong><?= esc($h['HoTen']) ?></strong> (<?= esc($h['MaKH']) ?>) · Lập lúc <?= fdt($h['NgayLap']) ?> · NV: <?= esc($h['NhanVien']) ?></p>
            <h6 class="fw-bold">Phòng</h6>
            <table class="table table-sm table-bordered">
                <thead class="table-light"><tr><th>STT</th><th>Phòng</th><th>Loại</th><th>Hình thức</th><th>Số người</th><th>Nhận</th><th>Trả</th><th class="text-end">Tiền phòng</th></tr></thead>
                <tbody>
                <?php foreach ($chiTiet['phong'] as $p): ?>
                    <tr><td><?= (int)$p['STT'] ?></td><td><?= esc($p['SoPhong']) ?></td><td><?= esc($p['Loai']) ?></td><td><?= esc($p['HinhThuc']) ?></td>
                        <td><?= (int)$p['SoNguoiDuKien'] ?></td><td><?= fdt($p['GioNhan']) ?></td><td><?= fdt($p['GioTra']) ?></td>
                        <td class="text-end"><?= $p['GioTra'] ? money($p['TienPhong']) : '—' ?></td></tr>
                <?php endforeach; ?>
                </tbody>
            </table>
            <div class="row">
                <div class="col-md-6">
                    <h6 class="fw-bold">Dịch vụ đã dùng</h6>
                    <?php if (!$chiTiet['dv']): ?><p class="text-muted small">Chưa dùng dịch vụ nào.</p><?php else: ?>
                    <table class="table table-sm table-bordered"><thead class="table-light"><tr><th>Dịch vụ</th><th>SL</th><th class="text-end">Thành tiền</th></tr></thead><tbody>
                    <?php foreach ($chiTiet['dv'] as $d): ?>
                        <tr><td><?= esc($d['TenDichVu']) ?></td><td><?= (int)$d['SoLuong'] ?></td><td class="text-end"><?= money($d['ThanhTien']) ?></td></tr>
                    <?php endforeach; ?></tbody></table><?php endif; ?>
                </div>
                <div class="col-md-6">
                    <h6 class="fw-bold">Thanh toán</h6>
                    <?php if (!$chiTiet['tt']): ?><p class="text-muted small">Chưa có khoản thanh toán.</p><?php else: ?>
                    <table class="table table-sm table-bordered"><thead class="table-light"><tr><th>Khoản</th><th>Phương thức</th><th class="text-end">Số tiền</th></tr></thead><tbody>
                    <?php foreach ($chiTiet['tt'] as $t): ?>
                        <tr><td><?= esc($t['LoaiKhoan']) ?></td><td><?= esc($t['PhuongThuc']) ?></td><td class="text-end"><?= money($t['SoTien']) ?></td></tr>
                    <?php endforeach; ?></tbody></table><?php endif; ?>
                </div>
            </div>
        </div>
    </div>
<?php elseif ($xem !== ''): ?>
    <div class="alert alert-warning">Không tìm thấy phiếu <?= esc($xem) ?>.</div>
<?php endif; ?>
 
<div class="card border-0 shadow-sm p-3">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h5 class="fw-bold mb-0">DANH SÁCH PHIẾU THUÊ PHÒNG</h5>
        <button class="btn btn-primary fw-bold" data-bs-toggle="modal" data-bs-target="#modalDat">+ Đặt phòng mới</button>
    </div>
 
    <form method="GET" class="row g-2 mb-3">
        <div class="col-md-5"><input type="text" name="q" value="<?= esc($q) ?>" class="form-control" placeholder="Tìm mã phiếu, mã/tên khách, số phòng..."></div>
        <div class="col-md-3">
            <select name="tt" class="form-select">
                <option value="">Tất cả trạng thái</option>
                <option value="dat"  <?= $tt === 'dat' ? 'selected' : '' ?>>Đã đặt</option>
                <option value="thue" <?= $tt === 'thue' ? 'selected' : '' ?>>Đang thuê</option>
                <option value="xong" <?= $tt === 'xong' ? 'selected' : '' ?>>Hoàn tất</option>
                <option value="huy"  <?= $tt === 'huy' ? 'selected' : '' ?>>Đã hủy</option>
            </select>
        </div>
        <div class="col-md-4 d-flex gap-2">
            <button class="btn btn-dark">Lọc</button>
            <a href="phieu_thue.php" class="btn btn-outline-secondary">Xóa lọc</a>
        </div>
    </form>
 
    <div class="table-responsive">
        <table class="table table-hover table-bordered align-middle">
            <thead class="table-dark">
            <tr><th>Mã PT</th><th>Khách hàng</th><th>Phòng</th><th>Trạng thái</th><th>Nhận</th><th>Trả</th><th class="text-center">Thao tác</th></tr>
            </thead>
            <tbody>
            <?php if (!$list): ?>
                <tr><td colspan="7" class="text-center text-muted py-4">Không có phiếu thuê nào.</td></tr>
            <?php endif; ?>
            <?php foreach ($list as $r): ?>
                <tr>
                    <td class="fw-bold"><?= esc($r['MaPhieuThue']) ?></td>
                    <td><?= esc($r['HoTen']) ?><br><small class="text-muted"><?= esc($r['MaKH']) ?></small></td>
                    <td><span class="badge bg-secondary"><?= esc($r['DsPhong']) ?></span></td>
                    <td><?= ptBadge($r['MaTT']) ?></td>
                    <td><?= fdt($r['GioNhan']) ?></td>
                    <td><?= fdt($r['GioTra']) ?></td>
                    <td class="text-center text-nowrap">
                        <a class="btn btn-sm btn-outline-dark" href="phieu_thue.php?xem=<?= esc($r['MaPhieuThue']) ?>">Chi tiết</a>
 
                        <?php if ($r['MaTT'] === 'dat'): ?>
                            <form method="POST" class="d-inline">
                                <input type="hidden" name="action" value="nhan_phong">
                                <input type="hidden" name="ma_phieu" value="<?= esc($r['MaPhieuThue']) ?>">
                                <button class="btn btn-sm btn-success">Nhận phòng</button>
                            </form>
                        <?php elseif ($r['MaTT'] === 'thue'): ?>
                            <button type="button" class="btn btn-sm btn-warning fw-bold btn-tra" data-bs-toggle="modal" data-bs-target="#modalTra"
                                    data-ma="<?= esc($r['MaPhieuThue']) ?>" data-khach="<?= esc($r['HoTen']) ?>">Trả phòng</button>
                        <?php elseif ($r['MaTT'] === 'xong' && (int)$r['CoHoaDon'] === 1): ?>
                            <a class="btn btn-sm btn-outline-primary" href="hoa_don.php?q=<?= esc($r['MaPhieuThue']) ?>">Hóa đơn</a>
                        <?php endif; ?>
 
                        <?php if ($r['MaTT'] === 'dat' || $r['MaTT'] === 'thue'): ?>
                            <form method="POST" class="d-inline" onsubmit="return confirm('Hủy phiếu <?= esc($r['MaPhieuThue']) ?>?');">
                                <input type="hidden" name="action" value="huy">
                                <input type="hidden" name="ma_phieu" value="<?= esc($r['MaPhieuThue']) ?>">
                                <button class="btn btn-sm btn-outline-danger">Hủy</button>
                            </form>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</div>
 
<!-- MODAL ĐẶT PHÒNG -->
<div class="modal fade" id="modalDat" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <form method="POST">
                <input type="hidden" name="action" value="dat_phong">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title fw-bold">ĐẶT PHÒNG MỚI</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Khách hàng</label>
                            <select name="ma_kh" class="form-select" required>
                                <option value="">-- Chọn khách --</option>
                                <?php foreach ($khachs as $k): ?>
                                    <option value="<?= esc($k['MaKH']) ?>" <?= ($_POST['ma_kh'] ?? '') === $k['MaKH'] ? 'selected' : '' ?>><?= esc($k['MaKH'] . ' - ' . $k['HoTen']) ?></option>
                                <?php endforeach; ?>
                            </select>
                            <div class="form-text">Khách mới? Thêm ở mục Quản Lý Khách Hàng.</div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Phòng</label>
                            <select name="ma_phong" class="form-select" required>
                                <option value="">-- Chọn phòng --</option>
                                <?php foreach ($phongs as $p): ?>
                                    <option value="<?= esc($p['MaPhong']) ?>" <?= $preChonPhong === $p['MaPhong'] ? 'selected' : '' ?>>
                                        P.<?= esc($p['SoPhong']) ?> - <?= esc($p['TenLoaiPhong']) ?> (<?= (int)$p['SucChua'] ?> người, <?= money($p['DonGiaTheoNgay']) ?>/ngày) [<?= esc($p['TinhTrang']) ?>]
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Hình thức thuê</label>
                            <?php $htOld = $_POST['hinh_thuc'] ?? 'ngay'; ?>
                            <select name="hinh_thuc" class="form-select">
                                <option value="gio"  <?= $htOld === 'gio' ? 'selected' : '' ?>>Theo giờ</option>
                                <option value="dem"  <?= $htOld === 'dem' ? 'selected' : '' ?>>Qua đêm</option>
                                <option value="ngay" <?= $htOld === 'ngay' ? 'selected' : '' ?>>Theo ngày</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Giờ nhận</label>
                            <input type="datetime-local" name="gio_nhan" class="form-control" value="<?= oldv('gio_nhan', $defNhan) ?>" required>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Giờ trả</label>
                            <input type="datetime-local" name="gio_tra" class="form-control" value="<?= oldv('gio_tra', $defTra) ?>" required>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Số người</label>
                            <input type="number" name="so_nguoi" min="1" class="form-control" value="<?= oldv('so_nguoi', 1) ?>" required>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Đặt cọc (đ)</label>
                            <input type="number" name="dat_coc" min="0" step="1000" class="form-control" value="<?= oldv('dat_coc', 0) ?>">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Phương thức cọc</label>
                            <select name="phuong_thuc" class="form-select">
                                <option value="tm">Tiền mặt</option>
                                <option value="ck">Chuyển khoản</option>
                                <option value="the">Thẻ</option>
                            </select>
                        </div>
                        <div class="col-12">
                            <label class="form-label fw-bold">Ghi chú</label>
                            <textarea name="ghi_chu" rows="2" class="form-control"><?= oldv('ghi_chu') ?></textarea>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>
                    <button type="submit" class="btn btn-primary fw-bold">Xác nhận đặt phòng</button>
                </div>
            </form>
        </div>
    </div>
</div>
 
<!-- MODAL TRẢ PHÒNG -->
<div class="modal fade" id="modalTra" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="POST">
                <input type="hidden" name="action" value="tra_phong">
                <input type="hidden" name="ma_phieu" id="tra_ma">
                <div class="modal-header bg-warning">
                    <h5 class="modal-title fw-bold">TRẢ PHÒNG & LẬP HÓA ĐƠN</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Phiếu: <strong id="tra_label"></strong></p>
                    <label class="form-label fw-bold">Phụ thu (đ) - nếu có</label>
                    <input type="number" name="phu_thu" min="0" step="1000" value="0" class="form-control">
                    <div class="form-text">Hệ thống tự tính tiền phòng, dịch vụ, ưu đãi theo hạng khách và VAT 10%.</div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Hủy</button>
                    <button type="submit" class="btn btn-success fw-bold">Xác nhận trả phòng</button>
                </div>
            </form>
        </div>
    </div>
</div>
 
<script>
    document.querySelectorAll('.btn-tra').forEach(function (b) {
        b.addEventListener('click', function () {
            document.getElementById('tra_ma').value = b.dataset.ma;
            document.getElementById('tra_label').textContent = b.dataset.ma + ' - ' + b.dataset.khach;
        });
    });
    <?php if ($reopen): ?>
    window.addEventListener('load', function () {
        new bootstrap.Modal(document.getElementById('modalDat')).show();
    });
    <?php endif; ?>
</script>
 
<?php include 'includes/footer.php'; ?>