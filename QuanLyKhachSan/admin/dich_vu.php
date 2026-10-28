
<?php
require_once __DIR__ . '/includes/functions.php';
$pageTitle  = 'Dịch Vụ Khách Sạn';
$activePage = 'dich_vu';
include 'includes/header.php';
 
$err    = '';
$tab    = $_GET['tab'] ?? 'dm';
$action = $_SERVER['REQUEST_METHOD'] === 'POST' ? ($_POST['action'] ?? '') : '';
$reopen = false;
 
function readDV(): array
{
    $ten = trim($_POST['ten'] ?? '');
    $moTa = trim($_POST['mo_ta'] ?? '');
    $dvt = trim($_POST['dvt'] ?? '');
    $gia = (int)round((float)($_POST['don_gia'] ?? -1));
    if ($ten === '' || mb_strlen($ten) > 100) {
        throw new Exception('Tên dịch vụ không được để trống và tối đa 100 ký tự.');
    }
    if ($dvt === '' || mb_strlen($dvt) > 20) {
        throw new Exception('Đơn vị tính không được để trống và tối đa 20 ký tự.');
    }
    if (mb_strlen($moTa) > 500) {
        throw new Exception('Mô tả tối đa 500 ký tự.');
    }
    if ($gia < 0) {
        throw new Exception('Đơn giá phải từ 0 trở lên.');
    }
    return ['ten' => $ten, 'mota' => $moTa === '' ? null : $moTa, 'dvt' => $dvt, 'gia' => $gia];
}
 
if ($action !== '') {
    try {
        if ($action === 'them') {
            $d = readDV();
            $ma = nextId($conn, 'DichVu', 'MaDichVu', 'DV', 2);
            qRun($conn, "INSERT INTO dbo.DichVu (MaDichVu, TenDichVu, MoTa, DonViTinh, DonGia)
                         VALUES (?, " . uSql(100) . ", " . uSql(500) . ", " . uSql(20) . ", ?)",
                [$ma, uni($d['ten']), uni($d['mota']), uni($d['dvt']), (string)$d['gia']]);
            redirectOk('dich_vu.php', "Đã thêm dịch vụ $ma.");
        } elseif ($action === 'sua') {
            $ma = trim($_POST['ma_dv'] ?? '');
            $d = readDV();
            $n = qRun($conn, "UPDATE dbo.DichVu SET TenDichVu = " . uSql(100) . ", MoTa = " . uSql(500) . ",
                                     DonViTinh = " . uSql(20) . ", DonGia = ? WHERE MaDichVu = ?",
                [uni($d['ten']), uni($d['mota']), uni($d['dvt']), (string)$d['gia'], $ma]);
            if ($n < 1) {
                throw new Exception('Không tìm thấy dịch vụ.');
            }
            redirectOk('dich_vu.php', "Đã cập nhật dịch vụ $ma.");
        } elseif ($action === 'xoa') {
            $ma = trim($_POST['ma_dv'] ?? '');
            if ((int)qVal($conn, "SELECT COUNT(*) FROM dbo.DungDichVu WHERE MaDichVu = ?", [$ma]) > 0) {
                throw new Exception('Dịch vụ này đã được sử dụng nên không thể xóa.');
            }
            qRun($conn, "DELETE FROM dbo.DichVu WHERE MaDichVu = ?", [$ma]);
            redirectOk('dich_vu.php', "Đã xóa dịch vụ $ma.");
        } elseif ($action === 'ghi_nhan') {
            $tab = 'gn';
            [$pt, $stt] = array_pad(explode('|', $_POST['chi_tiet'] ?? ''), 2, '');
            $maDV = trim($_POST['ma_dv'] ?? '');
            $sl   = (int)($_POST['so_luong'] ?? 0);
            $tg   = strtotime($_POST['gio_bd'] ?? '');
            if ($pt === '' || $stt === '' || $maDV === '') {
                throw new Exception('Vui lòng chọn phòng đang thuê và dịch vụ.');
            }
            if ($sl < 1) {
                throw new Exception('Số lượng phải lớn hơn 0.');
            }
            if (!$tg) {
                $tg = time();
            }
            $r = qBatch($conn, "SET NOCOUNT ON;
                DECLARE @gb DATETIME = CONVERT(DATETIME, CAST(? AS VARCHAR(30)), 126);
                DECLARE @tb NVARCHAR(300);
                EXEC dbo.sp_ThemDichVu @MaPhieuThue = ?, @STT = ?, @MaDichVu = ?, @SoLuong = ?, @GioBD = @gb, @ThongBao = @tb OUTPUT;
                SELECT CASE WHEN @tb LIKE N'Thêm dịch vụ thành công%' THEN 1 ELSE 0 END AS Ok, CAST(@tb AS NVARCHAR(MAX)) AS ThongBao;",
                [date('Y-m-d\TH:i:s', $tg), $pt, (string)(int)$stt, $maDV, (string)$sl]);
            if (!$r) {
                throw new Exception('Không nhận được kết quả từ thủ tục thêm dịch vụ.');
            }
            if ((int)$r['Ok'] !== 1) {
                throw new Exception($r['ThongBao']);
            }
            redirectOk('dich_vu.php', "Đã ghi nhận dịch vụ cho phiếu $pt.", '&tab=gn');
        }
    } catch (Throwable $e) {
        $err = friendlyErr($e);
        $reopen = in_array($action, ['them', 'sua'], true);
    }
}
 
// ---------------- DỮ LIỆU ----------------
$dvs = qAll($conn, "
    SELECT d.MaDichVu, " . nvc('d.TenDichVu', 'TenDichVu') . ", " . nvc('d.MoTa', 'MoTa') . ", " . nvc('d.DonViTinh', 'DonViTinh') . ", d.DonGia,
           (SELECT COUNT(*) FROM dbo.DungDichVu u WHERE u.MaDichVu = d.MaDichVu) AS SoLanDung
    FROM dbo.DichVu d ORDER BY d.MaDichVu");
 
$q = trim($_GET['q'] ?? '');
$dsLoc = array_filter($dvs, function ($r) use ($q) {
    return $q === '' || mb_stripos($r['MaDichVu'] . ' ' . $r['TenDichVu'] . ' ' . $r['MoTa'], $q) !== false;
});
 
$cts = qAll($conn, "
    SELECT ct.MaPhieuThue, ct.STT, ph.SoPhong, " . nvc('kh.HoTen', 'HoTen') . ", " . ptCodeSql('pt.TrangThai') . " AS MaTT
    FROM dbo.ChiTietPhieuThue ct
    JOIN dbo.PhieuThue pt ON pt.MaPhieuThue = ct.MaPhieuThue
    JOIN dbo.Phong ph ON ph.MaPhong = ct.MaPhong
    JOIN dbo.KhachHang kh ON kh.MaKH = pt.MaKH
    WHERE pt.TrangThai IN (N'Đã đặt', N'Đang thuê')
    ORDER BY ct.MaPhieuThue, ct.STT");
 
$lichSu = qAll($conn, "
    SELECT TOP 100 d.MaPhieuThue, d.STT, ph.SoPhong, " . nvc('dv.TenDichVu', 'TenDichVu') . ", " . nvc('dv.DonViTinh', 'DonViTinh') . ",
           d.SoLuong, dv.DonGia, d.SoLuong * dv.DonGia AS ThanhTien, " . dtc('d.GioBD', 'GioBD') . "
    FROM dbo.DungDichVu d
    JOIN dbo.ChiTietPhieuThue ct ON ct.MaPhieuThue = d.MaPhieuThue AND ct.STT = d.STT
    JOIN dbo.Phong ph ON ph.MaPhong = ct.MaPhong
    JOIN dbo.DichVu dv ON dv.MaDichVu = d.MaDichVu
    ORDER BY d.GioBD DESC, d.MaPhieuThue DESC");
$tongLS = 0;
foreach ($lichSu as $l) {
    $tongLS += (float)$l['ThanhTien'];
}
?>
 
<?php flashHtml($err); ?>
 
<ul class="nav nav-tabs mb-3">
    <li class="nav-item"><button class="nav-link <?= $tab === 'dm' ? 'active' : '' ?>" data-bs-toggle="tab" data-bs-target="#tab-dm" type="button">Danh mục dịch vụ</button></li>
    <li class="nav-item"><button class="nav-link <?= $tab === 'gn' ? 'active' : '' ?>" data-bs-toggle="tab" data-bs-target="#tab-gn" type="button">Ghi nhận sử dụng</button></li>
    <li class="nav-item"><button class="nav-link <?= $tab === 'ls' ? 'active' : '' ?>" data-bs-toggle="tab" data-bs-target="#tab-ls" type="button">Lịch sử sử dụng</button></li>
</ul>
 
<div class="tab-content">
 
    <!-- TAB 1: DANH MỤC -->
    <div class="tab-pane fade <?= $tab === 'dm' ? 'show active' : '' ?>" id="tab-dm">
        <div class="card border-0 shadow-sm p-3">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h5 class="fw-bold mb-0">DANH MỤC DỊCH VỤ (<?= count($dsLoc) ?>/<?= count($dvs) ?>)</h5>
                <button class="btn btn-primary fw-bold" id="btnThemDV" data-bs-toggle="modal" data-bs-target="#modalDV">+ Thêm dịch vụ</button>
            </div>
            <form method="GET" class="row g-2 mb-3">
                <div class="col-md-6"><input type="text" name="q" value="<?= esc($q) ?>" class="form-control" placeholder="Tìm mã, tên, mô tả dịch vụ..."></div>
                <div class="col-md-6 d-flex gap-2"><button class="btn btn-dark">Tìm</button><a href="dich_vu.php" class="btn btn-outline-secondary">Xóa lọc</a></div>
            </form>
            <div class="table-responsive">
                <table class="table table-hover table-bordered align-middle">
                    <thead class="table-dark"><tr><th>Mã</th><th>Tên dịch vụ</th><th>Mô tả</th><th>ĐVT</th><th class="text-end">Đơn giá</th><th class="text-center">Lượt dùng</th><th class="text-center">Thao tác</th></tr></thead>
                    <tbody>
                    <?php foreach ($dsLoc as $d): ?>
                        <tr>
                            <td class="fw-bold"><?= esc($d['MaDichVu']) ?></td>
                            <td><?= esc($d['TenDichVu']) ?></td>
                            <td class="small text-muted"><?= esc($d['MoTa'] ?? '') ?></td>
                            <td><?= esc($d['DonViTinh']) ?></td>
                            <td class="text-end fw-bold"><?= money($d['DonGia']) ?></td>
                            <td class="text-center"><?= (int)$d['SoLanDung'] ?></td>
                            <td class="text-center text-nowrap">
                                <button class="btn btn-sm btn-warning btn-sua-dv" data-bs-toggle="modal" data-bs-target="#modalDV"
                                        data-dv='<?= esc(json_encode(['ma' => $d['MaDichVu'], 'ten' => $d['TenDichVu'], 'mt' => $d['MoTa'] ?? '', 'dvt' => $d['DonViTinh'], 'gia' => (int)$d['DonGia']], JSON_UNESCAPED_UNICODE)) ?>'>Sửa</button>
                                <?php if ((int)$d['SoLanDung'] === 0): ?>
                                    <form method="POST" class="d-inline" onsubmit="return confirm('Xóa dịch vụ <?= esc($d['MaDichVu']) ?>?');">
                                        <input type="hidden" name="action" value="xoa"><input type="hidden" name="ma_dv" value="<?= esc($d['MaDichVu']) ?>">
                                        <button class="btn btn-sm btn-outline-danger">Xóa</button>
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
 
    <!-- TAB 2: GHI NHẬN -->
    <div class="tab-pane fade <?= $tab === 'gn' ? 'show active' : '' ?>" id="tab-gn">
        <div class="card border-0 shadow-sm p-3" style="max-width:720px">
            <h5 class="fw-bold mb-3">GHI NHẬN DỊCH VỤ CHO KHÁCH</h5>
            <?php if (!$cts): ?>
                <div class="alert alert-info mb-0">Hiện không có phiếu thuê nào đang hiệu lực (Đã đặt / Đang thuê).</div>
            <?php else: ?>
            <form method="POST">
                <input type="hidden" name="action" value="ghi_nhan">
                <div class="mb-3">
                    <label class="form-label fw-bold">Phòng / Phiếu thuê</label>
                    <select name="chi_tiet" class="form-select" required>
                        <option value="">-- Chọn phòng --</option>
                        <?php foreach ($cts as $c): $v = $c['MaPhieuThue'] . '|' . $c['STT']; ?>
                            <option value="<?= esc($v) ?>" <?= ($_POST['chi_tiet'] ?? '') === $v ? 'selected' : '' ?>>
                                <?= esc($c['MaPhieuThue']) ?> - P.<?= esc($c['SoPhong']) ?> - <?= esc($c['HoTen']) ?> (<?= $c['MaTT'] === 'thue' ? 'Đang thuê' : 'Đã đặt' ?>)
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">Dịch vụ</label>
                    <select name="ma_dv" class="form-select" required>
                        <option value="">-- Chọn dịch vụ --</option>
                        <?php foreach ($dvs as $d): ?>
                            <option value="<?= esc($d['MaDichVu']) ?>" <?= ($_POST['ma_dv'] ?? '') === $d['MaDichVu'] ? 'selected' : '' ?>>
                                <?= esc($d['TenDichVu']) ?> - <?= money($d['DonGia']) ?>/<?= esc($d['DonViTinh']) ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="row g-3 mb-3">
                    <div class="col-md-4"><label class="form-label fw-bold">Số lượng</label>
                        <input type="number" name="so_luong" min="1" class="form-control" value="<?= esc($_POST['so_luong'] ?? 1) ?>" required></div>
                    <div class="col-md-8"><label class="form-label fw-bold">Thời điểm sử dụng</label>
                        <input type="datetime-local" name="gio_bd" class="form-control" value="<?= esc($_POST['gio_bd'] ?? date('Y-m-d\TH:i')) ?>"></div>
                </div>
                <button class="btn btn-success fw-bold">Ghi nhận dịch vụ</button>
            </form>
            <?php endif; ?>
        </div>
    </div>
 
    <!-- TAB 3: LỊCH SỬ -->
    <div class="tab-pane fade <?= $tab === 'ls' ? 'show active' : '' ?>" id="tab-ls">
        <div class="card border-0 shadow-sm p-3">
            <h5 class="fw-bold mb-3">100 LẦN SỬ DỤNG GẦN NHẤT <small class="text-muted fs-6">(tổng: <?= money($tongLS) ?>)</small></h5>
            <div class="table-responsive">
                <table class="table table-hover table-bordered align-middle">
                    <thead class="table-dark"><tr><th>Thời điểm</th><th>Phiếu</th><th>Phòng</th><th>Dịch vụ</th><th class="text-center">SL</th><th class="text-end">Đơn giá</th><th class="text-end">Thành tiền</th></tr></thead>
                    <tbody>
                    <?php foreach ($lichSu as $l): ?>
                        <tr>
                            <td><?= fdt($l['GioBD']) ?></td>
                            <td><a href="phieu_thue.php?xem=<?= esc($l['MaPhieuThue']) ?>"><?= esc($l['MaPhieuThue']) ?></a></td>
                            <td><?= esc($l['SoPhong']) ?></td>
                            <td><?= esc($l['TenDichVu']) ?></td>
                            <td class="text-center"><?= (int)$l['SoLuong'] ?> <?= esc($l['DonViTinh']) ?></td>
                            <td class="text-end"><?= money($l['DonGia']) ?></td>
                            <td class="text-end fw-bold"><?= money($l['ThanhTien']) ?></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
 
<!-- MODAL THÊM / SỬA DỊCH VỤ -->
<div class="modal fade" id="modalDV" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="POST" id="formDV">
                <input type="hidden" name="action" id="dv_action" value="<?= esc(in_array($action, ['them', 'sua'], true) ? $action : 'them') ?>">
                <input type="hidden" name="ma_dv" id="dv_ma" value="<?= esc(in_array($action, ['them', 'sua'], true) ? ($_POST['ma_dv'] ?? '') : '') ?>">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title fw-bold" id="dv_title">THÊM DỊCH VỤ</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3"><label class="form-label fw-bold">Tên dịch vụ</label>
                        <input type="text" name="ten" id="dv_ten" class="form-control" maxlength="100" required value="<?= esc($_POST['ten'] ?? '') ?>"></div>
                    <div class="mb-3"><label class="form-label fw-bold">Mô tả</label>
                        <textarea name="mo_ta" id="dv_mt" rows="2" class="form-control" maxlength="500"><?= esc($_POST['mo_ta'] ?? '') ?></textarea></div>
                    <div class="row g-3">
                        <div class="col-md-6"><label class="form-label fw-bold">Đơn vị tính</label>
                            <input type="text" name="dvt" id="dv_dvt" class="form-control" maxlength="20" required value="<?= esc($_POST['dvt'] ?? '') ?>"></div>
                        <div class="col-md-6"><label class="form-label fw-bold">Đơn giá (đ)</label>
                            <input type="number" name="don_gia" id="dv_gia" min="0" step="1000" class="form-control" required value="<?= esc($_POST['don_gia'] ?? '') ?>"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>
                    <button type="submit" class="btn btn-success fw-bold">Lưu</button>
                </div>
            </form>
        </div>
    </div>
</div>
 
<script>
    function setV(id, v) { document.getElementById(id).value = v; }
    document.getElementById('btnThemDV').addEventListener('click', function () {
        setV('dv_action', 'them'); setV('dv_ma', '');
        ['dv_ten', 'dv_mt', 'dv_dvt', 'dv_gia'].forEach(function (i) { setV(i, ''); });
        document.getElementById('dv_title').textContent = 'THÊM DỊCH VỤ';
    });
    document.querySelectorAll('.btn-sua-dv').forEach(function (b) {
        b.addEventListener('click', function () {
            var d = JSON.parse(b.dataset.dv);
            setV('dv_action', 'sua'); setV('dv_ma', d.ma);
            setV('dv_ten', d.ten); setV('dv_mt', d.mt); setV('dv_dvt', d.dvt); setV('dv_gia', d.gia);
            document.getElementById('dv_title').textContent = 'SỬA DỊCH VỤ ' + d.ma;
        });
    });
    <?php if ($reopen): ?>
    window.addEventListener('load', function () {
        new bootstrap.Modal(document.getElementById('modalDV')).show();
    });
    <?php endif; ?>
</script>
 
<?php include 'includes/footer.php'; ?>
