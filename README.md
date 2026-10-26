# Quản lý đăng kiểm xe tải: Java + SQL Server 2012

Giữ nguyên giao diện web cũ (`static/index.html`), phần chạy phía sau viết bằng Java (JDBC) nối SQL Server 2012.
Không cần Flask/Python/PostgreSQL nữa.

## Cấu trúc
- `src/model` (LoaiXe, LichHenForm), `src/dao` (câu lệnh SQL), `src/service` (nghiệp vụ, kiểm tra dữ liệu),
  `src/controller` (nhận /api/... trả JSON), `src/util` (DB, Json), `src/Main.java`
- `sql/QuanLyDangKiem_SQLServer2012.sql`: tạo CSDL + 7 bảng + danh mục + dữ liệu mẫu
- `db.properties`: host, port, user, password của SQL Server trên máy bạn

## Chạy
1. Mở SSMS, mở file `sql/QuanLyDangKiem_SQLServer2012.sql`, bấm Execute.
2. Sửa `db.properties` (user/password SQL Server của bạn).
3. IntelliJ: File > Open, chọn thư mục này. Có `pom.xml` nên IntelliJ tự tải driver `mssql-jdbc`
   (nếu không dùng Maven: tải mssql-jdbc-9.4.1.jre11.jar rồi File > Project Structure > Libraries > + > Java).
4. Chuột phải `src/Main.java` > Run. Trình duyệt tự mở http://localhost:8080.
   Working directory phải là thư mục gốc project (nơi có db.properties và static/).

## Nếu không kết nối được
- SQL Server Configuration Manager: bật TCP/IP, cổng 1433, rồi restart service.
- SSMS > Server Properties > Security: chọn "SQL Server and Windows Authentication mode"; user `sa` phải được bật và có mật khẩu.
- Lỗi "TLS10 is not accepted" hoặc "protocol version": do SQL Server 2012 cũ + JDK mới.
  Dùng driver 9.4.1 (đã đặt trong pom) và cập nhật SQL Server 2012 lên SP4, hoặc mở
  `<JDK>/conf/security/java.security`, xóa `TLSv1, TLSv1.1` khỏi dòng `jdk.tls.disabledAlgorithms`.
- Nếu bạn đã có CSDL QuanLyDangKiem từ bản Java Swing cũ: script dùng IF OBJECT_ID nên không ghi đè bảng cũ,
  nhưng tên cột phải khớp. Nếu lệch, đổi `database=` trong db.properties sang tên mới (vd. QuanLyDangKiem2)
  và sửa tên trong 2 dòng đầu của script.
