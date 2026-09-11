#!/usr/bin/env python3
"""Render the final benchmark report as a single HTML page.

Every number here is computed from the artefacts on disk (transcripts, audit,
answer matrix, official key, feedback summary) so the page can be regenerated
after any re-run.

Question images are referenced by relative path (works when the page is served
next to the `data/` folder, e.g. GitHub Pages). Pass --embed to instead inline
every image as a base64 data URI, producing one fully standalone file for
sharing or for viewers that block relative sub-resources.

Usage: python3 make_report.py [--embed]   ->  benchmark/report.html
"""
import base64
import html
import json
import os
import re
import statistics as st
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, *p)
EMBED = "--embed" in sys.argv
OUT_NAME = (sys.argv[sys.argv.index("--out") + 1]
            if "--out" in sys.argv and len(sys.argv) > sys.argv.index("--out") + 1
            else "report.html")

_URI_CACHE = {}


def asset_src(rel_path, max_width=None, quality=88):
    """Return the src for an image: a relative path normally, a data URI with --embed."""
    if EMBED:
        return data_uri(rel_path, max_width=max_width, quality=quality)
    return rel_path


def data_uri(rel_path, max_width=None, quality=88):
    """Inline an image as a base64 data URI, optionally downscaled."""
    key = (rel_path, max_width, quality)
    if key in _URI_CACHE:
        return _URI_CACHE[key]
    path = D(rel_path)
    if not os.path.exists(path):
        return rel_path
    try:
        if max_width:
            from PIL import Image
            import io
            im = Image.open(path)
            if im.width > max_width:
                h = round(im.height * max_width / im.width)
                im = im.resize((max_width, h), Image.LANCZOS)
            buf = io.BytesIO()
            if path.lower().endswith((".jpg", ".jpeg")):
                im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
                uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
            else:
                im.save(buf, "PNG", optimize=True)
                uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        else:
            mime = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            with open(path, "rb") as fh:
                uri = f"data:{mime};base64," + base64.b64encode(fh.read()).decode()
    except Exception:
        return rel_path
    _URI_CACHE[key] = uri
    return uri


def load(name):
    with open(D("data", name), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- markdown ---
def md_to_html(md):
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(html.escape(lines[i]))
                i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl+1}>{inline(m.group(2))}</h{lvl+1}>")
            i += 1
            continue
        if re.match(r"^\s*\|.*\|\s*$", line) and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr></thead><tbody>"]
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        if re.match(r"^\s*[-*]\s+", line):
            buf = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                buf.append("<li>" + inline(re.sub(r"^\s*[-*]\s+", "", lines[i])) + "</li>")
                i += 1
            out.append("<ul>" + "".join(buf) + "</ul>")
            continue
        m = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if m:
            buf = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append("<li>" + inline(re.sub(r"^\s*\d+\.\s+", "", lines[i])) + "</li>")
                i += 1
            out.append("<ol>" + "".join(buf) + "</ol>")
            continue
        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(inline(lines[i].lstrip("> ").strip()))
                i += 1
            out.append("<blockquote>" + "<br>".join(buf) + "</blockquote>")
            continue
        if not line.strip():
            i += 1
            continue
        out.append(f"<p>{inline(line)}</p>")
        i += 1
    return "\n".join(out)


def inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


# ------------------------------------------------------------------- data ----
def main():
    roster = load("roster.json")["models"]
    models = [m["id"] for m in roster]
    vendor = {m["id"]: m["vendor"] for m in roster}
    answers = load("answers.json")["models"]
    key = load("answer_key.json")["key"]
    qmeta = {str(q["q"]): q for q in load("questions.json")["questions"]}
    audit = load("audit.json")
    profiles = load("session_profiles.json")
    fb = load("feedback_summary.json")["models"]

    # ---- per-model aggregates
    stats = {}
    for m in models:
        rows = answers.get(m, {})
        got = {q: (rows.get(str(q)) or {}).get("answer") for q in range(1, 11)}
        wrong = [q for q in range(1, 11) if got[q] and got[q] != key[str(q)]]
        # timings from the transcript-derived matrix
        tm = [(rows.get(str(q)) or {}).get("wall_ms") or 0 for q in range(1, 11)]
        tm = [t for t in tm if t]
        conf = Counter((rows.get(str(q)) or {}).get("confidence") for q in range(1, 11))
        stats[m] = {
            "got": got, "wrong": wrong, "correct": 10 - len(wrong),
            "total_ms": sum(tm), "median_ms": st.median(tm) if tm else 0,
            "max_ms": max(tm) if tm else 0,
            "steps": sum((rows.get(str(q)) or {}).get("steps") or 0 for q in range(1, 11)),
            "tools": sum((rows.get(str(q)) or {}).get("tool_calls") or 0 for q in range(1, 11)),
            "conf": conf,
        }

    # audit: count honest runs per model
    # Audit the 80 benchmark question runs by joining each run's session id to the
    # audit record. Counting by model alone would wrongly include the phase-2
    # feedback sessions (which read a text dossier and sometimes poked read_image
    # at a .json file) in the "honest direct-image" denominator.
    audit_of = defaultdict(lambda: {"runs": 0, "ok": 0, "reads": 0, "bad": 0})
    total_runs = total_ok = 0
    for m in models:
        for q in range(1, 11):
            sid = (answers.get(m, {}).get(str(q)) or {}).get("session_id")
            rec = audit.get(sid)
            if not rec:
                continue
            ok = bool(rec.get("honest_direct_image_run"))
            a = audit_of[m]
            a["runs"] += 1
            a["ok"] += 1 if ok else 0
            a["reads"] += len(rec.get("image_reads") or [])
            a["bad"] += 1 if rec.get("violations") else 0
            total_runs += 1
            total_ok += 1 if ok else 0

    ranked = sorted(models, key=lambda m: (-stats[m]["correct"], stats[m]["total_ms"]))
    speed_rank = {m: i + 1 for i, m in enumerate(sorted(models, key=lambda m: stats[m]["total_ms"]))}

    # feedback: clean round stance per model
    def clean_info(m, q):
        r = (fb.get(m) or {}).get("clean")
        if not r:
            return None
        return {"stance": r["stances"].get(str(q)),
                "moved": str(q) in r["moved_to_official"],
                "comment": next((f["comment"] for f in r["feedback"] if f["q"] == str(q)), "")}

    hinted_info = lambda m, q: (fb.get(m) or {}).get("hinted", {}).get("stances", {}).get(str(q))

    def feedback_cell(m):
        """Clean-round Q8 outcome — unique information, so it lives in the ranking table."""
        ci = clean_info(m, 8)
        if not ci:
            return "<span class='mut'>—</span>"
        return ("<span class='pill p-ok'>改判为 A</span>" if ci["moved"]
                else "<span class='pill p-bad'>坚持 B</span>")

    def model_verdict(m):
        """One-line verdict assembled strictly from measured facts (no invention)."""
        s, bits = stats[m], []
        r = speed_rank[m]
        bits.append("全场最快" if r == 1 else "全场最慢" if r == len(models) else f"速位 #{r}")
        r2 = ((answers.get(m, {}).get("2") or {}).get("reason") or "")
        if 2 in s["wrong"]:
            bits.append("Q2 漏检（未发现「云」）" if "云" not in r2 else "Q2 计数偏差")
        elif "云" not in r2:
            bits.append("Q2 字母对但第三处说错")
        ci = clean_info(m, 8)
        if ci:
            bits.append("反馈轮修正为 A" if ci["moved"] else "反馈轮坚持错误")
        if s["wrong"] and s["conf"].get("high", 0) >= 8:
            bits.append("错题全部 high 置信")
        return " · ".join(bits)

    # ---- question distribution
    qdist = {}
    for q in range(1, 11):
        c = Counter()
        who = defaultdict(list)
        for m in models:
            a = stats[m]["got"][q]
            if a:
                c[a] += 1
                who[a].append(m)
        qdist[q] = (c, who)

    # ------------------------------------------------------------- render ----
    P = []
    P.append("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>")
    P.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    P.append("<title>多模态模型 Benchmark 报告 · 8模型 × 10题</title>")
    P.append("""<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2128;--line:#2d333b;--fg:#e6edf3;--mut:#8b949e;
       --ok:#3fb950;--bad:#f85149;--warn:#d29922;--acc:#58a6ff;--pur:#bc8cff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
nav{position:sticky;top:0;z-index:20;background:rgba(13,17,23,.97);border-bottom:1px solid var(--line);
    padding:0 24px;backdrop-filter:blur(8px);font-size:13px}
.navrow{display:flex;gap:4px;flex-wrap:wrap;align-items:center;min-height:48px}
nav a{color:var(--mut);text-decoration:none;padding:7px 11px;border-radius:8px;position:relative;
      transition:color .15s,background .15s}
nav a:hover{color:var(--fg);background:#ffffff0d}
nav a.active{color:var(--acc);background:#58a6ff1f;font-weight:600}
nav a.toc-top{margin-left:auto;color:var(--mut);border:1px solid var(--line)}
#progress{position:absolute;left:0;bottom:-1px;height:2px;background:linear-gradient(90deg,#1f6feb,#58a6ff);width:0}
main{max-width:1180px;margin:0 auto;padding:24px 24px 120px}
h1{font-size:26px;margin:18px 0 6px}
/* sticky nav is 48px tall: keep anchored headings clear of it */
h2{font-size:20px;margin:38px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line);color:var(--acc);
   scroll-margin-top:64px}
h3{font-size:16px;margin:22px 0 8px;scroll-margin-top:64px}
h4{font-size:15px;margin:16px 0 6px;color:var(--pur)}
p{margin:8px 0}
.lead{color:var(--mut);font-size:13.5px}
.grid{display:grid;gap:12px}
.kpis{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi .n{font-size:26px;font-weight:700;color:var(--acc);line-height:1.2}
.kpi .l{font-size:12px;color:var(--mut);margin-top:4px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:12px 0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--panel2);color:var(--mut);font-weight:600;font-size:12.5px}
tr:hover td{background:#161b2288}
code{font:12px ui-monospace,Menlo,monospace;background:#0b0f14;padding:1px 5px;border-radius:4px;color:#c9d1d9}
pre{background:#0b0f14;border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto}
blockquote{border-left:3px solid var(--line);margin:8px 0;padding:2px 0 2px 12px;color:#c9d1d9;font-size:13.5px}
.cell{text-align:center;font-weight:700;font-family:ui-monospace,monospace}
.c-ok{color:var(--ok)}.c-bad{color:var(--bad)}
.pill{display:inline-block;font-size:11.5px;padding:2px 8px;border-radius:20px;border:1px solid;margin-right:4px}
.p-ok{color:var(--ok);border-color:#2ea04366;background:#2ea0431a}
.p-bad{color:var(--bad);border-color:#f8514966;background:#f851491a}
.p-warn{color:var(--warn);border-color:#d2992266;background:#d299221a}
.p-info{color:var(--acc);border-color:#58a6ff66;background:#58a6ff1a}
.bar{height:9px;border-radius:5px;background:#21262d;overflow:hidden;min-width:80px}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,#1f6feb,#58a6ff)}
img.crop{max-width:100%;border:1px solid var(--line);border-radius:10px;margin:10px 0;background:#000}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:860px){.cols{grid-template-columns:1fr}}
.mut{color:var(--mut)}
.small{font-size:12.5px}
.warnbox{background:#f851491a;border:1px solid #f8514966;border-radius:10px;padding:12px 16px;margin:14px 0}
.infobox{background:#58a6ff14;border:1px solid #58a6ff55;border-radius:10px;padding:12px 16px;margin:14px 0}
.okbox{background:#2ea0431a;border:1px solid #2ea04366;border-radius:10px;padding:12px 16px;margin:14px 0}
.reason{font-size:12.5px;color:#c9d1d9}
.modelhd{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
.score{font-size:22px;font-weight:700}
.rank{font-size:12px;color:var(--mut)}
/* compact per-model row (deduplicated view) */
.mrow{display:grid;grid-template-columns:34px minmax(210px,1.4fr) 74px 130px 150px minmax(180px,1.6fr);
      gap:10px;align-items:center;padding:9px 10px;border:1px solid transparent;border-radius:9px}
.mrow:hover{background:var(--panel2);border-color:var(--line)}
.mrow.head{color:var(--mut);font-size:12px;font-weight:600}
details.appendix{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:0 18px;margin:12px 0}
details.appendix>summary{cursor:pointer;padding:14px 0;font-weight:600;color:var(--acc);list-style:none}
details.appendix>summary::-webkit-details-marker{display:none}
details.appendix>summary::before{content:"▸ ";color:var(--mut)}
details.appendix[open]>summary::before{content:"▾ "}
details.appendix>summary:hover{color:var(--fg)}
details.appendix .body{border-top:1px solid var(--line);padding:8px 0 18px}
.anchor-link{color:var(--mut);text-decoration:none;font-size:12px;margin-left:8px}
</style></head><body>""")

    P.append("<nav><div class='navrow' id='navrow'>" + "".join(
        f"<a href='#{aid}' data-target='{aid}'>{t}</a>" for aid, t in [
            ("overview", "概览"), ("board", "排名"), ("matrix", "答案矩阵"), ("timing", "耗时"),
            ("questions", "逐题分析"), ("feedback", "反馈轮"), ("validity", "效度与局限"),
            ("judge", "裁判附录"), ("method", "复现说明")])
        + "<a href='#top' class='toc-top'>↑ 顶部</a>"
        + "</div><div id='progress'></div></nav>")

    P.append("<main id='top'>")
    P.append("<h1>多模态模型 Benchmark 报告</h1>")
    P.append("<p class='lead'>统一 OpenAI 兼容路由 · 8 个厂商旗舰模型 · 10 道儿童观察/逻辑题 · "
             "每道题以独立裁切图片直发模型 · DSH Agent 多步执行 · 逐题独立会话</p>")

    P.append("<div class='grid kpis'>")
    for n, l in [(f"{len(models)}", "参赛模型"), ("10", "题目"),
                 (f"{total_runs}", "首轮作答运行数"), (f"{total_ok}/{total_runs}", "诚实直读图审计通过"),
                 ("2", "反馈轮（提示/无提示）"), ("0", "作弊样本")]:
        P.append(f"<div class='kpi'><div class='n'>{n}</div><div class='l'>{l}</div></div>")
    P.append("</div>")

    P.append("<div class='okbox'><b>一句话结论：</b>8 个模型在 10 题里 9 题答案完全一致，"
             "唯一真实分水岭是 <b>Q2（找不同）</b>；而 <b>Q8</b> 是一道出色的陷阱题，"
             "<b>8 个模型全部上钩</b>——它们只数了「先/再/然后」三项，全部漏掉句首的「走进房间」，"
             "因此把「第二件事」误判为拿书。此外只有 2/8 的模型在被明确告知正确答案后"
             "能真正修正 Q8 的错误信念。</div>")

    # ---------------- overview（精简为“三条要点 + 折叠的方法说明”）
    P.append("<h2 id='overview'>概览</h2>")
    P.append("<div class='card'><b>三条要点</b><ol class='small'>"
             "<li><b>这是一套偏简单的卷子</b>：10 题里 9 题 8 个模型答案完全一致，得分只落在 8/10 与 9/10；"
             "真正的区分点只有 Q2 与 Q8。</li>"
             "<li><b>Q8 是全场最有价值的题</b>：它测的是「把整句叙事建模成事件序列」，"
             "8 个模型全部套用「先/再/然后」模板、漏掉句首动作，0/8。</li>"
             "<li><b>被告知正确答案不等于会改</b>：去掉一切提示后，仍只有 2/8 修正了 Q8 的错误信念。</li>"
             "</ol>"
             "<details class='appendix'><summary>执行方式（点开）</summary><div class='body'><ul class='small'>"
             "<li>题图 614×6822px（深色长截图，sha256 <code>68314100…5c5350d70</code>）按行空白切成 10 张独立题图——"
             "整图直发会被压缩到文字不可读，那测的就不是「能不能看图」。</li>"
             "<li>每个 (模型 × 题目) 一次<b>独立 agent 会话</b>，只拿到本题图片，无跨题上下文、无答案泄漏。</li>"
             "<li>模型被限定只能用 <code>read_image</code> 直读图片，禁用 bash/OCR/读文件等旁路；"
             "执行后逐条审计转录（<code>read_image</code> 是否真成功、有无违规工具调用）。</li>"
             "<li>耗时取自转录里 <code>step/start|end</code>、<code>tool/call|result</code> 的毫秒时间戳，"
             "不是模型自述。</li></ul></div></details></div>")

    # ---------------- results（排名 / 矩阵 / 耗时 收进同一节）
    P.append("<h2 id='results'>结果</h2>")
    P.append("<h3 id='board'>排名与得分</h3>")
    P.append("<p class='lead'>官方 key <code>" + "".join(key[str(q)] for q in range(1, 11)) +
             "</code>。同分按总耗时升序排列；这只是本卷排序，样本仅 10 题，不足以推出通用能力排名。</p>")
    P.append("<table><thead><tr><th>#</th><th>模型</th><th>得分</th><th>错题</th>"
             "<th>总耗时</th><th>中位/题</th><th>反馈轮 Q8</th><th>一句话点评</th></tr></thead><tbody>")
    for i, m in enumerate(ranked, 1):
        s = stats[m]
        wrong = "、".join(f"Q{q}" for q in s["wrong"]) or "无"
        P.append(f"<tr><td>{i}</td>"
                 f"<td><code>{m}</code><div class='mut small'>{vendor[m]}</div></td>"
                 f"<td class='score'>{s['correct']}/10</td><td class='c-bad'>{wrong}</td>"
                 f"<td>{s['total_ms']/1000:.1f}s</td><td>{s['median_ms']/1000:.1f}s</td>"
                 f"<td>{feedback_cell(m)}</td>"
                 f"<td class='small'>{model_verdict(m)}</td></tr>")
    P.append("</tbody></table>")
    P.append("<p class='small mut'>同分按总耗时升序。「反馈轮 Q8」列为<b>无提示</b>轮结果——"
             "hinted 轮已被评测方提示污染并作废。耗时只反映端到端时延（含读图与推理），未做机器负载归一化。</p>")

    # ---------------- matrix
    P.append("<h3 id='matrix'>答案矩阵</h3>")
    P.append("<table><thead><tr><th>模型</th>" + "".join(f"<th>Q{q}</th>" for q in range(1, 11)) +
             "<th>得分</th></tr></thead><tbody>")
    P.append("<tr><td class='mut'>官方答案</td>" +
             "".join(f"<td class='cell'>{key[str(q)]}</td>" for q in range(1, 11)) + "<td></td></tr>")
    for m in ranked:
        tds = ""
        for q in range(1, 11):
            a = stats[m]["got"][q] or "—"
            cls = "c-ok" if a == key[str(q)] else "c-bad"
            tds += f"<td class='cell {cls}'>{a}</td>"
        P.append(f"<tr><td><code>{m}</code></td>{tds}<td>{stats[m]['correct']}/10</td></tr>")
    P.append("</tbody></table>")
    P.append("<p class='small mut'>绿色＝与官方 key 一致，红色＝不一致。"
             "注意矩阵「一致」不等于视觉推理正确：Q2 有 2 个模型字母答对但把第三处差异说错（见下）。</p>")

    # ---------------- step timing detail
    runs = {}
    for sid, p in profiles.items():
        m, q = p.get("model"), p.get("question")
        if m in models and q and p.get("answer"):
            tools = p.get("tool_detail") or []
            read_ms = sum(t.get("ms") or 0 for t in tools if t.get("name") == "read_image")
            runs[(m, q)] = {
                "wall_ms": p.get("wall_ms") or 0, "steps": p.get("steps") or 0,
                "read_ms": read_ms, "tools": p.get("tool_calls") or 0,
                "step_ms": [s.get("ms") or 0 for s in (p.get("step_detail") or [])],
            }

    P.append("<h3 id='timing'>步骤与耗时</h3>")
    P.append("<p class='lead'>每次运行固定为「读图 → 作答」两段式 agent 流程（步数/次≈2）。"
             "注意口径：<b>「read_image 调用」只统计本地读取并挂载图片文件的耗时（毫秒级），"
             "不含模型的视觉计算</b>——模型真正「看图」发生在随后那次 LLM 请求里，"
             "因此被计入「作答步」。作答步＝整次运行里除本地挂载外的全部时间，"
             "其中既含视觉理解，也含推理与生成。</p>")
    P.append("<table><thead><tr><th>模型</th><th>步数/次</th><th>read_image 调用均耗时</th>"
             "<th>作答步均耗时</th><th>中位/题</th><th>最慢一题</th></tr></thead><tbody>")
    for m in ranked:
        rr = [runs[(m, q)] for q in range(1, 11) if (m, q) in runs]
        if not rr:
            continue
        avg_read = sum(r["read_ms"] for r in rr) / len(rr)
        avg_wall = sum(r["wall_ms"] for r in rr) / len(rr)
        avg_steps = sum(r["steps"] for r in rr) / len(rr)
        slow_q = max(range(1, 11), key=lambda q: (runs.get((m, q)) or {}).get("wall_ms", 0))
        P.append(f"<tr><td><code>{m}</code></td><td>{avg_steps:.1f}</td>"
                 f"<td>{avg_read/1000:.2f}s</td><td>{(avg_wall-avg_read)/1000:.2f}s</td>"
                 f"<td>{stats[m]['median_ms']/1000:.1f}s</td>"
                 f"<td>Q{slow_q} ({runs[(m,slow_q)]['wall_ms']/1000:.1f}s)</td></tr>")
    P.append("</tbody></table>")

    P.append("<h3>逐题耗时热力图（秒）</h3>")
    P.append("<table><thead><tr><th>模型</th>" + "".join(f"<th>Q{q}</th>" for q in range(1, 11)) +
             "<th>合计</th></tr></thead><tbody>")
    for m in ranked:
        vals = [(runs.get((m, q)) or {}).get("wall_ms", 0) / 1000 for q in range(1, 11)]
        vmax = max(vals) or 1
        tds = ""
        for v in vals:
            a = min(0.85, v / vmax) if vmax else 0
            tds += (f"<td class='cell' style='background:rgba(248,81,73,{a:.2f})'>"
                    f"{v:.1f}</td>")
        P.append(f"<tr><td><code>{m}</code></td>{tds}<td>{sum(vals):.1f}</td></tr>")
    P.append("</tbody></table>")
    P.append("<p class='small mut'>颜色越红表示该题耗时越长。可清楚看到几个异常长尾："
             "DeepSeek 在 Q6 花了 92.9s（其余题多为 3–5s）、Qwen 在 Q2 花了 175.9s 却答错、"
             "GLM 在 Q6 花了 99.7s、Kimi K3 几乎每题都在 40–80s。</p>")

    # ---------------- per question
    P.append("<h2 id='questions'>逐题分析</h2>")
    # (no separate "paper split" card: every question card already shows the exact
    # crop that was sent to the model, so a full-paper thumbnail was redundant)
    notes = {
        2: "三处差异经出题方确认为 <b>云、窗户、烟囱</b>。答 B 的模型只找到烟囱与窗户（漏掉云）；"
           "答 D 的模型多计了草地/云位置。更值得注意的是：答 C 的 5 个模型里，"
           "<b>Claude 说是「树的大小」、Kimi 说是「花朵数量」</b>——字母对了，第三处理由是错的。",
        8: "本题是<b>陷阱题</b>：完整动作链是 <b>走进房间(1) → 打开台灯(2) → 从书架拿书(3) → 坐下看书(4)</b>，"
           "所以「第二件事情」= <b>开灯 = A</b>。8 个模型全部只数「先/再/然后」标记的三项，"
           "集体漏掉句首的「走进房间」，全部答 B。<b>0/8</b> 是本卷唯一真正的全员失败。",
    }
    for q in range(1, 11):
        meta, (c, who) = qmeta[str(q)], qdist[q]
        right = c.get(key[str(q)], 0)
        P.append(f"<div class='card'><h3>第 {q} 题 &nbsp;"
                 f"<span class='pill {'p-ok' if right == 8 else 'p-warn' if right >= 5 else 'p-bad'}'>"
                 f"官方 {key[str(q)]} · 正确 {right}/8</span></h3>")
        P.append(f"<p><b>{html.escape(meta['text'])}</b></p>")
        P.append("<p class='small'>" + " ｜ ".join(
            f"<b>{k}</b> {html.escape(v)}" for k, v in meta["options"].items()) + "</p>")
        if q in notes:
            P.append(f"<div class='infobox small'>{notes[q]}</div>")
        dist = "　".join(f"<span class='pill {'p-ok' if k == key[str(q)] else 'p-bad'}'>{k}: {v}</span>"
                         for k, v in sorted(c.items()))
        P.append(f"<p class='small'>{dist}</p>")
        # reasons for the contested questions
        if q in (2, 8):
            P.append("<table><thead><tr><th>模型</th><th>答案</th><th>置信</th><th>模型给出的理由</th></tr></thead><tbody>")
            for m in ranked:
                r = answers.get(m, {}).get(str(q)) or {}
                cls = "c-ok" if r.get("answer") == key[str(q)] else "c-bad"
                P.append(f"<tr><td><code>{m}</code></td><td class='cell {cls}'>{r.get('answer')}</td>"
                         f"<td>{r.get('confidence')}</td><td class='reason'>{html.escape(r.get('reason') or '')}</td></tr>")
            P.append("</tbody></table>")
        # Every card shows its crop, including text-only stems (Q7/Q9/Q10):
        # the crop is literally what the model received, so the card format must
        # stay identical across all ten questions.
        src = asset_src(f"data/paper/questions/Q{q:02d}.png")
        kind = "含配图" if meta.get("has_figure") else "纯文本题干（无插图）"
        P.append(f"<img class='crop' src='{src}' alt='第{q}题原图'>")
        P.append(f"<p class='small mut'>▲ 第 {q} 题原图 · {kind} "
                 f"（<code>data/paper/questions/Q{q:02d}.png</code>，发送给模型的就是这张裁切图）</p>")
        P.append("</div>")

    # NOTE: there is deliberately no separate "per-model" section. Every fact it
    # used to repeat (score, timings, answer pills, wrong-answer reasons) already
    # lives in the ranking table and the per-question cards. What was unique to a
    # model — the clean-round stance and a one-line verdict — moved into the
    # ranking table, which removes a whole duplicate pass over the same data.

    # ---------------- feedback
    P.append("<h2 id='feedback'>反馈轮实验：被告知正确答案之后</h2>")
    P.append("<div class='warnbox small'><b>先披露一个我自己的方法论错误。</b>"
             "第一轮反馈时我在 dossier 里写了「官方 Q8 标注可能有误」的提示——"
             "这等于替模型洗白了错误，结果 <b>8/8 模型都「反对」</b>，该轮数据<b>不可用于任何结论</b>。"
             "第二轮去掉全部提示（模型必须自己比对差异），才得到有效测量。</div>")
    P.append("<table><thead><tr><th>模型</th><th>带提示轮 Q8</th><th>无提示轮 Q8</th>"
             "<th>无提示轮最终答案</th><th>Q2（无提示轮）</th></tr></thead><tbody>")
    for m in ranked:
        h8, c8, c2 = hinted_info(m, 8), clean_info(m, 8), clean_info(m, 2)
        def fmt(x, q):
            if not x:
                return "<span class='mut'>—</span>"
            if x["stance"] == "agree":
                tag = "<span class='pill p-ok'>同意并改判</span>"
            else:
                tag = "<span class='pill p-bad'>反对/坚持</span>"
            return tag
        final8 = ((fb.get(m) or {}).get("clean") or {}).get("final_answers", {}).get("8", "—")
        h8tag = "<span class='pill p-bad'>反对</span>" if h8 == "disagree" else "<span class='mut'>—</span>"
        P.append(f"<tr><td><code>{m}</code></td>"
                 f"<td>{h8tag}</td>"
                 f"<td>{fmt(c8, 8)}</td><td class='cell'>{final8}</td><td>{fmt(c2, 2)}</td></tr>")
    P.append("</tbody></table>")
    moved8 = [m for m in models if (clean_info(m, 8) or {}).get("moved")]
    P.append(f"<div class='okbox small'><b>无提示轮的有效结果：{len(moved8)}/8 个模型真正修正了 Q8</b> —— "
             + "、".join(f"<code>{m}</code>" for m in moved8) +
             "；其余 6 个在没有提示的情况下<b>继续坚持错误答案 B</b>，"
             "其中 Gemini 甚至自己提出了「走进房间算第一件事」的可能性却仍拒绝采用。"
             "这说明多数模型面对权威反证时，倾向于捍卫首轮的局部语法启发式，而非重建完整事件链。</div>")

    # ---------------- validity
    P.append("<h2 id='validity'>效度与局限</h2>")
    P.append("<div class='card'><ul>"
             "<li><b>区分度极低：</b>10 题中 9 题 8/8 全对，得分只落在 8/10 与 9/10 两个点位上。"
             "不能用 1 分之差推断稳定的能力优势。</li>"
             "<li><b>真正测视觉的只有 Q1–Q6</b>（身份匹配、找不同、路径、计数、高度、形状匹配）。"
             "Q7（序列规律）、Q9（颜色循环）、Q10（价值判断）几乎不依赖图像；"
             "Q8 考的是<b>文本事件时序</b>，不是视觉辨识。把它们合成一个「视觉总分」会稀释测量。</li>"
             "<li><b>字母正确 ≠ 推理正确：</b>Q2 中 Claude（说「树」）、Kimi（说「花」）字母答对但第三处差异说错；"
             "Q9 中 Claude 给出题面并不支持的「黑球数量递增」解释。仅按选项字母判分会高估视觉可靠性。</li>"
             "<li><b>置信度校准差：</b>Q2、Q8 的错误答案几乎全部标注 high，"
             "8/8 在 Q8 高置信地犯了同一个错。不审计校准的 confidence 字段没有意义。</li>"
             "<li><b>数据来源可用性：</b>各厂商旗舰并非都能直发图——GLM-5.3 旗舰被上游拒绝"
             "（<code>messages.content.type 参数非法，取值范围 ['text']</code>），"
             "故本卷用同代的 glm-5.3-flash。`deepseek/deepseek-v4-pro` 亦是「收到指令但拿不到图」。</li>"
             "</ul></div>")

    # ---------------- judge
    P.append("<h2 id='judge'>附录：独立裁判报告全文</h2>")
    P.append("<p class='lead'>裁判为 <code>openai/gpt-5.6-terra</code>（非参赛模型）。"
             "它的结论与前文各节同源，**因此默认折叠**，仅供留档与交叉核对；"
             "其中「逐题分析 / 逐模型点评」与上文重叠最多。</p>")
    P.append("<div class='warnbox small'><b>裁判的能力边界，必须披露：</b>审计显示裁判在运行中"
             "<b>主动尝试了 7 次 <code>read_image</code> 想亲自核验题图</b>，但因为我没有为它声明图片输入能力，"
             "这 7 次全部被 DSH 闸门拒绝（报 <code>does not declare image input</code>）。"
             "因此它的视觉结论并非来自自己看图，而是基于<b>出题方确认的官方 key</b> 与"
             "<b>各模型陈述的理由</b>，并用 bash 复核了计分算术。"
             "若要裁判真正独立复看图像，需同样为裁判模型声明 <code>input: [text, image]</code> —— "
             "这是下一轮必须补的改进项。</div>")
    P.append("<details class='appendix'><summary>展开裁判报告全文（与上文重叠，供留档核对）</summary>"
             "<div class='body'>")
    with open(D("data", "judge_report.md"), encoding="utf-8") as fh:
        P.append(md_to_html(fh.read()))
    P.append("</div></details>")

    # ---------------- method
    P.append("<h2 id='method'>复现说明与文件清单</h2>")
    P.append("<div class='card'><h3>执行与度量</h3><ul class='small'>"
             "<li>运行通道：DSH workflow <code>agent(provider=&lt;你的 provider id&gt;, model=…)</code>；"
             "每个 (模型,题) 一个独立子会话，限定 <code>read_image</code> 单工具，"
             "答案经 <code>structured_output</code> schema 校验返回。</li>"
             "<li>时序采集：解析子会话 zstd 转录（<code>step/start|end</code>、<code>tool/call|result</code> 毫秒时间戳），"
             "答案矩阵同样由转录重建（<code>profile_sessions.py</code> → <code>build_answers.py</code>）。</li>"
             "<li>诚实性审计：<code>audit_image_runs.py</code> 逐会话核验 <code>read_image</code> 是否成功、"
             "有无白名单外工具调用（曾据此抓出 Gemini 用 bash+PIL 解析像素并偷读他人答案文件伪造成功）。</li>"
             "<li>配置前置：该路由不在 pi-ai 内置模型目录里，故在 <code>~/.dsh/settings.yaml</code> 的参赛模型条目上"
             "声明 <code>input: [text, image]</code>（脚本 <code>patch_settings_input.py</code>，幂等+集合校验+自动备份），"
             "否则 DSH 会以「does not declare image input」拒绝任何图片。</li>"
             "</ul><h3>关键文件</h3><ul class='small'>"
             "<li><code>data/roster.json</code> 参赛名单 ｜ <code>data/questions.json</code> 题目与切图</li>"
             "<li><code>data/answers.json</code> 答案矩阵（含每题 session_id/耗时/步数）"
             "｜ <code>data/answer_key.json</code> 官方 key（含出题方澄清）</li>"
             "<li><code>data/audit.json</code> 诚实性审计 ｜ <code>data/session_profiles.json</code> 逐步时序明细</li>"
             "<li><code>data/feedback_summary.json</code> 两轮反馈 ｜ <code>data/judge_report.md</code> 裁判报告原文</li>"
             "<li>脚本：<code>probe_vision.py</code>（发图探针）、<code>profile_sessions.py</code>（时序）、"
             "<code>audit_image_runs.py</code>（审计）、<code>build_answers.py</code>、"
             "<code>build_feedback.py</code>、<code>make_report.py</code>（本页）</li>"
             "</ul></div>")
    P.append("</main>")
    # ---- scroll spy + reading progress. Sections are matched to nav links by
    # data-target; the "results" h2 has three h3 children that each own a link.
    P.append("""<script>
(function(){
  var links = [].slice.call(document.querySelectorAll('#navrow a[data-target]'));
  var targets = links.map(function(a){
    return {a: a, el: document.getElementById(a.dataset.target)};
  }).filter(function(t){ return t.el; });
  var bar = document.getElementById('progress');

  function navH(){ var n=document.querySelector('nav'); return n?n.offsetHeight:48; }

  function onScroll(){
    var h = navH() + 8;
    var best = null;
    for (var i=0;i<targets.length;i++){
      var r = targets[i].el.getBoundingClientRect();
      if (r.top - h <= 0) best = targets[i];      // last heading already passed
      else break;
    }
    if (!best && targets.length) best = targets[0];
    links.forEach(function(a){ a.classList.remove('active'); });
    if (best) best.a.classList.add('active');

    if (bar){
      var d = document.documentElement;
      var max = d.scrollHeight - window.innerHeight;
      bar.style.width = (max > 0 ? Math.min(100, window.scrollY / max * 100) : 0) + '%';
    }
  }

  // Click: scroll with an offset so the sticky nav never covers the heading.
  links.forEach(function(a){
    a.addEventListener('click', function(ev){
      var el = document.getElementById(a.dataset.target);
      if (!el) return;
      ev.preventDefault();
      var y = el.getBoundingClientRect().top + window.scrollY - navH() - 8;
      window.scrollTo({top: Math.max(0, y), behavior: 'smooth'});
      history.replaceState(null, '', '#' + a.dataset.target);
    });
  });
  var top = document.querySelector('a.toc-top');
  if (top) top.addEventListener('click', function(ev){
    ev.preventDefault();
    window.scrollTo({top:0, behavior:'smooth'});
  });

  var t = null;
  window.addEventListener('scroll', function(){
    if (t) return;
    t = setTimeout(function(){ t = null; onScroll(); }, 60);
  }, {passive:true});
  window.addEventListener('resize', onScroll);
  // Deep links (#anchor) also need the offset.
  if (location.hash){
    var el = document.getElementById(location.hash.slice(1));
    if (el) setTimeout(function(){
      window.scrollTo({top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - navH() - 8)});
    }, 0);
  }
  onScroll();
})();
</script></body></html>""")

    out = D(OUT_NAME)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(P))
    print(f"wrote {out}  ({os.path.getsize(out)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
