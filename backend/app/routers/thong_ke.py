from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models import Phong, KhachHang, HoaDon
from backend.app.schemas import ThongKeSummary

router = APIRouter(prefix="/thong-ke", tags=["Thống Kê Báo Cáo"])

@router.get("/tong-quan", response_model=ThongKeSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    tong_phong = db.query(Phong).count()
    phong_trong = db.query(Phong).filter(Phong.TinhTrang == "Trống").count()
    phong_dang_thue = db.query(Phong).filter(Phong.TinhTrang == "Đang thuê").count()
    phong_dang_don = db.query(Phong).filter(Phong.TinhTrang == "Đang dọn").count()
    phong_bao_tri = db.query(Phong).filter(Phong.TinhTrang == "Bảo trì").count()

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

