#!/usr/bin/env python3
"""Build the clean, upload-ready export of this benchmark.

The working directory accumulates scratch files (probe smoke tests, per-model
dossiers, stray session audits). This script produces a curated copy that:

  * contains only the artefacts that belong to the published benchmark,
  * re-scopes `audit.json` and `session_profiles.json` to the sessions that
    actually belong to this benchmark (96 runs), so no unrelated DSH session
    content from the host machine leaks into the repository,
  * adds a machine-readable `timings.csv`,
  * writes a MANIFEST with sha256 for every file,
  * refuses to finish if a credential or an out-of-scope session is found.

Usage:
  python3 package.py [--out DIR] [--zip]
Defaults: --out ../dsh-vision-benchmark
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, *p)

# ---------------------------------------------------------------- include ----
INCLUDE = [
    "README.md", "requirements.txt", ".gitignore", "index.html",
    ".env.example", "config.py", "_config.yml",
    "docs/settings-dsh-input-declaration.md",
    "prompts/01-answer.md", "prompts/02-feedback-hinted.md",
    "prompts/03-feedback-clean.md", "prompts/04-judge.md", "prompts/05-readiness.md",
    "report.html",
    # 题卷
    "data/paper/blocks.json",
    "data/questions.json", "data/roster.json", "data/answer_key.json",
    # 结果
    "data/answers.json", "data/answers.md", "data/answers_preview.md",
    "data/feedback_summary.json", "data/judge_report.md",
    # 前期筛选（exploration）
    "data/all_models_raw.json", "data/all_model_ids.txt", "data/vision_models.json",
    "data/shortlist.json", "shortlist.md", "shortlist.html",
    "probes/probe_results.json", "probes/capability_test.png",
    # 脚本
    "probe_vision.py", "patch_settings_input.py", "profile_sessions.py",
    "audit_image_runs.py", "build_answers.py", "build_feedback.py",
    "make_report.py", "verify_report.py", "generate_shortlist.py",
    "generate_vision_catalog.py", "package.py",
]
PURPOSE = {
    "README.md": "总入口：结果速览、方法、复现步骤、效度局限",
    "index.html": "GitHub Pages 入口：自动跳转到 report.html",
    "report.html": "**最终网页报告**（逐题原图/答案矩阵/耗时热力图/折叠的裁判全文）",
    "requirements.txt": "Python 依赖",
    ".gitignore": "忽略凭证、缓存、可再生成的中间产物",
    "docs/settings-dsh-input-declaration.md": "为什么/如何为模型声明 input:[text,image]（DSH 图片闸门）",
    "prompts/01-answer.md": "作答阶段提示词（逐题独立会话）",
    "prompts/02-feedback-hinted.md": "反馈轮 v1（**已污染，作废**，保留以记录方法论错误）",
    "prompts/03-feedback-clean.md": "反馈轮 v2（有效版本）",
    "prompts/04-judge.md": "独立裁判提示词（含其看不见图的局限披露）",
    "prompts/05-readiness.md": "探针 / 闸门复验 / 题卷转录提示词",
    "data/paper/blocks.json": "行空白切分得到的 10 个题目纵向边界",
    "data/questions.json": "题目文本/选项/是否有配图（转录，供报告与核对）",
    "data/roster.json": "参赛名单（厂商、上下文、价格、闸门验证状态）",
    "data/answer_key.json": "官方答案 key + 出题方对 Q2/Q8 的澄清",
    "data/answers.json": "答案矩阵 8×10，含每题 session_id/耗时/步数（可追到转录）",
    "data/answers.md": "答案矩阵 Markdown 版",
    "data/answers_preview.md": "按题分组的 8 模型答案+理由对照（含分歧）",
    "data/feedback_summary.json": "两轮反馈轮结构化结果（立场/是否改判/原文）",
    "data/judge_report.md": "独立裁判报告原文",
    "data/audit.json": "诚实性审计（已收敛到本次 96 个会话）",
    "data/session_profiles.json": "逐步时序明细（已收敛到本次 96 个会话）",
    "data/timings.csv": "每次运行一行：模型/题号/答案/耗时/步数/是否诚实",
    "data/all_models_raw.json": "路由 /v1/models 原始元数据（205 个模型）",
    "data/all_model_ids.txt": "上者的模型 id 清单",
    "data/vision_models.json": "前期筛选：可发图模型清单（含探针实测结论）",
    "data/shortlist.json": "前期筛选：各厂商最新旗舰候选（含闸门/探针状态）",
    "shortlist.md": "候选清单 Markdown（含元数据误报案例）",
    "shortlist.html": "候选清单交互筛选页",
    "probes/probe_results.json": "直连 API 发图探针原始回包",
    "probes/capability_test.png": "探针图（红圆+绿方+CODE 7291）",
    "probe_vision.py": "直连 API 发图探针",
    "patch_settings_input.py": "为名单内模型声明 input:[text,image]（幂等/集合校验/备份）",
    "profile_sessions.py": "从 DSH 会话转录提取逐步时序与答案",
    "audit_image_runs.py": "诚实性审计：是否真 read_image、有无 OCR/偷看旁路",
    "build_answers.py": "从转录重建答案矩阵",
    "build_feedback.py": "从转录重建两轮反馈结果",
    "make_report.py": "生成 report.html（--embed 出图片内嵌单文件版，--out 指定输出名）",
    "verify_report.py": "校验报告中的数字仍与原始数据一致（防文档漂移）",
    "config.py": "集中配置：读取根目录 .env，并可回退到本机 DSH 自动探测",
    ".env.example": "配置模板（复制为 .env；.env 已被 .gitignore 忽略）",
    "_config.yml": "GitHub Pages/Jekyll 配置：强制包含 .env.example，避免站点上 404",
    "generate_shortlist.py": "生成前期候选清单（md/json/html）",
    "generate_vision_catalog.py": "生成可发图模型目录（需先跑探针）",
    "package.py": "打包本导出目录（会话范围收敛 + 清单 + 安全校验）",
    "evidence/gate/": "闸门复验原始回包（每个模型一份）",
}


def walk_files(root_dir):
    """Yield paths of real artefacts, never descending into .git."""
    for root, dirs, fns in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for fn in fns:
            yield os.path.join(root, fn)


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def scope_sessions():
    """Session ids belonging to this benchmark, with their phase."""
    answers = json.load(open(D("data", "answers.json")))["models"]
    fb = json.load(open(D("data", "feedback_summary.json")))["models"]
    scope = {}
    for model, rows in answers.items():
        for q, r in rows.items():
            if r.get("session_id"):
                scope[r["session_id"]] = {"phase": "answer", "model": model, "question": int(q)}
    for model, phases in fb.items():
        for phase, r in phases.items():
            if r.get("session_id"):
                scope[r["session_id"]] = {"phase": f"feedback-{phase}", "model": model, "question": None}
    return scope


def write_scoped(out, scope):
    """Re-scope audit + profiles (and add timings.csv) inside the export."""
    for name in ("audit.json", "session_profiles.json"):
        src = json.load(open(D("data", name)))
        kept = {sid: rec for sid, rec in src.items() if sid in scope}
        for sid, rec in kept.items():
            rec["benchmark_phase"] = scope[sid]["phase"]
        json.dump(kept, open(os.path.join(out, "data", name), "w"), ensure_ascii=False, indent=2)
        print(f"  scoped data/{name}: {len(kept)}/{len(src)} sessions kept")

    rows = []
    for sid, meta in sorted(scope.items(), key=lambda kv: (kv[1]["model"] or "", kv[1]["question"] or 0)):
        audit = json.load(open(os.path.join(out, "data", "audit.json"))).get(sid, {})
        prof = json.load(open(os.path.join(out, "data", "session_profiles.json"))).get(sid, {})
        tools = prof.get("tool_detail") or []
        read_ms = sum(t.get("ms") or 0 for t in tools if t.get("name") == "read_image")
        rows.append({
            "model": meta["model"], "question": meta["question"] or "",
            "phase": meta["phase"], "session_id": sid,
            "answer": prof.get("answer") or "", "confidence": prof.get("confidence") or "",
            "wall_ms": prof.get("wall_ms") or "", "steps": prof.get("steps") or "",
            "tool_calls": prof.get("tool_calls") or "", "read_image_ms": read_ms,
            "read_image_ok": sum(1 for r in (audit.get("image_reads") or []) if r.get("ok")),
            "honest": audit.get("honest_direct_image_run", ""),
            "violations": ";".join(sorted({v.get("tool") or "?" for v in (audit.get("violations") or [])})),
        })
    path = os.path.join(out, "data", "timings.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote data/timings.csv: {len(rows)} runs")


def security_scan(out, scope):
    """Fail loudly on credentials or out-of-scope session ids."""
    problems = []

    # Resolve the live key through config.py (.env → env → DSH), so the scanner
    # never hardcodes a credential file path or an account's variable name.
    try:
        import config as _cfg
        key = _cfg.get_api_key() or None
    except Exception:
        key = None

    for p in walk_files(out):
        if True:
            fn = os.path.basename(p)
            if os.path.getsize(p) > 6 << 20:
                continue
            try:
                blob = open(p, "rb").read().decode("utf-8", "ignore")
            except Exception:
                continue
            if key and key in blob:
                problems.append(f"凭证泄露: {os.path.relpath(p, out)}")
            for pat, label in [(r"sk-[A-Za-z0-9]{20,}", "看起来像 API key"),
                               (r"AIza[0-9A-Za-z_-]{30,}", "Google API key"),
                               (r"ghp_[A-Za-z0-9]{30,}", "GitHub token")]:
                if re.search(pat, blob):
                    problems.append(f"{label}: {os.path.relpath(p, out)}")

    # every session id present in the exported artifacts must be in scope
    for name in ("audit.json", "session_profiles.json", "answers.json", "feedback_summary.json"):
        p = os.path.join(out, "data", name)
        if not os.path.exists(p):
            continue
        blob = open(p, encoding="utf-8").read()
        for sid in set(re.findall(r"session-[0-9a-f-]{36}", blob)) | set(re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", blob)):
            if sid not in scope:
                problems.append(f"范围外会话出现在 data/{name}: {sid}")
    return sorted(set(problems))


def not_benchmark():
    """Fingerprints of unrelated host sessions that must never appear."""
    return ["dsh-web", "course-schedule", "课程表", "dsh-web-probe"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "dsh-vision-benchmark"))
    ap.add_argument("--zip", action="store_true")
    args = ap.parse_args()
    out = os.path.abspath(args.out)

    # Rebuild in place, but never destroy an existing git history.
    if os.path.exists(out):
        for entry in os.listdir(out):
            if entry == ".git":
                continue
            p = os.path.join(out, entry)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    else:
        os.makedirs(out)
    print(f"export -> {out}")

    scope = scope_sessions()
    print(f"benchmark sessions in scope: {len(scope)} "
          f"(answer={sum(1 for v in scope.values() if v['phase']=='answer')}, "
          f"feedback={sum(1 for v in scope.values() if v['phase'].startswith('feedback'))})")

    copied = []
    for rel in INCLUDE:
        src = D(rel)
        if not os.path.exists(src):
            print(f"  !! missing, skipped: {rel}")
            continue
        dst = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)

    # 题图 & 闸门证据（目录）
    for rel in sorted(os.listdir(D("data/paper/questions"))):
        s, d = D("data/paper/questions", rel), os.path.join(out, "data/paper/questions", rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        copied.append(f"data/paper/questions/{rel}")
    os.makedirs(os.path.join(out, "evidence/gate"), exist_ok=True)
    for src_dir, pat in ((D("data/gate"), None), (D("probes"), "gate_")):
        if not os.path.isdir(src_dir):
            continue
        for fn in sorted(os.listdir(src_dir)):
            if not fn.endswith(".json"):
                continue
            if pat and not fn.startswith(pat):
                continue
            if not (fn.startswith("gate_") or pat):
                continue
            shutil.copy2(os.path.join(src_dir, fn), os.path.join(out, "evidence/gate", fn))
            copied.append(f"evidence/gate/{fn}")

    write_scoped(out, scope)

    # ---- manifest
    lines = ["# MANIFEST", "",
             "本目录由 `package.py` 生成：只收录本次 benchmark 的产物，"
             "并把 `audit.json` / `session_profiles.json` 收敛到本次的 96 个会话"
             "（80 次作答 + 16 次反馈），避免宿主机上无关会话内容被一并上传。", "",
             "> 读 `audit.json` 时的口径：**80 次作答**全部通过「真实直读图」审计"
             "（`honest_direct_image_run: true`）；**16 次反馈轮**按设计只读取文本 dossier、"
             "不读图，因此它们的该字段为 `false` 属预期，不是作弊。"
             "每个会话都带 `benchmark_phase` 字段（`answer` / `feedback-hinted` / `feedback-clean`）。", "",
             "| 文件 | 大小 | sha256（前 16 位） | 用途 |", "|---|---:|---|---|"]
    files = []
    for p in walk_files(out):
        files.append(os.path.relpath(p, out))
    for rel in sorted(files):
        if rel == "MANIFEST.md":
            continue
        p = os.path.join(out, rel)
        size = os.path.getsize(p)
        pur = PURPOSE.get(rel)
        if pur is None:
            if rel.startswith("data/paper/questions/"):
                pur = "切分后的题图（发给模型的就是它）"
            elif rel.startswith("evidence/gate/"):
                pur = "闸门复验原始回包"
            else:
                pur = ""
        lines.append(f"| `{rel}` | {size/1024:.1f} KB | `{sha256(p)[:16]}` | {pur} |")
    total = sum(os.path.getsize(os.path.join(out, f)) for f in files)
    lines += ["", f"合计 {len(files)} 个文件，{total/1024/1024:.2f} MB。", ""]
    open(os.path.join(out, "MANIFEST.md"), "w").write("\n".join(lines))
    print(f"  wrote MANIFEST.md ({len(files)} files, {total/1024/1024:.2f} MB)")

    # ---- security
    problems = security_scan(out, scope)
    leak = []
    for p in walk_files(out):
        if True:
            fn = os.path.basename(p)
            if fn == "package.py":
                continue        # the scanner names these fingerprints itself
            if os.path.getsize(p) > 8 << 20:
                continue
            blob = open(p, "rb").read().decode("utf-8", "ignore")
            for fp in not_benchmark():
                if fp in blob:
                    leak.append(f"{os.path.relpath(p, out)}: 命中无关会话指纹 {fp!r}")
    problems += sorted(set(leak))

    print("\n=== 安全检查 ===")
    if problems:
        for p in problems[:20]:
            print("  ✗", p)
        print(f"  共 {len(problems)} 项，**未通过**：请先处理再上传。")
    else:
        print("  ✓ 未发现凭证明文")
        print("  ✓ 未发现范围外/无关会话内容")

    if args.zip:
        z = shutil.make_archive(out, "zip", out)
        print(f"\nzip -> {z} ({os.path.getsize(z)/1024/1024:.2f} MB)")

    print(f"\nexport ready: {out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
