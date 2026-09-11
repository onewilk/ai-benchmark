#!/usr/bin/env python3
"""Rebuild the answer matrix from session transcripts (authoritative source).

The model's structured answer, the question it answered, its wall-clock time,
step count and tool count all live in the transcript, so the matrix is rebuilt
from disk rather than transcribed by hand.

Usage: python3 build_answers.py
Writes benchmark/data/answers.json and benchmark/data/answers.md
"""
import json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.path.join(HERE, "data", "session_profiles.json")
ROSTER = os.path.join(HERE, "data", "roster.json")
OUT = os.path.join(HERE, "data", "answers.json")

# transcription / gate helper runs are not benchmark runs
IGNORE_MODELS = {"google/gemini-3.8-flash-transcribe"}


def main():
    profiles = json.load(open(PROFILES))
    roster = [m["id"] for m in json.load(open(ROSTER))["models"]]
    roster_set = set(roster)

    matrix = defaultdict(dict)
    for sid, p in profiles.items():
        model, q = p.get("model"), p.get("question")
        if model not in roster_set or not q:
            continue
        if p.get("answer") is None:      # gate / transcription style runs
            continue
        # keep the latest run per (model, question) if a re-run happened
        prev = matrix[model].get(q)
        if prev and (prev.get("started_at") or 0) >= (p.get("started_at") or 0):
            continue
        matrix[model][q] = {
            "answer": p["answer"], "reason": p.get("reason"),
            "confidence": p.get("confidence"), "session_id": sid,
            "wall_ms": p.get("wall_ms"), "steps": p.get("steps"),
            "tool_calls": p.get("tool_calls"), "images": p.get("images"),
        }

    out = {"models": {}, "generated_from": "session_profiles.json"}
    for m in roster:
        out["models"][m] = {str(q): matrix[m][q] for q in sorted(matrix[m])}
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)

    print(f"{'model':<34} " + " ".join(f"Q{q:<2}" for q in range(1, 11)) + "  answered")
    for m in roster:
        row = [matrix[m].get(q, {}).get("answer") or "-" for q in range(1, 11)]
        n = sum(1 for a in row if a != "-")
        print(f"{m:<34} " + "  ".join(f"{a:<2}" for a in row) + f"   {n}/10")

    # per-question disagreement
    print("\nper-question answers:")
    for q in range(1, 11):
        dist = defaultdict(list)
        for m in roster:
            a = matrix[m].get(q, {}).get("answer")
            if a:
                dist[a].append(m.split("/")[-1])
        summary = "  ".join(f"{k}:{len(v)}" for k, v in sorted(dist.items()))
        print(f"  Q{q:<3} {summary}")

    lines = ["# 原始答案矩阵（由转录自动重建）", "",
             "| 模型 | " + " | ".join(f"Q{q}" for q in range(1, 11)) + " | 作答数 |",
             "|---|" + "---|" * 11]
    for m in roster:
        row = [matrix[m].get(q, {}).get("answer") or "—" for q in range(1, 11)]
        n = sum(1 for a in row if a != "—")
        lines.append(f"| `{m}` | " + " | ".join(row) + f" | {n}/10 |")
    open(os.path.join(HERE, "data", "answers.md"), "w").write("\n".join(lines) + "\n")
    print(f"\nwrote {OUT} and data/answers.md")


if __name__ == "__main__":
    main()
