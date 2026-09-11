#!/usr/bin/env python3
"""Build the phase-2 (post-feedback) analysis from transcripts.

Two feedback passes were run:
  hinted — the dossier included a note saying the official key was wrong on Q8
  clean  — the dossier carried no note and no list of differences

Both are extracted from the session transcripts, not copied by hand.

Usage: python3 build_feedback.py
Writes benchmark/data/feedback_summary.json and prints the comparison.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.path.join(HERE, "data", "session_profiles.json")
ANSWERS = os.path.join(HERE, "data", "answers.json")
KEY = os.path.join(HERE, "data", "answer_key.json")
OUT = os.path.join(HERE, "data", "feedback_summary.json")


def main():
    profiles = json.load(open(PROFILES))
    original = json.load(open(ANSWERS))["models"]
    key = json.load(open(KEY))["key"]

    runs = {}
    for sid, p in profiles.items():
        st = p.get("structured")
        if not isinstance(st, dict) or "feedback" not in st:
            continue
        task = p.get("first_task") or ""
        phase = "clean" if "feedback_clean" in task else "hinted"
        model = p.get("model")
        runs[(model, phase)] = {
            "session_id": sid,
            "differing_questions": st.get("differing_questions"),
            "feedback": st.get("feedback"),
            "final_answers": {f["q"]: f["answer"] for f in st.get("final_answers") or []},
            "overall": st.get("overall"),
        }

    roster = [m["id"] for m in json.load(open(os.path.join(HERE, "data", "roster.json")))["models"]]
    summary = {}
    for m in roster:
        row = {}
        for phase in ("hinted", "clean"):
            r = runs.get((m, phase))
            if not r:
                continue
            stances = {f["q"]: f["stance"] for f in r["feedback"] or []}
            final = r["final_answers"]
            # did the model move to the official answer on a question it got wrong?
            moved, held = [], []
            for q, a in final.items():
                if q not in key:
                    continue
                before = (original[m].get(q) or {}).get("answer")
                if before and before != key[q]:
                    (moved if a == key[q] else held).append(q)
            row[phase] = {
                "stances": stances, "moved_to_official": moved, "held_wrong": held,
                "feedback": r["feedback"],
                "final_answers": final, "overall": r["overall"],
                "session_id": r["session_id"],
            }
        summary[m] = row

    json.dump({"key": key, "models": summary}, open(OUT, "w"), ensure_ascii=False, indent=2)

    print(f"{'model':<34} {'hinted Q8':<12} {'clean Q8':<12} {'clean Q2':<12}")
    for m in roster:
        row = summary[m]
        def cell(phase, q):
            r = row.get(phase)
            if not r:
                return "-"
            s = r["stances"].get(q)
            if s is None:
                return "n/a"           # answered correctly in round 1
            moved = q in r["moved_to_official"]
            return f"{s}{'/改判' if moved else '/坚持'}"
        print(f"{m:<34} {cell('hinted','8'):<12} {cell('clean','8'):<12} {cell('clean','2'):<12}")

    print("\n无提示(clean)轮：对 Q8 的立场统计")
    for m in roster:
        r = summary[m].get("clean")
        if not r:
            continue
        s = r["stances"].get("8")
        if s is None:
            continue
        moved = "8" in r["moved_to_official"]
        print(f"  {m.split('/')[-1]:<24} {s:<9} {'→ 改判为官方 A' if moved else '→ 坚持自己的 B'}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
