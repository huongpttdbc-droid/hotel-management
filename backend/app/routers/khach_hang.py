from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import KhachHang, KhachHangSDT, LoaiKhachHang
from backend.app.schemas import KhachHangOut, KhachHangCreate

router = APIRouter(prefix="/khach-hang", tags=["Quản lý Khách Hàng"])

@router.get("", response_model=List[KhachHangOut])
def list_customers(
    keyword: Optional[str] = Query(None, description="Tìm theo Tên, CCCD hoặc SĐT"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(KhachHang).join(LoaiKhachHang, KhachHang.MaLoaiKH == LoaiKhachHang.MaLoaiKH)

    if keyword:
        k = f"%{keyword.strip()}%"
        query = query.filter(
            (KhachHang.HoTen.ilike(k)) | (KhachHang.CCCD.ilike(k)) | (KhachHang.MaKH.ilike(k))
        )

    customers = query.order_by(KhachHang.MaKH.desc()).limit(limit).all()
    results = []

    for c in customers:
        # Lấy số điện thoại đầu tiên
        sdt_record = db.query(KhachHangSDT.SDT).filter(KhachHangSDT.MaKH == c.MaKH).first()
        sdt = sdt_record[0] if sdt_record else None

        results.append(
            KhachHangOut(
                MaKH=c.MaKH,
                HoTen=c.HoTen,
                NgaySinh=c.NgaySinh,
                CCCD=c.CCCD,
                DiaChi=c.DiaChi,
                MaLoaiKH=c.MaLoaiKH,
                TenLoaiKH=c.loai_khach_hang.TenLoai if c.loai_khach_hang else None,
                PhanTramUuDai=float(c.loai_khach_hang.PhanTramUuDai) if c.loai_khach_hang else 0.0,
                SDT=sdt
            )
        )

    return results

@router.post("", response_model=KhachHangOut)
def create_customer(req: KhachHangCreate, db: Session = Depends(get_db)):
    # 1. Kiểm tra đủ 18 tuổi
    today = date.today()
    age = today.year - req.NgaySinh.year - ((today.month, today.day) < (req.NgaySinh.month, req.NgaySinh.day))
    if age < 18:
        raise HTTPException(status_code=400, detail="Khách hàng phải từ đủ 18 tuổi trở lên.")

    # 2. Kiểm tra CCCD 12 số
    cccd = req.CCCD.strip()
    if len(cccd) != 12 or not cccd.isdigit():
        raise HTTPException(status_code=400, detail="Số CCCD phải gồm đúng 12 chữ số.")

    # Kiểm tra trùng CCCD
    exist = db.query(KhachHang).filter(KhachHang.CCCD == cccd).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"CCCD {cccd} đã tồn tại trong hệ thống (Mã KH: {exist.MaKH}).")

    # 3. Tự động sinh Mã KH nếu chưa có
    ma_kh = req.MaKH
    if not ma_kh:
        # Tìm mã lớn nhất dạng KHxxx
        count = db.query(KhachHang).count()
        ma_kh = f"KH{count + 1:03d}"
        # Đảm bảo duy nhất
        while db.query(KhachHang).filter(KhachHang.MaKH == ma_kh).first():
            count += 1
            ma_kh = f"KH{count:03d}"

    new_kh = KhachHang(
        MaKH=ma_kh,
        HoTen=req.HoTen.strip(),
        NgaySinh=req.NgaySinh,
        CCCD=cccd,
        DiaChi=req.DiaChi.strip() if req.DiaChi else None,
        MaLoaiKH=req.MaLoaiKH or "LKH01"
    )
    db.add(new_kh)
    db.flush()

    # Thêm SĐT nếu có
    if req.SDT:
        sdt_clean = req.SDT.strip()
        new_sdt = KhachHangSDT(MaKH=ma_kh, SDT=sdt_clean)
        db.add(new_sdt)

    db.commit()
    db.refresh(new_kh)

    loai = db.query(LoaiKhachHang).filter(LoaiKhachHang.MaLoaiKH == new_kh.MaLoaiKH).first()

    return KhachHangOut(
        MaKH=new_kh.MaKH,
        HoTen=new_kh.HoTen,
        NgaySinh=new_kh.NgaySinh,
        CCCD=new_kh.CCCD,
        DiaChi=new_kh.DiaChi,
        MaLoaiKH=new_kh.MaLoaiKH,
        TenLoaiKH=loai.TenLoai if loai else None,
        PhanTramUuDai=float(loai.PhanTramUuDai) if loai else 0.0,
        SDT=req.SDT
    )

