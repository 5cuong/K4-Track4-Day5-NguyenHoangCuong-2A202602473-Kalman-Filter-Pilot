# Hướng dẫn chấm điểm nhanh — Bài Lab Kalman Filter (Phần 9: Nhiệm vụ thật)

Dành cho giảng viên/trợ giảng. Hai file công cụ nằm cùng thư mục với notebook:
`instructor_answer_key.py` và `grade_lab.py`. **Không phát hai file này cho học viên.**

## Vì sao dữ liệu "giấu được" dù chạy trên máy học viên

Bài lab chạy hoàn toàn offline trên máy học viên (không có server), nên không thể giấu
tuyệt đối — một học viên đọc kỹ code vẫn có thể tự suy ra đáp án. Thiết kế ở đây nhắm tới
**"đủ khó để không đáng bõ công, và dễ phát hiện nếu có"**, thay vì an toàn tuyệt đối:

- Mỗi học viên có **quỹ đạo và lỗi cảm biến khác nhau**, sinh ra từ `hash(STUDENT_ID)`
  (SHA-256) — cùng một hàm, cùng một "quy luật", nhưng khác mã số thì ra khác kết quả.
  Vì vậy **chép đáp số của người khác sẽ không khớp dữ liệu của chính mình**.
- Giảng viên có thể tái tạo đáp án thật **cực nhanh, không cần chạy notebook của học
  viên** — chỉ cần biết `STUDENT_ID` họ khai (xem mục 1 bên dưới).
- Nếu muốn an toàn hơn nữa (không một dòng code đáp án nào lọt tới máy học viên), xem
  mục "Nâng cấp" ở cuối tài liệu này.

## 1. Sinh đáp án cho cả lớp — một lần, trước khi chấm (vài giây)

```bash
# roster.txt: mỗi dòng một STUDENT_ID (đúng chuỗi học viên khai trong notebook)
python3 instructor_answer_key.py roster.txt answer_key.csv
```

Ra ngay một bảng `answer_key.csv` với `fault_sensor`, `fault_type` thật của **từng**
học viên trong lớp — không cần mở notebook nào cả. Giữ file này riêng, không chia sẻ.

## 2. Chấm hàng loạt bài nộp

```bash
# submissions/: thư mục chứa toàn bộ file .ipynb học viên đã nộp
python3 grade_lab.py submissions/ --key answer_key.csv --out gradesheet.csv --review-dir review/
```

Script sẽ, với **mỗi** bài nộp:
1. Chạy notebook bằng kernel sạch. Nếu học viên chưa làm xong một bài tập (`NotImplementedError`),
   nó dừng đúng chỗ đó — mọi bài tập **trước** điểm dừng vẫn được chấm điểm bình thường.
   Phần 8 nằm sau nhiệm vụ, nên học viên bỏ bonus vẫn được chấm Phần 9.
2. Tự động cộng bài 5.1 (10), 5.2 (15), 6.1 (15), 7.1 (10). Phần 1–4 đã điền sẵn, không chấm.
3. Trích `STUDENT_ID`. Nếu còn nguyên câu mẫu `nhap_ma_so_sinh_vien_hoac_ten_cua_ban`,
   toàn bộ Phần 9 = 0.
4. Đối chiếu chẩn đoán với `answer_key.csv`: đúng cảm biến và loại lỗi = 15, đúng cảm biến
   sai loại = 8, sai cảm biến = 0.
5. Đối chiếu `FIX_SENSOR` / `FIX_METHOD` (`bias`, `inflate_R`, `gate`) với đáp án thật = 7,
   và cộng 8 nếu ô kiểm tra báo pooled mean NIS < 8.
6. Trích một ô báo cáo (dấu ✍️) vào `review/<ten_file>_review.md`, kèm bốn ô tick 5 điểm.

`auto_subtotal` tối đa **80**. `bonus_8_1` là cột riêng (0 hoặc 4), không nằm trong 80.
`manual_remaining_points` là **20** (một báo cáo).

**Điểm cuối cùng = `auto_subtotal` + điểm báo cáo (≤ 20) + thưởng (≤ 5).**
Thưởng là bài 8.1 hoặc thử thách sau giờ, cộng lại không quá 5, kể cả khi cột `bonus_8_1` là 4.

## 3. Chấm báo cáo (một màn hình, trong `review/*.md`)

Bốn mục, mỗi mục 5 điểm. File review đã in sẵn đáp án thật, `FIX_*`, pooled NIS, và các dòng
`GPS:` / `UWB:` mà học viên in ra.

- Bằng chứng: mean/median NIS và residual trong báo cáo khớp đúng những dòng đó.
- Cách sửa: nói đúng `bias` / `inflate_R` / `gate` trên đúng cảm biến, và loại được hai cách kia.
- 1σ cuối: có một số mét lấy từ `P`, không phải câu chữ chung chung.
- Hạn chế: một tình huống mà cách sửa này thất bại (lỗi đổi theo thời gian, cả hai cảm biến cùng lỗi, ...).

Số trong báo cáo không khớp dòng NIS đã in là dấu hiệu chép bài. Hỏi lại học viên đó.

## Nâng cấp (tuỳ chọn): giấu đáp án triệt để hơn

Thiết kế hiện tại ("một notebook chung, dữ liệu theo quy luật từ mã số") là lựa chọn cân
bằng giữa bảo mật và sự tiện lợi khi phát bài. Nếu muốn an toàn gần như tuyệt đối (không
một dòng code sinh lỗi/đáp án nào tồn tại trên máy học viên), có thể nâng cấp bằng cách:
phát sẵn cho mỗi học viên một file dữ liệu `.npz` (sinh trước bởi giảng viên, không chứa
code), notebook học viên chỉ đọc file đó thay vì tự sinh dữ liệu. Cách này an toàn hơn
nhưng cần thêm một bước vận hành (cần danh sách mã số trước, phát file riêng từng người
qua LMS/email). Nếu muốn đi hướng này, nhắn lại để triển khai thêm.
