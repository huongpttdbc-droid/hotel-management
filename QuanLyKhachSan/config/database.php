<?php
// config/database.php
ini_set('default_charset', 'UTF-8');
mb_internal_encoding('UTF-8');

$serverName = "localhost\\MSSQLSERVER01";
$database   = "QuanLyKhachSan";

try {
    $conn = new PDO(
        "odbc:Driver={ODBC Driver 18 for SQL Server};Server=$serverName;Database=$database;Trusted_Connection=yes;TrustServerCertificate=yes;",
        "",
        ""
    );
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $conn->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $conn->setAttribute(PDO::ODBC_ATTR_ASSUME_UTF8, true);
} catch (PDOException $e) {
    die("<div style='color:red; font-weight:bold; padding:20px;'>Lỗi kết nối: " . $e->getMessage() . "</div>");
}
?>