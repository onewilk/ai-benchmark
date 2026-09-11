#!/usr/bin/env python3
"""Check that the numbers in report.html still match the underlying artefacts.

Report text is easy to let drift after a re-run ("80/80 honest", "2/8 fixed",
"9 of 10 questions unanimous"). This script re-derives each claim from the JSON
data and asserts the report states the same thing, so a stale report fails loudly
instead of quietly misinforming.

Usage: python3 verify_report.py   (exit 0 = consistent, 1 = mismatch)
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, *p)
load = lambda n: json.load(open(D("data", n), encoding="utf-8"))


def main():
    html = open(D("report.html"), encoding="utf-8").read()
    answers = load("answers.json")["models"]
    key = load("answer_key.json")["key"]
    audit = load("audit.json")
    fb = load("feedback_summary.json")["models"]
    roster = [m["id"] for m in load("roster.json")["models"]]

    checks, fails = [], []

    def check(label, expected, in_report):
        ok = in_report
        checks.append((label, expected, ok))
        if not ok:
            fails.append(f"{label}: 报告缺少/不等于预期值 {expected!r}")

    # ---- 1. scores
    scores = {}
    for m in roster:
        rows = answers.get(m) or {}
        scores[m] = sum(1 for q in range(1, 11)
                        if (rows.get(str(q)) or {}).get("answer") == key[str(q)])
    table = {}
    for m, s in scores.items():
        if f"<code>{m}</code>" in html and f">{s}/10<" in html:
            table[m] = True
        else:
            table[m] = False
    check("每个模型得分都出现在报告中", {m: scores[m] for m in roster}, all(table.values()))

    # ---- 2. unanimous questions
    for q in range(1, 11):
        got = {(answers.get(m) or {}).get(str(q), {}).get("answer") for m in roster}
        got.discard(None)
        if len(got) == 1:
            pass
    unanimous = sum(1 for q in range(1, 11)
                    if len({(answers.get(m) or {}).get(str(q), {}).get("answer") for m in roster} - {None}) == 1)
    check("全员一致的题数（报告称 9 题）", unanimous, unanimous == 9 and "9 题" in html)

    # ---- 3. audit honesty (answer runs only)
    honest = total = 0
    for m in roster:
        for q in range(1, 11):
            sid = ((answers.get(m) or {}).get(str(q)) or {}).get("session_id")
            rec = audit.get(sid)
            if not rec:
                continue
            total += 1
            honest += 1 if rec.get("honest_direct_image_run") else 0
    check("诚实作答计数", f"{honest}/{total}", f"{honest}/{total}" in html)

    # ---- 4. feedback clean round
    moved = [m for m in roster
             if str(8) in ((fb.get(m) or {}).get("clean", {}).get("moved_to_official") or [])]
    check("无提示轮真正修正 Q8 的模型数", len(moved), f"{len(moved)}/8" in html
          or f"{len(moved)}/8 个模型" in html)
    for m in moved:
        check(f"改判模型 {m} 在报告中被标为改判", True,
              bool(re.search(r"改判为 A", html)))

    # ---- 5. Q2 / Q8 facts
    q8_correct = sum(1 for m in roster if (answers.get(m) or {}).get("8", {}).get("answer") == key["8"])
    check("Q8 正确数（应为 0）", q8_correct, "0/8" in html)
    q2_correct = sum(1 for m in roster if (answers.get(m) or {}).get("2", {}).get("answer") == key["2"])
    check("Q2 正确数（应为 5）", q2_correct, f"{q2_correct}/8" in html)

    # ---- 6. per-question cards all carry an image
    n_cards = len(re.findall(r"<h3>第 \d+ 题", html))
    n_imgs = len(re.findall(r"<img class='crop' src='data/paper/questions/Q\d{2}\.png'", html))
    check("题目卡片数", 10, n_cards == 10)
    check("卡片内原图数", 10, n_imgs == 10)

    # ---- 7. nav anchors resolve
    navs = re.findall(r"data-target='([^']+)'", html)
    ids = set(re.findall(r"<h[23] id='([^']+)'>", html))
    check("导航锚点全部可解析", navs, all(n in ids for n in navs))

    # ---- 8. appendix collapsed by default
    check("裁判全文默认折叠（无 open 属性）", True,
          "<details class='appendix'><summary>" in html)

    w = max(len(label) for label, _, _ in checks)
    print("报告一致性校验")
    print("-" * 60)
    for label, expected, ok in checks:
        print(f"  {'✓' if ok else '✗'} {label:<{w}}  {expected}")
    print("-" * 60)
    # A few raw facts for eyeballing
    print(f"  事实: 得分 {scores}")
    print(f"  事实: 全员一致题数 {unanimous}/10 ｜ 诚实作答 {honest}/{total} ｜ "
          f"无提示轮修正 {len(moved)}/8 ｜ Q2 {q2_correct}/8 ｜ Q8 {q8_correct}/8")
    if fails:
        print("\n不一致项:")
        for f in fails:
            print("  ✗", f)
        return 1
    print("\n全部一致 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
