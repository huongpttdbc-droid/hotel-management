
<?php
require_once __DIR__ . '/includes/functions.php';
$pageTitle  = 'Quản Lý Khách Hàng';
$activePage = 'khach_hang';
include 'includes/header.php';
 
$err = '';
 
function parseList(string $s): array
{
    $a = preg_split('/[\s,;]+/', trim($s), -1, PREG_SPLIT_NO_EMPTY);
    return array_values(array_unique($a ?: []));
}
 
/** Đọc và kiểm tra dữ liệu form khách hàng. */
function readKH(array $loaiHopLe): array
{
    $hoTen = trim($_POST['ho_ten'] ?? '');
    if ($hoTen === '' || mb_strlen($hoTen) > 100) {
        throw new Exception('Họ tên không được để trống và tối đa 100 ký tự.');
    }
    $ns = DateTime::createFromFormat('Y-m-d', $_POST['ngay_sinh'] ?? '');
    if (!$ns || $ns->format('Y-m-d') !== ($_POST['ngay_sinh'] ?? '') || $ns > new DateTime('today')) {
        throw new Exception('Ngày sinh không hợp lệ.');
    }
    $cccd = trim($_POST['cccd'] ?? '');
    if (!preg_match('/^\d{12}$/', $cccd)) {
        throw new Exception('CCCD phải gồm đúng 12 chữ số.');
    }
    $diaChi = trim($_POST['dia_chi'] ?? '');
    if (mb_strlen($diaChi) > 200) {
        throw new Exception('Địa chỉ tối đa 200 ký tự.');
    }
    $loai = $_POST['ma_loai'] ?? '';
    if (!in_array($loai, $loaiHopLe, true)) {
        throw new Exception('Hạng khách hàng không hợp lệ.');
    }
    $sdts = parseList($_POST['sdt'] ?? '');
    foreach ($sdts as $s) {
        if (!preg_match('/^\d{10,11}$/', $s)) {
            throw new Exception("Số điện thoại \"$s\" không hợp lệ (10-11 chữ số).");
        }
    }
    $emails = parseList($_POST['email'] ?? '');
    foreach ($emails as $m) {
        if (!filter_var($m, FILTER_VALIDATE_EMAIL) || strlen($m) > 100) {
            throw new Exception("Email \"$m\" không hợp lệ.");
        }
    }
    return [
        'hoten' => $hoTen, 'ngaysinh' => $ns->format('Y-m-d'), 'cccd' => $cccd,
        'diachi' => $diaChi === '' ? null : $diaChi, 'loai' => $loai, 'sdts' => $sdts, 'emails' => $emails,
    ];
}
 
function luuLienHe(PDO $conn, string $ma, array $d): void
{
    foreach ($d['sdts'] as $s) {
        qRun($conn, "INSERT INTO dbo.KhachHang_SDT (MaKH, SDT) VALUES (?, ?)", [$ma, $s]);
    }
    foreach ($d['emails'] as $m) {
        qRun($conn, "INSERT INTO dbo.KhachHang_Email (MaKH, Email) VALUES (?, ?)", [$ma, $m]);
    }
}
 
$loais = qAll($conn, "SELECT MaLoaiKH, " . nvc('TenLoai') . ", PhanTramUuDai FROM dbo.LoaiKhachHang ORDER BY MaLoaiKH");
$loaiIds = array_column($loais, 'MaLoaiKH');
 
// ---------------- THÊM / SỬA / XÓA ----------------
$action = $_SERVER['REQUEST_METHOD'] === 'POST' ? ($_POST['action'] ?? '') : '';
$reopen = false;
if ($action !== '') {
    try {
        if ($action === 'them') {
            $d = readKH($loaiIds);
            $conn->beginTransaction();
            $ma = nextId($conn, 'KhachHang', 'MaKH', 'KH', 3);
            qRun($conn, "INSERT INTO dbo.KhachHang (MaKH, HoTen, NgaySinh, CCCD, DiaChi, MaLoaiKH)
                         VALUES (?, " . uSql(100) . ", CONVERT(DATE, CAST(? AS VARCHAR(10)), 23), ?, " . uSql(200) . ", ?)",
                [$ma, uni($d['hoten']), $d['ngaysinh'], $d['cccd'], uni($d['diachi']), $d['loai']]);
            luuLienHe($conn, $ma, $d);
            $conn->commit();
            redirectOk('khach_hang.php', "Đã thêm khách hàng $ma.");
        } elseif ($action === 'sua') {
            $ma = trim($_POST['ma_kh'] ?? '');
            $d = readKH($loaiIds);
            $conn->beginTransaction();
            $n = qRun($conn, "UPDATE dbo.KhachHang
                              SET HoTen = " . uSql(100) . ", NgaySinh = CONVERT(DATE, CAST(? AS VARCHAR(10)), 23),
                                  CCCD = ?, DiaChi = " . uSql(200) . ", MaLoaiKH = ?
                              WHERE MaKH = ?",
                [uni($d['hoten']), $d['ngaysinh'], $d['cccd'], uni($d['diachi']), $d['loai'], $ma]);
            if ($n < 1) {
                throw new Exception('Không tìm thấy khách hàng.');
            }
            qRun($conn, "DELETE FROM dbo.KhachHang_SDT WHERE MaKH = ?", [$ma]);
            qRun($conn, "DELETE FROM dbo.KhachHang_Email WHERE MaKH = ?", [$ma]);
            luuLienHe($conn, $ma, $d);
            $conn->commit();
            redirectOk('khach_hang.php', "Đã cập nhật khách hàng $ma.");
        } elseif ($action === 'xoa') {
            $ma = trim($_POST['ma_kh'] ?? '');
            if ((int)qVal($conn, "SELECT COUNT(*) FROM dbo.PhieuThue WHERE MaKH = ?", [$ma]) > 0) {
                throw new Exception('Khách này đã có phiếu thuê nên không thể xóa.');
            }
            $conn->beginTransaction();
            qRun($conn, "DELETE FROM dbo.KhachHang_SDT WHERE MaKH = ?", [$ma]);
            qRun($conn, "DELETE FROM dbo.KhachHang_Email WHERE MaKH = ?", [$ma]);
            qRun($conn, "DELETE FROM dbo.KhachHang WHERE MaKH = ?", [$ma]);
            $conn->commit();
            redirectOk('khach_hang.php', "Đã xóa khách hàng $ma.");
        }
    } catch (Throwable $e) {
        if ($conn->inTransaction()) {
            $conn->rollBack();
        }
        $err = friendlyErr($e);
        $reopen = in_array($action, ['them', 'sua'], true);
    }
}
 
// ---------------- DỮ LIỆU ----------------
$all = qAll($conn, "
    SELECT kh.MaKH, " . nvc('kh.HoTen', 'HoTen') . ", " . dtc('kh.NgaySinh', 'NgaySinh', 23, 10) . ", kh.CCCD,
           " . nvc('kh.DiaChi', 'DiaChi') . ", kh.MaLoaiKH, " . nvc('lk.TenLoai', 'Hang') . ", lk.PhanTramUuDai,
           CAST((SELECT STRING_AGG(s.SDT, ', ') FROM dbo.KhachHang_SDT s WHERE s.MaKH = kh.MaKH) AS NVARCHAR(MAX)) AS DsSDT,
           CAST((SELECT STRING_AGG(m.Email, ', ') FROM dbo.KhachHang_Email m WHERE m.MaKH = kh.MaKH) AS NVARCHAR(MAX)) AS DsEmail,
           (SELECT COUNT(*) FROM dbo.PhieuThue pt WHERE pt.MaKH = kh.MaKH) AS SoPhieu
    FROM dbo.KhachHang kh
    JOIN dbo.LoaiKhachHang lk ON lk.MaLoaiKH = kh.MaLoaiKH
    ORDER BY kh.MaKH");
 
$q = trim($_GET['q'] ?? '');
$fLoai = $_GET['loai'] ?? '';
$list = array_filter($all, function ($r) use ($q, $fLoai) {
    if ($fLoai !== '' && $r['MaLoaiKH'] !== $fLoai) {
        return false;
    }
    if ($q !== '') {
        $hay = $r['MaKH'] . ' ' . $r['HoTen'] . ' ' . $r['CCCD'] . ' ' . $r['DsSDT'] . ' ' . $r['DsEmail'];
        if (mb_stripos($hay, $q) === false) {
            return false;
        }
    }
    return true;
});
 
// Lịch sử thuê của 1 khách (dùng hàm fn_LichSuThueCuaKhach)
$xem = trim($_GET['xem'] ?? '');
$lichSu = [];
$khachXem = null;
if ($xem !== '') {
    foreach ($all as $r) {
        if ($r['MaKH'] === $xem) {
            $khachXem = $r;
        }
    }
    if ($khachXem) {
        $lichSu = qAll($conn, "SELECT MaPhieuThue, " . dtc('NgayLap', 'NgayLap') . ", " . ptCodeSql('TrangThai') . " AS MaTT,
                                      SoPhong, " . nvc('HinhThucThue', 'HinhThucThue') . ",
                                      " . dtc('GioNhan', 'GioNhan') . ", " . dtc('GioTra', 'GioTra') . ",
                                      ThoiGianThueGio, TienPhongUocTinh
                               FROM dbo.fn_LichSuThueCuaKhach(?)", [$xem]);
    }
}
?>
 
<?php flashHtml($err); ?>
 
<?php if ($khachXem): ?>
    <div class="card border-0 shadow-sm mb-4">
        <div class="card-header bg-dark text-white d-flex justify-content-between">
            <span class="fw-bold">Lịch sử thuê phòng: <?= esc($khachXem['HoTen']) ?> (<?= esc($khachXem['MaKH']) ?>)</span>
            <a href="khach_hang.php" class="btn btn-sm btn-light">Đóng</a>
        </div>
        <div class="card-body">
            <?php if (!$lichSu): ?>
                <p class="text-muted mb-0">Khách này chưa có phiếu thuê nào.</p>
            <?php else: ?>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered align-middle mb-0">
                        <thead class="table-light"><tr><th>Mã PT</th><th>Trạng thái</th><th>Phòng</th><th>Hình thức</th><th>Nhận</th><th>Trả</th><th>Số giờ</th><th class="text-end">Tiền phòng ước tính</th></tr></thead>
                        <tbody>
                        <?php foreach ($lichSu as $l): ?>
                            <tr>
                                <td><?= esc($l['MaPhieuThue']) ?></td><td><?= ptBadge($l['MaTT']) ?></td><td><?= esc($l['SoPhong']) ?></td>
                                <td><?= esc($l['HinhThucThue']) ?></td><td><?= fdt($l['GioNhan']) ?></td><td><?= fdt($l['GioTra']) ?></td>
                                <td><?= $l['ThoiGianThueGio'] !== null ? (int)$l['ThoiGianThueGio'] : '—' ?></td>
                                <td class="text-end"><?= (float)$l['TienPhongUocTinh'] > 0 ? money($l['TienPhongUocTinh']) : '—' ?></td>
                            </tr>
                        <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            <?php endif; ?>
        </div>
    </div>
<?php endif; ?>
 
<div class="card border-0 shadow-sm p-3">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h5 class="fw-bold mb-0">DANH SÁCH KHÁCH HÀNG (<?= count($list) ?>/<?= count($all) ?>)</h5>
        <button class="btn btn-primary fw-bold" id="btnThem" data-bs-toggle="modal" data-bs-target="#modalKH">+ Thêm khách hàng</button>
    </div>
 
    <form method="GET" class="row g-2 mb-3">
        <div class="col-md-5"><input type="text" name="q" value="<?= esc($q) ?>" class="form-control" placeholder="Tìm mã, họ tên, CCCD, SĐT, email..."></div>
        <div class="col-md-3">
            <select name="loai" class="form-select">
                <option value="">Tất cả hạng</option>
                <?php foreach ($loais as $l): ?>
                    <option value="<?= esc($l['MaLoaiKH']) ?>" <?= $fLoai === $l['MaLoaiKH'] ? 'selected' : '' ?>><?= esc($l['TenLoai']) ?></option>
                <?php endforeach; ?>
            </select>
        </div>
        <div class="col-md-4 d-flex gap-2">
            <button class="btn btn-dark">Lọc</button>
            <a href="khach_hang.php" class="btn btn-outline-secondary">Xóa lọc</a>
        </div>
    </form>
 
    <div class="table-responsive">
        <table class="table table-hover table-bordered align-middle">
            <thead class="table-dark">
            <tr><th>Mã KH</th><th>Họ tên</th><th>Ngày sinh</th><th>CCCD</th><th>Liên hệ</th><th>Hạng</th><th class="text-center">Số phiếu</th><th class="text-center">Thao tác</th></tr>
            </thead>
            <tbody>
            <?php if (!$list): ?>
                <tr><td colspan="8" class="text-center text-muted py-4">Không có khách hàng nào.</td></tr>
            <?php endif; ?>
            <?php foreach ($list as $r): ?>
                <tr>
                    <td class="fw-bold"><?= esc($r['MaKH']) ?></td>
                    <td><strong><?= esc($r['HoTen']) ?></strong><br><small class="text-muted"><?= esc($r['DiaChi'] ?? '') ?></small></td>
                    <td><?= fdt($r['NgaySinh'], 'd/m/Y') ?></td>
                    <td><?= esc($r['CCCD']) ?></td>
                    <td class="small"><?= esc($r['DsSDT'] ?? '') ?><br><span class="text-muted"><?= esc($r['DsEmail'] ?? '') ?></span></td>
                    <td><?=hangBadge((string)$r['Hang']) ?><br><small class="text-muted">Ưu đãi <?= rtrim(rtrim(number_format((float)$r['PhanTramUuDai'], 2, '.', ''), '0'), '.') ?>%</small></td>
                    <td class="text-center"><?= (int)$r['SoPhieu'] ?></td>
                    <td class="text-center text-nowrap">
                        <a class="btn btn-sm btn-outline-dark" href="khach_hang.php?xem=<?= esc($r['MaKH']) ?>">Lịch sử</a>
                        <button class="btn btn-sm btn-warning btn-sua" data-bs-toggle="modal" data-bs-target="#modalKH"
                                data-kh='<?= esc(json_encode([
                                    'ma' => $r['MaKH'], 'ten' => $r['HoTen'], 'ns' => $r['NgaySinh'], 'cccd' => $r['CCCD'],
                                    'dc' => $r['DiaChi'] ?? '', 'loai' => $r['MaLoaiKH'],
                                    'sdt' => str_replace(', ', ', ', $r['DsSDT'] ?? ''), 'email' => $r['DsEmail'] ?? '',
                                ], JSON_UNESCAPED_UNICODE)) ?>'>Sửa</button>
                        <?php if ((int)$r['SoPhieu'] === 0): ?>
                            <form method="POST" class="d-inline" onsubmit="return confirm('Xóa khách <?= esc($r['MaKH']) ?>?');">
                                <input type="hidden" name="action" value="xoa">
                                <input type="hidden" name="ma_kh" value="<?= esc($r['MaKH']) ?>">
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
 
<!-- MODAL THÊM / SỬA (dùng chung) -->
<div class="modal fade" id="modalKH" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <form method="POST" id="formKH">
                <input type="hidden" name="action" id="kh_action" value="<?= esc($_POST['action'] ?? 'them') ?>">
                <input type="hidden" name="ma_kh" id="kh_ma" value="<?= esc($_POST['ma_kh'] ?? '') ?>">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title fw-bold" id="kh_title">THÊM KHÁCH HÀNG</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row g-3">
                        <div class="col-md-6"><label class="form-label fw-bold">Họ tên</label>
                            <input type="text" name="ho_ten" id="kh_ten" class="form-control" maxlength="100" required value="<?= esc($_POST['ho_ten'] ?? '') ?>"></div>
                        <div class="col-md-3"><label class="form-label fw-bold">Ngày sinh</label>
                            <input type="date" name="ngay_sinh" id="kh_ns" class="form-control" required value="<?= esc($_POST['ngay_sinh'] ?? '') ?>"></div>
                        <div class="col-md-3"><label class="form-label fw-bold">CCCD (12 số)</label>
                            <input type="text" name="cccd" id="kh_cccd" class="form-control" maxlength="12" pattern="\d{12}" required value="<?= esc($_POST['cccd'] ?? '') ?>"></div>
                        <div class="col-md-8"><label class="form-label fw-bold">Địa chỉ</label>
                            <input type="text" name="dia_chi" id="kh_dc" class="form-control" maxlength="200" value="<?= esc($_POST['dia_chi'] ?? '') ?>"></div>
                        <div class="col-md-4"><label class="form-label fw-bold">Hạng khách hàng</label>
                            <select name="ma_loai" id="kh_loai" class="form-select" required>
                                <?php foreach ($loais as $l): ?>
                                    <option value="<?= esc($l['MaLoaiKH']) ?>" <?= ($_POST['ma_loai'] ?? '') === $l['MaLoaiKH'] ? 'selected' : '' ?>><?= esc($l['TenLoai']) ?></option>
                                <?php endforeach; ?>
                            </select></div>
                        <div class="col-md-6"><label class="form-label fw-bold">Số điện thoại</label>
                            <input type="text" name="sdt" id="kh_sdt" class="form-control" placeholder="Nhiều số cách nhau bằng dấu phẩy" value="<?= esc($_POST['sdt'] ?? '') ?>"></div>
                        <div class="col-md-6"><label class="form-label fw-bold">Email</label>
                            <input type="text" name="email" id="kh_email" class="form-control" placeholder="Nhiều email cách nhau bằng dấu phẩy" value="<?= esc($_POST['email'] ?? '') ?>"></div>
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
    function setVal(id, v) { document.getElementById(id).value = v; }
    document.getElementById('btnThem').addEventListener('click', function () {
        document.getElementById('formKH').reset();
        setVal('kh_action', 'them'); setVal('kh_ma', '');
        ['kh_ten', 'kh_ns', 'kh_cccd', 'kh_dc', 'kh_sdt', 'kh_email'].forEach(function (i) { setVal(i, ''); });
        document.getElementById('kh_title').textContent = 'THÊM KHÁCH HÀNG';
    });
    document.querySelectorAll('.btn-sua').forEach(function (b) {
        b.addEventListener('click', function () {
            var d = JSON.parse(b.dataset.kh);
            setVal('kh_action', 'sua'); setVal('kh_ma', d.ma);
            setVal('kh_ten', d.ten); setVal('kh_ns', d.ns); setVal('kh_cccd', d.cccd); setVal('kh_dc', d.dc);
            setVal('kh_loai', d.loai); setVal('kh_sdt', d.sdt); setVal('kh_email', d.email);
            document.getElementById('kh_title').textContent = 'SỬA KHÁCH HÀNG ' + d.ma;
        });
    });
    <?php if ($reopen): ?>
    window.addEventListener('load', function () {
        document.getElementById('kh_title').textContent = <?= json_encode(($_POST['action'] ?? '') === 'sua' ? 'SỬA KHÁCH HÀNG ' . ($_POST['ma_kh'] ?? '') : 'THÊM KHÁCH HÀNG') ?>;
        new bootstrap.Modal(document.getElementById('modalKH')).show();
    });
    <?php endif; ?>
</script>
 
<?php include 'includes/footer.php'; ?>