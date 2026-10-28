from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import DichVu, DungDichVu, PhieuThue
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

    dv = db.query(DichVu).filter(DichVu.MaDichVu == req.MaDichVu).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ")

    now = datetime.now()
    new_use = DungDichVu(
        MaPhieuThue=req.MaPhieuThue,
        STT=req.STT,
        MaDichVu=req.MaDichVu,
        GioBD=now,
        SoLuong=req.SoLuong,
        DonGiaApDung=dv.DonGia
    )
    db.add(new_use)
    db.commit()

    return {
        "message": f"Đã ghi nhận dịch vụ '{dv.TenDichVu}' x {req.SoLuong} cho phiếu thuê {req.MaPhieuThue}.",
        "DonGia": float(dv.DonGia),
        "ThanhTien": float(dv.DonGia) * req.SoLuong
    }

