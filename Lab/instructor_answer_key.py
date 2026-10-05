#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instructor_answer_key.py -- CHỈ DÀNH CHO GIẢNG VIÊN, KHÔNG PHÁT CHO HỌC VIÊN.

Sinh sẵn đáp án thật (cảm biến lỗi, loại lỗi) cho TOÀN BỘ danh sách lớp, một lần,
KHÔNG cần mở hay chạy từng bài nộp của học viên. Vì generate_mission_log() dùng
seed = hash(STUDENT_ID), đáp án hoàn toàn xác định (deterministic) chỉ từ ID --
ta tái dùng chính "quy luật" đó để tạo bảng tra cứu nhanh.

Cách dùng:
    python3 instructor_answer_key.py roster.txt answer_key.csv

roster.txt: mỗi dòng một STUDENT_ID (đúng chuỗi mà học viên đã/sẽ nhập trong notebook).
answer_key.csv: bảng tra cứu xuất ra -- GIỮ RIÊNG, không chia sẻ với lớp.
"""
import sys, csv, hashlib
import numpy as np


def seed_from_id(student_id: str) -> int:
    """Derive a reproducible personal random seed from a student ID.

    Args:
        student_id: The student's ID or name, as a string.

    Returns:
        int: A deterministic seed derived from the SHA-256 hash of the
        (lowercased, stripped) `student_id`. The same ID always yields the
        same seed; different IDs yield different (effectively random) seeds.
    """
    h = hashlib.sha256(student_id.strip().lower().encode()).hexdigest()
    return int(h[:8], 16)


def true_fault_only(student_id: str, T: float = 90.0):
    """Reconstruct just the hidden fault parameters for one student, fast.

    Mirrors the random-number consumption order of
    `generate_mission_log`/`_true_mission_path` in the lab notebook exactly
    (same seed, same sequence of `rng` calls) so the result is identical to
    calling `generate_mission_log(student_id, _reveal_truth=True)` -- but
    without generating the full trajectory or sensor measurements, which is
    unnecessary for grading and much slower across a whole class roster.

    Args:
        student_id: The student's ID or name, as declared in their notebook.
        T: Mission duration, in seconds. Must match the value used by the
            notebook's `generate_mission_log` call (default 90.0).

    Returns:
        dict: The true fault parameters for this student: `student_id`,
        `seed`, `fault_sensor`, `fault_type`, `bias_x`, `bias_y`,
        `noise_mult`, `burst_start`, `burst_len`.
    """
    rng = np.random.default_rng(seed_from_id(student_id))
    # Phải gọi rng theo ĐÚNG thứ tự như trong generate_mission_log() để seed khớp:
    # 1) số lượng waypoint, 2) toạ độ waypoint (bị bỏ qua ở đây nhưng vẫn phải "tiêu thụ" rng)
    n_wp = rng.integers(4, 7)
    rng.uniform(-40, 40, size=(n_wp, 2))
    fault_sensor = rng.choice(["GPS", "UWB"])
    fault_type = rng.choice(["bias", "underrated_noise", "outlier_burst"])
    bias_vec = rng.normal(0, 1.0, 2) * rng.choice([-1, 1], 2) * 2.5 if fault_type == "bias" else np.zeros(2)
    noise_mult = rng.uniform(2.5, 4.5) if fault_type == "underrated_noise" else 1.0
    burst_start = rng.uniform(25, T - 20)
    burst_len = rng.uniform(4, 9)
    return dict(student_id=student_id, seed=seed_from_id(student_id),
                fault_sensor=fault_sensor, fault_type=fault_type,
                bias_x=round(float(bias_vec[0]), 3), bias_y=round(float(bias_vec[1]), 3),
                noise_mult=round(float(noise_mult), 3),
                burst_start=round(float(burst_start), 1), burst_len=round(float(burst_len), 1))


def main():
    """Generate a bulk answer-key CSV for a class roster.

    Reads a roster file (one STUDENT_ID per line) from `sys.argv[1]`, and
    writes the true fault parameters for every student to the CSV path
    given in `sys.argv[2]`.

    Returns:
        None: Writes the answer key CSV to disk and prints a summary.
    """
    if len(sys.argv) != 3:
        print("Dùng: python3 instructor_answer_key.py roster.txt answer_key.csv")
        sys.exit(1)
    roster_path, out_path = sys.argv[1], sys.argv[2]
    with open(roster_path, encoding="utf-8") as f:
        ids = [line.strip() for line in f if line.strip()]

    rows = [true_fault_only(sid) for sid in ids]
    fields = ["student_id", "seed", "fault_sensor", "fault_type",
              "bias_x", "bias_y", "noise_mult", "burst_start", "burst_len"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Đã sinh đáp án cho {len(rows)} học viên -> {out_path}")
    from collections import Counter
    print("Phân bố cảm biến lỗi:", Counter(r["fault_sensor"] for r in rows))
    print("Phân bố loại lỗi:    ", Counter(r["fault_type"] for r in rows))


if __name__ == "__main__":
    main()
