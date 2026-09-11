#!/usr/bin/env python3
"""Audit agent runs for honest image input.

The model's own claim ("I read the image") is not evidence: a model whose
read_image is gated off will happily fall back to bash + PIL/OCR, read other
agents' answer files, and then report success. This audit reads the transcript
instead and reports, per session:

  * every read_image call and whether it succeeded,
  * any tool call outside the allow-list (the OCR/peek side channels),
  * whether the run should be trusted as a genuine direct-image run.

Usage:
  python3 audit_image_runs.py [--since HH:MM] [--allow read_image,write]
"""
import glob, json, os, subprocess, sys, time

import config

SESS_ROOT = str(config.SESSIONS_DIR)
# tools a direct-image benchmark run is allowed to use
# structured_output is the harness mechanism for emitting a schema-validated
# answer, not a side channel.
DEFAULT_ALLOW = {"read_image", "write", "present", "todo_write", "ask_user_question",
                 "structured_output"}
# module-level so audit() can read it; main() may override from --allow
ALLOW = set(DEFAULT_ALLOW)


def events_of(path):
    raw = subprocess.run(["zstd", "-dc", path], capture_output=True, check=True).stdout
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def audit(events):
    model = None
    calls, image_reads, violations = {}, [], []
    open_calls = {}
    first_task = None
    depth = events[0].get("delegationDepth") if events else None
    for e in events:
        t, data = e.get("type"), e.get("data") or {}
        if t == "request/header":
            cfg = (data.get("header") or {}).get("config") or {}
            model = cfg.get("model") or model
        elif t == "user/message" and first_task is None:
            src = (data.get("source") or {}).get("kind")
            content = (data.get("message") or {}).get("content") or data.get("content")
            if src not in ("plugin",):
                if isinstance(content, str):
                    first_task = content
                elif isinstance(content, list):
                    txt = "".join(b.get("text", "") for b in content
                                  if isinstance(b, dict) and b.get("type") == "text")
                    if txt:
                        first_task = txt
        elif t == "tool/call":
            name = data.get("name")
            calls[name] = calls.get(name, 0) + 1
            open_calls[data.get("callId")] = (name, str(data.get("arguments"))[:200])
        elif t == "tool/result":
            cid = ((data.get("message") or {}).get("source") or {}).get("callId")
            name, args = open_calls.pop(cid, (None, None))
            msg = data.get("message") or {}
            body = json.dumps(msg, ensure_ascii=False)
            if name == "read_image":
                # NOTE: never test for the substring "Error" -- a successful
                # result carries "isError": false and would match it.
                failed = msg.get("isError") is True
                if "does not declare image input" in body or "Error: cannot read" in body:
                    failed = True
                image_reads.append({"ok": not failed, "args": args,
                                    "snippet": body[:200].replace("\\n", " ")})
            elif name not in ALLOW:
                violations.append({"tool": name, "args": args,
                                   "snippet": body[:160].replace("\\n", " ")})
    honest = bool(image_reads) and all(r["ok"] for r in image_reads) and not violations
    return {"model": model, "depth": depth, "first_task": (first_task or "")[:200],
            "tool_counts": calls, "image_reads": image_reads,
            "violations": violations, "honest_direct_image_run": honest}


def main():
    global ALLOW
    if "--allow" in sys.argv:
        ALLOW = set(sys.argv[sys.argv.index("--allow") + 1].split(","))
    since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else None

    rows, errors = {}, []
    for path in glob.glob(os.path.join(SESS_ROOT, "*", "*", "session.v3.jsonl.zstd")):
        sid = os.path.basename(os.path.dirname(path))
        if since and time.strftime("%H:%M", time.localtime(os.path.getmtime(path))) < since:
            continue
        try:
            r = audit(events_of(path))
        except Exception as exc:            # never swallow: a broken audit must be loud
            errors.append((sid, f"{type(exc).__name__}: {exc}"))
            continue
        # An "image run" is a session that actually attempted to read an image.
        # Sessions that only read a text dossier (e.g. the feedback rounds) are
        # not image runs and must not enter the honesty denominator.
        if r.get("image_reads"):
            if r.get("depth") == 0 and "--include-main" not in sys.argv:
                continue          # the orchestrator's own session is not a run
            rows[sid] = r
        elif r.get("violations") and "--include-nonimage" in sys.argv:
            rows[sid] = r

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "audit.json")
    prev = json.load(open(out)) if os.path.exists(out) else {}
    prev.update(rows)
    json.dump(prev, open(out, "w"), ensure_ascii=False, indent=2)

    print(f"{'verdict':<18} {'model':<38} reads(violations)  other tools")
    bad_runs = 0
    for sid, r in sorted(rows.items(), key=lambda kv: (kv[1].get("model") or "", kv[0])):
        ok = r.get("honest_direct_image_run")
        reads = r.get("image_reads") or []
        okreads = sum(1 for x in reads if x["ok"])
        bad = r.get("violations") or []
        other = ",".join(sorted({v["tool"] for v in bad})) or "-"
        verdict = "OK direct-image" if ok else ("CHEATED/INVALID" if bad or (reads and okreads == 0) else "no-image-call")
        if not ok:
            bad_runs += 1
        print(f"{verdict:<18} {str(r.get('model')):<38} {okreads}/{len(reads)} "
              f"({len(bad)})  {other}  {sid[:8]}")
        for v in bad[:3]:
            print(f"    └ {v['tool']}: {v['args'][:110]}")
    print(f"\n{len(rows)} image runs audited, {bad_runs} not honest, {len(errors)} unreadable -> {out}")
    for sid, err in errors[:5]:
        print(f"  !! {sid[:8]} {err}")


if __name__ == "__main__":
    main()
