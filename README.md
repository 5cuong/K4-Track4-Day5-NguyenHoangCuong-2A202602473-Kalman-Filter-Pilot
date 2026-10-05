# K4 · Track 4 · Ngày 5 — Kalman Filter Pilot

Bài lab 120 phút: từ số đo nhiễu đến một bộ theo dõi hợp nhất LiDAR, radar và camera, viết bằng NumPy. Buổi lab kết thúc bằng nhiệm vụ chẩn đoán cảm biến cho xe tự hành **Lynx-07**. Mỗi học viên nhận một quỹ đạo và một lỗi cảm biến riêng, sinh từ `STUDENT_ID`.

## Cấu trúc

| File | Ai dùng | Ghi chú |
|:--|:--|:--|
| `Lab/kalman_fusion_lab_STUDENT.ipynb` | Học viên | Notebook phát trên lớp |
| `Lab/kalman_fusion_lab_SOLUTIONS.ipynb` | Giảng viên | Lời giải bài 5–8. Không phát trước khi lab kết thúc |
| `Lab/instructor_answer_key.py` | Giảng viên | Sinh đáp án Phần 9 từ danh sách mã số |
| `Lab/grade_lab.py` | Giảng viên | Chấm tự động hàng loạt file nộp |
| `Lab/HUONG_DAN_CHAM_DIEM.md` | Giảng viên | Quy trình chấm chi tiết |

**Không phát** `instructor_answer_key.py`, `grade_lab.py`, và `HUONG_DAN_CHAM_DIEM.md` cho học viên.

## Yêu cầu

- Python 3.9+
- `numpy`, `matplotlib`, `scipy`
- Jupyter (laptop) hoặc Google Colab (upload file `.ipynb`)
- `ipywidgets` chỉ cho vài slider tùy chọn

Chấm tự động cần thêm `nbformat`, `nbclient`, và một kernel Jupyter tên `python3`.

```bash
pip install numpy matplotlib scipy jupyter ipywidgets nbformat nbclient
```

## Học viên

1. Mở `Lab/kalman_fusion_lab_STUDENT.ipynb`.
2. Chạy các cell từ trên xuống. Sau mỗi bài tập, chạy ô kiểm tra — dòng `✅ Exercise … passed` nghĩa là bài đó đúng.
3. Phần 1–4 đã điền sẵn: chạy và đọc, không chấm.
4. Tự viết bài **5.1, 5.2, 6.1, 7.1** (đang là `raise NotImplementedError`).
5. Ở Phần 9, đổi `STUDENT_ID` thành mã số hoặc tên của bạn, rồi đọc NIS, khai báo chẩn đoán, chọn một cách sửa, và viết một báo cáo.
6. Nộp file `.ipynb` đã chạy (có output).

Để nguyên câu mẫu `nhap_ma_so_sinh_vien_hoac_ten_cua_ban` thì toàn bộ Phần 9 = 0. Chép nhãn chẩn đoán của người khác không khớp dữ liệu của bạn.

### Lịch trong buổi (120 phút)

| Phút | Phần | Việc |
|--:|:--|:--|
| 5 | 0. Thiết lập | Chạy một lần |
| 25 | 1–3. Trung bình trượt → Kalman 1 chiều | Chạy code có sẵn, đọc nhận định. Không chấm |
| 10 | 4. NIS | Thấy NIS ≈ 1. Dùng lại ở Phần 9. Không chấm |
| 25 | 5. Kalman dạng ma trận | Tự code 5.1, 5.2 |
| 12 | 6. Hợp nhất LiDAR + radar + camera | Tự code 6.1 |
| 10 | 7. Outlier | Tự code 7.1 |
| 25 | 9. Nhiệm vụ Lynx-07 | Chẩn đoán, sửa, viết báo cáo |
| 8 | Đệm | Hỏi nếu kẹt |

Phần 8 (EKF) và các thử thách sau giờ nằm ngoài 120 phút. Thưởng tối đa **+5**.

## Thang điểm

Tổng **100**, cộng thưởng tối đa **+5** tách riêng.

**Tự code — 50 điểm** (đúng hết hoặc 0, không có điểm một phần):

| Bài | Điều kiện | Điểm |
|:--|:--|--:|
| 5.1 | `✅ Exercise 5.1 passed` | 10 |
| 5.2 | `✅ Exercise 5.2 passed` | 15 |
| 6.1 | `✅ Exercise 6.1 passed` | 15 |
| 7.1 | `✅ Exercise 7.1 passed` | 10 |

**Phần 9 — 30 điểm tự động + 20 điểm báo cáo:**

| Mục | Điều kiện | Điểm |
|:--|:--|--:|
| 9.1 | Đúng cảm biến và đúng loại lỗi | 15 |
| 9.1 một phần | Đúng cảm biến, sai loại lỗi | 8 |
| 9.2 NIS | Pooled mean NIS < 8 | 8 |
| 9.2 Cách sửa | `FIX_SENSOR` đúng cảm biến và `FIX_METHOD` đúng (`bias`, `inflate_R`, hoặc `gate`) | 7 |
| Báo cáo | Bằng chứng số, cách sửa, 1σ cuối, một hạn chế | 20 |

`auto_subtotal` tối đa **80**. Điểm cuối = `auto_subtotal` + điểm báo cáo (≤ 20) + thưởng (≤ 5).

## Giảng viên — chấm điểm

Chi tiết nằm trong [`Lab/HUONG_DAN_CHAM_DIEM.md`](Lab/HUONG_DAN_CHAM_DIEM.md). Tóm tắt:

```bash
cd Lab

# roster.txt: mỗi dòng một STUDENT_ID đúng chuỗi học viên khai trong notebook
python3 instructor_answer_key.py roster.txt answer_key.csv

# submissions/: các file .ipynb đã nộp
python3 grade_lab.py submissions/ --key answer_key.csv --out gradesheet.csv --review-dir review/
```

`grade_lab.py` chạy từng notebook bằng kernel sạch. Bài tập chưa làm (`NotImplementedError`) dừng đúng chỗ đó; mọi bài trước điểm dừng vẫn được chấm. Script ghi:

- `gradesheet.csv` — điểm tự động (tối đa 80) và cột thưởng 8.1
- `review/<tên_file>_review.md` — một báo cáo để chấm tay 20 điểm (bốn mục, mỗi mục 5)

Nếu một `STUDENT_ID` không có trong `answer_key.csv`, script vẫn tự tính đáp án tại chỗ. Giữ `answer_key.csv` riêng, không chia sẻ với lớp.
