<?php
// admin/includes/functions.php
// Hàm dùng chung. Hoạt động với PDO_ODBC (giữ nguyên ODBC_ATTR_ASSUME_UTF8 = true).

require_once __DIR__ . '/auth.php';
if (!defined('NO_AUTH')) {
    requireRole('admin');   // chưa đăng nhập admin thì bị đá về login.php
}

function esc($s): string
{
    return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8');
}

/** CAST cột chữ sang NVARCHAR(MAX): PDO_ODBC đọc theo từng đoạn nên không bị "String data, right truncated". */
function nvc(string $expr, ?string $alias = null): string
{
    if ($alias === null) {
        $alias = preg_replace('/^.*\./', '', $expr);
    }
    return "CAST($expr AS NVARCHAR(MAX)) AS [$alias]";
}

/** Đổi ngày giờ sang chuỗi ASCII (style 120 = yyyy-mm-dd hh:mi:ss, style 23 = yyyy-mm-dd). */
function dtc(string $expr, ?string $alias = null, int $style = 120, int $len = 19): string
{
    if ($alias === null) {
        $alias = preg_replace('/^.*\./', '', $expr);
    }
    return "CONVERT(VARCHAR($len), $expr, $style) AS [$alias]";
}

/** Mã hóa chuỗi Unicode thành hex UTF-16LE (chỉ gồm ký tự ASCII) để gửi vào SQL không bị hỏng dấu. */
function uni(?string $s): ?string
{
    if ($s === null) {
        return null;
    }
    return bin2hex(mb_convert_encoding($s, 'UTF-16LE', 'UTF-8'));
}

/** Đoạn SQL nhận tham số hex từ uni() và trả về NVARCHAR đúng dấu. */
function uSql(int $len = 200): string
{
    return "CAST(CONVERT(VARBINARY(MAX), CAST(? AS VARCHAR(MAX)), 2) AS NVARCHAR($len))";
}

/** Hằng NVARCHAR dạng hex (ASCII thuần) - dùng thay cho N'Tiếng Việt' viết thẳng trong câu SQL. */
function nl(string $s): string
{
    return 'CAST(0x' . bin2hex(mb_convert_encoding($s, 'UTF-16LE', 'UTF-8')) . ' AS NVARCHAR(MAX))';
}

/** Đoạn SQL đổi mã phương thức thanh toán (tm / ck / the) sang chữ tiếng Việt. */
function pmSql(): string
{
    return "CASE CAST(? AS VARCHAR(10)) WHEN 'ck' THEN " . nl('Chuyển khoản')
        . " WHEN 'the' THEN " . nl('Thẻ')
        . " ELSE " . nl('Tiền mặt') . " END";
}

function pmCode($v): string
{
    return in_array($v, ['tm', 'ck', 'the'], true) ? $v : 'tm';
}

function money($n): string
{
    return number_format((float)$n, 0, ',', '.') . 'đ';
}

function fdt($s, string $fmt = 'd/m/Y H:i'): string
{
    if ($s === null || $s === '') {
        return '—';
    }
    $t = strtotime((string)$s);
    return $t ? date($fmt, $t) : '—';
}

/** Mã ASCII cho trạng thái phiếu thuê (để PHP so sánh không phụ thuộc encoding). */
function ptCodeSql(string $col): string
{
    return "CASE $col WHEN " . nl('Đã đặt') . " THEN 'dat'"
        . " WHEN " . nl('Đang thuê') . " THEN 'thue'"
        . " WHEN " . nl('Hoàn tất') . " THEN 'xong'"
        . " ELSE 'huy' END";
}

function qAll(PDO $c, string $sql, array $p = []): array
{
    $s = $c->prepare($sql);
    $s->execute($p);
    return $s->fetchAll();
}

function qOne(PDO $c, string $sql, array $p = []): ?array
{
    $r = qAll($c, $sql, $p);
    return $r[0] ?? null;
}

function qVal(PDO $c, string $sql, array $p = [])
{
    $r = qOne($c, $sql, $p);
    return $r === null ? null : array_values($r)[0];
}

function qRun(PDO $c, string $sql, array $p = []): int
{
    $s = $c->prepare($sql);
    $s->execute($p);
    return $s->rowCount();
}

/** Chạy batch có EXEC thủ tục + SELECT kết quả cuối, trả về dòng đầu tiên. */
function qBatch(PDO $c, string $sql, array $p = []): ?array
{
    $s = $c->prepare($sql);
    $s->execute($p);
    try {
        do {
            try {
                $r = $s->fetch();
            } catch (PDOException $e) {
                $r = false;
            }
            if ($r) {
                return $r;
            }
        } while ($s->nextRowset());
    } catch (PDOException $e) {
        return null;
    }
    return null;
}

/** Sinh mã kế tiếp: prefix + số (MAX + 1). Chỉ dùng với tham số nội bộ. */
function nextId(PDO $c, string $table, string $col, string $prefix, int $pad): string
{
    $start = strlen($prefix) + 1;
    $n = (int)qVal($c, "SELECT ISNULL(MAX(TRY_CAST(SUBSTRING($col, $start, 20) AS INT)), 0) + 1 FROM dbo.$table WHERE $col LIKE '{$prefix}%'");
    return $prefix . str_pad((string)$n, $pad, '0', STR_PAD_LEFT);
}

function friendlyErr(Throwable $e): string
{
    $m = $e->getMessage();
    if (stripos($m, 'UNIQUE') !== false || stripos($m, 'duplicate') !== false || stripos($m, 'UQ_') !== false) {
        return 'Dữ liệu bị trùng (CCCD / tên đã tồn tại).';
    }
    if (stripos($m, 'REFERENCE constraint') !== false || stripos($m, 'FOREIGN KEY') !== false) {
        return 'Dữ liệu đang được sử dụng ở nơi khác nên không thể xóa/sửa.';
    }
    if (stripos($m, 'CHECK constraint') !== false) {
        return 'Dữ liệu không hợp lệ (vi phạm ràng buộc CHECK).';
    }
    return $m;
}

/** Chuyển trang bằng JS (vì header.php đã in HTML nên không dùng header('Location')). */
function redirectJs(string $url): void
{
    echo '<script>window.location.href=' . json_encode($url) . ';</script>';
    exit;
}

function redirectOk(string $page, string $msg, string $extra = ''): void
{
    redirectJs($page . '?ok=' . urlencode($msg) . $extra);
}

function flashHtml(string $err = ''): void
{
    $btn = '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    if (!empty($_GET['ok'])) {
        echo '<div class="alert alert-success alert-dismissible fade show">' . esc($_GET['ok']) . $btn . '</div>';
    }
    if (!empty($_GET['err'])) {
        echo '<div class="alert alert-danger alert-dismissible fade show">' . esc($_GET['err']) . $btn . '</div>';
    }
    if ($err !== '') {
        echo '<div class="alert alert-danger alert-dismissible fade show">' . esc($err) . $btn . '</div>';
    }
}

function ptBadge(string $code): string
{
    $map = [
        'dat'  => ['primary', 'Đã đặt'],
        'thue' => ['danger', 'Đang thuê'],
        'xong' => ['success', 'Hoàn tất'],
        'huy'  => ['secondary', 'Đã hủy'],
    ];
    [$cls, $txt] = $map[$code] ?? ['secondary', $code];
    return '<span class="badge bg-' . $cls . '">' . $txt . '</span>';
}

/** Badge màu theo hạng khách: mỗi hạng một màu. */
function hangBadge(string $ten): string
{
    $k = mb_strtolower($ten, 'UTF-8');
    if (mb_strpos($k, 'vip') !== false) {
        $st = 'background:#FFC107;color:#212529';   // VIP: vàng
    } elseif (mb_strpos($k, 'doanh') !== false) {
        $st = 'background:#DC3545;color:#fff';       // Doanh nghiệp: đỏ
    } elseif (mb_strpos($k, 'thân') !== false) {
        $st = 'background:#8E24AA;color:#fff';       // Thân thiết: tím
    } elseif (mb_strpos($k, 'thường') !== false) {
        $st = 'background:#0D6EFD;color:#fff';       // Thường: xanh dương
    } else {
        $st = 'background:#6c757d;color:#fff';       // Hạng khác: xám
    }
    return '<span class="badge" style="' . $st . '">' . esc($ten) . '</span>';
}