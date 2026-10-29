import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database import get_db
from backend.app.models import (
    HoaDon, PhieuThue, ChiTietPhieuThue, DungDichVu,
    KhachHang, LoaiKhachHang, NhanVien, Phong, LoaiPhong, DichVu, ThanhToan
)
from backend.app.schemas import HoaDonOut, ChiTietDichVuHoaDon

router = APIRouter(prefix="/hoa-don", tags=["Hóa Đơn & Thanh Toán"])

def calculate_room_charge(ct: ChiTietPhieuThue, pt_status: str):
    """Tính tiền phòng theo hình thức thuê chuẩn công thức fn_TinhTienPhongTheoHinhThuc trong CSDL"""
    gio_nhan = ct.GioNhan
    gio_tra = ct.GioTra

    # Nếu chưa có giờ trả thực tế:
    # Với phiếu đã hủy / đã hoàn tất / đã đặt: ưu tiên giờ trả dự kiến để không bị cộng dồn thời gian
    if not gio_tra:
        if pt_status in ["Đã hủy", "Hoàn tất", "Đã đặt"] or ct.GioTraDuKien:
            gio_tra = ct.GioTraDuKien or gio_nhan
        else:
            gio_tra = datetime.now()

    don_gia = float(ct.DonGiaApDung or 0)
    hinh_thuc = (ct.HinhThucThue or "Theo ngày").strip()

    if not gio_nhan or not gio_tra or gio_tra <= gio_nhan:
        if pt_status == "Đã hủy":
            return 0.0, "0 giờ", gio_tra
        return don_gia, "1 đơn vị", gio_tra

    diff_seconds = max(0.0, (gio_tra - gio_nhan).total_seconds())

    if hinh_thuc == "Theo giờ":
        minutes = diff_seconds / 60.0
        so_gio = max(1, math.ceil(minutes / 60.0))
        return don_gia * so_gio, f"{so_gio} giờ", gio_tra
    elif hinh_thuc == "Qua đêm":
        so_dem = max(1, math.ceil(diff_seconds / 86400.0))
        return don_gia * so_dem, f"{so_dem} đêm", gio_tra
    else:  # Theo ngày
        hours = diff_seconds / 3600.0
        so_ngay = max(1, math.ceil(hours / 24.0))
        return don_gia * so_ngay, f"{so_ngay} ngày", gio_tra

def build_rich_invoice_response(hd: HoaDon, pt: PhieuThue, db: Session) -> HoaDonOut:
    """Tạo đối tượng hóa đơn đầy đủ thông tin chi tiết khách, phòng, dịch vụ để hiển thị/in ấn đẹp mắt"""
    kh = pt.khach_hang if pt else None
    
    # 1. Thông tin khách
    cust_phone = ""
    if kh and hasattr(kh, "so_dien_thoai") and kh.so_dien_thoai:
        cust_phone = kh.so_dien_thoai[0].SDT if hasattr(kh.so_dien_thoai[0], "SDT") else str(kh.so_dien_thoai[0])

    phan_tram_uu_dai = 0.0
    ten_loai_kh = "Thường"
    if kh and kh.loai_khach_hang:
        phan_tram_uu_dai = float(kh.loai_khach_hang.PhanTramUuDai or 0)
        ten_loai_kh = kh.loai_khach_hang.TenLoai

    # 2. Thông tin phòng
    ct0 = pt.chi_tiet[0] if (pt and pt.chi_tiet) else None
    so_phong = ""
    ten_loai_phong = ""
    hinh_thuc_thue = ct0.HinhThucThue if ct0 else "Theo ngày"
    don_gia_ap_dung = float(ct0.DonGiaApDung) if ct0 else 0.0
    gio_nhan = ct0.GioNhan if ct0 else None
    thoi_gian_str = "1 ngày"
    gio_tra_final = None

    if ct0:
        p = db.query(Phong).filter(Phong.MaPhong == ct0.MaPhong).first()
        if p:
            so_phong = p.SoPhong
            lp = db.query(LoaiPhong).filter(LoaiPhong.MaLoaiPhong == p.MaLoaiPhong).first()
            if lp:
                ten_loai_phong = lp.TenLoai
        _, thoi_gian_str, gio_tra_final = calculate_room_charge(ct0, pt.TrangThai)

    # 3. Thông tin nhân viên lập
    nv = db.query(NhanVien).filter(NhanVien.MaNV == hd.MaNV).first()
    nv_name = f"{nv.HoTen} ({nv.ChucVu})" if nv else f"Nhân viên ({hd.MaNV})"

    # 4. Chi tiết dịch vụ đã dùng
    services_list = []
    if pt:
        used_services = db.query(DungDichVu).filter(DungDichVu.MaPhieuThue == pt.MaPhieuThue).all()
        for us in used_services:
            dv = db.query(DichVu).filter(DichVu.MaDichVu == us.MaDichVu).first()
            try:
                dg = float(us.DonGiaApDung if us.DonGiaApDung is not None else (dv.DonGia if dv else 0))
            except (ValueError, TypeError):
                dg = float(dv.DonGia if dv else 0)
            try:
                sl = int(us.SoLuong) if us.SoLuong is not None else 1
            except (ValueError, TypeError):
                sl = 1
            thanh_tien = round(dg * sl)
            services_list.append(
                ChiTietDichVuHoaDon(
                    TenDichVu=dv.TenDichVu if dv else us.MaDichVu,
                    DonViTinh=dv.DonViTinh if dv else "Lần",
                    DonGia=dg,
                    SoLuong=sl,
                    ThanhTien=thanh_tien
                )
            )

    tien_phong = float(hd.TienPhong or 0)
    tien_dv = float(hd.TienDichVu or 0)
    tien_phu_thu = float(hd.TienPhuThu or 0)
    uu_dai = float(hd.UuDai or 0)
    vat_rate = float(hd.TyLeVAT or 10.0)

    subtotal = max(0.0, tien_phong + tien_dv + tien_phu_thu - uu_dai)
    tong = round(subtotal + (subtotal * vat_rate / 100.0))

    return HoaDonOut(
        MaHD=hd.MaHD,
        MaPhieuThue=hd.MaPhieuThue,
        MaNV=hd.MaNV,
        NgayLap=hd.NgayLap,
        TienPhong=tien_phong,
        TienDichVu=tien_dv,
        TienPhuThu=tien_phu_thu,
        UuDai=uu_dai,
        TyLeVAT=vat_rate,
        TongTien=tong,
        TrangThai=hd.TrangThai,

        TenKhachHang=kh.HoTen if kh else (pt.TenKhachHang if hasattr(pt, "TenKhachHang") else None),
        SoDienThoai=cust_phone,
        CCCD=kh.CCCD if kh else None,
        DiaChi=kh.DiaChi if kh else None,
        TenLoaiKH=ten_loai_kh,
        PhanTramUuDai=phan_tram_uu_dai,
        SoPhong=so_phong,
        TenLoaiPhong=ten_loai_phong,
        HinhThucThue=hinh_thuc_thue,
        DonGiaApDung=don_gia_ap_dung,
        GioNhan=gio_nhan,
        GioTra=ct0.GioTra if (ct0 and ct0.GioTra) else gio_tra_final,
        ThoiGianThue=thoi_gian_str,
        NhanVienLap=nv_name,
        ChiTietDichVu=services_list
    )

@router.get("", response_model=List[HoaDonOut])
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(HoaDon).order_by(HoaDon.NgayLap.desc()).limit(50).all()
    results = []
    for h in invoices:
        pt = db.query(PhieuThue).filter(PhieuThue.MaPhieuThue == h.MaPhieuThue).first()
        results.append(build_rich_invoice_response(h, pt, db))
    return results

@router.post("/tao-hoa-don/{ma_pt}", response_model=HoaDonOut)
def generate_invoice(ma_pt: str, db: Session = Depends(get_db)):
    # 1. Kiểm tra phiếu thuê
    pt = db.query(PhieuThue).filter(PhieuThue.MaPhieuThue == ma_pt).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu thuê")

    # 2. Tính tiền phòng chuẩn xác theo loại hình thuê
    tien_phong = 0.0
    for ct in pt.chi_tiet:
        tien_ct, _, _ = calculate_room_charge(ct, pt.TrangThai)
        tien_phong += tien_ct

    # 3. Tính tiền dịch vụ
    tien_dich_vu = 0.0
    used_services = db.query(DungDichVu).filter(DungDichVu.MaPhieuThue == ma_pt).all()
    for s in used_services:
        try:
            s_dg = float(s.DonGiaApDung or 0)
        except (ValueError, TypeError):
            s_dg = 0.0
        try:
            s_sl = int(s.SoLuong) if s.SoLuong is not None else 1
        except (ValueError, TypeError):
            s_sl = 1
        tien_dich_vu += s_dg * s_sl

    # 4. Tính ưu đãi khách hàng
    kh = db.query(KhachHang).filter(KhachHang.MaKH == pt.MaKH).first()
    phan_tram_uu_dai = 0.0
    if kh and kh.loai_khach_hang:
        phan_tram_uu_dai = float(kh.loai_khach_hang.PhanTramUuDai or 0)
    uu_dai = round((tien_phong + tien_dich_vu) * phan_tram_uu_dai / 100.0)

    # 5. Kiểm tra hóa đơn đã tồn tại chưa
    hd_exist = db.query(HoaDon).filter(HoaDon.MaPhieuThue == ma_pt).first()
    if hd_exist:
        # Nếu chưa thanh toán, cập nhật lại số tiền theo công thức chuẩn đã sửa
        if hd_exist.TrangThai == "Chưa thanh toán":
            hd_exist.TienPhong = tien_phong
            hd_exist.TienDichVu = tien_dich_vu
            hd_exist.UuDai = uu_dai
            db.commit()
            db.refresh(hd_exist)
        return build_rich_invoice_response(hd_exist, pt, db)

    # 6. Sinh mã hóa đơn mới
    now = datetime.now()
    count_hd = db.query(HoaDon).count()
    ma_hd = f"HD{now.strftime('%y%m%d')}{count_hd + 1:03d}"
    while db.query(HoaDon).filter(HoaDon.MaHD == ma_hd).first():
        count_hd += 1
        ma_hd = f"HD{now.strftime('%y%m%d')}{count_hd:03d}"

    # Lấy mã nhân viên từ phiếu thuê hoặc NV01
    ma_nv = pt.MaNV or "NV01"

    new_hd = HoaDon(
        MaHD=ma_hd,
        MaPhieuThue=ma_pt,
        MaNV=ma_nv,
        NgayLap=now,
        TienPhong=tien_phong,
        TienDichVu=tien_dich_vu,
        TienPhuThu=0,
        UuDai=uu_dai,
        TyLeVAT=10,
        TrangThai="Chưa thanh toán"
    )
    db.add(new_hd)
    db.commit()
    db.refresh(new_hd)

    return build_rich_invoice_response(new_hd, pt, db)

@router.post("/{ma_hd}/thanh-toan")
def pay_invoice(ma_hd: str, db: Session = Depends(get_db)):
    hd = db.query(HoaDon).filter(HoaDon.MaHD == ma_hd).first()
    if not hd:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")

    if hd.TrangThai == "Đã thanh toán":
        return {"message": f"Hóa đơn {ma_hd} đã được thanh toán trước đó."}

    # Chuyển đổi an toàn các trường tiền sang float
    try:
        tp = float(hd.TienPhong or 0)
    except (ValueError, TypeError):
        tp = 0.0
    try:
        tdv = float(hd.TienDichVu or 0)
    except (ValueError, TypeError):
        tdv = 0.0
    try:
        tpt = float(hd.TienPhuThu or 0)
    except (ValueError, TypeError):
        tpt = 0.0
    try:
        ud = float(hd.UuDai or 0)
    except (ValueError, TypeError):
        ud = 0.0
    try:
        vat_rate = float(hd.TyLeVAT or 10)
    except (ValueError, TypeError):
        vat_rate = 10.0

    # 1. Tính đúng tổng tiền thực tế
    tien_goc = tp + tdv + tpt - ud
    vat = round(tien_goc * vat_rate / 100.0)
    tong_tien = round(tien_goc + vat)

    # 2. Kiểm tra số tiền đã thu trong bảng ThanhToan qua ORM (tương thích 100% PostgreSQL, MSSQL, SQLite)
    payments = db.query(ThanhToan).filter(ThanhToan.MaPhieuThue == hd.MaPhieuThue).all()
    da_thu = sum(
        -float(p.SoTien or 0) if p.LoaiKhoan == "Hoàn tiền" else float(p.SoTien or 0)
        for p in payments
    )

    can_thu = max(0, round(tong_tien - da_thu))

    # 3. Nếu chưa đủ tiền, tạo bản ghi ThanhToan mới (loại Thanh toán)
    if can_thu > 0:
        last_tt = db.query(ThanhToan.MaThanhToan).filter(ThanhToan.MaThanhToan.like("TTT%")).order_by(ThanhToan.MaThanhToan.desc()).first()
        max_val = last_tt[0] if last_tt else None
        num = 1
        if max_val and max_val.startswith("TTT"):
            try:
                num = int(max_val[3:]) + 1
            except ValueError:
                num = 1
        ma_tt = f"TTT{num:04d}"

        new_tt = ThanhToan(
            MaThanhToan=ma_tt,
            MaPhieuThue=hd.MaPhieuThue,
            MaNV=hd.MaNV or "NV01",
            NgayGioThanhToan=datetime.now(),
            PhuongThuc="Tiền mặt",
            SoTien=can_thu,
            LoaiKhoan="Thanh toán"
        )
        db.add(new_tt)

    # 4. Cập nhật trạng thái hóa đơn sang Đã thanh toán
    hd.TrangThai = "Đã thanh toán"

    # Nếu đang dùng SQLite fallback, cập nhật trực tiếp cột TongTien và TienVAT
    if db.bind and db.bind.dialect.name == "sqlite":
        try:
            vat_val = round(((hd.TienPhong or 0) + (hd.TienDichVu or 0) + (hd.TienPhuThu or 0) - (hd.UuDai or 0)) * float(hd.TyLeVAT or 10) / 100.0)
            db.execute(text("UPDATE HoaDon SET TongTien = :tong, TienVAT = :vat WHERE MaHD = :ma"), {
                'tong': tong_tien,
                'vat': vat_val,
                'ma': ma_hd
            })
        except Exception:
            pass

    # 5. Cập nhật phiếu thuê sang Hoàn tất nếu phiếu không bị hủy và tất cả phòng trong phiếu đã trả
    pt = db.query(PhieuThue).filter(PhieuThue.MaPhieuThue == hd.MaPhieuThue).first()
    if pt and pt.TrangThai != "Đã hủy" and all(ct.GioTra is not None for ct in pt.chi_tiet):
        pt.TrangThai = "Hoàn tất"

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Không thể thu tiền: {e.orig if hasattr(e, 'orig') else e}")

    return {"message": f"Hóa đơn {ma_hd} đã được thu tiền và thanh toán thành công!"}
