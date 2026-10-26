"""Quản lý đăng kiểm xe tải (Đề 3.3 xe tải nhẹ + Đề 3.4 xe tải nặng).

Web Flask + PostgreSQL. Cùng mô hình nhiều tầng với bản Java:
  - tầng truy cập dữ liệu: các hàm q()/call() và hàm SQL trong schema.sql
  - tầng nghiệp vụ: LichHenService, KiemDinhService, ThongKeService
  - tầng giao diện: static/index.html gọi các API /api/...
Chuỗi kết nối lấy từ biến môi trường DATABASE_URL.
"""
import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
from flask import Flask, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
VN = timezone(timedelta(hours=7))
GIO_HOP_LE = "07:30,08:00,08:30,09:00,09:30,10:00,13:30,14:00,14:30,15:00,15:30,16:00".split(",")

app = Flask(__name__, static_folder=os.path.join(BASE, "static"), static_url_path="/static")


class LoiNghiepVu(Exception):
    """Lỗi nghiệp vụ, thông báo hiển thị thẳng cho người dùng."""


# ---------------------------------------------------------------- tầng dữ liệu
def db_url():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("Chưa đặt biến môi trường DATABASE_URL (chuỗi kết nối PostgreSQL).")
    return url.replace("postgres://", "postgresql://", 1)


@contextmanager
def cursor():
    conn = psycopg2.connect(db_url())
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def q(sql, *params):
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def scalar(sql, *params):
    return q(sql, *params)[0][0]


def khoi_tao():
    """Tạo bảng, hàm, dữ liệu danh mục và dữ liệu mẫu nếu chưa có."""
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        schema = f.read()
    with cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(424242)")
        cur.execute(schema)
    if os.environ.get("SEED_DEMO", "1") != "0":
        with open(os.path.join(BASE, "seed_demo.sql"), encoding="utf-8") as f:
            seed = f.read()
        with cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(424242)")
            cur.execute(seed)


# ------------------------------------------------------------------ danh mục
def lay_loai(ma):
    r = q("SELECT MaLoai,TenLoai,TaiTrongToiThieu,TaiTrongToiDa,SoTrucToiThieu,SoTrucToiDa,"
          "PhiKiemDinh,PhiGiayChungNhan,ChuKyThang FROM LoaiPhuongTien WHERE MaLoai=%s", ma)
    if not r:
        raise LoiNghiepVu("Loại xe không tồn tại")
    x = r[0]
    return {"ma": x[0], "ten": x[1], "min": float(x[2]), "max": float(x[3]), "trucMin": x[4], "trucMax": x[5],
            "phi": float(x[6]), "giay": float(x[7]), "ky": x[8]}


def tieu_chi(ma):
    return [{"id": r[0], "ten": r[1]} for r in
            q("SELECT MaTC,TenTieuChi FROM TieuChiKiemDinh WHERE MaLoai=%s ORDER BY MaTC", ma)]


# ------------------------------------------------------------ nghiệp vụ lịch hẹn
def hom_nay():
    return datetime.now(VN).date()


def so(text):
    return float(text.strip().replace(",", "."))


def kiem_tra(loai, f):
    """f = [biển số, số khung, chủ xe, SĐT, nhãn hiệu, năm SX, tải trọng, số trục, ngày hẹn, giờ]."""
    f = [(x or "") for x in f]
    bs, sk = f[0].strip().upper(), f[1].strip().upper()
    if not re.fullmatch(r"\d{2}[A-Z]-\d{3,5}(\.\d{2})?", bs):
        raise LoiNghiepVu("Biển số dạng 51C-123.45 hoặc 51C-1234")
    if not re.fullmatch(r"[A-Z0-9]{17}", sk):
        raise LoiNghiepVu("Số khung gồm đủ 17 ký tự chữ và số")
    if not f[2].strip():
        raise LoiNghiepVu("Nhập họ tên chủ xe")
    if not re.fullmatch(r"0\d{9,10}", f[3].strip()):
        raise LoiNghiepVu("SĐT gồm 10–11 số, bắt đầu bằng 0")
    nam = hom_nay().year
    try:
        ns = int(f[5].strip())
        if ns < 1990 or ns > nam:
            raise ValueError
    except ValueError:
        raise LoiNghiepVu("Năm sản xuất từ 1990 đến %d" % nam)
    try:
        tt = so(f[6])
    except ValueError:
        raise LoiNghiepVu("Tải trọng phải là số")
    if tt < loai["min"] or tt > loai["max"]:
        raise LoiNghiepVu("Tải trọng %s phải từ %g đến %g tấn" % (loai["ten"].lower(), loai["min"], loai["max"]))
    try:
        tr = int(f[7].strip())
    except ValueError:
        raise LoiNghiepVu("Số trục phải là số nguyên")
    if tr < loai["trucMin"] or tr > loai["trucMax"]:
        raise LoiNghiepVu("Số trục phải từ %d đến %d" % (loai["trucMin"], loai["trucMax"]))
    try:
        ngay = datetime.strptime(f[8].strip(), "%d/%m/%Y").date()
    except ValueError:
        raise LoiNghiepVu("Ngày hẹn nhập dạng dd/MM/yyyy")
    if ngay < hom_nay():
        raise LoiNghiepVu("Ngày hẹn phải từ hôm nay trở đi")
    gio = f[9].strip()
    if gio not in GIO_HOP_LE:
        raise LoiNghiepVu("Khung giờ không hợp lệ")
    return dict(bs=bs, sk=sk, cx=f[2].strip(), sd=f[3].strip(), nh=f[4].strip(), ns=ns, tt=tt, tr=tr, ngay=ngay, gio=gio)


class LichHenService:
    def __init__(self, loai):
        self.loai = loai

    def danh_sach(self, kw):
        k = "%" + kw + "%"
        rows = q("SELECT h.MaLich,p.BienSo,c.HoTen,c.SoDienThoai,p.TaiTrong,to_char(h.NgayHen,'DD/MM/YYYY'),h.KhungGio,h.TrangThai "
                 "FROM LichHen h JOIN PhuongTien p ON p.MaPT=h.MaPT JOIN ChuXe c ON c.MaChuXe=p.MaChuXe "
                 "WHERE p.MaLoai=%s AND (p.BienSo ILIKE %s OR c.HoTen ILIKE %s) ORDER BY h.NgayHen DESC,h.KhungGio",
                 self.loai["ma"], k, k)
        return [[r[0], r[1], r[2], r[3], float(r[4]), r[5], r[6], r[7]] for r in rows]

    def chi_tiet(self, id_):
        rows = q("SELECT p.BienSo,p.SoKhung,c.HoTen,c.SoDienThoai,p.NhanHieu,p.NamSanXuat,p.TaiTrong,p.SoTruc,"
                 "to_char(h.NgayHen,'DD/MM/YYYY'),h.KhungGio,h.TrangThai FROM LichHen h "
                 "JOIN PhuongTien p ON p.MaPT=h.MaPT JOIN ChuXe c ON c.MaChuXe=p.MaChuXe "
                 "WHERE h.MaLich=%s AND p.MaLoai=%s", id_, self.loai["ma"])
        if not rows:
            raise LoiNghiepVu("Không tìm thấy lịch hẹn.")
        r = rows[0]
        return [r[0], r[1], r[2], r[3], r[4], r[5], float(r[6]), r[7], r[8], r[9], r[10]]

    def luu(self, raw, edit_id):
        v = kiem_tra(self.loai, raw)
        ex = edit_id or 0
        if scalar("SELECT COUNT(*) FROM LichHen WHERE NgayHen=%s AND KhungGio=%s AND TrangThai<>'Đã hủy' AND MaLich<>%s",
                  v["ngay"], v["gio"], ex) >= 2:
            raise LoiNghiepVu("Khung giờ này đã đủ 2 xe. Chọn giờ khác.")
        if scalar("SELECT COUNT(*) FROM LichHen h JOIN PhuongTien p ON p.MaPT=h.MaPT "
                  "WHERE p.BienSo=%s AND h.TrangThai='Chờ kiểm' AND h.MaLich<>%s", v["bs"], ex) > 0:
            raise LoiNghiepVu("Xe này đã có lịch hẹn đang chờ kiểm.")
        if scalar("SELECT COUNT(*) FROM PhuongTien WHERE BienSo=%s AND MaLoai<>%s", v["bs"], self.loai["ma"]) > 0:
            raise LoiNghiepVu("Biển số này đã đăng ký thuộc loại xe khác.")
        if scalar("SELECT COUNT(*) FROM PhuongTien WHERE SoKhung=%s AND BienSo<>%s", v["sk"], v["bs"]) > 0:
            raise LoiNghiepVu("Số khung này đã thuộc một xe khác.")
        if edit_id and scalar("SELECT COUNT(*) FROM LichHen WHERE MaLich=%s AND TrangThai='Chờ kiểm'", edit_id) == 0:
            raise LoiNghiepVu("Chỉ sửa được lịch đang chờ kiểm.")
        try:
            q("SELECT fn_luu_lich(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", self.loai["ma"], v["bs"], v["sk"], v["cx"],
              v["sd"], v["nh"], v["ns"], v["tt"], v["tr"], v["ngay"], v["gio"], edit_id)
        except psycopg2.Error as e:
            raise LoiNghiepVu(thong_bao_csdl(e))

    def huy(self, id_):
        if scalar("SELECT COUNT(*) FROM LichHen WHERE MaLich=%s AND TrangThai='Chờ kiểm'", id_) == 0:
            raise LoiNghiepVu("Chỉ hủy được lịch đang chờ kiểm.")
        q("UPDATE LichHen SET TrangThai='Đã hủy' WHERE MaLich=%s RETURNING MaLich", id_)

    def xoa(self, id_):
        if scalar("SELECT COUNT(*) FROM LichHen WHERE MaLich=%s AND TrangThai='Hoàn thành'", id_) > 0:
            raise LoiNghiepVu("Không xóa được lịch đã có phiếu kiểm định.")
        q("DELETE FROM LichHen WHERE MaLich=%s RETURNING MaLich", id_)


def thong_bao_csdl(e):
    text = str(e).strip().splitlines()[0] if str(e).strip() else "Lỗi cơ sở dữ liệu"
    if "duplicate key" in text or "violates unique" in text:
        return "Dữ liệu bị trùng với bản ghi đã có (biển số hoặc số khung)."
    return text.replace("ERROR:", "").strip()


# ---------------------------------------------------------- nghiệp vụ đăng kiểm
class KiemDinhService:
    def __init__(self, loai):
        self.loai = loai

    def dang_cho(self):
        rows = q("SELECT h.MaLich,p.BienSo,c.HoTen,to_char(h.NgayHen,'DD/MM/YYYY'),h.KhungGio FROM LichHen h "
                 "JOIN PhuongTien p ON p.MaPT=h.MaPT JOIN ChuXe c ON c.MaChuXe=p.MaChuXe "
                 "WHERE p.MaLoai=%s AND h.TrangThai='Chờ kiểm' ORDER BY h.NgayHen,h.KhungGio", self.loai["ma"])
        return [{"id": r[0], "text": "%s · %s · %s %s" % (r[1], r[2], r[3], r[4])} for r in rows]

    def lap(self, lich_id, dkv, kq):
        if not lich_id:
            raise LoiNghiepVu("Chọn xe cần kiểm định.")
        if not dkv.strip():
            raise LoiNghiepVu("Nhập tên đăng kiểm viên.")
        if scalar("SELECT COUNT(*) FROM LichHen h JOIN PhuongTien p ON p.MaPT=h.MaPT "
                  "WHERE h.MaLich=%s AND p.MaLoai=%s AND h.TrangThai='Chờ kiểm'", lich_id, self.loai["ma"]) == 0:
            raise LoiNghiepVu("Lịch hẹn này không còn ở trạng thái chờ kiểm.")
        tcs = [t["id"] for t in tieu_chi(self.loai["ma"])]
        if len(kq) != len(tcs):
            raise LoiNghiepVu("Số hạng mục chấm không khớp với loại xe.")
        dat = all(kq)
        return scalar("SELECT sp_LapPhieuKiemDinh(%s,%s,%s,%s,%s)", lich_id, "Đạt" if dat else "Không đạt",
                      dkv.strip(), tcs, kq)


# ------------------------------------------------------------------- thống kê
class ThongKeService:
    def __init__(self, loai):
        self.loai = loai

    def lich_su(self):
        rows = q("SELECT k.MaPhieu,p.BienSo,c.HoTen,c.SoDienThoai,to_char(k.NgayKiem,'DD/MM/YYYY'),k.KetQua,k.TongPhi,"
                 "COALESCE(to_char(k.NgayHetHan,'DD/MM/YYYY'),'—'),k.DangKiemVien "
                 "FROM PhieuKiemDinh k JOIN LichHen h ON h.MaLich=k.MaLich JOIN PhuongTien p ON p.MaPT=h.MaPT "
                 "JOIN ChuXe c ON c.MaChuXe=p.MaChuXe WHERE p.MaLoai=%s ORDER BY k.MaPhieu DESC", self.loai["ma"])
        return [{"ma": r[0], "bs": r[1], "cx": r[2], "sd": r[3], "ngay": r[4], "kq": r[5], "phi": float(r[6]),
                 "het": r[7], "dkv": r[8]} for r in rows]

    def thong_ke(self, ls):
        ma = self.loai["ma"]
        dat = sum(1 for p in ls if p["kq"] == "Đạt")
        cho = scalar("SELECT COUNT(*) FROM LichHen h JOIN PhuongTien p ON p.MaPT=h.MaPT "
                     "WHERE p.MaLoai=%s AND h.TrangThai='Chờ kiểm'", ma)
        sap = scalar("SELECT COUNT(*) FROM PhieuKiemDinh k JOIN LichHen h ON h.MaLich=k.MaLich "
                     "JOIN PhuongTien p ON p.MaPT=h.MaPT WHERE p.MaLoai=%s AND k.KetQua='Đạt' "
                     "AND k.NgayHetHan BETWEEN %s AND %s", ma, hom_nay(), hom_nay() + timedelta(days=30))
        return {"cho": cho, "dat": dat, "khongDat": len(ls) - dat, "doanhThu": sum(p["phi"] for p in ls), "sapHan": sap}

    def chi_tiet(self, id_):
        return [[r[0], r[1]] for r in
                q("SELECT t.TenTieuChi,d.Dat FROM ChiTietKiemDinh d JOIN TieuChiKiemDinh t ON t.MaTC=d.MaTC "
                  "WHERE d.MaPhieu=%s ORDER BY t.MaTC", id_)]


# ------------------------------------------------------------------------ API
def so_nguyen(name, default=0):
    try:
        return int(request.values.get(name, default))
    except (TypeError, ValueError):
        return default


@app.route("/api/<kind>/<ma>", methods=["GET", "POST"])
@app.route("/api/<kind>/<ma>/<action>", methods=["GET", "POST"])
def api(kind, ma, action=""):
    try:
        loai = lay_loai(ma)
        p = request.values
        if kind == "loai":
            return jsonify({"loai": loai, "tieuChi": tieu_chi(ma)})
        if kind == "lich":
            sv = LichHenService(loai)
            if action == "chitiet":
                return jsonify(sv.chi_tiet(so_nguyen("id")))
            if action == "huy":
                sv.huy(so_nguyen("id"))
                return jsonify({})
            if action == "xoa":
                sv.xoa(so_nguyen("id"))
                return jsonify({})
            if action == "luu":
                sv.luu([p.get("f%d" % i, "") for i in range(10)], so_nguyen("id") or None)
                return jsonify({})
            return jsonify(sv.danh_sach(p.get("q", "")))
        if kind == "cho":
            return jsonify(KiemDinhService(loai).dang_cho())
        if kind == "kiem":
            kq = [x == "1" for x in p.get("kq", "").split(",")]
            return jsonify({"ma": KiemDinhService(loai).lap(so_nguyen("lichId"), p.get("dkv", ""), kq)})
        if kind == "tk":
            sv = ThongKeService(loai)
            ls = sv.lich_su()
            return jsonify({"stats": sv.thong_ke(ls), "phieu": ls})
        if kind == "phieu":
            return jsonify(ThongKeService(loai).chi_tiet(so_nguyen("id")))
        raise LoiNghiepVu("API không tồn tại: " + kind)
    except LoiNghiepVu as e:
        return jsonify({"error": str(e)}), 400
    except psycopg2.Error as e:
        app.logger.exception("Lỗi cơ sở dữ liệu")
        return jsonify({"error": "Lỗi cơ sở dữ liệu: " + thong_bao_csdl(e)}), 500


@app.route("/healthz")
def healthz():
    scalar("SELECT 1")
    return "ok"


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


_san_sang = False


@app.before_request
def dam_bao_khoi_tao():
    global _san_sang
    if not _san_sang:
        khoi_tao()
        _san_sang = True


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
