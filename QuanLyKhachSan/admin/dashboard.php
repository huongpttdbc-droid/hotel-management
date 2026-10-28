<?php
require_once __DIR__ . '/includes/functions.php';
$pageTitle  = 'Sơ Đồ Phòng';
$activePage = 'dashboard';
include 'includes/header.php';

$err = '';

// Đổi tình trạng phòng (Trống / Đang dọn / Bảo trì)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'doi_tinh_trang') {
    $ma = trim($_POST['ma_phong'] ?? '');
    $to = $_POST['tinh_trang'] ?? '';
    try {
        if (!in_array($to, ['trong', 'don', 'bt'], true)) {
            throw new Exception('Trạng thái không hợp lệ.');
        }
        $n = qRun($conn, "UPDATE dbo.Phong
                          SET TinhTrang = CASE CAST(? AS VARCHAR(10))
                                WHEN 'trong' THEN " . nl('Trống') . "
                                WHEN 'don' THEN " . nl('Đang dọn') . "
                                ELSE " . nl('Bảo trì') . " END
                          WHERE MaPhong = ? AND TinhTrang <> " . nl('Đang thuê'), [$to, $ma]);
        if ($n < 1) {
            throw new Exception('Không thể đổi trạng thái (phòng không tồn tại hoặc đang có khách).');
        }
        redirectOk('dashboard.php', 'Đã cập nhật tình trạng phòng ' . $ma . '.');
    } catch (Throwable $e) {
        $err = friendlyErr($e);
    }
}

$rooms = qAll($conn, "
    SELECT ph.MaPhong, ph.SoPhong, ph.Tang,
           CASE ph.TinhTrang WHEN " . nl('Trống') . " THEN 'trong'
                             WHEN " . nl('Đang thuê') . " THEN 'thue'
                             WHEN " . nl('Đang dọn') . " THEN 'don'
                             ELSE 'bt' END AS MaTT,
           " . nvc('ph.TinhTrang') . ",
           " . nvc('ph.TenLoaiPhong') . ",
           ph.SucChua, ph.DonGiaTheoNgay,
           (SELECT TOP 1 CAST(k.HoTen AS NVARCHAR(MAX))
              FROM dbo.ChiTietPhieuThue ct
              JOIN dbo.PhieuThue pt ON pt.MaPhieuThue = ct.MaPhieuThue
              JOIN dbo.KhachHang k ON k.MaKH = pt.MaKH
             WHERE ct.MaPhong = ph.MaPhong AND pt.TrangThai = " . nl('Đang thuê') . "
             ORDER BY ct.GioNhan DESC) AS KhachHienTai,
           (SELECT TOP 1 pt.MaPhieuThue
              FROM dbo.ChiTietPhieuThue ct
              JOIN dbo.PhieuThue pt ON pt.MaPhieuThue = ct.MaPhieuThue
             WHERE ct.MaPhong = ph.MaPhong AND pt.TrangThai = " . nl('Đang thuê') . "
             ORDER BY ct.GioNhan DESC) AS PhieuHienTai
    FROM dbo.vw_TrangThaiPhong ph
    ORDER BY ph.Tang, ph.SoPhong");

$cnt = ['trong' => 0, 'thue' => 0, 'don' => 0, 'bt' => 0];
$byFloor = [];
foreach ($rooms as $r) {
    $cnt[$r['MaTT']]++;
    $byFloor[$r['Tang']][] = $r;
}

$pt = qOne($conn, "SELECT
        ISNULL(SUM(CASE WHEN TrangThai = " . nl('Đã đặt') . "    THEN 1 ELSE 0 END), 0) AS DaDat,
        ISNULL(SUM(CASE WHEN TrangThai = " . nl('Đang thuê') . " THEN 1 ELSE 0 END), 0) AS DangThue
    FROM dbo.PhieuThue");
$hdNo = (int)qVal($conn, "SELECT COUNT(*) FROM dbo.HoaDon WHERE TrangThai = " . nl('Chưa thanh toán'));

$style = [
    'trong' => ['success', 'st-trong'],
    'thue'  => ['danger', 'st-thue'],
    'don'   => ['warning text-dark', 'st-don'],
    'bt'    => ['secondary', 'st-bt'],
];
?>
<style>
    .room-card { border-left: 6px solid #ccc; }
    .st-trong { border-left-color: #198754; }
    .st-thue  { border-left-color: #dc3545; }
    .st-don   { border-left-color: #ffc107; }
    .st-bt    { border-left-color: #6c757d; }
    .room-filter { opacity: .55; }
    .room-filter.active { opacity: 1; box-shadow: 0 0 0 3px rgba(13,110,253,.35); }
    .stat-click { cursor: pointer; }
    .stat-click:hover { box-shadow: 0 .25rem .75rem rgba(0,0,0,.15) !important; }
</style>

<?php flashHtml($err); ?>

<div class="row g-3 mb-4">
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm stat-click" data-f="all"><div class="card-body">
        <div class="text-muted small">Tổng số phòng</div><div class="fs-3 fw-bold"><?= count($rooms) ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm stat-click" data-f="trong"><div class="card-body">
        <div class="text-muted small">Phòng trống</div><div class="fs-3 fw-bold text-success"><?= $cnt['trong'] ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm stat-click" data-f="thue"><div class="card-body">
        <div class="text-muted small">Đang có khách</div><div class="fs-3 fw-bold text-danger"><?= $cnt['thue'] ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm stat-click" data-f="don"><div class="card-body">
        <div class="text-muted small">Đang dọn / Bảo trì</div><div class="fs-3 fw-bold text-warning"><?= $cnt['don'] ?> / <?= $cnt['bt'] ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Phiếu đã đặt (chờ nhận)</div><div class="fs-3 fw-bold text-primary"><?= (int)$pt['DaDat'] ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Phiếu đang thuê</div><div class="fs-3 fw-bold"><?= (int)$pt['DangThue'] ?></div></div></div></div>
    <div class="col-6 col-xl-3"><div class="card border-0 shadow-sm"><div class="card-body">
        <div class="text-muted small">Hóa đơn chưa thanh toán</div>
        <div class="fs-3 fw-bold text-danger"><?= $hdNo ?></div>
        <a href="hoa_don.php?tt=chua" class="small">Xem danh sách</a></div></div></div>
</div>

<div class="card border-0 shadow-sm p-3 mb-3">
    <div class="d-flex flex-wrap gap-2 align-items-center">
        <strong class="me-2">Lọc phòng:</strong>
        <button class="btn btn-sm btn-dark room-filter active" data-f="all">Tất cả (<?= count($rooms) ?>)</button>
        <button class="btn btn-sm btn-success room-filter" data-f="trong">Trống (<?= $cnt['trong'] ?>)</button>
        <button class="btn btn-sm btn-danger room-filter" data-f="thue">Đang thuê (<?= $cnt['thue'] ?>)</button>
        <button class="btn btn-sm btn-warning room-filter" data-f="don">Đang dọn (<?= $cnt['don'] ?>)</button>
        <button class="btn btn-sm btn-secondary room-filter" data-f="bt">Bảo trì (<?= $cnt['bt'] ?>)</button>
    </div>
</div>

<?php foreach ($byFloor as $tang => $list): ?>
<div class="floor-block">
    <h5 class="fw-bold mt-4 mb-2">Tầng <?= (int)$tang ?></h5>
    <div class="row g-3">
        <?php foreach ($list as $r):
            [$badge, $cls] = $style[$r['MaTT']];
        ?>
            <div class="col-12 col-md-6 col-xl-4 col-xxl-3 room-item" data-status="<?= $r['MaTT'] ?>">
                <div class="card h-100 shadow-sm room-card <?= $cls ?>">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="fw-bold fs-4">P.<?= esc($r['SoPhong']) ?></span>
                            <span class="badge bg-<?= $badge ?>"><?= esc($r['TinhTrang']) ?></span>
                        </div>
                        <div class="small text-muted"><?= esc($r['TenLoaiPhong']) ?> · tối đa <?= (int)$r['SucChua'] ?> người</div>
                        <div class="small mb-2"><?= money($r['DonGiaTheoNgay']) ?> / ngày</div>

                        <?php if ($r['MaTT'] === 'thue'): ?>
                            <div class="small">Khách: <strong><?= esc($r['KhachHienTai'] ?? '—') ?></strong></div>
                            <?php if (!empty($r['PhieuHienTai'])): ?>
                                <a class="btn btn-sm btn-outline-dark mt-2" href="phieu_thue.php?xem=<?= esc($r['PhieuHienTai']) ?>">Xem phiếu <?= esc($r['PhieuHienTai']) ?></a>
                            <?php endif; ?>

                        <?php elseif ($r['MaTT'] === 'trong'): ?>
                            <div class="d-flex gap-2 mt-2">
                                <a class="btn btn-sm btn-success" href="phieu_thue.php?phong=<?= esc($r['MaPhong']) ?>">Đặt phòng</a>
                                <form method="POST" onsubmit="return confirm('Chuyển phòng <?= esc($r['SoPhong']) ?> sang BẢO TRÌ?');">
                                    <input type="hidden" name="action" value="doi_tinh_trang">
                                    <input type="hidden" name="ma_phong" value="<?= esc($r['MaPhong']) ?>">
                                    <input type="hidden" name="tinh_trang" value="bt">
                                    <button class="btn btn-sm btn-outline-secondary">Báo bảo trì</button>
                                </form>
                            </div>

                        <?php elseif ($r['MaTT'] === 'don'): ?>
                            <form method="POST" class="mt-2">
                                <input type="hidden" name="action" value="doi_tinh_trang">
                                <input type="hidden" name="ma_phong" value="<?= esc($r['MaPhong']) ?>">
                                <input type="hidden" name="tinh_trang" value="trong">
                                <button class="btn btn-sm btn-warning fw-bold">Dọn xong → Trống</button>
                            </form>

                        <?php else: ?>
                            <form method="POST" class="mt-2">
                                <input type="hidden" name="action" value="doi_tinh_trang">
                                <input type="hidden" name="ma_phong" value="<?= esc($r['MaPhong']) ?>">
                                <input type="hidden" name="tinh_trang" value="trong">
                                <button class="btn btn-sm btn-secondary">Hoàn tất bảo trì → Trống</button>
                            </form>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        <?php endforeach; ?>
    </div>
</div>
<?php endforeach; ?>

<script>
(function () {
    var btns   = document.querySelectorAll('.room-filter');
    var items  = document.querySelectorAll('.room-item');
    var floors = document.querySelectorAll('.floor-block');

    function apply(f) {
        items.forEach(function (el) {
            el.style.display = (f === 'all' || el.dataset.status === f) ? '' : 'none';
        });
        // Ẩn tầng không còn phòng nào hiển thị
        floors.forEach(function (fl) {
            var any = Array.prototype.some.call(fl.querySelectorAll('.room-item'), function (el) {
                return el.style.display !== 'none';
            });
            fl.style.display = any ? '' : 'none';
        });
        btns.forEach(function (b) { b.classList.toggle('active', b.dataset.f === f); });
        try { sessionStorage.setItem('roomFilter', f); } catch (e) {}
    }

    btns.forEach(function (b) {
        b.addEventListener('click', function () { apply(b.dataset.f); });
    });
    document.querySelectorAll('.stat-click').forEach(function (c) {
        c.addEventListener('click', function () { apply(c.dataset.f); });
    });

    var saved = 'all';
    try { saved = sessionStorage.getItem('roomFilter') || 'all'; } catch (e) {}
    apply(saved);
})();
</script>

<?php include 'includes/footer.php'; ?>