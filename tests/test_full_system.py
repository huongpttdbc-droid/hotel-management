import os
import sys
import unittest
from datetime import date, datetime, timedelta

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

class TestHotelManagementSystem(unittest.TestCase):
    """
    Toàn bộ Test Suite kiểm thử toàn diện các luồng nghiệp vụ hệ thống:
    - Xác thực & Phân quyền
    - Sơ đồ phòng & Vòng đời phòng
    - Khách hàng & Ràng buộc nghiệp vụ
    - Thuê phòng -> Sử dụng dịch vụ -> Trả phòng
    - Tính toán hóa đơn -> Thu tiền -> Đồng bộ ThanhToan
    - Báo cáo thống kê
    """

    # =========================================================================
    # 1. HỆ THỐNG & TĨNH
    # =========================================================================
    def test_01_health_check(self):
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")

    def test_02_static_pages(self):
        for page in ["/index.html", "/login.html", "/booking.html"]:
            res = client.get(page)
            self.assertEqual(res.status_code, 200, f"Trang {page} không truy cập được")

    # =========================================================================
    # 2. XÁC THỰC & NGƯỜI DÙNG
    # =========================================================================
    def test_03_login_admin_demo(self):
        res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user"]["role"], "admin")

    def test_04_login_receptionist(self):
        # Đăng nhập lễ tân hoa.nt với mật khẩu chuẩn
        res = client.post("/api/auth/login", json={"username": "hoa.nt", "password": "Hoa@2026"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user"]["role"], "staff")

    def test_05_login_case_insensitivity_and_alias(self):
        # Đăng nhập nam.tv với mật khẩu thường nam@2026
        res = client.post("/api/auth/login", json={"username": "nam.tv", "password": "nam@2026"})
        self.assertEqual(res.status_code, 200)

        # Đăng nhập bằng tên gọi tắt 'nam'
        res_alias = client.post("/api/auth/login", json={"username": "nam", "password": "Nam@2026"})
        self.assertEqual(res_alias.status_code, 200)

    def test_06_login_manager_role(self):
        # tuan.hm là Quản lý
        res = client.post("/api/auth/login", json={"username": "tuan.hm", "password": "Tuan@2026"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user"]["role"], "admin")

    def test_07_login_locked_account(self):
        # long.bv có TrangThai = 'Khóa'
        res = client.post("/api/auth/login", json={"username": "long.bv", "password": "Long@2026"})
        self.assertIn(res.status_code, [403, 401])

    def test_08_login_wrong_password(self):
        res = client.post("/api/auth/login", json={"username": "hoa.nt", "password": "SaiMatKhau123"})
        self.assertEqual(res.status_code, 401)

    def test_09_staff_list(self):
        res = client.get("/api/auth/staff-list")
        self.assertEqual(res.status_code, 200)
        staffs = res.json()
        self.assertGreater(len(staffs), 0)

    # =========================================================================
    # 3. QUẢN LÝ PHÒNG & LOẠI PHÒNG
    # =========================================================================
    def test_10_list_rooms_and_types(self):
        res_rooms = client.get("/api/phong")
        self.assertEqual(res_rooms.status_code, 200)
        rooms = res_rooms.json()
        self.assertGreaterEqual(len(rooms), 10)

        res_types = client.get("/api/phong/loai-phong")
        self.assertEqual(res_types.status_code, 200)
        types = res_types.json()
        self.assertEqual(len(types), 5)

    def test_11_filter_rooms(self):
        res = client.get("/api/phong?tang=1")
        self.assertEqual(res.status_code, 200)
        for r in res.json():
            self.assertEqual(r["Tang"], 1)

    def test_12_update_room_maintenance(self):
        # Tìm phòng trống để đổi sang bảo trì rồi hoàn trả lại trống
        res_rooms = client.get("/api/phong?tinh_trang=Trống")
        self.assertEqual(res_rooms.status_code, 200)
        empty_rooms = res_rooms.json()
        if empty_rooms:
            test_room = empty_rooms[0]["MaPhong"]
            # 1. Chuyển sang Bảo trì
            res1 = client.put(f"/api/phong/{test_room}/tinh-trang", json={"TinhTrang": "Bảo trì"})
            self.assertEqual(res1.status_code, 200)
            # 2. Chuyển lại sang Trống
            res2 = client.put(f"/api/phong/{test_room}/tinh-trang", json={"TinhTrang": "Trống"})
            self.assertEqual(res2.status_code, 200)

    # =========================================================================
    # 4. QUẢN LÝ KHÁCH HÀNG & RÀNG BUỘC
    # =========================================================================
    def test_13_customer_validations(self):
        # 1. Kiểm tra dưới 18 tuổi
        young_dob = (date.today() - timedelta(days=365 * 10)).isoformat()
        res_young = client.post("/api/khach-hang", json={
            "HoTen": "Em Bé Test",
            "NgaySinh": young_dob,
            "CCCD": "999888777666",
            "SDT": "0988777666"
        })
        self.assertEqual(res_young.status_code, 400)
        self.assertIn("18 tuổi", res_young.json().get("detail", ""))

        # 2. Kiểm tra CCCD không đúng 12 chữ số
        adult_dob = (date.today() - timedelta(days=365 * 25)).isoformat()
        res_cccd = client.post("/api/khach-hang", json={
            "HoTen": "Khách Test",
            "NgaySinh": adult_dob,
            "CCCD": "12345",  # không đủ 12 số
            "SDT": "0988777666"
        })
        self.assertEqual(res_cccd.status_code, 400)

    def test_14_customer_create_and_search(self):
        # Tạo khách hàng hợp lệ với CCCD ngẫu nhiên duy nhất
        import random
        rand_cccd = f"001{random.randint(100000000, 999999999)}"
        adult_dob = (date.today() - timedelta(days=365 * 22)).isoformat()

        res_create = client.post("/api/khach-hang", json={
            "HoTen": "Nguyễn Văn Kiểm Thử",
            "NgaySinh": adult_dob,
            "CCCD": rand_cccd,
            "SDT": "0912345678",
            "DiaChi": "Hà Nội"
        })
        self.assertEqual(res_create.status_code, 200)
        created = res_create.json()
        self.assertEqual(created["CCCD"], rand_cccd)

        # Tìm kiếm khách hàng vừa tạo
        res_search = client.get(f"/api/khach-hang?keyword={rand_cccd}")
        self.assertEqual(res_search.status_code, 200)
        found = res_search.json()
        self.assertTrue(any(c["CCCD"] == rand_cccd for c in found))

    # =========================================================================
    # 5. DỊCH VỤ KHÁCH SẠN
    # =========================================================================
    def test_15_list_services(self):
        res = client.get("/api/dich-vu")
        self.assertEqual(res.status_code, 200)
        services = res.json()
        self.assertGreaterEqual(len(services), 5)

    # =========================================================================
    # 6. LUỒNG NGHIỆP VỤ ĐẦY ĐỦ (END-TO-END)
    # Thuê phòng -> Sử dụng dịch vụ -> Trả phòng -> Xuất HĐ -> Thu tiền
    # =========================================================================
    def test_16_full_lifecycle_flow(self):
        # BƯỚC 1: Tìm phòng trống
        res_rooms = client.get("/api/phong?tinh_trang=Trống")
        empty_rooms = res_rooms.json()
        self.assertGreater(len(empty_rooms), 0, "Cần có ít nhất 1 phòng trống để test luồng")

        # BƯỚC 2: Lấy 1 khách hàng có sẵn
        res_cust = client.get("/api/khach-hang?limit=1")
        self.assertEqual(res_cust.status_code, 200)
        target_cust = res_cust.json()[0]
        ma_kh = target_cust["MaKH"]

        # BƯỚC 3: Lập phiếu thuê phòng (Theo ngày) trên phòng trống khả dụng
        res_rental = None
        ma_phong = None
        for room in empty_rooms:
            rental_data = {
                "MaKH": ma_kh,
                "MaPhong": room["MaPhong"],
                "HinhThucThue": "Theo ngày",
                "SoNguoiDuKien": 1,
                "GhiChu": "Test E2E Automated Suite"
            }
            try_res = client.post("/api/phieu-thue", json=rental_data)
            if try_res.status_code == 200:
                res_rental = try_res
                ma_phong = room["MaPhong"]
                break

        self.assertIsNotNone(res_rental, "Không lập được phiếu thuê trên các phòng trống")
        self.assertEqual(res_rental.status_code, 200)
        created_pt = res_rental.json()
        ma_pt = created_pt["MaPhieuThue"]

        # Kiểm tra phòng chuyển sang 'Đang thuê'
        res_check_room = client.get(f"/api/phong/{ma_phong}")
        self.assertEqual(res_check_room.json()["TinhTrang"], "Đang thuê")

        # BƯỚC 4: Sử dụng dịch vụ
        res_service = client.post("/api/dich-vu/su-dung", json={
            "MaPhieuThue": ma_pt,
            "MaDichVu": "DV01",
            "SoLuong": 2
        })
        self.assertEqual(res_service.status_code, 200)

        # BƯỚC 5: Trả phòng (Checkout)
        res_checkout = client.post(f"/api/phieu-thue/{ma_pt}/tra-phong")
        self.assertEqual(res_checkout.status_code, 200)

        # Kiểm tra phòng chuyển sang 'Đang dọn'
        res_room_cleaning = client.get(f"/api/phong/{ma_phong}")
        self.assertEqual(res_room_cleaning.json()["TinhTrang"], "Đang dọn")

        # Hoàn tất dọn dẹp đưa phòng về 'Trống'
        res_clean_done = client.put(f"/api/phong/{ma_phong}/tinh-trang", json={"TinhTrang": "Trống"})
        self.assertEqual(res_clean_done.status_code, 200)

        # BƯỚC 6: Tạo hóa đơn thanh toán
        res_inv = client.post(f"/api/hoa-don/tao-hoa-don/{ma_pt}")
        self.assertEqual(res_inv.status_code, 200)
        inv = res_inv.json()
        ma_hd = inv["MaHD"]
        self.assertGreater(inv["TongTien"], 0)
        self.assertEqual(inv["TrangThai"], "Chưa thanh toán")

        # BƯỚC 7: Thu tiền hóa đơn
        res_pay = client.post(f"/api/hoa-don/{ma_hd}/thanh-toan")
        self.assertEqual(res_pay.status_code, 200)

        # BƯỚC 8: Thử thu tiền lần 2 (đảm bảo tính idempotent, không lỗi)
        res_pay_again = client.post(f"/api/hoa-don/{ma_hd}/thanh-toan")
        self.assertEqual(res_pay_again.status_code, 200)
        self.assertIn("đã được thanh toán", res_pay_again.json()["message"])

    # =========================================================================
    # 7. DANH SÁCH HÓA ĐƠN & BÁO CÁO THỐNG KÊ
    # =========================================================================
    def test_17_list_invoices(self):
        res = client.get("/api/hoa-don")
        self.assertEqual(res.status_code, 200)
        invoices = res.json()
        self.assertGreater(len(invoices), 0)
        # Kiểm tra cấu trúc hóa đơn không bị lỗi kiểu dữ liệu
        first_inv = invoices[0]
        self.assertIn("TongTien", first_inv)
        self.assertIsInstance(first_inv["TongTien"], (int, float))

    def test_18_dashboard_statistics(self):
        res = client.get("/api/thong-ke/tong-quan")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["tong_phong"], 0)
        self.assertGreater(data["tong_khach_hang"], 0)
        self.assertGreaterEqual(data["doanh_thu_thang"], 0)

    def test_19_staff_hierarchy_and_filtering(self):
        # Kiểm tra sắp xếp thứ bậc chức vụ
        res = client.get("/api/auth/staff-list")
        self.assertEqual(res.status_code, 200)
        staffs = res.json()
        self.assertGreaterEqual(len(staffs), 20)
        roles = [s["chuc_vu"] for s in staffs]
        self.assertEqual(roles[0], "Quản lý")
        self.assertEqual(roles[1], "Quản lý")
        self.assertEqual(roles[2], "Kế toán")
        self.assertEqual(roles[3], "Kế toán")
        self.assertEqual(roles[4], "Lễ tân")
        self.assertEqual(roles[-1], "Bảo vệ")

        # Kiểm tra lọc theo từ khóa
        res_kw = client.get("/api/auth/staff-list?keyword=Hoa")
        self.assertEqual(res_kw.status_code, 200)
        self.assertTrue(any(s["ma_nv"] == "NV01" for s in res_kw.json()))

        # Kiểm tra lọc theo chức vụ
        res_role = client.get("/api/auth/staff-list?chuc_vu=Kế toán")
        self.assertEqual(res_role.status_code, 200)
        self.assertEqual(len(res_role.json()), 2)

    def test_20_dynamic_revenue_reporting(self):
        # Báo cáo động theo Tháng và Năm
        res_m = client.get("/api/thong-ke/doanh-thu-chi-tiet?month=7&year=2026")
        self.assertEqual(res_m.status_code, 200)
        data_m = res_m.json()
        self.assertIn("kpi", data_m)
        self.assertEqual(data_m["kpi"]["so_hoa_don_da_thu"], 9)
        self.assertGreater(data_m["kpi"]["tong_doanh_thu"], 0)

        # Báo cáo động theo Quý và Năm
        res_q = client.get("/api/thong-ke/doanh-thu-chi-tiet?quarter=3&year=2026")
        self.assertEqual(res_q.status_code, 200)
        data_q = res_q.json()
        self.assertEqual(data_q["kpi"]["so_hoa_don_da_thu"], 27)

    def test_21_swagger_docs_accessible(self):
        # Đảm bảo route /docs vẫn hoạt động bình thường ở backend
        res = client.get("/docs")
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()

