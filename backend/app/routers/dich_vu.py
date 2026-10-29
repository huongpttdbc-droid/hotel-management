from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import DichVu, DungDichVu, PhieuThue, ChiTietPhieuThue
from backend.app.schemas import DichVuOut, DungDichVuCreate

router = APIRouter(prefix="/dich-vu", tags=["Dịch Vụ Khách Sạn"])

@router.get("", response_model=List[DichVuOut])
def list_services(db: Session = Depends(get_db)):
    services = db.query(DichVu).all()
    return [
        DichVuOut(
            MaDichVu=s.MaDichVu,
            TenDichVu=s.TenDichVu,
            DonViTinh=s.DonViTinh,
            DonGia=float(s.DonGia),
            MoTa=s.MoTa
        )
        for s in services
    ]

@router.post("/su-dung")
def use_service(req: DungDichVuCreate, db: Session = Depends(get_db)):
    pt = db.query(PhieuThue).filter(PhieuThue.MaPhieuThue == req.MaPhieuThue).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu thuê")
    if pt.TrangThai == "Đã hủy":
        raise HTTPException(status_code=400, detail="Không thể thêm dịch vụ cho phiếu thuê đã hủy.")

    dv = db.query(DichVu).filter(DichVu.MaDichVu == req.MaDichVu).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ")

    # Xác định STT phòng hợp lệ trong phiếu thuê
    stt_target = req.STT
    ct = db.query(ChiTietPhieuThue).filter(
        ChiTietPhieuThue.MaPhieuThue == req.MaPhieuThue,
        ChiTietPhieuThue.STT == req.STT
    ).first()
    if not ct:
        ct_first = db.query(ChiTietPhieuThue).filter(ChiTietPhieuThue.MaPhieuThue == req.MaPhieuThue).first()
        if not ct_first:
            raise HTTPException(status_code=400, detail="Phiếu thuê chưa có chi tiết phòng.")
        stt_target = ct_first.STT

    now = datetime.now()
    new_use = DungDichVu(
        MaPhieuThue=req.MaPhieuThue,
        STT=stt_target,
        MaDichVu=req.MaDichVu,
        GioBD=now,
        SoLuong=req.SoLuong,
        DonGiaApDung=dv.DonGia
    )
    db.add(new_use)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Không thể thêm dịch vụ: {e.orig if hasattr(e, 'orig') else e}")

    return {
        "message": f"Đã ghi nhận dịch vụ '{dv.TenDichVu}' x {req.SoLuong} cho phiếu thuê {req.MaPhieuThue}.",
        "DonGia": float(dv.DonGia),
        "ThanhTien": float(dv.DonGia) * req.SoLuong
    }

