import collections
from datetime import datetime, timedelta, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from backend.app.database import get_db
from backend.app.models import (
    PhieuThue, ChiTietPhieuThue, Phong, KhachHang, LoaiPhong,
    DichVu, DungDichVu, KhachHangSDT
)
from backend.app.schemas import (
    PhieuThueOut, PhieuThueCreate, ChiTietPhieuThueOut,
    KhachHuyDatPhongRequest, TraCuuDatPhongRequest, ChiTietDichVuHoaDon
)

router = APIRouter(prefix="/phieu-thue", tags=["Quản lý Thuê Phòng"])

@router.get("", response_model=List[PhieuThueOut])
def list_rentals(
    trang_thai: Optional[str] = Query(None, description="Lọc: Đang thuê, Đã đặt, Hoàn tất"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(PhieuThue).options(
        joinedload(PhieuThue.khach_hang).joinedload(KhachHang.so_dien_thoai),
        joinedload(PhieuThue.chi_tiet).joinedload(ChiTietPhieuThue.phong)
    )

    if trang_thai:
        query = query.filter(PhieuThue.TrangThai == trang_thai)

    rentals = query.order_by(PhieuThue.NgayLap.desc()).limit(limit).all()
    if not rentals:
        return []

    # Batch load toàn bộ dịch vụ kèm joinedload(DichVu) trong đúng 1 query duy nhất
    pt_ids = [pt.MaPhieuThue for pt in rentals if pt.MaPhieuThue]
    services_by_pt = collections.defaultdict(list)
    if pt_ids:
        used_services = (
            db.query(DungDichVu)
            .options(joinedload(DungDichVu.dich_vu))
            .filter(DungDichVu.MaPhieuThue.in_(pt_ids))
            .all()
        )
        for us in used_services:
            dv = us.dich_vu
            dg = float(us.DonGiaApDung if us.DonGiaApDung is not None else (dv.DonGia if dv else 0))
            sl = int(us.SoLuong or 1)
            services_by_pt[us.MaPhieuThue].append(
                ChiTietDichVuHoaDon(
                    TenDichVu=dv.TenDichVu if dv else us.MaDichVu,
                    DonViTinh=dv.DonViTinh if dv else "Lần",
                    DonGia=dg,
                    SoLuong=sl,
                    ThanhTien=round(dg * sl)
                )
            )

    results = []
    for pt in rentals:
        details = []
        for ct in pt.chi_tiet:
            p = ct.phong
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

        kh = pt.khach_hang
        sdt = kh.so_dien_thoai[0].SDT if (kh and kh.so_dien_thoai) else None
        dia_chi = kh.DiaChi if kh else None

        results.append(
            PhieuThueOut(
                MaPhieuThue=pt.MaPhieuThue,
                NgayLap=pt.NgayLap,
                TrangThai=pt.TrangThai,
                MaKH=pt.MaKH,
                TenKhachHang=kh.HoTen if kh else None,
                SoDienThoai=sdt,
                DiaChi=dia_chi,
                MaNV=pt.MaNV,
                ChiTiet=details,
                DichVu=services_by_pt.get(pt.MaPhieuThue, [])
            )
        )

    return results

@router.post("", response_model=PhieuThueOut)
def create_rental(req: PhieuThueCreate, db: Session = Depends(get_db)):
    # 1. Kiểm tra & cập nhật hoặc tự động tạo khách hàng
    kh = None
    if req.MaKH:
        kh = db.query(KhachHang).options(joinedload(KhachHang.so_dien_thoai)).filter(KhachHang.MaKH == req.MaKH).first()

    if not kh and req.CCCD:
        cccd_clean = req.CCCD.strip()
        kh = db.query(KhachHang).options(joinedload(KhachHang.so_dien_thoai)).filter(KhachHang.CCCD == cccd_clean).first()

    if not kh and req.HoTen and req.CCCD:
        cccd_clean = req.CCCD.strip()
        count_kh = db.query(KhachHang).count()
        new_makh = f"KH{count_kh + 1:03d}"
        while db.query(KhachHang).filter(KhachHang.MaKH == new_makh).first():
            count_kh += 1
            new_makh = f"KH{count_kh:03d}"

        dob = req.NgaySinh or date(1995, 1, 1)
        kh = KhachHang(
            MaKH=new_makh,
            HoTen=req.HoTen.strip(),
            NgaySinh=dob,
            CCCD=cccd_clean,
            DiaChi=(req.dia_chi or req.DiaChi or "Đặt trực tuyến").strip(),
            MaLoaiKH="LKH01"
        )
        db.add(kh)
        db.flush()

        if req.SDT:
            db.add(KhachHangSDT(MaKH=new_makh, SDT=req.SDT.strip()))
            db.flush()
        db.refresh(kh)

    if not kh:
        raise HTTPException(
            status_code=400,
            detail="Không tìm thấy khách hàng. Vui lòng cung cấp MaKH hoặc đầy đủ HoTen, CCCD, SDT để tạo mới."
        )

    # Lưu thêm trường dia_chi từ khách hàng nếu có
    client_address = (req.dia_chi or req.DiaChi or "").strip()
    if client_address:
        kh.DiaChi = client_address

    if req.SDT and not any(s.SDT.strip() == req.SDT.strip() for s in (kh.so_dien_thoai or [])):
        db.add(KhachHangSDT(MaKH=kh.MaKH, SDT=req.SDT.strip()))
        db.flush()

    # 2. Kiểm tra phòng
    phong = db.query(Phong).filter(Phong.MaPhong == req.MaPhong).first()
    if not phong:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")
    if phong.TinhTrang != "Trống":
        raise HTTPException(status_code=400, detail=f"Phòng {phong.SoPhong} hiện tại không trống (Tình trạng: {phong.TinhTrang})")

    # 3. Lấy đơn giá áp dụng từ loại phòng & kiểm tra sức chứa
    lp = db.query(LoaiPhong).filter(LoaiPhong.MaLoaiPhong == phong.MaLoaiPhong).first()
    suc_chua = 99
    if lp and lp.SucChua is not None:
        try:
            suc_chua = int(lp.SucChua)
        except (ValueError, TypeError):
            suc_chua = 99

    if req.SoNguoiDuKien > suc_chua:
        raise HTTPException(
            status_code=400,
            detail=f"Số người dự kiến ({req.SoNguoiDuKien}) vượt quá sức chứa tối đa ({suc_chua} người) của loại phòng {lp.TenLoai if lp else ''}."
        )

    don_gia = 0
    if req.HinhThucThue == "Theo giờ":
        don_gia = float(lp.DonGiaTheoGio or 0)
    elif req.HinhThucThue == "Qua đêm":
        don_gia = float(lp.DonGiaQuaDem or 0)
    else:
        don_gia = float(lp.DonGiaTheoNgay or 0)

    # 4. Chuẩn hóa ngày giờ nhận & trả
    now = datetime.now()
    gio_nhan = req.gio_nhan or req.GioNhan or now
    gio_tra = req.gio_tra or req.GioTraDuKien or (gio_nhan + timedelta(days=1))
    if gio_tra <= gio_nhan:
        raise HTTPException(status_code=400, detail="Thời gian trả phòng dự kiến phải sau thời gian nhận phòng.")

    # 5. Sinh mã phiếu thuê mới
    count_today = db.query(PhieuThue).filter(PhieuThue.MaPhieuThue.like(f"PT{now.strftime('%y%m%d')}%")).count()
    ma_pt = f"PT{now.strftime('%y%m%d')}{count_today + 1:03d}"
    while db.query(PhieuThue).filter(PhieuThue.MaPhieuThue == ma_pt).first():
        count_today += 1
        ma_pt = f"PT{now.strftime('%y%m%d')}{count_today:03d}"

    trang_thai = (req.TrangThai or "Đã đặt").strip()

    # 6. Insert PhieuThue
    new_pt = PhieuThue(
        MaPhieuThue=ma_pt,
        NgayLap=now,
        TrangThai=trang_thai,
        MaKH=kh.MaKH,
        MaNV=req.MaNV or "NV01"  # Nhân viên lập phiếu hoặc mặc định
    )
    db.add(new_pt)
    db.flush()

    # 7. Insert ChiTietPhieuThue
    new_ct = ChiTietPhieuThue(
        MaPhieuThue=ma_pt,
        STT=1,
        MaPhong=req.MaPhong,
        HinhThucThue=req.HinhThucThue,
        DonGiaApDung=don_gia,
        SoNguoiDuKien=req.SoNguoiDuKien,
        KhachDatCoOPhongNay=True,
        GioNhan=gio_nhan,
        GioTraDuKien=gio_tra,
        GioTra=None,
        GhiChu=req.GhiChu
    )
    db.add(new_ct)
    db.flush()

    # Cập nhật trạng thái phòng sang 'Đang thuê' để giữ chỗ
    phong.TinhTrang = "Đang thuê"

    # 8. Xử lý dịch vụ đi kèm nếu có (danh_sach_dich_vu)
    booked_services_out = []
    if req.danh_sach_dich_vu:
        for idx, item in enumerate(req.danh_sach_dich_vu):
            ma_dv = item.get_ma_dich_vu()
            sl = item.get_so_luong()
            if not ma_dv or sl <= 0:
                continue
            dv = db.query(DichVu).filter(DichVu.MaDichVu == ma_dv).first()
            if not dv:
                continue
            don_gia_dv = float(dv.DonGia)
            # Giờ bắt đầu dịch vụ mặc định = giờ nhận phòng, cộng thêm vài giây để tránh trùng PK nếu cùng lúc
            gio_bd_dv = gio_nhan + timedelta(seconds=idx)
            new_dv = DungDichVu(
                MaPhieuThue=ma_pt,
                STT=1,
                MaDichVu=ma_dv,
                GioBD=gio_bd_dv,
                GioKT=None,
                SoLuong=sl,
                DonGiaApDung=don_gia_dv
            )
            db.add(new_dv)
            booked_services_out.append(
                ChiTietDichVuHoaDon(
                    TenDichVu=dv.TenDichVu,
                    DonViTinh=dv.DonViTinh,
                    DonGia=don_gia_dv,
                    SoLuong=sl,
                    ThanhTien=round(don_gia_dv * sl)
                )
            )

    try:
        db.commit()
        db.refresh(new_pt)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Không thể lập phiếu thuê: {e.orig if hasattr(e, 'orig') else e}")

    sdt_kh = kh.so_dien_thoai[0].SDT if (kh.so_dien_thoai and len(kh.so_dien_thoai) > 0) else None

    return PhieuThueOut(
        MaPhieuThue=new_pt.MaPhieuThue,
        NgayLap=new_pt.NgayLap,
        TrangThai=new_pt.TrangThai,
        MaKH=new_pt.MaKH,
        TenKhachHang=kh.HoTen,
        SoDienThoai=sdt_kh,
        DiaChi=kh.DiaChi,
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
                GioTraDuKien=gio_tra
            )
        ],
        DichVu=booked_services_out
    )

@router.post("/khach-huy")
def cancel_rental_by_customer(req: KhachHuyDatPhongRequest, db: Session = Depends(get_db)):
    """API Hủy đặt phòng dành cho khách hàng tự hủy bằng Mã phiếu thuê và Số điện thoại"""
    ma_pt = req.MaPhieuThue.strip()
    phone = req.SoDienThoai.strip()

    pt = (
        db.query(PhieuThue)
        .options(
            joinedload(PhieuThue.khach_hang).joinedload(KhachHang.so_dien_thoai),
            joinedload(PhieuThue.chi_tiet).joinedload(ChiTietPhieuThue.phong)
        )
        .filter(PhieuThue.MaPhieuThue == ma_pt)
        .first()
    )
    if not pt:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy phiếu thuê {ma_pt}.")

    # Xác thực số điện thoại
    kh = pt.khach_hang
    phones = [s.SDT.strip() for s in kh.so_dien_thoai] if (kh and kh.so_dien_thoai) else []
    if phone not in phones:
        raise HTTPException(
            status_code=403,
            detail="Số điện thoại không khớp với thông tin khách hàng trên phiếu đặt."
        )

    # Chỉ cho hủy nếu đang ở trạng thái 'Đã đặt'
    if pt.TrangThai != "Đã đặt":
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ có thể hủy phiếu đang ở trạng thái 'Đã đặt'. Phiếu hiện tại đang là '{pt.TrangThai}'."
        )

    # 1. Cập nhật trạng thái phiếu thành 'Đã hủy'
    pt.TrangThai = "Đã hủy"

    # 2. Giải phóng các phòng về trạng thái 'Trống'
    for ct in pt.chi_tiet:
        p = ct.phong
        if p and p.TinhTrang in ["Đang thuê", "Đã đặt"]:
            p.TinhTrang = "Trống"

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Không thể hủy phiếu thuê: {e.orig if hasattr(e, 'orig') else e}")

    return {
        "success": True,
        "message": f"Hủy đặt phòng thành công cho phiếu {ma_pt}. Phòng đã được giải phóng sang trạng thái 'Trống'.",
        "MaPhieuThue": ma_pt,
        "TrangThai": "Đã hủy"
    }

@router.post("/tra-cuu")
def lookup_rental_by_customer(req: TraCuuDatPhongRequest, db: Session = Depends(get_db)):
    """API Tra cứu thông tin phiếu đặt phòng dành cho khách hàng"""
    ma_pt = req.MaPhieuThue.strip()
    phone = req.SoDienThoai.strip()

    pt = (
        db.query(PhieuThue)
        .options(
            joinedload(PhieuThue.khach_hang).joinedload(KhachHang.so_dien_thoai),
            joinedload(PhieuThue.chi_tiet).joinedload(ChiTietPhieuThue.phong).joinedload(Phong.loai_phong)
        )
        .filter(PhieuThue.MaPhieuThue == ma_pt)
        .first()
    )
    if not pt:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy phiếu thuê {ma_pt}.")

    kh = pt.khach_hang
    phones = [s.SDT.strip() for s in kh.so_dien_thoai] if (kh and kh.so_dien_thoai) else []
    if phone not in phones:
        raise HTTPException(
            status_code=403,
            detail="Số điện thoại không khớp với thông tin khách hàng trên phiếu đặt."
        )

    # Lấy dịch vụ đã đặt
    used_services = (
        db.query(DungDichVu)
        .options(joinedload(DungDichVu.dich_vu))
        .filter(DungDichVu.MaPhieuThue == ma_pt)
        .all()
    )
    services_list = []
    for us in used_services:
        dv = us.dich_vu
        dg = float(us.DonGiaApDung if us.DonGiaApDung is not None else (dv.DonGia if dv else 0))
        sl = int(us.SoLuong or 1)
        services_list.append({
            "TenDichVu": dv.TenDichVu if dv else us.MaDichVu,
            "DonViTinh": dv.DonViTinh if dv else "Lần",
            "DonGia": dg,
            "SoLuong": sl,
            "ThanhTien": round(dg * sl)
        })

    ct0 = pt.chi_tiet[0] if pt.chi_tiet else None
    room_info = None
    if ct0 and ct0.phong:
        room_info = {
            "SoPhong": ct0.phong.SoPhong,
            "TenLoai": ct0.phong.loai_phong.TenLoai if ct0.phong.loai_phong else "Tiêu chuẩn",
            "HinhThucThue": ct0.HinhThucThue,
            "DonGiaApDung": float(ct0.DonGiaApDung or 0),
            "GioNhan": ct0.GioNhan,
            "GioTraDuKien": ct0.GioTraDuKien,
            "GhiChu": ct0.GhiChu
        }

    return {
        "success": True,
        "MaPhieuThue": pt.MaPhieuThue,
        "NgayLap": pt.NgayLap,
        "TrangThai": pt.TrangThai,
        "KhachHang": {
            "HoTen": kh.HoTen if kh else "",
            "SDT": phone,
            "CCCD": kh.CCCD if kh else "",
            "DiaChi": kh.DiaChi if kh else ""
        },
        "Phong": room_info,
        "DichVu": services_list
    }

@router.post("/{ma_pt}/tra-phong")
def check_out_rental(ma_pt: str, db: Session = Depends(get_db)):
    pt = db.query(PhieuThue).options(joinedload(PhieuThue.chi_tiet)).filter(PhieuThue.MaPhieuThue == ma_pt).first()
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

@router.post("/{ma_pt}/nhan-phong")
def check_in_rental(ma_pt: str, db: Session = Depends(get_db)):
    """API Làm thủ tục Nhận phòng (Check-in) cho phiếu thuê đang ở trạng thái 'Đã đặt'"""
    pt = (
        db.query(PhieuThue)
        .options(
            joinedload(PhieuThue.chi_tiet).joinedload(ChiTietPhieuThue.phong),
            joinedload(PhieuThue.khach_hang)
        )
        .filter(PhieuThue.MaPhieuThue == ma_pt)
        .first()
    )
    if not pt:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy phiếu thuê {ma_pt}")

    if pt.TrangThai == "Đang thuê":
        raise HTTPException(status_code=400, detail=f"Phiếu thuê {ma_pt} đã được nhận phòng trước đó (đang ở trạng thái 'Đang thuê').")

    if pt.TrangThai in ["Hoàn tất", "Đã hủy"]:
        raise HTTPException(status_code=400, detail=f"Không thể nhận phòng cho phiếu đã ở trạng thái '{pt.TrangThai}'.")

    now = datetime.now()
    pt.TrangThai = "Đang thuê"

    # Cập nhật thời gian nhận phòng thực tế và đảm bảo các phòng ở trạng thái 'Đang thuê'
    for ct in pt.chi_tiet:
        ct.GioNhan = now
        p = ct.phong
        if p:
            p.TinhTrang = "Đang thuê"

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Không thể làm thủ tục nhận phòng: {e.orig if hasattr(e, 'orig') else e}")

    ten_kh = pt.khach_hang.HoTen if pt.khach_hang else "Khách hàng"
    so_phong = pt.chi_tiet[0].phong.SoPhong if (pt.chi_tiet and pt.chi_tiet[0].phong) else ""

    return {
        "success": True,
        "message": f"Làm thủ tục nhận phòng thành công cho khách hàng {ten_kh} (Phòng {so_phong}). Trạng thái phiếu đã chuyển sang 'Đang thuê'.",
        "MaPhieuThue": ma_pt,
        "TrangThai": "Đang thuê",
        "GioNhan": now
    }

@router.post("/{ma_pt}/huy")
def cancel_rental_by_admin(ma_pt: str, db: Session = Depends(get_db)):
    """API Hủy phiếu thuê/đặt phòng dành cho nhân viên quản trị"""
    pt = db.query(PhieuThue).options(joinedload(PhieuThue.chi_tiet).joinedload(ChiTietPhieuThue.phong)).filter(PhieuThue.MaPhieuThue == ma_pt).first()
    if not pt:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy phiếu thuê {ma_pt}")

    if pt.TrangThai in ["Hoàn tất", "Đã hủy"]:
        raise HTTPException(status_code=400, detail=f"Không thể hủy phiếu ở trạng thái: '{pt.TrangThai}'")

    pt.TrangThai = "Đã hủy"
    for ct in pt.chi_tiet:
        p = ct.phong
        if p and p.TinhTrang in ["Đang thuê", "Đã đặt"]:
            p.TinhTrang = "Trống"

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Không thể hủy phiếu thuê: {e.orig if hasattr(e, 'orig') else e}")

    return {"message": f"Đã hủy phiếu thuê {ma_pt} thành công. Phòng đã được trả về trạng thái 'Trống'."}

