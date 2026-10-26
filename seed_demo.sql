-- Dữ liệu mẫu để thầy mở web lên là thấy có dữ liệu (chỉ nạp một lần, khi CSDL còn trống).
DO $$
DECLARE hom DATE := (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date; v_lich INT; v_ma INT;
BEGIN
  IF EXISTS (SELECT 1 FROM CauHinh WHERE Khoa = 'demo_seeded') OR EXISTS (SELECT 1 FROM LichHen) THEN RETURN; END IF;
  v_lich := fn_luu_lich('TAI_NHE','42C-6677','RLNHB2T5X6M123401','Đức','0362555094','Isuzu',2021,2,2,hom,'07:30',NULL);
  PERFORM sp_LapPhieuKiemDinh(v_lich,'Không đạt','mino',
     ARRAY(SELECT MaTC FROM TieuChiKiemDinh WHERE MaLoai='TAI_NHE' ORDER BY MaTC),
     ARRAY[true,true,false,false,false]);
  PERFORM fn_luu_lich('TAI_NHE','51C-123.45','RLNHB2T5X6M123402','Nguyễn Văn An','0903123456','Hyundai',2022,1.9,2,hom+1,'08:00',NULL);
  PERFORM fn_luu_lich('TAI_NANG','29H-456.78','RLNHB2T5X6M123403','Trần Quốc Bảo','0912345678','Hino',2019,15,3,hom+1,'09:00',NULL);
  PERFORM fn_luu_lich('TAI_NANG','60C-987.65','RLNHB2T5X6M123404','Lê Thị Cúc','0987654321','Howo',2018,24,4,hom+2,'13:30',NULL);
  INSERT INTO CauHinh VALUES ('demo_seeded','1');
END $$;
