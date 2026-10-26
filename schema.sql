-- QUẢN LÝ ĐĂNG KIỂM XE: Đề 3.3 (Xe tải nhẹ) + Đề 3.4 (Xe tải nặng)
-- PostgreSQL (bản chuyển từ script SQL Server QuanLyDangKiem.sql, cùng 7 bảng và nghiệp vụ)
-- Chạy lặp lại nhiều lần vẫn an toàn.

CREATE TABLE IF NOT EXISTS LoaiPhuongTien(
  MaLoai VARCHAR(10) PRIMARY KEY,                 -- TAI_NHE / TAI_NANG
  TenLoai VARCHAR(50) NOT NULL,
  TaiTrongToiThieu NUMERIC(5,2) NOT NULL,         -- tấn
  TaiTrongToiDa NUMERIC(5,2) NOT NULL,
  PhiKiemDinh NUMERIC(12,0) NOT NULL,
  PhiGiayChungNhan NUMERIC(12,0) NOT NULL,
  ChuKyThang INT NOT NULL,
  SoTrucToiThieu INT NOT NULL,
  SoTrucToiDa INT NOT NULL
);
CREATE TABLE IF NOT EXISTS ChuXe(
  MaChuXe SERIAL PRIMARY KEY,
  HoTen VARCHAR(100) NOT NULL,
  SoDienThoai VARCHAR(11) NOT NULL CHECK (SoDienThoai LIKE '0%' AND LENGTH(SoDienThoai) BETWEEN 10 AND 11),
  DiaChi VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS PhuongTien(
  MaPT SERIAL PRIMARY KEY,
  BienSo VARCHAR(12) NOT NULL UNIQUE,
  SoKhung VARCHAR(17) NOT NULL UNIQUE CHECK (LENGTH(SoKhung)=17),
  MaLoai VARCHAR(10) NOT NULL REFERENCES LoaiPhuongTien(MaLoai),
  NhanHieu VARCHAR(50),
  NamSanXuat INT CHECK (NamSanXuat BETWEEN 1990 AND 2100),
  TaiTrong NUMERIC(5,2) NOT NULL,                 -- tấn
  SoTruc INT NOT NULL,
  MaChuXe INT NOT NULL REFERENCES ChuXe(MaChuXe)
);
CREATE TABLE IF NOT EXISTS LichHen(
  MaLich SERIAL PRIMARY KEY,
  MaPT INT NOT NULL REFERENCES PhuongTien(MaPT),
  NgayHen DATE NOT NULL,
  KhungGio VARCHAR(5) NOT NULL,                   -- 07:30, 08:00 ...
  TrangThai VARCHAR(20) NOT NULL DEFAULT 'Chờ kiểm'
     CHECK (TrangThai IN ('Chờ kiểm','Đang kiểm','Hoàn thành','Đã hủy')),
  GhiChu VARCHAR(200),
  CONSTRAINT UQ_Lich UNIQUE(NgayHen, KhungGio, MaPT)
);
CREATE TABLE IF NOT EXISTS TieuChiKiemDinh(
  MaTC SERIAL PRIMARY KEY,
  MaLoai VARCHAR(10) NOT NULL REFERENCES LoaiPhuongTien(MaLoai),
  TenTieuChi VARCHAR(150) NOT NULL,
  BatBuoc BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS PhieuKiemDinh(
  MaPhieu SERIAL PRIMARY KEY,
  MaLich INT NOT NULL UNIQUE REFERENCES LichHen(MaLich) ON DELETE CASCADE,
  NgayKiem TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'Asia/Ho_Chi_Minh'),
  KetQua VARCHAR(10) NOT NULL CHECK (KetQua IN ('Đạt','Không đạt')),
  TongPhi NUMERIC(12,0) NOT NULL,
  NgayHetHan DATE NULL,
  DangKiemVien VARCHAR(100)
);
CREATE TABLE IF NOT EXISTS ChiTietKiemDinh(
  MaPhieu INT NOT NULL REFERENCES PhieuKiemDinh(MaPhieu) ON DELETE CASCADE,
  MaTC INT NOT NULL REFERENCES TieuChiKiemDinh(MaTC),
  Dat BOOLEAN NOT NULL,
  GhiChu VARCHAR(200),
  PRIMARY KEY(MaPhieu, MaTC)
);
CREATE TABLE IF NOT EXISTS CauHinh(
  Khoa VARCHAR(50) PRIMARY KEY,
  GiaTri VARCHAR(200)
);

-- Dữ liệu danh mục
INSERT INTO LoaiPhuongTien VALUES
 ('TAI_NHE','Xe tải nhẹ',0.5,3.5,330000,90000,12,2,2),
 ('TAI_NANG','Xe tải nặng',3.51,40,560000,90000,6,2,6)
ON CONFLICT (MaLoai) DO NOTHING;

INSERT INTO TieuChiKiemDinh(MaLoai,TenTieuChi)
SELECT v.ml, v.tc FROM (VALUES
 ('TAI_NHE','Giấy tờ xe, bảo hiểm TNDS còn hạn'),
 ('TAI_NHE','Kiểm tra ngoại thất, thùng hàng'),
 ('TAI_NHE','Hệ thống phanh'),
 ('TAI_NHE','Hệ thống đèn, còi, gạt mưa'),
 ('TAI_NHE','Khí thải'),
 ('TAI_NANG','Giấy tờ xe, bảo hiểm TNDS còn hạn'),
 ('TAI_NANG','Kiểm tra khung gầm, thùng hàng, kích thước bao'),
 ('TAI_NANG','Phanh (kiểm tra theo từng trục)'),
 ('TAI_NANG','Tải trọng trục và tổng tải trọng'),
 ('TAI_NANG','Thiết bị giám sát hành trình'),
 ('TAI_NANG','Khí thải (động cơ diesel - độ khói)')) AS v(ml,tc)
WHERE NOT EXISTS (SELECT 1 FROM TieuChiKiemDinh);

-- Thêm hoặc sửa lịch hẹn kèm chủ xe và phương tiện (một giao dịch)
CREATE OR REPLACE FUNCTION fn_luu_lich(
  p_loai VARCHAR, p_bs VARCHAR, p_sk VARCHAR, p_cx VARCHAR, p_sd VARCHAR, p_nh VARCHAR,
  p_ns INT, p_tt NUMERIC, p_tr INT, p_ngay DATE, p_gio VARCHAR, p_edit INT)
RETURNS INT AS $$
DECLARE v_pt INT; v_cx INT; v_loai VARCHAR; v_lich INT;
BEGIN
  SELECT MaPT, MaChuXe, MaLoai INTO v_pt, v_cx, v_loai FROM PhuongTien WHERE BienSo = p_bs;
  IF FOUND THEN
    IF v_loai <> p_loai THEN RAISE EXCEPTION 'Biển số này đã đăng ký thuộc loại xe khác.'; END IF;
    UPDATE ChuXe SET HoTen = p_cx, SoDienThoai = p_sd WHERE MaChuXe = v_cx;
    UPDATE PhuongTien SET SoKhung = p_sk, NhanHieu = p_nh, NamSanXuat = p_ns, TaiTrong = p_tt, SoTruc = p_tr WHERE MaPT = v_pt;
  ELSE
    INSERT INTO ChuXe(HoTen, SoDienThoai) VALUES (p_cx, p_sd) RETURNING MaChuXe INTO v_cx;
    INSERT INTO PhuongTien(BienSo, SoKhung, NhanHieu, NamSanXuat, TaiTrong, SoTruc, MaLoai, MaChuXe)
      VALUES (p_bs, p_sk, p_nh, p_ns, p_tt, p_tr, p_loai, v_cx) RETURNING MaPT INTO v_pt;
  END IF;
  IF p_edit IS NULL THEN
    INSERT INTO LichHen(MaPT, NgayHen, KhungGio) VALUES (v_pt, p_ngay, p_gio) RETURNING MaLich INTO v_lich;
  ELSE
    UPDATE LichHen SET MaPT = v_pt, NgayHen = p_ngay, KhungGio = p_gio WHERE MaLich = p_edit;
    v_lich := p_edit;
  END IF;
  RETURN v_lich;
END; $$ LANGUAGE plpgsql;

-- Thủ tục: tính phí + ngày hết hạn + lưu phiếu kiểm định và chi tiết từng hạng mục
CREATE OR REPLACE FUNCTION sp_LapPhieuKiemDinh(
  p_lich INT, p_ketqua VARCHAR, p_dkv VARCHAR, p_tc INT[], p_dat BOOLEAN[])
RETURNS INT AS $$
DECLARE v_phi NUMERIC; v_giay NUMERIC; v_ky INT; v_ma INT; v_hom DATE;
BEGIN
  v_hom := (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date;
  SELECT l.PhiKiemDinh, l.PhiGiayChungNhan, l.ChuKyThang INTO v_phi, v_giay, v_ky
    FROM LichHen h JOIN PhuongTien p ON p.MaPT = h.MaPT
    JOIN LoaiPhuongTien l ON l.MaLoai = p.MaLoai WHERE h.MaLich = p_lich;
  INSERT INTO PhieuKiemDinh(MaLich, KetQua, TongPhi, NgayHetHan, DangKiemVien)
  VALUES (p_lich, p_ketqua,
          v_phi + CASE WHEN p_ketqua = 'Đạt' THEN v_giay ELSE 0 END,
          CASE WHEN p_ketqua = 'Đạt' THEN (v_hom + make_interval(months => v_ky))::date END,
          p_dkv)
  RETURNING MaPhieu INTO v_ma;
  INSERT INTO ChiTietKiemDinh(MaPhieu, MaTC, Dat)
    SELECT v_ma, t.tc, t.d FROM unnest(p_tc, p_dat) AS t(tc, d);
  UPDATE LichHen SET TrangThai = 'Hoàn thành' WHERE MaLich = p_lich;
  RETURN v_ma;
END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE VIEW vw_LichHen AS
SELECT h.MaLich, p.BienSo, l.TenLoai, c.HoTen, c.SoDienThoai, h.NgayHen, h.KhungGio, h.TrangThai
FROM LichHen h JOIN PhuongTien p ON p.MaPT = h.MaPT
JOIN LoaiPhuongTien l ON l.MaLoai = p.MaLoai JOIN ChuXe c ON c.MaChuXe = p.MaChuXe;
