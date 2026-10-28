<?php
define('NO_AUTH', true);                       // functions.php không ép đăng nhập admin
require_once __DIR__ . '/../admin/includes/functions.php';
require_once __DIR__ . '/../config/database.php';
requireRole('khach');

/** Bỏ dấu tiếng Việt + bỏ khoảng trắng: "Gia đình" -> "giadinh". */
function slugVN(string $s): string
{
    static $map = null;
    if ($map === null) {
        $map = [];
        $groups = ['a' => 'àáạảãâầấậẩẫăằắặẳẵ', 'e' => 'èéẹẻẽêềếệểễ', 'i' => 'ìíịỉĩ',
                   'o' => 'òóọỏõôồốộổỗơờớợởỡ', 'u' => 'ùúụủũưừứựửữ', 'y' => 'ỳýỵỷỹ', 'd' => 'đ'];
        foreach ($groups as $to => $chars) {
            foreach (mb_str_split($chars) as $c) {
                $map[$c] = $to;
            }
        }
    }
    $s = strtr(mb_strtolower($s, 'UTF-8'), $map);
    return preg_replace('/[^a-z0-9]+/', '', $s);
}

// Loại phòng nào tên không trùng tên ảnh thì ghép tay ở đây:
// 'tên loại phòng viết thường không dấu' => 'tên file ảnh (không có đuôi)'
$anhAlias = [
    // 'don' => 'Thuong',
];

$u      = authUser();
$maKH   = $u['ma'];
$maNV   = 'NV01';          // nhân viên "đại diện" ghi nhận phiếu đặt online
$err    = '';
$reopen = false;
$action = $_SERVER['REQUEST_METHOD'] === 'POST' ? ($_POST['action'] ?? '') : '';

// ---------------- XỬ LÝ ĐẶT / HỦY ----------------
if ($action !== '') {
    try {
        if ($action === 'dat_phong') {
            $maPhong = trim($_POST['ma_phong'] ?? '');
            $ht      = $_POST['hinh_thuc'] ?? 'ngay';
            if (!in_array($ht, ['gio', 'dem', 'ngay'], true)) {
                $ht = 'ngay';
            }
            $soNguoi = max(1, (int)($_POST['so_nguoi'] ?? 1));
            $tn      = strtotime($_POST['gio_nhan'] ?? '');
            $tt      = strtotime($_POST['gio_tra'] ?? '');
            $ghiChu  = trim($_POST['ghi_chu'] ?? '');

            if ($maPhong === '') {
                throw new Exception('Vui lòng chọn phòng.');
            }
            if (!$tn || !$tt) {
                throw new Exception('Vui lòng nhập giờ nhận và giờ trả.');
            }
            if ($tt <= $tn) {
                throw new Exception('Giờ trả phải sau giờ nhận.');
            }

            $sql = "SET NOCOUNT ON;
                DECLARE @ht NVARCHAR(20) = CASE CAST(? AS VARCHAR(10))
                    WHEN 'gio' THEN " . nl('Theo giờ') . " WHEN 'dem' THEN " . nl('Qua đêm') . " ELSE " . nl('Theo ngày') . " END;
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
                throw new Exception('Không nhận được kết quả từ hệ thống đặt phòng.');
            }
            if ((int)$r['Ok'] !== 1) {
                $err = $r['ThongBao'];
                $reopen = true;
            } else {
                header('Location: index.php?tab=pt&ok=' . urlencode($r['ThongBao']));
                exit;
            }
        } elseif ($action === 'huy') {
            $pt = trim($_POST['ma_phieu'] ?? '');
            // chỉ cho hủy phiếu CỦA CHÍNH KHÁCH và đang ở trạng thái "Đã đặt"
            $own = (int)qVal($conn, "SELECT COUNT(*) FROM dbo.PhieuThue WHERE MaPhieuThue = ? AND MaKH = ? AND TrangThai = " . nl('Đã đặt'), [$pt, $maKH]);
            if ($own !== 1) {
                throw new Exception('Chỉ hủy được phiếu của bạn đang ở trạng thái "Đã đặt".');
            }
            $r = qBatch($conn, "SET NOCOUNT ON;
                DECLARE @tb NVARCHAR(300);
                EXEC dbo.sp_HuyPhieuThue @MaPhieuThue = ?, @MaNV = ?, @ThongBao = @tb OUTPUT;
                SELECT CAST(@tb AS NVARCHAR(MAX)) AS ThongBao;", [$pt, $maNV]);
            $da = (int)qVal($conn, "SELECT CASE WHEN TrangThai = " . nl('Đã hủy') . " THEN 1 ELSE 0 END FROM dbo.PhieuThue WHERE MaPhieuThue = ?", [$pt]);
            if ($da !== 1) {
                throw new Exception($r['ThongBao'] ?? 'Không hủy được phiếu.');
            }
            header('Location: index.php?tab=pt&ok=' . urlencode("Đã hủy phiếu $pt."));
            exit;
        }
    } catch (Throwable $e) {
        $err = friendlyErr($e);
        $reopen = ($action === 'dat_phong');
    }
}

// ---------------- DỮ LIỆU ----------------
$tab = $_GET['tab'] ?? 'phong';
if ($action === 'huy') {
    $tab = 'pt';
}

$tenKH = qVal($conn, "SELECT " . nvc('HoTen') . " FROM dbo.KhachHang WHERE MaKH = ?", [$maKH]) ?? $u['name'];

$rooms = qAll($conn, "
    SELECT p.MaPhong, p.MaLoaiPhong, v.SoPhong, " . nvc('v.TenLoaiPhong') . ", v.SucChua, v.DonGiaTheoNgay,
           CASE v.TinhTrang WHEN " . nl('Trống') . " THEN 'trong' WHEN " . nl('Đang thuê') . " THEN 'thue'
                            WHEN " . nl('Đang dọn') . " THEN 'don' ELSE 'bt' END AS MaTT
    FROM dbo.vw_TrangThaiPhong v
    JOIN dbo.Phong p ON p.MaPhong = v.MaPhong
    ORDER BY v.SoPhong");

$types = [];
$bookable = [];
$ttLabel = ['trong' => 'Trống', 'thue' => 'Đang có khách', 'don' => 'Đang dọn'];
foreach ($rooms as $r) {
    $k = $r['MaLoaiPhong'];
    if (!isset($types[$k])) {
        $types[$k] = ['ma' => $k, 'ten' => $r['TenLoaiPhong'], 'gia' => (float)$r['DonGiaTheoNgay'],
                      'sc' => (int)$r['SucChua'], 'tong' => 0, 'trong' => 0];
    }
    $types[$k]['tong']++;
    $types[$k]['gia'] = min($types[$k]['gia'], (float)$r['DonGiaTheoNgay']);
    $types[$k]['sc']  = max($types[$k]['sc'], (int)$r['SucChua']);
    if ($r['MaTT'] === 'trong') {
        $types[$k]['trong']++;
    }
    if ($r['MaTT'] !== 'bt') {
        $bookable[] = ['ma' => $r['MaPhong'], 'loai' => $k, 'so' => $r['SoPhong'],
                       'tt' => $ttLabel[$r['MaTT']], 'gia' => money($r['DonGiaTheoNgay']), 'sc' => (int)$r['SucChua']];
    }
}

$dvs = qAll($conn, "SELECT MaDichVu, " . nvc('TenDichVu') . ", " . nvc('MoTa') . ", " . nvc('DonViTinh') . ", DonGia
                    FROM dbo.DichVu ORDER BY MaDichVu");

$myPT = qAll($conn, "
    SELECT pt.MaPhieuThue, " . dtc('pt.NgayLap', 'NgayLap') . ", " . ptCodeSql('pt.TrangThai') . " AS MaTT,
           CAST((SELECT STRING_AGG(p.SoPhong, ', ') FROM dbo.ChiTietPhieuThue ct
                 JOIN dbo.Phong p ON p.MaPhong = ct.MaPhong WHERE ct.MaPhieuThue = pt.MaPhieuThue) AS NVARCHAR(MAX)) AS DsPhong,
           (SELECT CONVERT(VARCHAR(19), MIN(ct.GioNhan), 120) FROM dbo.ChiTietPhieuThue ct WHERE ct.MaPhieuThue = pt.MaPhieuThue) AS GioNhan,
           (SELECT CONVERT(VARCHAR(19), MAX(ct.GioTra), 120) FROM dbo.ChiTietPhieuThue ct WHERE ct.MaPhieuThue = pt.MaPhieuThue) AS GioTra
    FROM dbo.PhieuThue pt
    WHERE pt.MaKH = ?
    ORDER BY pt.NgayLap DESC, pt.MaPhieuThue DESC", [$maKH]);

$defNhan = date('Y-m-d\TH:i');
$defTra  = date('Y-m-d\T12:00', strtotime('+1 day'));
$gradients = ['#4facfe,#00f2fe', '#f6d365,#fda085', '#a18cd1,#fbc2eb', '#84fab0,#8fd3f4', '#fccb90,#d57eeb'];
?>
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Đặt phòng - Hotel</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body { background: #f1f5f9; }
    .room-img { height: 180px; background-size: cover; background-position: center;
                display: flex; align-items: center; justify-content: center; font-size: 3rem; }
</style>
</head>
<body>
<nav class="navbar navbar-dark bg-dark px-3 mb-4">
    <span class="navbar-brand fw-bold">🏨 HOTEL</span>
    <div class="text-white d-flex align-items-center gap-3">
        <span>Xin chào, <strong><?= esc($tenKH) ?></strong> (<?= esc($maKH) ?>)</span>
        <a href="<?= APP_BASE ?>/logout.php" class="btn btn-sm btn-outline-light">Đăng xuất</a>
    </div>
</nav>

<div class="container pb-5">
    <?php if (!empty($_GET['ok'])): ?>
        <div class="alert alert-success alert-dismissible fade show"><?= esc($_GET['ok']) ?><button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
    <?php endif; ?>
    <?php if ($err !== ''): ?>
        <div class="alert alert-danger alert-dismissible fade show"><?= esc($err) ?><button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
    <?php endif; ?>

    <ul class="nav nav-tabs mb-3">
        <li class="nav-item"><button class="nav-link <?= $tab === 'phong' ? 'active' : '' ?>" data-bs-toggle="tab" data-bs-target="#tab-phong" type="button">Phòng &amp; đặt phòng</button></li>
        <li class="nav-item"><button class="nav-link <?= $tab === 'dv' ? 'active' : '' ?>" data-bs-toggle="tab" data-bs-target="#tab-dv" type="button">Dịch vụ</button></li>
        <li class="nav-item"><button class="nav-link <?= $tab === 'pt' ? 'active' : '' ?>" data-bs-toggle="tab" data-bs-target="#tab-pt" type="button">Phiếu của tôi (<?= count($myPT) ?>)</button></li>
    </ul>

    <div class="tab-content">
        <!-- TAB PHÒNG -->
        <div class="tab-pane fade <?= $tab === 'phong' ? 'show active' : '' ?>" id="tab-phong">
        <?php $dirImg = __DIR__ . '/img'; ?>
</div>
            <div class="row g-4">
                <?php $i = 0; foreach ($types as $t):
                    // Tìm ảnh theo tên loại phòng: Thường -> Thuong.png, Gia đình -> Giadinh.png ...
                    $hasImg = false;
                    $slug   = slugVN($t['ten']);
                    $imgRel = 'img/' . $slug . '.png';   // tên gợi ý khi chưa có ảnh
                    $cands  = array_filter([$anhAlias[$slug] ?? null, $t['ma'], $slug, ucfirst($slug), strtoupper($slug)]);
                    foreach ($cands as $nm) {
                        foreach (['png', 'jpg', 'jpeg', 'webp'] as $ext) {
                            if (file_exists(__DIR__ . '/img/' . $nm . '.' . $ext)) {
                                $imgRel = 'img/' . $nm . '.' . $ext;
                                $hasImg = true;
                                break 2;
                            }
                        }
                    }
                    $grad = $gradients[$i++ % count($gradients)];
                ?>
                <div class="col-md-6 col-lg-4">
                    <div class="card border-0 shadow-sm h-100 overflow-hidden">
                        <?php if ($hasImg): ?>
                            <div class="room-img" style="background-image:url('<?= esc($imgRel) ?>')"></div>
                        <?php else: ?>
                            <div class="room-img" style="background:linear-gradient(135deg,<?= $grad ?>)">🛏️</div>
                        <?php endif; ?>
                        <div class="card-body">
                            <h5 class="fw-bold mb-1"><?= esc($t['ten']) ?></h5>
                            <div class="text-muted small mb-2">Tối đa <?= (int)$t['sc'] ?> người · <?= (int)$t['tong'] ?> phòng</div>
                            <div class="fs-5 fw-bold text-primary mb-2">Từ <?= money($t['gia']) ?> <small class="text-muted fs-6">/ ngày</small></div>
                            <span class="badge <?= $t['trong'] > 0 ? 'bg-success' : 'bg-secondary' ?>">Còn <?= (int)$t['trong'] ?> phòng trống</span>
                            <?php if (!$hasImg): ?><div class="text-muted" style="font-size:.7rem">(thêm ảnh: khach/<?= esc($imgRel) ?>)</div><?php endif; ?>
                        </div>
                        <div class="card-footer bg-white border-0 pb-3">
                            <button class="btn btn-primary w-100 fw-bold btn-dat" data-loai="<?= esc($t['ma']) ?>" data-bs-toggle="modal" data-bs-target="#modalDat">Đặt phòng loại này</button>
                        </div>
                    </div>
                </div>
                <?php endforeach; ?>
            </div>
        </div>

        <!-- TAB DỊCH VỤ -->
        <div class="tab-pane fade <?= $tab === 'dv' ? 'show active' : '' ?>" id="tab-dv">
            <div class="row g-3">
                <?php foreach ($dvs as $d): ?>
                <div class="col-md-6 col-lg-4">
                    <div class="card border-0 shadow-sm h-100"><div class="card-body">
                        <div class="d-flex justify-content-between">
                            <h6 class="fw-bold mb-1"><?= esc($d['TenDichVu']) ?></h6>
                            <span class="fw-bold text-primary"><?= money($d['DonGia']) ?></span>
                        </div>
                        <div class="small text-muted">Đơn vị: <?= esc($d['DonViTinh']) ?></div>
                        <p class="small mb-0 mt-2"><?= esc($d['MoTa'] ?? '') ?></p>
                    </div></div>
                </div>
                <?php endforeach; ?>
            </div>
            <div class="small text-muted mt-3">Dịch vụ được ghi nhận bởi lễ tân khi bạn lưu trú.</div>
        </div>

        <!-- TAB PHIẾU CỦA TÔI -->
        <div class="tab-pane fade <?= $tab === 'pt' ? 'show active' : '' ?>" id="tab-pt">
            <div class="card border-0 shadow-sm p-3">
                <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-dark"><tr><th>Mã phiếu</th><th>Phòng</th><th>Nhận</th><th>Trả</th><th>Trạng thái</th><th></th></tr></thead>
                    <tbody>
                    <?php if (!$myPT): ?><tr><td colspan="6" class="text-center text-muted py-4">Bạn chưa có phiếu thuê nào.</td></tr><?php endif; ?>
                    <?php foreach ($myPT as $p): ?>
                    <tr>
                        <td class="fw-bold"><?= esc($p['MaPhieuThue']) ?></td>
                        <td><span class="badge bg-secondary"><?= esc($p['DsPhong']) ?></span></td>
                        <td><?= fdt($p['GioNhan']) ?></td>
                        <td><?= fdt($p['GioTra']) ?></td>
                        <td><?= ptBadge($p['MaTT']) ?></td>
                        <td class="text-end">
                            <?php if ($p['MaTT'] === 'dat'): ?>
                            <form method="POST" onsubmit="return confirm('Hủy phiếu <?= esc($p['MaPhieuThue']) ?>?');">
                                <input type="hidden" name="action" value="huy">
                                <input type="hidden" name="ma_phieu" value="<?= esc($p['MaPhieuThue']) ?>">
                                <button class="btn btn-sm btn-outline-danger">Hủy phiếu</button>
                            </form>
                            <?php endif; ?>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- MODAL ĐẶT PHÒNG -->
<div class="modal fade" id="modalDat" tabindex="-1">
<div class="modal-dialog modal-lg"><div class="modal-content">
<form method="POST">
    <input type="hidden" name="action" value="dat_phong">
    <div class="modal-header bg-primary text-white">
        <h5 class="modal-title fw-bold">ĐẶT PHÒNG</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
    </div>
    <div class="modal-body"><div class="row g-3">
        <div class="col-md-6">
            <label class="form-label fw-bold">Phòng</label>
            <select name="ma_phong" id="selPhong" class="form-select" required></select>
        </div>
        <div class="col-md-6">
            <label class="form-label fw-bold">Hình thức thuê</label>
            <?php $htOld = $_POST['hinh_thuc'] ?? 'ngay'; ?>
            <select name="hinh_thuc" class="form-select">
                <option value="gio"  <?= $htOld === 'gio'  ? 'selected' : '' ?>>Theo giờ</option>
                <option value="dem"  <?= $htOld === 'dem'  ? 'selected' : '' ?>>Qua đêm</option>
                <option value="ngay" <?= $htOld === 'ngay' ? 'selected' : '' ?>>Theo ngày</option>
            </select>
        </div>
        <div class="col-md-4"><label class="form-label fw-bold">Giờ nhận</label>
            <input type="datetime-local" name="gio_nhan" class="form-control" value="<?= esc($_POST['gio_nhan'] ?? $defNhan) ?>" required></div>
        <div class="col-md-4"><label class="form-label fw-bold">Giờ trả</label>
            <input type="datetime-local" name="gio_tra" class="form-control" value="<?= esc($_POST['gio_tra'] ?? $defTra) ?>" required></div>
        <div class="col-md-4"><label class="form-label fw-bold">Số người</label>
            <input type="number" name="so_nguoi" min="1" class="form-control" value="<?= esc($_POST['so_nguoi'] ?? 1) ?>" required></div>
        <div class="col-12"><label class="form-label fw-bold">Ghi chú</label>
            <textarea name="ghi_chu" rows="2" class="form-control"><?= esc($_POST['ghi_chu'] ?? '') ?></textarea></div>
    </div></div>
    <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>
        <button type="submit" class="btn btn-primary fw-bold">Xác nhận đặt phòng</button>
    </div>
</form>
</div></div></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
var ROOMS = <?= json_encode($bookable, JSON_UNESCAPED_UNICODE) ?>;
var PRE   = <?= json_encode($_POST['ma_phong'] ?? '') ?>;
function fillRooms(loai, pre) {
    var s = document.getElementById('selPhong');
    s.innerHTML = '<option value="">-- Chọn phòng --</option>';
    ROOMS.forEach(function (r) {
        if (loai && r.loai !== loai) { return; }
        var o = document.createElement('option');
        o.value = r.ma;
        o.textContent = 'P.' + r.so + ' (' + r.sc + ' người, ' + r.gia + '/ngày) [' + r.tt + ']';
        if (pre && pre === r.ma) { o.selected = true; }
        s.appendChild(o);
    });
}
document.querySelectorAll('.btn-dat').forEach(function (b) {
    b.addEventListener('click', function () { fillRooms(b.dataset.loai, ''); });
});
<?php if ($reopen): ?>
window.addEventListener('load', function () {
    fillRooms('', PRE);
    new bootstrap.Modal(document.getElementById('modalDat')).show();
});
<?php endif; ?>
</script>
</body>
</html>