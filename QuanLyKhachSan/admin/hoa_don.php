
<?php
require_once __DIR__ . '/includes/functions.php';
$pageTitle  = 'Quản Lý Hóa Đơn & Thanh Toán';
$activePage = 'hoa_don';
include 'includes/header.php';
 
$maNV = 'NV01';
$err  = '';
 
// ---------------- THU TIỀN CÔNG NỢ ----------------
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'thu_tien') {
    try {
        $maHD   = trim($_POST['ma_hd'] ?? '');
        $soTien = (int)round((float)($_POST['so_tien'] ?? 0));
        $pm     = pmCode($_POST['phuong_thuc'] ?? 'tm');
 
        $hd = qOne($conn, "SELECT MaPhieuThue, SoTienConNo FROM dbo.vw_ChiTietHoaDon WHERE MaHD = ?", [$maHD]);
        if (!$hd) {
            throw new Exception('Không tìm thấy hóa đơn.');
        }
        $conNo = (float)$hd['SoTienConNo'];
        if ($soTien <= 0) {
            throw new Exception('Số tiền thu phải lớn hơn 0.');
        }
        if ($soTien > $conNo) {
            throw new Exception('Số tiền thu (' . money($soTien) . ') vượt quá số còn nợ (' . money($conNo) . ').');
        }
 
        $conn->beginTransaction();
        $maTT = nextId($conn, 'ThanhToan', 'MaThanhToan', 'TTT', 4);
        qRun($conn, "INSERT INTO dbo.ThanhToan (MaThanhToan, MaPhieuThue, MaNV, NgayGioThanhToan, PhuongThuc, SoTien, LoaiKhoan)
                     VALUES (?, ?, ?, GETDATE(), " . pmSql() . ", ?, N'Thanh toán')",
            [$maTT, $hd['MaPhieuThue'], $maNV, $pm, (string)$soTien]);
 
        // Hết nợ thì chuyển hóa đơn sang "Đã thanh toán"
        if ($soTien >= $conNo) {
            qRun($conn, "UPDATE dbo.HoaDon SET TrangThai = N'Đã thanh toán' WHERE MaHD = ?", [$maHD]);
        }
        $conn->commit();
        redirectOk('hoa_don.php', "Đã thu " . money($soTien) . " cho hóa đơn $maHD.");
    } catch (Throwable $e) {
        if ($conn->inTransaction()) {
            $conn->rollBack();
        }
        $err = friendlyErr($e);
    }
}
 
// ---------------- DỮ LIỆU ----------------
$rows = qAll($conn, "
    SELECT MaHD, MaPhieuThue, MaKH,
           " . nvc('HoTenKhachHang') . ",
           " . nvc('HangKhachHang') . ",
           " . nvc('DanhSachSoPhong') . ",
           " . dtc('NgayLapHoaDon', 'NgayLap') . ",
           TienPhong, TienDichVu, TienPhuThu, TienUuDai, ThueVAT_10, TongThanhTien, TongDaThanhToan, SoTienConNo,
           CASE WHEN TrangThaiHoaDon = N'Đã thanh toán' THEN 1
                WHEN TrangThaiHoaDon = N'Đã hủy' THEN 2 ELSE 0 END AS TT
    FROM dbo.vw_ChiTietHoaDon
    ORDER BY NgayLapHoaDon DESC, MaHD DESC");
 
$tongTien = $tongThu = $tongNo = 0;
$soChua = 0;
foreach ($rows as $r) {
    if ((int)$r['TT'] === 2) {
        continue;
    }
    $tongTien += (float)$r['TongThanhTien'];
    $tongThu  += (float)$r['TongDaThanhToan'];
    $tongNo   += max(0, (float)$r['SoTienConNo']);
    if ((float)$r['SoTienConNo'] > 0) {
        $soChua++;
    }
}
 
$fTT = $_GET['tt'] ?? '';
$q   = trim($_GET['q'] ?? '');
$list = array_filter($rows, function ($r) use ($fTT, $q) {
    if ($fTT === 'chua' && !((int)$r['TT'] !== 2 && (float)$r['SoTienConNo'] > 0)) {
        return false;
    }
    if ($fTT === 'da' && !((int)$r['TT'] !== 2 && (float)$r['SoTienConNo'] <= 0)) {
        return false;
    }
    if ($q !== '') {
        $hay = $r['MaHD'] . ' ' . $r['MaPhieuThue'] . ' ' . $r['MaKH'] . ' ' . $r['HoTenKhachHang'] . ' ' . $r['DanhSachSoPhong'];
        if (mb_stripos($hay, $q) === false) {
            return false;
        }
    }
    return true;
});
?>
 
<?php flashHtml($err); ?>
 
<div class="row g-3 mb-3">
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Tổng giá trị hóa đơn</div><div class="fs-5 fw-bold text-primary"><?= money($tongTien) ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Đã thu</div><div class="fs-5 fw-bold text-success"><?= money($tongThu) ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Công nợ còn lại</div><div class="fs-5 fw-bold text-danger"><?= money($tongNo) ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Hóa đơn còn nợ</div><div class="fs-5 fw-bold"><?= $soChua ?></div></div></div></div>
</div>
 
<div class="card border-0 shadow-sm p-3">
    <form method="GET" class="row g-2 mb-3">
        <div class="col-md-5"><input type="text" name="q" value="<?= esc($q) ?>" class="form-control" placeholder="Tìm mã HD, mã phiếu, khách hàng, số phòng..."></div>
        <div class="col-md-3">
            <select name="tt" class="form-select">
                <option value="">Tất cả hóa đơn</option>
                <option value="chua" <?= $fTT === 'chua' ? 'selected' : '' ?>>Còn nợ</option>
                <option value="da"   <?= $fTT === 'da' ? 'selected' : '' ?>>Đã thanh toán đủ</option>
            </select>
        </div>
        <div class="col-md-4 d-flex gap-2">
            <button class="btn btn-dark">Lọc</button>
            <a href="hoa_don.php" class="btn btn-outline-secondary">Xóa lọc</a>
        </div>
    </form>
 
    <div class="table-responsive">
        <table class="table table-hover table-bordered align-middle">
            <thead class="table-dark text-center">
            <tr>
                <th>Mã HD</th><th>Khách hàng</th><th>Phòng</th><th>Tiền phòng</th><th>Dịch vụ</th>
                <th>Tổng (đã VAT)</th><th>Đã thanh toán</th><th>Còn nợ</th><th>Trạng thái</th><th>Thao tác</th>
            </tr>
            </thead>
            <tbody>
            <?php if (!$list): ?>
                <tr><td colspan="10" class="text-center text-muted py-4">Không có hóa đơn nào.</td></tr>
            <?php endif; ?>
            <?php foreach ($list as $hd):
                $conNo = (float)$hd['SoTienConNo'];
                $huy   = (int)$hd['TT'] === 2;
            ?>
                <tr>
                    <td class="fw-bold text-center"><?= esc($hd['MaHD']) ?><br>
                        <small class="text-muted fw-normal"><?= esc($hd['MaPhieuThue']) ?></small></td>
                    <td>
                        <strong><?= esc($hd['HoTenKhachHang']) ?></strong><br>
                        <small class="text-muted">Mã: <?= esc($hd['MaKH']) ?> (Hạng: <?= esc($hd['HangKhachHang']) ?>)</small>
                    </td>
                    <td class="text-center"><?= esc($hd['DanhSachSoPhong']) ?></td>
                    <td class="text-end"><?= money($hd['TienPhong']) ?></td>
                    <td class="text-end"><?= money($hd['TienDichVu']) ?></td>
                    <td class="text-end fw-bold text-primary"><?= money($hd['TongThanhTien']) ?></td>
                    <td class="text-end text-success fw-bold"><?= money($hd['TongDaThanhToan']) ?></td>
                    <td class="text-end text-danger fw-bold"><?= money(max(0, $conNo)) ?></td>
                    <td class="text-center">
                        <?php if ($huy): ?>
                            <span class="badge bg-secondary">Đã hủy</span>
                        <?php elseif ($conNo > 0): ?>
                            <span class="badge bg-danger">Còn nợ</span>
                        <?php else: ?>
                            <span class="badge bg-success">Đã thanh toán</span>
                        <?php endif; ?>
                    </td>
                    <td class="text-center text-nowrap">
                        <?php if (!$huy && $conNo > 0): ?>
                            <button class="btn btn-sm btn-warning text-dark fw-bold btn-thu" data-bs-toggle="modal" data-bs-target="#modalThu"
                                    data-mahd="<?= esc($hd['MaHD']) ?>" data-khach="<?= esc($hd['HoTenKhachHang']) ?>"
                                    data-tong="<?= esc($hd['TongThanhTien']) ?>" data-conno="<?= esc((int)round($conNo)) ?>">Thu Tiền</button>
                        <?php else: ?>
                            <button class="btn btn-sm btn-outline-secondary" disabled>Hoàn tất</button>
                        <?php endif; ?>
                        <button class="btn btn-sm btn-outline-dark btn-ct" data-bs-toggle="modal" data-bs-target="#modalCT"
                                data-hd='<?= esc(json_encode([
                                    'ma' => $hd['MaHD'], 'ngay' => fdt($hd['NgayLap']), 'khach' => $hd['HoTenKhachHang'],
                                    'phong' => money($hd['TienPhong']), 'dv' => money($hd['TienDichVu']), 'phuthu' => money($hd['TienPhuThu']),
                                    'uudai' => money($hd['TienUuDai']), 'vat' => money($hd['ThueVAT_10']), 'tong' => money($hd['TongThanhTien']),
                                    'da' => money($hd['TongDaThanhToan']), 'no' => money(max(0, $conNo)),
                                ], JSON_UNESCAPED_UNICODE)) ?>'>Chi tiết</button>
                    </td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</div>
 
<!-- MODAL THU TIỀN (dùng chung) -->
<div class="modal fade" id="modalThu" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="POST">
                <input type="hidden" name="action" value="thu_tien">
                <input type="hidden" name="ma_hd" id="thu_mahd">
                <div class="modal-header bg-warning">
                    <h5 class="modal-title fw-bold">THU TIỀN HÓA ĐƠN: <span id="thu_title"></span></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Khách hàng: <strong id="thu_khach"></strong></p>
                    <p>Tổng tiền hóa đơn: <strong class="text-primary" id="thu_tong"></strong></p>
                    <p>Số tiền còn thiếu: <strong class="text-danger fs-5" id="thu_conno_txt"></strong></p>
                    <hr>
                    <div class="mb-3">
                        <label class="form-label fw-bold">Phương thức thanh toán</label>
                        <select name="phuong_thuc" class="form-select" required>
                            <option value="tm">Tiền mặt</option>
                            <option value="ck">Chuyển khoản</option>
                            <option value="the">Thẻ ATM/Credit</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold">Số tiền thu</label>
                        <input type="number" name="so_tien" id="thu_sotien" min="1" class="form-control fw-bold text-danger fs-5" required>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Hủy</button>
                    <button type="submit" class="btn btn-success fw-bold">Xác Nhận Thu Tiền</button>
                </div>
            </form>
        </div>
    </div>
</div>
 
<!-- MODAL CHI TIẾT -->
<div class="modal fade" id="modalCT" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-dark text-white">
                <h5 class="modal-title fw-bold">HÓA ĐƠN <span id="ct_ma"></span></h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="mb-2">Khách: <strong id="ct_khach"></strong><br>Ngày lập: <span id="ct_ngay"></span></p>
                <table class="table table-sm mb-0">
                    <tr><td>Tiền phòng</td><td class="text-end" id="ct_phong"></td></tr>
                    <tr><td>Tiền dịch vụ</td><td class="text-end" id="ct_dv"></td></tr>
                    <tr><td>Phụ thu</td><td class="text-end" id="ct_phuthu"></td></tr>
                    <tr><td>Ưu đãi (trừ)</td><td class="text-end text-success" id="ct_uudai"></td></tr>
                    <tr><td>Thuế VAT 10%</td><td class="text-end" id="ct_vat"></td></tr>
                    <tr class="fw-bold"><td>Tổng thanh toán</td><td class="text-end text-primary" id="ct_tong"></td></tr>
                    <tr><td>Đã thanh toán (đã trừ hoàn tiền)</td><td class="text-end text-success" id="ct_da"></td></tr>
                    <tr class="fw-bold"><td>Còn nợ</td><td class="text-end text-danger" id="ct_no"></td></tr>
                </table>
            </div>
        </div>
    </div>
</div>
 
<script>
    function vnd(n) { return Number(n).toLocaleString('vi-VN') + 'đ'; }
    document.querySelectorAll('.btn-thu').forEach(function (b) {
        b.addEventListener('click', function () {
            document.getElementById('thu_mahd').value = b.dataset.mahd;
            document.getElementById('thu_title').textContent = b.dataset.mahd;
            document.getElementById('thu_khach').textContent = b.dataset.khach;
            document.getElementById('thu_tong').textContent = vnd(b.dataset.tong);
            document.getElementById('thu_conno_txt').textContent = vnd(b.dataset.conno);
            var i = document.getElementById('thu_sotien');
            i.value = b.dataset.conno;
            i.max = b.dataset.conno;
        });
    });
    document.querySelectorAll('.btn-ct').forEach(function (b) {
        b.addEventListener('click', function () {
            var d = JSON.parse(b.dataset.hd);
            ['ma', 'khach', 'ngay', 'phong', 'dv', 'phuthu', 'uudai', 'vat', 'tong', 'da', 'no'].forEach(function (k) {
                document.getElementById('ct_' + k).textContent = d[k];
            });
        });
    });
</script>
 
<?php include 'includes/footer.php'; ?>