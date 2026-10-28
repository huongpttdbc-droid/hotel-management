<?php
// admin/includes/auth.php - đăng nhập demo (tài khoản đặt cứng)
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

const APP_BASE = '/QuanLyKhachSan';   // đổi nếu tên thư mục web khác

const DEMO_ACCOUNTS = [
    'admin' => ['pass' => 'admin123', 'role' => 'admin', 'ma' => 'NV01',  'name' => 'Nguyễn Thị Hoa'],
    'khach' => ['pass' => 'khach123', 'role' => 'khach', 'ma' => 'KH001', 'name' => 'Khách hàng demo'],
];

function authUser(): ?array
{
    return $_SESSION['user'] ?? null;
}

function homeFor(string $role): string
{
    return $role === 'admin' ? APP_BASE . '/admin/dashboard.php' : APP_BASE . '/khach/index.php';
}

function requireRole(string $role): void
{
    $u = authUser();
    if (!$u || $u['role'] !== $role) {
        header('Location: ' . APP_BASE . '/login.php');
        exit;
    }
}