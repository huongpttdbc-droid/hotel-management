<?php
require_once __DIR__ . '/admin/includes/auth.php';

if (authUser()) {
    header('Location: ' . homeFor(authUser()['role']));
    exit;
}

$err = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user = trim($_POST['username'] ?? '');
    $pass = (string)($_POST['password'] ?? '');
    $acc  = DEMO_ACCOUNTS[$user] ?? null;
    if ($acc && hash_equals($acc['pass'], $pass)) {
        session_regenerate_id(true);
        $_SESSION['user'] = ['username' => $user, 'role' => $acc['role'], 'ma' => $acc['ma'], 'name' => $acc['name']];
        header('Location: ' . homeFor($acc['role']));
        exit;
    }
    $err = 'Sai tên đăng nhập hoặc mật khẩu.';
}
function h($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
?>
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Đăng nhập - Hotel</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body { background: linear-gradient(135deg, #1e293b, #0f172a); min-height: 100vh; }
    .demo-box { border: 2px dashed #0d6efd; border-radius: .5rem; }
</style>
</head>
<body class="d-flex align-items-center justify-content-center p-3">
<div class="card shadow border-0" style="max-width: 440px; width: 100%;">
    <div class="card-body p-4">
        <h3 class="fw-bold text-center mb-1">🏨 HOTEL</h3>
        <p class="text-center text-muted mb-4">Đăng nhập hệ thống</p>

        <?php if ($err): ?><div class="alert alert-danger py-2"><?= h($err) ?></div><?php endif; ?>

        <form method="POST" class="mb-4">
            <div class="mb-3">
                <label class="form-label fw-bold">Tên đăng nhập</label>
                <input type="text" name="username" class="form-control" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label fw-bold">Mật khẩu</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button class="btn btn-primary w-100 fw-bold">Đăng nhập</button>
        </form>

        <div class="small text-muted mb-2">Tài khoản demo (bấm nút để đăng nhập nhanh):</div>
        <?php foreach (DEMO_ACCOUNTS as $u => $a): ?>
        <form method="POST" class="demo-box p-2 mb-2 d-flex justify-content-between align-items-center">
            <input type="hidden" name="username" value="<?= h($u) ?>">
            <input type="hidden" name="password" value="<?= h($a['pass']) ?>">
            <div>
                <div class="fw-bold"><?= $a['role'] === 'admin' ? 'Quản trị / Lễ tân' : 'Khách hàng' ?></div>
                <div class="small">Tên: <code><?= h($u) ?></code> · Mật khẩu: <code><?= h($a['pass']) ?></code></div>
            </div>
            <button class="btn btn-sm btn-outline-primary">Vào ngay</button>
        </form>
        <?php endforeach; ?>
    </div>
</div>
</body>
</html>