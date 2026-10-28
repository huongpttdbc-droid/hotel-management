import sys
import os

# Đảm bảo đường dẫn gốc của project
sys.path.insert(0, os.path.abspath("."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

print("1. Kiểm tra /api/health...")
r = client.get("/api/health")
print("Status:", r.status_code, r.json())
assert r.status_code == 200

print("\n2. Kiểm tra /api/phong...")
r = client.get("/api/phong")
print("Status:", r.status_code, "Số phòng lấy được:", len(r.json()))
assert r.status_code == 200
if r.json():
    p = r.json()[0]
    print(f"Mẫu phòng đầu tiên: Phòng {p['SoPhong']}, Loại {p['TenLoaiPhong']}, Giá {p['DonGiaTheoNgay']:,} VNĐ, Tình trạng: {p['TinhTrang']}")

print("\n3. Kiểm tra /api/thong-ke/tong-quan...")
r = client.get("/api/thong-ke/tong-quan")
print("Status:", r.status_code, r.json())
assert r.status_code == 200

print("\n4. Kiểm tra /api/dich-vu...")
r = client.get("/api/dich-vu")
print("Status:", r.status_code, "Số dịch vụ:", len(r.json()))
assert r.status_code == 200
if r.json():
    dv = r.json()[0]
    print(f"Mẫu dịch vụ đầu tiên: {dv['TenDichVu']} ({dv['DonGia']:,} VNĐ/{dv['DonViTinh']})")

print("\n5. Kiểm tra /api/khach-hang...")
r = client.get("/api/khach-hang?limit=5")
print("Status:", r.status_code, "Số khách hàng:", len(r.json()))
assert r.status_code == 200
if r.json():
    kh = r.json()[0]
    print(f"Mẫu khách hàng: {kh['HoTen']} - CCCD: {kh['CCCD']} - Loại: {kh['TenLoaiKH']}")

print("\n6. Kiểm tra /api/auth/login (Demo account)...")
r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
print("Status:", r.status_code, r.json())
assert r.status_code == 200

print("\n>>> TẤT CẢ TEST ĐỀU THÀNH CÔNG RỰC RỠ! <<<")
