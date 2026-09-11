#!/usr/bin/env python3
"""Profile DSH session transcripts into per-run step timings.

Each agent (including every workflow child) persists a zstd-compressed JSONL
event stream under $DSH_HOME/sessions/<cwd-slug>/<session-id>/. Events carry
millisecond timestamps, so step / tool / model latency can be reconstructed
exactly rather than self-reported by the model.

Usage:
  python3 profile_sessions.py                 # profile every session found
  python3 profile_sessions.py --since 23:00   # only sessions started after
Writes benchmark/data/session_profiles.json
"""
import glob, json, os, re, subprocess, sys, time

import config

SESS_ROOT = str(config.SESSIONS_DIR)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "session_profiles.json")


def read_events(path):
    try:
        raw = subprocess.run(["zstd", "-dc", path], capture_output=True, check=True).stdout
    except Exception:
        return []
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def profile(events, session_id, path):
    if not events:
        return None
    head = events[0]
    model = provider = None
    tasks = []
    steps = []            # {turn, step, start, end, ms}
    tools = []            # {turn, step, name, ms, ok}
    structured = None     # schema-validated final answer, if the run used one
    step_open = {}
    tool_open = {}
    turn_bounds = {}
    usage = {}
    images = 0
    started = head.get("createdAt")
    last = started

    for e in events:
        t, data = e.get("type"), e.get("data") or {}
        ts = e.get("time")
        if ts:
            last = ts
        if t == "request/header":
            cfg = (data.get("header") or {}).get("config") or {}
            provider, model = cfg.get("provider"), cfg.get("model")
        elif t == "model/selection":
            provider = data.get("provider") or provider
            model = data.get("model") or model
        elif t == "user/message":
            txt = text_of((data.get("message") or {}).get("content") or data.get("content"))
            src = (data.get("source") or {}).get("kind")
            if txt and src not in ("plugin",):
                tasks.append(txt)
            for block in (data.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "image":
                    images += 1
        elif t == "step/start":
            key = (data.get("turn"), data.get("step"))
            step_open[key] = ts
        elif t == "step/end":
            key = (data.get("turn"), data.get("step"))
            s = step_open.pop(key, None)
            steps.append({"turn": key[0], "step": key[1], "start": s, "end": ts,
                          "ms": (ts - s) if s else None})
        elif t == "tool/call":
            tool_open[data.get("callId")] = (data.get("name"), ts, data.get("turn"), data.get("step"))
            if data.get("name") == "structured_output":
                try:
                    structured = json.loads(data.get("arguments") or "{}")
                except json.JSONDecodeError:
                    structured = {"_unparsed": str(data.get("arguments"))[:200]}
        elif t == "tool/result":
            cid = ((data.get("message") or {}).get("source") or {}).get("callId")
            info = tool_open.pop(cid, None)
            if info:
                name, st, turn, step = info
                ok = "error" not in json.dumps(data.get("message") or {})[:400].lower()
                tools.append({"turn": turn, "step": step, "name": name,
                              "ms": (ts - st) if st else None, "ok": ok})
        elif t == "turn/start":
            turn_bounds.setdefault(data.get("turn"), {})["start"] = ts
        elif t == "turn/end":
            turn_bounds.setdefault(data.get("turn"), {})["end"] = ts
            turn_bounds[data.get("turn")]["reason"] = (data.get("reason") or {}).get("kind")
        elif t == "token-usage" or t == "session/usage":
            usage = data

    tool_ms = sum(t["ms"] or 0 for t in tools)
    step_ms = sum(s["ms"] or 0 for s in steps)
    task = tasks[0] if tasks else ""
    m = re.search(r"/(Q\d{2})\.png", task)
    return {
        "session_id": session_id,
        "path": path,
        "provider": provider,
        "model": model,
        "question": (int(m.group(1)[1:]) if m else None),
        "structured": structured,
        "answer": (structured or {}).get("answer"),
        "reason": (structured or {}).get("reason"),
        "confidence": (structured or {}).get("confidence"),
        "started_at": started,
        "ended_at": last,
        "wall_ms": (last - started) if started and last else None,
        "turns": len(turn_bounds),
        "steps": len(steps),
        "step_ms_sum": step_ms,
        "tool_calls": len(tools),
        "tool_ms_sum": tool_ms,
        "images": images,
        "first_task": (task[:400] if task else None),
        "step_detail": steps,
        "tool_detail": tools,
        "turn_detail": [{"turn": k, **v} for k, v in sorted(turn_bounds.items())],
        "usage": usage,
    }


def main():
    since = None
    if "--since" in sys.argv:
        since = sys.argv[sys.argv.index("--since") + 1]
    out = {}
    for path in sorted(glob.glob(os.path.join(SESS_ROOT, "*", "*", "session.v3.jsonl.zstd"))):
        session_id = os.path.basename(os.path.dirname(path))
        if since:
            mtime = time.strftime("%H:%M", time.localtime(os.path.getmtime(path)))
            if mtime < since:
                continue
        prof = profile(read_events(path), session_id, path)
        if prof:
            out[session_id] = prof
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"profiled {len(out)} sessions -> {OUT}")
    for sid, p in sorted(out.items(), key=lambda kv: kv[1]["started_at"] or 0):
        ts = time.strftime("%H:%M:%S", time.localtime((p["started_at"] or 0) / 1000))
        q = f"Q{p['question']:<2}" if p.get("question") else "  - "
        ans = p.get("answer") or "-"
        print(f"  {ts}  {str(p['model']):<34} {q} ans={str(ans):<3} steps={p['steps']:<3} tools={p['tool_calls']:<3} "
              f"wall={((p['wall_ms'] or 0)/1000):6.1f}s  {sid[:8]}")


if __name__ == "__main__":
    main()
