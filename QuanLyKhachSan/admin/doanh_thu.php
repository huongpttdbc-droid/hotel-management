
<?php
require_once __DIR__ . '/includes/functions.php';
$pageTitle  = 'Báo Cáo Doanh Thu';
$activePage = 'doanh_thu';
include 'includes/header.php';
 
$years = array_column(qAll($conn, "SELECT DISTINCT Nam FROM dbo.vw_TongHopDoanhThu ORDER BY Nam DESC"), 'Nam');
$nam = (int)($_GET['nam'] ?? ($years[0] ?? date('Y')));
 
$months = qAll($conn, "
    SELECT Thang, KyBaoCao, TongSoHoaDon, SoHoaDonDaThanhToan, SoHoaDonChuaThanhToan, TongLuotPhongThue,
           DoanhThuTienPhong, DoanhThuDichVu, TongTienPhuThu, TongTienUuDai, TongThueVAT,
           TongDoanhThuSauThue, TongThucThu, TongCongNoConLai
    FROM dbo.vw_TongHopDoanhThu WHERE Nam = ? ORDER BY Thang", [$nam]);
 
$sum = ['hd' => 0, 'luot' => 0, 'phong' => 0, 'dv' => 0, 'uudai' => 0, 'vat' => 0, 'tong' => 0, 'thu' => 0, 'no' => 0];
$labels = $dtData = $thuData = [];
foreach ($months as $m) {
    $sum['hd']    += (int)$m['TongSoHoaDon'];
    $sum['luot']  += (int)$m['TongLuotPhongThue'];
    $sum['phong'] += (float)$m['DoanhThuTienPhong'];
    $sum['dv']    += (float)$m['DoanhThuDichVu'];
    $sum['uudai'] += (float)$m['TongTienUuDai'];
    $sum['vat']   += (float)$m['TongThueVAT'];
    $sum['tong']  += (float)$m['TongDoanhThuSauThue'];
    $sum['thu']   += (float)$m['TongThucThu'];
    $sum['no']    += (float)$m['TongCongNoConLai'];
    $labels[]  = 'Tháng ' . (int)$m['Thang'];
    $dtData[]  = (float)$m['TongDoanhThuSauThue'];
    $thuData[] = (float)$m['TongThucThu'];
}
 
$theoLoai = qAll($conn, "
    SELECT " . nvc('lp.TenLoai', 'TenLoai') . ", COUNT(*) AS SoLuot,
           SUM(dbo.fn_TinhTienPhongTheoHinhThuc(ct.MaPhong, ct.HinhThucThue, ct.GioNhan, ct.GioTra)) AS DoanhThu
    FROM dbo.HoaDon hd
    JOIN dbo.ChiTietPhieuThue ct ON ct.MaPhieuThue = hd.MaPhieuThue
    JOIN dbo.Phong ph ON ph.MaPhong = ct.MaPhong
    JOIN dbo.LoaiPhong lp ON lp.MaLoaiPhong = ph.MaLoaiPhong
    WHERE hd.TrangThai <> N'Đã hủy' AND YEAR(hd.NgayLap) = ?
    GROUP BY lp.TenLoai
    ORDER BY DoanhThu DESC", [$nam]);
 
$topDV = qAll($conn, "
    SELECT TOP 5 " . nvc('dv.TenDichVu', 'TenDichVu') . ", SUM(d.SoLuong) AS SoLuong, SUM(d.SoLuong * dv.DonGia) AS DoanhThu
    FROM dbo.DungDichVu d
    JOIN dbo.HoaDon hd ON hd.MaPhieuThue = d.MaPhieuThue
    JOIN dbo.DichVu dv ON dv.MaDichVu = d.MaDichVu
    WHERE hd.TrangThai <> N'Đã hủy' AND YEAR(hd.NgayLap) = ?
    GROUP BY dv.MaDichVu, dv.TenDichVu
    ORDER BY DoanhThu DESC", [$nam]);
 
$topKH = qAll($conn, "
    SELECT TOP 5 MaKH, " . nvc('HoTenKhachHang', 'HoTen') . ", COUNT(*) AS SoHD, SUM(TongThanhTien) AS Tong
    FROM dbo.vw_ChiTietHoaDon
    WHERE TrangThaiHoaDon <> N'Đã hủy' AND YEAR(NgayLapHoaDon) = ?
    GROUP BY MaKH, HoTenKhachHang
    ORDER BY Tong DESC", [$nam]);
?>
 
<form method="GET" class="d-flex align-items-center gap-2 mb-3">
    <label class="fw-bold">Năm báo cáo:</label>
    <select name="nam" class="form-select w-auto" onchange="this.form.submit()">
        <?php if (!$years): ?><option value="<?= $nam ?>"><?= $nam ?></option><?php endif; ?>
        <?php foreach ($years as $y): ?>
            <option value="<?= (int)$y ?>" <?= (int)$y === $nam ? 'selected' : '' ?>><?= (int)$y ?></option>
        <?php endforeach; ?>
    </select>
    <noscript><button class="btn btn-dark">Xem</button></noscript>
</form>
 
<?php if (!$months): ?>
    <div class="alert alert-info">Chưa có dữ liệu hóa đơn trong năm <?= $nam ?>.</div>
<?php else: ?>
 
<div class="row g-3 mb-4">
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Doanh thu (sau VAT)</div><div class="fs-5 fw-bold text-primary"><?= money($sum['tong']) ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Thực thu</div><div class="fs-5 fw-bold text-success"><?= money($sum['thu']) ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Công nợ còn lại</div><div class="fs-5 fw-bold text-danger"><?= money($sum['no']) ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Số hóa đơn / Lượt phòng</div><div class="fs-5 fw-bold"><?= $sum['hd'] ?> / <?= $sum['luot'] ?></div></div></div></div>
</div>
 
<div class="card border-0 shadow-sm p-3 mb-4">
    <h5 class="fw-bold">Doanh thu theo tháng - năm <?= $nam ?></h5>
    <div style="position:relative;height:320px"><canvas id="chartDT"></canvas></div>
</div>
 
<div class="card border-0 shadow-sm p-3 mb-4">
    <h5 class="fw-bold mb-3">Chi tiết theo tháng</h5>
    <div class="table-responsive">
        <table class="table table-hover table-bordered align-middle text-end">
            <thead class="table-dark text-center">
            <tr><th>Kỳ</th><th>Số HĐ</th><th>Lượt phòng</th><th>Tiền phòng</th><th>Dịch vụ</th><th>Ưu đãi</th><th>VAT</th><th>Doanh thu</th><th>Thực thu</th><th>Công nợ</th></tr>
            </thead>
            <tbody>
            <?php foreach ($months as $m): ?>
                <tr>
                    <td class="text-center fw-bold"><?= esc($m['KyBaoCao']) ?></td>
                    <td class="text-center"><?= (int)$m['TongSoHoaDon'] ?> <small class="text-muted">(<?= (int)$m['SoHoaDonChuaThanhToan'] ?> nợ)</small></td>
                    <td class="text-center"><?= (int)$m['TongLuotPhongThue'] ?></td>
                    <td><?= money($m['DoanhThuTienPhong']) ?></td>
                    <td><?= money($m['DoanhThuDichVu']) ?></td>
                    <td class="text-success">-<?= money($m['TongTienUuDai']) ?></td>
                    <td><?= money($m['TongThueVAT']) ?></td>
                    <td class="fw-bold text-primary"><?= money($m['TongDoanhThuSauThue']) ?></td>
                    <td class="fw-bold text-success"><?= money($m['TongThucThu']) ?></td>
                    <td class="fw-bold text-danger"><?= money($m['TongCongNoConLai']) ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
            <tfoot class="table-light fw-bold">
            <tr><td class="text-center">Tổng</td><td class="text-center"><?= $sum['hd'] ?></td><td class="text-center"><?= $sum['luot'] ?></td>
                <td><?= money($sum['phong']) ?></td><td><?= money($sum['dv']) ?></td><td class="text-success">-<?= money($sum['uudai']) ?></td>
                <td><?= money($sum['vat']) ?></td><td class="text-primary"><?= money($sum['tong']) ?></td>
                <td class="text-success"><?= money($sum['thu']) ?></td><td class="text-danger"><?= money($sum['no']) ?></td></tr>
            </tfoot>
        </table>
    </div>
    <div class="small text-muted">Công nợ có thể âm nếu khách đã trả dư (ví dụ cọc lớn hơn hóa đơn).</div>
</div>
 
<div class="row g-3">
    <div class="col-lg-4"><div class="card border-0 shadow-sm p-3 h-100">
        <h6 class="fw-bold">Tiền phòng theo loại phòng</h6>
        <table class="table table-sm mb-0"><thead><tr><th>Loại</th><th class="text-center">Lượt</th><th class="text-end">Doanh thu</th></tr></thead><tbody>
        <?php foreach ($theoLoai as $t): ?>
            <tr><td><?= esc($t['TenLoai']) ?></td><td class="text-center"><?= (int)$t['SoLuot'] ?></td><td class="text-end"><?= money($t['DoanhThu']) ?></td></tr>
        <?php endforeach; ?>
        </tbody></table>
    </div></div>
    <div class="col-lg-4"><div class="card border-0 shadow-sm p-3 h-100">
        <h6 class="fw-bold">Top 5 dịch vụ</h6>
        <table class="table table-sm mb-0"><thead><tr><th>Dịch vụ</th><th class="text-center">SL</th><th class="text-end">Doanh thu</th></tr></thead><tbody>
        <?php foreach ($topDV as $t): ?>
            <tr><td><?= esc($t['TenDichVu']) ?></td><td class="text-center"><?= (int)$t['SoLuong'] ?></td><td class="text-end"><?= money($t['DoanhThu']) ?></td></tr>
        <?php endforeach; ?>
        <?php if (!$topDV): ?><tr><td colspan="3" class="text-muted">Chưa có dữ liệu.</td></tr><?php endif; ?>
        </tbody></table>
    </div></div>
    <div class="col-lg-4"><div class="card border-0 shadow-sm p-3 h-100">
        <h6 class="fw-bold">Top 5 khách hàng</h6>
        <table class="table table-sm mb-0"><thead><tr><th>Khách</th><th class="text-center">HĐ</th><th class="text-end">Tổng chi</th></tr></thead><tbody>
        <?php foreach ($topKH as $t): ?>
            <tr><td><?= esc($t['HoTen']) ?><br><small class="text-muted"><?= esc($t['MaKH']) ?></small></td><td class="text-center"><?= (int)$t['SoHD'] ?></td><td class="text-end"><?= money($t['Tong']) ?></td></tr>
        <?php endforeach; ?>
        <?php if (!$topKH): ?><tr><td colspan="3" class="text-muted">Chưa có dữ liệu.</td></tr><?php endif; ?>
        </tbody></table>
    </div></div>
</div>
 
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    window.addEventListener('load', function () {
        if (typeof Chart === 'undefined') { return; }
        new Chart(document.getElementById('chartDT'), {
            type: 'bar',
            data: {
                labels: <?= json_encode($labels, JSON_UNESCAPED_UNICODE) ?>,
                datasets: [
                    { label: 'Doanh thu (sau VAT)', data: <?= json_encode($dtData) ?>, backgroundColor: 'rgba(13,110,253,.7)' },
                    { label: 'Thực thu', data: <?= json_encode($thuData) ?>, backgroundColor: 'rgba(25,135,84,.7)' }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { y: { beginAtZero: true, ticks: { callback: function (v) { return v.toLocaleString('vi-VN'); } } } },
                plugins: { tooltip: { callbacks: { label: function (c) { return c.dataset.label + ': ' + c.parsed.y.toLocaleString('vi-VN') + 'đ'; } } } }
            }
        });
    });
</script>
 
<?php endif; ?>
 
<?php include 'includes/footer.php'; ?>