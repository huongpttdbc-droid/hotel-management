from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models import Phong, LoaiPhong, PhieuThue, ChiTietPhieuThue, KhachHang
from backend.app.schemas import PhongOut, PhongStatusUpdate, LoaiPhongOut

router = APIRouter(prefix="/phong", tags=["Quản lý Phòng"])

@router.get("", response_model=List[PhongOut])
def list_rooms(
    tang: Optional[int] = Query(None, description="Lọc theo tầng"),
    tinh_trang: Optional[str] = Query(None, description="Lọc theo tình trạng"),
    db: Session = Depends(get_db)
):
    # Eager load loai_phong bằng joinedload để loại bỏ N+1 query
    query = db.query(Phong).options(joinedload(Phong.loai_phong))

    if tang is not None:
        query = query.filter(Phong.Tang == tang)
    if tinh_trang:
        query = query.filter(Phong.TinhTrang == tinh_trang)

    rooms = query.order_by(Phong.Tang.asc(), Phong.SoPhong.asc()).all()

    # Eager batch load toàn bộ thông tin khách đang thuê trong đúng 1 query duy nhất
    rented_room_ids = [r.MaPhong for r in rooms if r.TinhTrang == "Đang thuê"]
    current_guests = {}
    if rented_room_ids:
        active_rents = (
            db.query(ChiTietPhieuThue.MaPhong, KhachHang.HoTen, PhieuThue.MaPhieuThue)
            .join(PhieuThue, KhachHang.MaKH == PhieuThue.MaKH)
            .join(ChiTietPhieuThue, PhieuThue.MaPhieuThue == ChiTietPhieuThue.MaPhieuThue)
            .filter(
                ChiTietPhieuThue.MaPhong.in_(rented_room_ids),
                PhieuThue.TrangThai == "Đang thuê"
            )
            .order_by(ChiTietPhieuThue.GioNhan.desc())
            .all()
        )
        for ma_phong, ho_ten, ma_pt in active_rents:
            if ma_phong not in current_guests:
                current_guests[ma_phong] = (ho_ten, ma_pt)

    results = []
    for r in rooms:
        khach_hien_tai, ma_phieu_thue = current_guests.get(r.MaPhong, (None, None))
        results.append(
            PhongOut(
                MaPhong=r.MaPhong,
                SoPhong=r.SoPhong,
                Tang=r.Tang,
                TinhTrang=r.TinhTrang,
                MaLoaiPhong=r.MaLoaiPhong,
                TenLoaiPhong=r.loai_phong.TenLoai if r.loai_phong else None,
                SucChua=r.loai_phong.SucChua if r.loai_phong else None,
                DonGiaTheoNgay=float(r.loai_phong.DonGiaTheoNgay) if r.loai_phong else 0.0,
                KhachHienTai=khach_hien_tai,
                MaPhieuThue=ma_phieu_thue
            )
        )

    return results

@router.get("/loai-phong", response_model=List[LoaiPhongOut])
def list_room_types(db: Session = Depends(get_db)):
    types = db.query(LoaiPhong).all()
    return types

@router.get("/{ma_phong}", response_model=PhongOut)
def get_room_detail(ma_phong: str, db: Session = Depends(get_db)):
    r = (
        db.query(Phong)
        .options(joinedload(Phong.loai_phong))
        .filter(Phong.MaPhong == ma_phong)
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy phòng {ma_phong}")
    
    return PhongOut(
        MaPhong=r.MaPhong,
        SoPhong=r.SoPhong,
        Tang=r.Tang,
        TinhTrang=r.TinhTrang,
        MaLoaiPhong=r.MaLoaiPhong,
        TenLoaiPhong=r.loai_phong.TenLoai if r.loai_phong else None,
        SucChua=r.loai_phong.SucChua if r.loai_phong else None,
        DonGiaTheoNgay=float(r.loai_phong.DonGiaTheoNgay) if r.loai_phong else 0.0
    )

@router.put("/{ma_phong}/tinh-trang")
def update_room_status(ma_phong: str, req: PhongStatusUpdate, db: Session = Depends(get_db)):
    target_status = req.TinhTrang.strip()
    valid_statuses = ["Trống", "Đang thuê", "Đang dọn", "Bảo trì"]
    
    if target_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Tình trạng không hợp lệ. Phải là một trong: {valid_statuses}")

    r = db.query(Phong).filter(Phong.MaPhong == ma_phong).first()
    if not r:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")

    if r.TinhTrang == "Đang thuê" and target_status != "Đang thuê":
        raise HTTPException(
            status_code=400,
            detail="Phòng đang có khách thuê. Hãy thực hiện trả phòng tại mục Phiếu Thuê trước khi đổi trạng thái!"
        )

    r.TinhTrang = target_status
    db.commit()
    return {"message": f"Đã cập nhật tình trạng phòng {ma_phong} thành '{target_status}'.", "MaPhong": ma_phong, "TinhTrang": target_status}

