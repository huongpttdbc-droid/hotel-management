<?php
// Gửi Header ép trình duyệt nhận diện chuẩn mã hóa UTF-8
header('Content-Type: text/html; charset=utf-8');

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}
require_once __DIR__ . '/../../config/database.php';
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= isset($pageTitle) ? $pageTitle : 'Hệ Thống Quản Lý Khách Sạn' ?></title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- FontAwesome 6 Icons -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f6f9; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
        .sidebar {
            height: 100vh; position: sticky; top: 0; align-self: flex-start; overflow-y: auto;
            background: #1e293b; color: #f8fafc;
        }
        .sidebar .brand { font-size: 1.25rem; font-weight: 700; color: #38bdf8; padding: 18px 20px; border-bottom: 1px solid #334155; }
        .sidebar .nav-link { color: #94a3b8; padding: 12px 20px; font-weight: 500; border-left: 4px solid transparent; transition: all 0.2s; }
        .sidebar .nav-link:hover, .sidebar .nav-link.active { color: #ffffff; background: #0f172a; border-left-color: #38bdf8; }
        .sidebar .nav-link i { width: 26px; }
        .main-content { padding: 25px; }
        .card-room { border-radius: 10px; border: none; transition: transform 0.2s, box-shadow 0.2s; }
        .card-room:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }
        .status-Trong { background-color: #d1e7dd; border-top: 5px solid #198754; color: #0f5132; }
        .status-Dang-thue { background-color: #f8d7da; border-top: 5px solid #dc3545; color: #842029; }
        .status-Dang-don { background-color: #fff3cd; border-top: 5px solid #ffc107; color: #664d03; }
        .status-Bao-tri { background-color: #e2e3e5; border-top: 5px solid #6c757d; color: #41464b; }
    </style>
</head>
<body>
<div class="container-fluid">
    <div class="row">
        <!-- SIDEBAR NAVIGATION -->
        <div class="col-md-3 col-lg-2 px-0 sidebar d-none d-md-block">
            <div class="brand">
                <i class="fa-solid fa-hotel me-2"></i>HOTEL ADMIN
            </div>
            <div class="nav flex-column mt-3">
                <a href="dashboard.php" class="nav-link <?= ($activePage == 'dashboard') ? 'active' : '' ?>">
                    <i class="fa-solid fa-grip"></i> Sơ Đồ Phòng
                </a>
                <a href="phieu_thue.php" class="nav-link <?= ($activePage == 'phieu_thue') ? 'active' : '' ?>">
                    <i class="fa-solid fa-calendar-check"></i> Đặt & Thuê Phòng
                </a>
                <a href="hoa_don.php" class="nav-link <?= ($activePage == 'hoa_don') ? 'active' : '' ?>">
                    <i class="fa-solid fa-file-invoice-dollar"></i> Hóa Đơn & Thu Tiền
                </a>
                <a href="dich_vu.php" class="nav-link <?= ($activePage == 'dich_vu') ? 'active' : '' ?>">
                    <i class="fa-solid fa-concierge-bell"></i> Dịch Vụ Khách Sạn
                </a>
                <a href="khach_hang.php" class="nav-link <?= ($activePage == 'khach_hang') ? 'active' : '' ?>">
                    <i class="fa-solid fa-users"></i> Quản Lý Khách Hàng
                </a>
                <a href="doanh_thu.php" class="nav-link <?= ($activePage == 'doanh_thu') ? 'active' : '' ?>">
                    <i class="fa-solid fa-chart-line"></i> Báo Cáo Doanh Thu
                </a>
            </div>
        </div>

        <!-- MAIN CONTENT AREA -->
        <div class="col-md-9 col-lg-10 main-content">
            <!-- TOP BAR -->
            <div class="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom bg-white p-3 rounded shadow-sm">
                <h4 class="m-0 fw-bold text-dark"><?= isset($pageTitle) ? $pageTitle : 'Quản Lý Khách Sạn' ?></h4>
                <div class="d-flex align-items-center gap-3">
                    <span class="badge bg-primary fs-6">
                        <i class="fa-solid fa-user-gear me-1"></i>
                        Lễ Tân: <?= htmlspecialchars(authUser()['name'] ?? 'Nguyễn Thị Hoa') ?> (<?= htmlspecialchars(authUser()['ma'] ?? 'NV01') ?>)
                    </span>
                    <a href="<?= APP_BASE ?>/logout.php" class="btn btn-sm btn-outline-danger">
                        <i class="fa-solid fa-right-from-bracket me-1"></i>Đăng xuất
                    </a>
                </div>
            </div>