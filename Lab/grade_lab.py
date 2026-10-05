#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grade_lab.py -- chấm điểm tự động hàng loạt cho kalman_fusion_lab (bản nộp của học viên).

Cách dùng:
    python3 grade_lab.py SUBMISSIONS_DIR/ [--key answer_key.csv] [--out gradesheet.csv] [--review-dir review/]

SUBMISSIONS_DIR/: thư mục chứa các file .ipynb học viên đã nộp (tên file tuỳ ý).
answer_key.csv (tuỳ chọn): xuất từ instructor_answer_key.py. Nếu một STUDENT_ID không có
    trong file này, script tự tính đáp án ngay tại chỗ (vẫn rất nhanh, không cần chạy lại
    toàn bộ quỹ đạo) -- không bắt buộc phải có answer_key.csv trước.

Quy trình cho MỖI bài nộp:
  1. Chạy toàn bộ notebook bằng một kernel sạch (timeout riêng từng bài).
  2. Nếu một cell lỗi (TODO chưa làm), dừng lại đúng chỗ đó -- mọi bài tập TRƯỚC đó vẫn
     được chấm điểm bình thường từ output đã có. Phần 8 nằm sau Phần 9, nên bỏ bonus
     không xóa điểm nhiệm vụ.
  3. Quét output: bài 5.1, 5.2, 6.1, 7.1 (50đ) và Phần 9 (30đ). Phần 1–4 không chấm.
  4. Trích ô markdown "✍️" (một báo cáo) ra file review để chấm 20 điểm tay.

Điểm tự động tối đa 80. Thưởng bài 8.1 ghi ở cột riêng, không cộng vào auto_subtotal.
Giảng viên chỉ đọc một báo cáo rồi điền tối đa 20 điểm. Tổng thưởng (8.1 hoặc thử thách)
không quá +5.
"""
import sys, os, re, csv, json, argparse, importlib.util
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("iak", os.path.join(HERE, "instructor_answer_key.py"))
iak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(iak)

# ---------------------------------------------------------------------------
# Auto points, max 80. Parts 1-4 are prefilled and are not graded.
# 5.1+5.2+6.1+7.1 = 50. Part 9 diagnosis + NIS + fix method = 30.
# ---------------------------------------------------------------------------
PART_A_MARKERS = [
    ("✅ Exercise 5.1 passed", 10.0, "5.1 make_F/make_H"),
    ("✅ Exercise 5.2 passed", 15.0, "5.2 KalmanFilter class"),
    ("✅ Exercise 6.1 passed", 15.0, "6.1 run_fusion"),
    ("✅ Exercise 7.1 passed", 10.0, "7.1 gated_update"),
]  # sums to exactly 50.0 -- keep in sync with the rubric table in the notebooks
BONUS_8_1_MARKER = ("✅ Exercise 8.1 passed", 4.0, "8.1 EKF Jacobian (bonus, not in the 80)")
PLACEHOLDER_ID = "nhap_ma_so_sinh_vien_hoac_ten_cua_ban"
METHOD_FOR_FAULT = {
    "bias": "bias",
    "underrated_noise": "inflate_R",
    "outlier_burst": "gate",
}

DIAG_STRUCT_MARKER = "✅ Đã ghi nhận chẩn đoán:"
DIAG_RE = re.compile(r"✅ Đã ghi nhận chẩn đoán:\s*([A-Z]+)\s*/\s*(\w+)")
FIX_RE = re.compile(r"✅ FIX_SENSOR=([A-Z]+) FIX_METHOD=([A-Za-z_]+)")
STUDENT_ID_RE = re.compile(r"Nhiệm vụ đã tạo cho '([^']+)'")
POOLED_NIS_MARKER = "✅ Bộ lọc chạy hợp lệ"
POOLED_NIS_RE = re.compile(r"[Pp]ooled mean NIS\s*=\s*(\d+\.?\d*)")


def cell_outputs_text(cell):
    """Concatenate all textual output of one executed notebook cell.

    Args:
        cell: An `nbformat` cell dict (after execution), with an
            `"outputs"` list.

    Returns:
        str: All stream text and text/plain rich output, concatenated in
        order.
    """
    txt = []
    for out in cell.get("outputs", []):
        if "text" in out:
            txt.append(out["text"])
        elif "data" in out and "text/plain" in out["data"]:
            t = out["data"]["text/plain"]
            txt.append(t if isinstance(t, str) else "".join(t))
    return "".join(txt)


def extract_markdown_answers(nb):
    """Collect every hand-written markdown answer cell, in order.

    Args:
        nb: A loaded `nbformat` notebook object.

    Returns:
        list: The raw markdown source of each "✍️" answer cell found, in
        the order they appear in the notebook -- for fast instructor review.
    """
    blocks = []
    for c in nb.cells:
        if c.cell_type == "markdown":
            src = "".join(c.get("source", []))
            if "✍️" in src:
                blocks.append(src.strip())
    return blocks


def grade_one(path, answer_key, timeout=240):
    """Execute and auto-grade one submitted student notebook.

    Runs the notebook end-to-end with a clean kernel, stopping gracefully
    at the first incomplete exercise (if any) while still crediting
    everything completed before that point. Scores exercises 5.1-7.1 from
    their printed "Exercise X.Y passed" markers, and Part 9 from the
    diagnosis labels, the FIX_SENSOR/FIX_METHOD line, and the NIS check.
    A placeholder STUDENT_ID zeros every Part 9 score. Bonus 8.1 is reported
    separately and is not included in `auto_subtotal`.

    Args:
        path: Filesystem path to the student's `.ipynb` submission.
        answer_key: List of dict rows (as loaded by `load_answer_key`),
            each with at least `student_id`, `fault_sensor`, `fault_type`.
            If a student's ID is not found here, the true fault is computed
            on the fly via `instructor_answer_key.true_fault_only`.
        timeout: Per-cell execution timeout, in seconds.

    Returns:
        dict: A grading record for this submission, including the
        extracted `student_id`, per-criterion auto-scores (max 80), the
        separate bonus flag, and the extracted report for the 20 manual points.
    """
    nb = nbformat.read(open(path, encoding="utf-8"), as_version=4)
    client = NotebookClient(nb, timeout=timeout, kernel_name="python3")
    exec_error = None
    try:
        client.execute()
    except CellExecutionError as e:
        exec_error = str(e).splitlines()[0] if str(e) else "unknown error"

    all_text = "\n".join(cell_outputs_text(c) for c in nb.cells if c.cell_type == "code")

    # --- Exercises 5.1-7.1 (50) ---
    part_a = 0.0
    part_a_detail = {}
    for marker, pts, label in PART_A_MARKERS:
        got = marker in all_text
        part_a += pts if got else 0.0
        part_a_detail[label] = pts if got else 0.0
    # Reported only. Do not add this to auto_subtotal; the instructor caps all bonuses at +5.
    bonus_81 = BONUS_8_1_MARKER[1] if BONUS_8_1_MARKER[0] in all_text else 0.0

    # --- STUDENT_ID ---
    m = STUDENT_ID_RE.search(all_text)
    student_id = m.group(1) if m else None
    placeholder = (not student_id) or student_id.strip().lower() == PLACEHOLDER_ID

    # --- 9.1 diagnosis (15 / 8 / 0) ---
    diag_struct_ok = DIAG_STRUCT_MARKER in all_text
    dm = DIAG_RE.search(all_text)
    declared_sensor, declared_type = (dm.group(1), dm.group(2)) if dm else (None, None)

    score_91 = 0.0
    truth_row = None
    if student_id and not placeholder:
        row = next((r for r in answer_key if r["student_id"] == student_id), None)
        truth_row = row if row else iak.true_fault_only(student_id)
    elif student_id and placeholder:
        truth_row = iak.true_fault_only(student_id)
    if not placeholder and diag_struct_ok and truth_row and declared_sensor and declared_type:
        if declared_sensor == truth_row["fault_sensor"] and declared_type == truth_row["fault_type"]:
            score_91 = 15.0
        elif declared_sensor == truth_row["fault_sensor"]:
            score_91 = 8.0  # right sensor, wrong fault type
        else:
            score_91 = 0.0

    # --- 9.2 method (7) and NIS (8), scored independently ---
    fm = FIX_RE.search(all_text)
    fix_sensor, fix_method = (fm.group(1), fm.group(2)) if fm else (None, None)
    expected_method = METHOD_FOR_FAULT.get(truth_row["fault_type"]) if truth_row else None
    score_92_method = 0.0
    if (not placeholder and truth_row and fix_sensor and fix_method
            and fix_sensor == truth_row["fault_sensor"] and fix_method == expected_method):
        score_92_method = 7.0

    score_92_nis = 8.0 if (not placeholder and POOLED_NIS_MARKER in all_text) else 0.0
    nm = POOLED_NIS_RE.search(all_text)
    pooled_nis = float(nm.group(1)) if nm else None
    sensor_lines = [
        ln for ln in all_text.splitlines()
        if (ln.startswith("GPS: ") or ln.startswith("UWB: ")) and "mean(NIS)" in ln
    ]

    auto_subtotal = part_a + score_91 + score_92_nis + score_92_method
    manual_remaining = 20.0

    return dict(
        file=os.path.basename(path),
        student_id=student_id or "??? (không trích được, kiểm tra tay)",
        placeholder_blocked=placeholder and bool(student_id),
        exec_error=exec_error or "",
        part_a_total=round(part_a, 1),
        part_a_detail=part_a_detail,
        bonus_8_1=bonus_81,
        diagnosis_ran=diag_struct_ok,
        declared_sensor=declared_sensor,
        declared_type=declared_type,
        truth_sensor=truth_row["fault_sensor"] if truth_row else None,
        truth_type=truth_row["fault_type"] if truth_row else None,
        score_9_1=score_91,
        fix_sensor=fix_sensor,
        fix_method=fix_method,
        expected_fix_method=expected_method,
        score_9_2_method=score_92_method,
        pooled_nis=pooled_nis,
        score_9_2_nis=score_92_nis,
        sensor_lines=sensor_lines or [],
        auto_subtotal=round(auto_subtotal, 1),
        manual_remaining_points=manual_remaining,
        written_answers=extract_markdown_answers(nb),
    )


def load_answer_key(path):
    """Load a pre-generated answer-key CSV, if one was provided.

    Args:
        path: Path to an `answer_key.csv` produced by
            `instructor_answer_key.py`, or None.

    Returns:
        list: A list of dict rows (one per student), or an empty list if
        `path` is None or does not exist.
    """
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    """Command-line entry point: grade every submission in a directory.

    Parses CLI arguments, loads the optional answer key, grades every
    `.ipynb` file in the submissions directory, writes a consolidated
    `gradesheet.csv`, and writes one per-student review Markdown file
    summarizing their hand-written answers for fast manual review.

    Returns:
        None: Writes `gradesheet.csv` and the review directory to disk, and
        prints a progress summary.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("submissions_dir")
    ap.add_argument("--key", default=None, help="answer_key.csv từ instructor_answer_key.py")
    ap.add_argument("--out", default="gradesheet.csv")
    ap.add_argument("--review-dir", default="review")
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    answer_key = load_answer_key(args.key)
    os.makedirs(args.review_dir, exist_ok=True)

    files = sorted(f for f in os.listdir(args.submissions_dir) if f.endswith(".ipynb"))
    if not files:
        print(f"Không tìm thấy file .ipynb nào trong {args.submissions_dir}")
        sys.exit(1)

    results = []
    for fn in files:
        path = os.path.join(args.submissions_dir, fn)
        print(f"Đang chấm: {fn} ...", end=" ", flush=True)
        try:
            r = grade_one(path, answer_key, timeout=args.timeout)
        except Exception as e:
            print(f"LỖI NGHIÊM TRỌNG: {e}")
            r = dict(file=fn, student_id="LỖI", placeholder_blocked=False, exec_error=str(e),
                      part_a_total=0, bonus_8_1=0, diagnosis_ran=False,
                      declared_sensor=None, declared_type=None,
                      truth_sensor=None, truth_type=None, score_9_1=0,
                      fix_sensor=None, fix_method=None, expected_fix_method=None,
                      score_9_2_method=0, pooled_nis=None, score_9_2_nis=0,
                      sensor_lines=[], auto_subtotal=0, manual_remaining_points=20,
                      written_answers=[], part_a_detail={})
        results.append(r)
        print(f"auto={r['auto_subtotal']} / 80 (ID: {r['student_id']})")

        # per-student review packet: one report, four checkboxes
        rp = os.path.join(args.review_dir, f"{os.path.splitext(fn)[0]}_review.md")
        with open(rp, "w", encoding="utf-8") as f:
            f.write(f"# Review nhanh: {fn}\n\n")
            f.write(f"**STUDENT_ID trích được:** {r['student_id']}\n\n")
            if r.get("placeholder_blocked"):
                f.write("**STUDENT_ID còn là câu mẫu.** Toàn bộ Phần 9 = 0 cho đến khi họ đổi ID.\n\n")
            if r["exec_error"]:
                f.write(f"**Notebook dừng giữa chừng tại lỗi:** `{r['exec_error']}`\n"
                        "(mọi bài tập sau điểm dừng này coi như chưa làm, điểm 0 cho phần đó)\n\n")
            f.write(f"**Bài 5–7 (tự động):** {r['part_a_total']}/50\n\n")
            f.write(f"**Chẩn đoán 9.1:** khai báo = {r['declared_sensor']}/{r['declared_type']}  "
                    f"| đáp án thật = {r['truth_sensor']}/{r['truth_type']}  "
                    f"| điểm = {r['score_9_1']}/15\n\n")
            f.write(f"**Cách sửa 9.2:** khai báo = {r['fix_sensor']}/{r['fix_method']}  "
                    f"| kỳ vọng = {r['truth_sensor']}/{r['expected_fix_method']}  "
                    f"| điểm = {r['score_9_2_method']}/7\n\n")
            f.write(f"**Pooled NIS:** {r['pooled_nis']}  | điểm NIS = {r['score_9_2_nis']}/8\n\n")
            f.write(f"**Thưởng 8.1 (không nằm trong 80):** {r['bonus_8_1']}/4. "
                    "Cộng thưởng tối đa +5 cho cả 8.1 và thử thách.\n\n")
            if r.get("sensor_lines"):
                f.write("**Số NIS học viên đã in (đối chiếu với báo cáo):**\n\n")
                for ln in r["sensor_lines"]:
                    f.write(f"- `{ln}`\n")
                f.write("\n")
            f.write("## Báo cáo — chấm tay, tối đa 20\n\n")
            f.write("- [ ] 5 — bằng chứng mean/median NIS và residual khớp các số in ở trên\n")
            f.write("- [ ] 5 — nói đúng cách sửa và vì sao hai cách kia không khớp\n")
            f.write("- [ ] 5 — có 1σ vị trí cuối, là số cụ thể\n")
            f.write("- [ ] 5 — một hạn chế hợp lý\n\n")
            f.write("Điểm tay = __ / 20\n\n")
            f.write("## Ô viết tay trích được\n\n")
            for block in r["written_answers"]:
                f.write(block + "\n\n---\n\n")
        r["review_file"] = rp

    fields = ["file", "student_id", "placeholder_blocked", "exec_error", "part_a_total", "bonus_8_1",
              "declared_sensor", "declared_type", "truth_sensor", "truth_type", "score_9_1",
              "fix_sensor", "fix_method", "expected_fix_method", "score_9_2_method",
              "pooled_nis", "score_9_2_nis",
              "auto_subtotal", "manual_remaining_points", "review_file"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fields})

    print(f"\nXong. Bảng điểm tự động: {args.out}")
    print(f"Gói review (một báo cáo / học viên): {args.review_dir}/")
    print("\nĐiểm cuối = auto_subtotal (tối đa 80) + điểm tay (tối đa 20) "
          "+ thưởng (tối đa 5, không nằm trong auto_subtotal).")


if __name__ == "__main__":
    main()
