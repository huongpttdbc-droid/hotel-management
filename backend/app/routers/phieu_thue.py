from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import PhieuThue, ChiTietPhieuThue, Phong, KhachHang, LoaiPhong
from backend.app.schemas import PhieuThueOut, PhieuThueCreate, ChiTietPhieuThueOut

router = APIRouter(prefix="/phieu-thue", tags=["Quản lý Thuê Phòng"])

@router.get("", response_model=List[PhieuThueOut])
def list_rentals(
    trang_thai: Optional[str] = Query(None, description="Lọc: Đang thuê, Đã đặt, Hoàn tất"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(PhieuThue).join(KhachHang, PhieuThue.MaKH == KhachHang.MaKH)

    if trang_thai:
        query = query.filter(PhieuThue.TrangThai == trang_thai)

    rentals = query.order_by(PhieuThue.NgayLap.desc()).limit(limit).all()
    results = []

    for pt in rentals:
        details = []
        for ct in pt.chi_tiet:
            p = db.query(Phong).filter(Phong.MaPhong == ct.MaPhong).first()
            details.append(
                ChiTietPhieuThueOut(
                    STT=ct.STT,
                    MaPhong=ct.MaPhong,
                    SoPhong=p.SoPhong if p else None,
                    HinhThucThue=ct.HinhThucThue,
                    DonGiaApDung=float(ct.DonGiaApDung),
                    SoNguoiDuKien=ct.SoNguoiDuKien,
                    GioNhan=ct.GioNhan,
                    GioTraDuKien=ct.GioTraDuKien,
                    GioTra=ct.GioTra
                )
            )

        results.append(
            PhieuThueOut(
                MaPhieuThue=pt.MaPhieuThue,
                NgayLap=pt.NgayLap,
                TrangThai=pt.TrangThai,
                MaKH=pt.MaKH,
                TenKhachHang=pt.khach_hang.HoTen if pt.khach_hang else None,
                MaNV=pt.MaNV,
                ChiTiet=details
            )
        )

    return results

@router.post("", response_model=PhieuThueOut)
def create_rental(req: PhieuThueCreate, db: Session = Depends(get_db)):
    # 1. Kiểm tra khách hàng
    kh = db.query(KhachHang).filter(KhachHang.MaKH == req.MaKH).first()
    if not kh:
        raise HTTPException(status_code=404, detail="Khách hàng không tồn tại")

    # 2. Kiểm tra phòng
    phong = db.query(Phong).filter(Phong.MaPhong == req.MaPhong).first()
    if not phong:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")
    if phong.TinhTrang != "Trống":
        raise HTTPException(status_code=400, detail=f"Phòng {phong.SoPhong} hiện tại không trống (Tình trạng: {phong.TinhTrang})")

    # 3. Lấy đơn giá áp dụng từ loại phòng
    lp = db.query(LoaiPhong).filter(LoaiPhong.MaLoaiPhong == phong.MaLoaiPhong).first()
    don_gia = 0
    if req.HinhThucThue == "Theo giờ":
        don_gia = float(lp.DonGiaTheoGio or 0)
    elif req.HinhThucThue == "Qua đêm":
        don_gia = float(lp.DonGiaQuaDem or 0)
    else:
        don_gia = float(lp.DonGiaTheoNgay or 0)

    # 4. Sinh mã phiếu thuê mới
    now = datetime.now()
    count_today = db.query(PhieuThue).filter(PhieuThue.MaPhieuThue.like(f"PT{now.strftime('%y%m%d')}%")).count()
    ma_pt = f"PT{now.strftime('%y%m%d')}{count_today + 1:03d}"
    while db.query(PhieuThue).filter(PhieuThue.MaPhieuThue == ma_pt).first():
        count_today += 1
        ma_pt = f"PT{now.strftime('%y%m%d')}{count_today:03d}"

    gio_nhan = req.GioNhan or now
    gio_tra_du_kien = req.GioTraDuKien or (gio_nhan + timedelta(days=1))

    new_pt = PhieuThue(
        MaPhieuThue=ma_pt,
        NgayLap=now,
        TrangThai="Đang thuê",
        MaKH=req.MaKH,
        MaNV=req.MaNV or "NV01"  # Nhân viên lập phiếu
    )
    db.add(new_pt)
    db.flush()

    new_ct = ChiTietPhieuThue(
        MaPhieuThue=ma_pt,
        STT=1,
        MaPhong=req.MaPhong,
        HinhThucThue=req.HinhThucThue,
        DonGiaApDung=don_gia,
        SoNguoiDuKien=req.SoNguoiDuKien,
        KhachDatCoOPhongNay=True,
        GioNhan=gio_nhan,
        GioTraDuKien=gio_tra_du_kien,
        GhiChu=req.GhiChu
    )
    db.add(new_ct)

    # Cập nhật trạng thái phòng sang 'Đang thuê'
    phong.TinhTrang = "Đang thuê"

    db.commit()
    db.refresh(new_pt)

    return PhieuThueOut(
        MaPhieuThue=new_pt.MaPhieuThue,
        NgayLap=new_pt.NgayLap,
        TrangThai=new_pt.TrangThai,
        MaKH=new_pt.MaKH,
        TenKhachHang=kh.HoTen,
        MaNV=new_pt.MaNV,
        ChiTiet=[
            ChiTietPhieuThueOut(
                STT=1,
                MaPhong=phong.MaPhong,
                SoPhong=phong.SoPhong,
                HinhThucThue=req.HinhThucThue,
                DonGiaApDung=don_gia,
                SoNguoiDuKien=req.SoNguoiDuKien,
                GioNhan=gio_nhan,
                GioTraDuKien=gio_tra_du_kien
            )
        ]
    )

@router.post("/{ma_pt}/tra-phong")
def check_out_rental(ma_pt: str, db: Session = Depends(get_db)):
    pt = db.query(PhieuThue).filter(PhieuThue.MaPhieuThue == ma_pt).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu thuê")

    if pt.TrangThai != "Đang thuê":
        raise HTTPException(status_code=400, detail=f"Phiếu thuê đang ở trạng thái '{pt.TrangThai}', không thể trả phòng.")

    now = datetime.now()

    # 1. Ghi giờ trả cho từng phòng TRƯỚC
    for ct in pt.chi_tiet:
        ct.GioTra = now
    db.flush()   # Đẩy UPDATE ChiTietPhieuThue xuống DB ngay

    # 2. Rồi mới hoàn tất phiếu (trigger TR_PhieuThue_TrangThai sẽ thấy GioTra đã có,
    #    và tự chuyển phòng sang 'Đang dọn')
    pt.TrangThai = "Hoàn tất"

    # Cập nhật thêm phòng sang 'Đang dọn' (phòng trường hợp chạy SQLite fallback không có trigger)
    for ct in pt.chi_tiet:
        p = db.query(Phong).filter(Phong.MaPhong == ct.MaPhong).first()
        if p and p.TinhTrang == "Đang thuê":
            p.TinhTrang = "Đang dọn"

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Không thể trả phòng: {e.orig if hasattr(e, 'orig') else e}")

    return {"message": f"Đã trả phòng thành công cho phiếu thuê {ma_pt}. Các phòng đã được chuyển sang trạng thái 'Đang dọn'."}

