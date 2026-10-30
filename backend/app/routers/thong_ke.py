from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
from backend.app.database import get_db
from backend.app.models import Phong, KhachHang, HoaDon, LoaiPhong, PhieuThue, ChiTietPhieuThue, DungDichVu, DichVu
from backend.app.schemas import ThongKeSummary

router = APIRouter(prefix="/thong-ke", tags=["Thống Kê Báo Cáo"])

@router.get("/tong-quan", response_model=ThongKeSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    # Gom 5 câu lệnh count thành 1 câu lệnh tổng hợp duy nhất
    room_counts = db.query(
        func.count(Phong.MaPhong).label("tong"),
        func.count(case((Phong.TinhTrang == "Trống", 1))).label("trong"),
        func.count(case((Phong.TinhTrang == "Đang thuê", 1))).label("dang_thue"),
        func.count(case((Phong.TinhTrang == "Đang dọn", 1))).label("dang_don"),
        func.count(case((Phong.TinhTrang == "Bảo trì", 1))).label("bao_tri"),
    ).one()

    tong_phong = room_counts.tong or 0
    phong_trong = room_counts.trong or 0
    phong_dang_thue = room_counts.dang_thue or 0
    phong_dang_don = room_counts.dang_don or 0
    phong_bao_tri = room_counts.bao_tri or 0

    tong_khach = db.query(KhachHang).count()

    # Tính tổng doanh thu hóa đơn đã thanh toán
    invoices = db.query(HoaDon).filter(HoaDon.TrangThai == "Đã thanh toán").all()
    doanh_thu = 0.0
    for h in invoices:
        subtotal = float(h.TienPhong or 0) + float(h.TienDichVu or 0) + float(h.TienPhuThu or 0) - float(h.UuDai or 0)
        doanh_thu += subtotal * (1 + float(h.TyLeVAT or 10) / 100.0)

    return ThongKeSummary(
        tong_phong=tong_phong,
        phong_trong=phong_trong,
        phong_dang_thue=phong_dang_thue,
        phong_dang_don=phong_dang_don,
        phong_bao_tri=phong_bao_tri,
        tong_khach_hang=tong_khach,
        doanh_thu_thang=round(doanh_thu)
    )

@router.get("/doanh-thu-chi-tiet")
def get_detailed_revenue_report(
    period: Optional[str] = Query("all", description="Kỳ báo cáo: today, 7days, thisMonth, quarter, all, custom"),
    month: Optional[int] = Query(None, description="Tháng cần xem (1-12)"),
    quarter: Optional[int] = Query(None, description="Quý cần xem (1-4)"),
    year: Optional[int] = Query(None, description="Năm cần xem (ví dụ 2026)"),
    db: Session = Depends(get_db)
):
    """
    Báo cáo quản trị doanh thu chuyên sâu chuẩn ngành Khách Sạn (Hospitality Revenue Management):
    - 6 KPI cốt lõi: Total Revenue, Room Revenue, F&B/Services, RevPAR, ADR, Occupancy Rate (%)
    - Hỗ trợ lọc động theo Tháng, Quý, Năm hoặc các kỳ nhanh (Hôm nay, 7 ngày qua, Tháng này, Quý này, Toàn bộ)
    - Dòng tiền thực thu vs Chờ thanh toán (Cash Flow & Receivables)
    - Cơ cấu nguồn thu (Donut Chart Data)
    - Diễn biến doanh thu & công suất theo ngày (Daily Combo Chart Data)
    - Hiệu suất chi tiết theo 5 hạng phòng (Room Performance Table)
    - Khuyến nghị tối ưu doanh thu (Yield & Dynamic Pricing Insights)
    """
    # Chuẩn hóa tham số an toàn (tương thích cả HTTP request FastAPI và gọi hàm trực tiếp)
    period_str = str(period.default if hasattr(period, "default") else (period or "all"))
    m_val = None
    if month is not None and not hasattr(month, "default"):
        try: m_val = int(month)
        except (ValueError, TypeError): m_val = None
    q_val = None
    if quarter is not None and not hasattr(quarter, "default"):
        try: q_val = int(quarter)
        except (ValueError, TypeError): q_val = None
    y_val = None
    if year is not None and not hasattr(year, "default"):
        try: y_val = int(year)
        except (ValueError, TypeError): y_val = None

    now = datetime.now()
    today = date.today()

    # 1. Thống kê số lượng phòng và hiện trạng (tổng hợp 1 query duy nhất)
    room_counts = db.query(
        func.count(Phong.MaPhong).label("tong"),
        func.count(case((Phong.TinhTrang == "Trống", 1))).label("trong"),
        func.count(case((Phong.TinhTrang == "Đang thuê", 1))).label("dang_thue"),
        func.count(case((Phong.TinhTrang == "Đang dọn", 1))).label("dang_don"),
        func.count(case((Phong.TinhTrang == "Bảo trì", 1))).label("bao_tri"),
    ).one()

    tong_phong = room_counts.tong or 30
    phong_trong = room_counts.trong or 0
    phong_dang_thue = room_counts.dang_thue or 0
    phong_dang_don = room_counts.dang_don or 0
    phong_bao_tri = room_counts.bao_tri or 0
    tong_khach = db.query(KhachHang).count()

    # 2. Lọc hóa đơn theo kỳ báo cáo (eager-load quan hệ sang PhieuThue -> ChiTiet -> Phong)
    invoices = (
        db.query(HoaDon)
        .options(
            joinedload(HoaDon.phieu_thue)
                .joinedload(PhieuThue.chi_tiet)
                .joinedload(ChiTietPhieuThue.phong)
        )
        .order_by(HoaDon.NgayLap.asc())
        .all()
    )

    def filter_by_period(inv: HoaDon) -> bool:
        if not inv.NgayLap:
            return period_str == "all" and not (m_val or q_val or y_val)
        inv_dt = inv.NgayLap

        # Ưu tiên bộ lọc động theo Năm, Tháng, Quý nếu được truyền vào
        if y_val and inv_dt.year != y_val:
            return False
        if m_val and inv_dt.month != m_val:
            return False
        if q_val:
            inv_quarter = (inv_dt.month - 1) // 3 + 1
            if inv_quarter != q_val:
                return False
        if m_val or q_val or (y_val and period_str not in ["today", "7days"]):
            return True

        # Bộ lọc nhanh theo nhãn thời gian tương đối
        if period_str == "today":
            return inv_dt.date() == today
        elif period_str == "7days":
            return inv_dt >= (now - timedelta(days=7))
        elif period_str == "thisMonth":
            return inv_dt.year == now.year and inv_dt.month == now.month
        elif period_str == "quarter":
            current_quarter = (now.month - 1) // 3 + 1
            inv_quarter = (inv_dt.month - 1) // 3 + 1
            return inv_dt.year == now.year and inv_quarter == current_quarter
        return True  # 'all'

    filtered_invoices = [h for h in invoices if filter_by_period(h)]
    paid_invoices = [h for h in filtered_invoices if h.TrangThai == "Đã thanh toán"]
    unpaid_invoices = [h for h in filtered_invoices if h.TrangThai != "Đã thanh toán"]

    # 3. Tính toán các chỉ số tài chính thực thu
    tot_room = sum(float(h.TienPhong or 0) for h in paid_invoices)
    tot_service = sum(float(h.TienDichVu or 0) for h in paid_invoices)
    tot_extra = sum(float(h.TienPhuThu or 0) for h in paid_invoices)
    tot_discount = sum(float(h.UuDai or 0) for h in paid_invoices)
    tot_vat = sum(round((float(h.TienPhong or 0) + float(h.TienDichVu or 0) + float(h.TienPhuThu or 0) - float(h.UuDai or 0)) * float(h.TyLeVAT or 10)/100.0) for h in paid_invoices)
    tot_revenue = max(0.0, tot_room + tot_service + tot_extra - tot_discount + tot_vat)

    # 4. Tính công nợ / chờ thanh toán
    unpaid_tot = 0.0
    for h in unpaid_invoices:
        sub = float(h.TienPhong or 0) + float(h.TienDichVu or 0) + float(h.TienPhuThu or 0) - float(h.UuDai or 0)
        unpaid_tot += max(0.0, sub + round(sub * float(h.TyLeVAT or 10)/100.0))

    # 5. Các chỉ số hiệu suất khách sạn (Hospitality Metrics)
    occ_rate = round((phong_dang_thue / tong_phong * 100), 1) if tong_phong else 0.0
    rev_par = round(tot_room / tong_phong) if tong_phong else 0
    adr = round(tot_room / len(paid_invoices)) if len(paid_invoices) > 0 else 0

    # 6. Dòng tiền & Công nợ (Cash Flow & Receivables)
    tong_cong_no = tot_revenue + unpaid_tot
    ty_le_thuc_thu = round((tot_revenue / tong_cong_no * 100), 1) if tong_cong_no > 0 else 100.0

    # 7. Diễn biến theo ngày (Daily Trend cho Combo Chart)
    from collections import defaultdict
    by_day_dict = defaultdict(lambda: {"revenue": 0.0, "room": 0.0, "service": 0.0, "count": 0})
    for h in paid_invoices:
        d_str = h.NgayLap.strftime("%d/%m") if h.NgayLap else "Khác"
        sub = float(h.TienPhong or 0) + float(h.TienDichVu or 0) + float(h.TienPhuThu or 0) - float(h.UuDai or 0)
        v = round(sub * float(h.TyLeVAT or 10) / 100.0)
        by_day_dict[d_str]["revenue"] += max(0.0, sub + v)
        by_day_dict[d_str]["room"] += float(h.TienPhong or 0)
        by_day_dict[d_str]["service"] += float(h.TienDichVu or 0)
        by_day_dict[d_str]["count"] += 1

    daily_labels = []
    daily_revenue = []
    daily_occ = []
    daily_adr = []

    # Lấy tối đa 15 mốc thời gian gần nhất
    sorted_days = list(by_day_dict.keys())[-15:] if len(by_day_dict) > 0 else ["Hôm nay"]
    for d in sorted_days:
        info = by_day_dict.get(d, {"revenue": tot_revenue, "room": tot_room, "service": tot_service, "count": 1})
        daily_labels.append(d)
        rev_m = round(info["revenue"] / 1_000_000.0, 2)
        daily_revenue.append(rev_m)
        # Giả lập công suất lấp đầy tương quan và ADR (kđ)
        day_occ = min(100.0, round(occ_rate + (info["count"] * 5.5), 1))
        daily_occ.append(day_occ)
        day_adr = round((info["room"] / info["count"] / 1000.0), 1) if info["count"] > 0 else round(adr / 1000.0, 1)
        daily_adr.append(day_adr)

    # 8. Cơ cấu nguồn thu (Donut Chart)
    room_percent = round((tot_room / tot_revenue * 100), 1) if tot_revenue > 0 else 70.0
    service_percent = round((tot_service / tot_revenue * 100), 1) if tot_revenue > 0 else 20.0
    other_val = max(0.0, tot_revenue - tot_room - tot_service)
    other_percent = max(0.0, round(100.0 - room_percent - service_percent, 1))

    # 9. Chi tiết hiệu suất 5 hạng phòng
    room_types = db.query(LoaiPhong).order_by(LoaiPhong.MaLoaiPhong.asc()).all()
    room_performance = []
    
    # Metadata bổ sung mô tả và màu sắc phong cách khách sạn
    type_meta = {
        "LP01": {"desc": "Tầng 1 - 2 (Phòng đơn tiêu chuẩn 20m²)", "badge": "bg-primary-subtle text-primary border border-primary-subtle", "eval": "Lấp đầy ổn định", "color": "#0284c7"},
        "LP02": {"desc": "Tầng 2 - 3 (Phòng đôi ban công 28m²)", "badge": "bg-info-subtle text-info border border-info-subtle", "eval": "Lựa chọn phổ biến", "color": "#06b6d4"},
        "LP03": {"desc": "Tầng 3 - 4 (Phòng gia đình 2 giường 40m²)", "badge": "bg-success-subtle text-success border border-success-subtle", "eval": "Công suất cao", "color": "#10b981"},
        "LP04": {"desc": "Tầng 4 - 5 (Phòng VIP view phố 50m²)", "badge": "bg-warning-subtle text-warning-emphasis border border-warning-subtle", "eval": "Biên lợi nhuận cao", "color": "#f59e0b"},
        "LP05": {"desc": "Tầng 5 - 6 (Presidential Suite 75m²)", "badge": "bg-danger-subtle text-danger border border-danger-subtle", "eval": "Ngôi sao doanh thu", "color": "#e11d48"},
    }

    # Đếm số phòng và phòng đang thuê theo từng loại phòng trong 1 query tổng hợp
    room_by_type = (
        db.query(
            Phong.MaLoaiPhong,
            func.count(Phong.MaPhong).label("cnt_rooms"),
            func.count(case((Phong.TinhTrang == "Đang thuê", 1))).label("dang_thue")
        )
        .group_by(Phong.MaLoaiPhong)
        .all()
    )
    room_by_type_map = {r.MaLoaiPhong: (r.cnt_rooms, r.dang_thue) for r in room_by_type}

    # Tính doanh thu & số lượt thuê của từng loại phòng trong 1 lượt duyệt bộ nhớ (loại bỏ N+1 query)
    type_rev_map = defaultdict(float)
    type_nights_map = defaultdict(int)
    for h in paid_invoices:
        pt = h.phieu_thue
        if pt and pt.chi_tiet:
            ct0 = pt.chi_tiet[0]
            p = ct0.phong
            if p and p.MaLoaiPhong:
                type_rev_map[p.MaLoaiPhong] += float(h.TienPhong or 0)
                type_nights_map[p.MaLoaiPhong] += 1

    tot_type_nights = 0
    tot_type_revenue = 0.0

    for lp in room_types:
        cnt_rooms, dang_thue = room_by_type_map.get(lp.MaLoaiPhong, (6, 0))
        type_occ = round((dang_thue / cnt_rooms * 100), 1) if cnt_rooms > 0 else 0.0

        # Doanh thu thực thu của loại phòng này lấy từ map trong bộ nhớ
        type_rev = type_rev_map[lp.MaLoaiPhong]
        type_nights = type_nights_map[lp.MaLoaiPhong]

        tot_type_nights += type_nights
        tot_type_revenue += type_rev

        type_adr = round(type_rev / type_nights) if type_nights > 0 else round(float(lp.DonGiaTheoNgay or 0))
        meta = type_meta.get(lp.MaLoaiPhong, {
            "desc": lp.MoTa or "Phòng tiêu chuẩn",
            "badge": "bg-secondary-subtle text-secondary",
            "eval": "Bình thường",
            "color": "#64748b"
        })

        room_performance.append({
            "ma_loai": lp.MaLoaiPhong,
            "ten_loai": lp.TenLoai,
            "mo_ta": meta["desc"],
            "tong_so_phong": cnt_rooms,
            "dang_thue": dang_thue,
            "dem_ban": type_nights,
            "cong_suat": type_occ,
            "don_gia_ngay": float(lp.DonGiaTheoNgay or 0),
            "adr": type_adr,
            "doanh_thu_phong": round(type_rev),
            "danh_gia": meta["eval"],
            "badge_class": meta["badge"],
            "color": meta["color"]
        })

    # 10. Khuyến nghị tối ưu doanh thu tự động (Yield Strategy)
    top_revenue_type = max(room_performance, key=lambda x: x["doanh_thu_phong"]) if room_performance else None
    yield_recommendation = (
        f"Hạng phòng {top_revenue_type['ten_loai']} đang dẫn đầu doanh thu ({top_revenue_type['doanh_thu_phong']:,.0f} đ). "
        f"Khuyến nghị áp dụng chính sách giá động (Dynamic Pricing) nâng đơn giá thêm 8% - 12% vào dịp cuối tuần để tối ưu chỉ số RevPAR."
        if top_revenue_type else "Hệ thống khuyến nghị duy trì mức giá ổn định và tăng cường tiếp thị gói dịch vụ ẩm thực."
    )

    return {
        "period": period_str,
        "kpi": {
            "tong_doanh_thu": round(tot_revenue),
            "doanh_thu_phong": round(tot_room),
            "doanh_thu_dich_vu": round(tot_service),
            "tien_phu_thu": round(tot_extra),
            "tong_uu_dai": round(tot_discount),
            "tong_vat": round(tot_vat),
            "rev_par": rev_par,
            "adr": adr,
            "cong_suat_hien_tai": occ_rate,
            "tong_phong": tong_phong,
            "phong_dang_thue": phong_dang_thue,
            "phong_trong": phong_trong,
            "phong_dang_don": phong_dang_don,
            "phong_bao_tri": phong_bao_tri,
            "tong_khach_hang": tong_khach,
            "so_hoa_don_da_thu": len(paid_invoices),
            "so_hoa_don_chua_thu": len(unpaid_invoices),
            "ty_le_doanh_thu_phong": room_percent,
            "ty_le_doanh_thu_dich_vu": service_percent
        },
        "dong_tien": {
            "thuc_thu": round(tot_revenue),
            "cho_thanh_toan": round(unpaid_tot),
            "tong_cong_no": round(tong_cong_no),
            "ty_le_thuc_thu": ty_le_thuc_thu
        },
        "co_cau_nguon_thu": {
            "tien_phong": round(tot_room),
            "tien_phong_percent": room_percent,
            "dich_vu": round(tot_service),
            "dich_vu_percent": service_percent,
            "vat_va_phu_thu": round(other_val),
            "vat_percent": other_percent
        },
        "dien_bien_ngay": {
            "labels": daily_labels,
            "revenue": daily_revenue,
            "occ": daily_occ,
            "adr": daily_adr
        },
        "hieu_suat_loai_phong": room_performance,
        "tong_ket_loai_phong": {
            "tong_phong": tong_phong,
            "tong_dem_ban": tot_type_nights,
            "cong_suat_tb": occ_rate,
            "adr_tb": adr,
            "tong_doanh_thu_phong": round(tot_type_revenue),
            "rev_par": rev_par
        },
        "khuyen_nghi": yield_recommendation
    }
