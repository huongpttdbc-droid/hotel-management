<?php
require_once __DIR__ . '/admin/includes/auth.php';
$_SESSION = [];
session_destroy();
header('Location: ' . APP_BASE . '/login.php');
exit;