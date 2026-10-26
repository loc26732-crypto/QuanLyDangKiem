# Quản lý đăng kiểm xe tải – bản web Python + PostgreSQL

Đề 3.3 (xe tải nhẹ) và Đề 3.4 (xe tải nặng). Cùng nghiệp vụ, cùng giao diện với bản Java Swing/SQL Server,
nhưng chạy như một website: thầy mở link là dùng được, dữ liệu lưu thật trong PostgreSQL, máy của nhóm không cần bật.

## Cấu trúc
- `app.py`: Flask. Gồm các tầng dữ liệu, `LichHenService`, `KiemDinhService`, `ThongKeService` (tương ứng các lớp Java cùng tên) và các API `/api/...`.
- `schema.sql`: 7 bảng (LoaiPhuongTien, ChuXe, PhuongTien, LichHen, TieuChiKiemDinh, PhieuKiemDinh, ChiTietKiemDinh), khóa chính, khóa ngoại, ràng buộc CHECK/UNIQUE,
  hàm `sp_LapPhieuKiemDinh` (tính phí, ngày hết hạn, lưu phiếu), `fn_luu_lich` và view `vw_LichHen`. Chuyển từ `QuanLyDangKiem.sql` của SQL Server.
- `seed_demo.sql`: vài lịch hẹn mẫu, nạp một lần khi CSDL còn trống. Đặt biến `SEED_DEMO=0` nếu không muốn.
- `static/index.html`: giao diện (3 tab cho mỗi đề, xem phiếu, xuất CSV).

Khi chạy lần đầu, ứng dụng tự tạo bảng và nạp dữ liệu danh mục, không cần chạy SQL bằng tay.

## Cách 1: đưa lên mạng (khuyên dùng, miễn phí)
1. **Tạo CSDL PostgreSQL miễn phí tại [neon.tech](https://neon.tech):** tạo project, sao chép chuỗi kết nối (dạng `postgresql://user:pass@host/db?sslmode=require`).
2. **Đưa thư mục này lên GitHub** (một repo mới, chứa đúng các file trong thư mục này).
3. **Tạo dịch vụ tại [render.com](https://render.com):** New + → Blueprint (hoặc Web Service) → chọn repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
   - Environment: `DATABASE_URL` = chuỗi kết nối ở bước 1.
4. Chờ deploy xong, Render cấp một địa chỉ dạng `https://quan-ly-dang-kiem.onrender.com`. Gửi link này cho thầy.

Lưu ý: gói miễn phí của Render "ngủ" khi lâu không ai truy cập, lần mở đầu có thể chậm khoảng một phút. Nên mở thử trước khi thầy vào chấm.
Dịch vụ cụ thể và điều khoản miễn phí có thể thay đổi, bạn kiểm tra lại trên trang của họ. Các nền tảng khác (Railway, Fly.io, Koyeb...) cũng chạy được vì chỉ cần Python và biến `DATABASE_URL`.

## Cách 2: chạy trên máy
```
pip install -r requirements.txt
set DATABASE_URL=postgresql://postgres:matkhau@localhost:5432/dangkiem    (Windows: set, Linux/Mac: export)
python app.py
```
Tạo sẵn CSDL rỗng tên `dangkiem` trong PostgreSQL. Mở http://localhost:8080.

## Kiểm tra nhanh sau khi deploy
- `/healthz` trả về `ok` nghĩa là web đã nối được CSDL.
- Đăng ký một lịch hẹn, vào tab Xử lý đăng kiểm lập phiếu, rồi xem lại ở tab Thống kê. Dữ liệu giữ nguyên khi tải lại trang vì đã nằm trong PostgreSQL.
