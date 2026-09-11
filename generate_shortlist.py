#!/usr/bin/env python3
"""Curated shortlist: newest flagship vision model per vendor.

Reads router metadata + live image-probe results, applies a hand-curated
vendor->latest-flagship mapping, and emits:
  data/shortlist.json  - machine readable
  shortlist.md         - markdown table
  shortlist.html       - interactive picker (recommended preselected)
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "all_models_raw.json")
PROBE = os.path.join(HERE, "probes", "probe_results.json")

# --- hand-curated: newest flagship tier per vendor, then same-gen alternates ---
CURATED = [
    # (model_id, vendor_cn, tier, note)
    ("openai/gpt-6-astra",               "OpenAI",     "recommended", "GPT-6 旗舰，端到端 agent / 深度研究"),
    ("openai/gpt-5.6-sol",               "OpenAI",     "alternate",   "GPT-5.6 系列旗舰（Sol 层）"),
    ("openai/gpt-5.6-terra",             "OpenAI",     "alternate",   "GPT-5.6 均衡层（Terra）"),
    ("anthropic/claude-opus-5",          "Anthropic",  "recommended", "Opus 5 旗舰，复杂推理+长期规划"),
    ("anthropic/claude-sonnet-5",        "Anthropic",  "alternate",   "Sonnet 5，最新 Sonnet 级"),
    ("anthropic/claude-fable-5.1",       "Anthropic",  "alternate",   "Fable 5.1，知识工作向"),
    ("google/gemini-3.8-flash",          "Google",     "recommended", "Gemini 3.8 Flash，最新一代"),
    ("google/gemini-3.7-flash",          "Google",     "alternate",   "Gemini 3.7 Flash"),
    ("google/gemini-3.6-flash",          "Google",     "alternate",   "Gemini 3.6 Flash"),
    ("deepseek/deepseek-v4.1-flash",     "DeepSeek",   "recommended", "V4.1 Flash，最新视觉实验线"),
    ("deepseek/deepseek-v4-flash-vision-exp", "DeepSeek", "alternate", "V4 Flash Vision Exp"),
    ("ali/qwen3.8-max-0902",             "阿里 Qwen",  "recommended", "Qwen3.8-Max 快照版，2.4T MoE 旗舰"),
    ("ali/qwen3.8-max",                  "阿里 Qwen",  "alternate",   "Qwen3.8-Max 正式版"),
    ("ali/qwen3.8-flash",                "阿里 Qwen",  "alternate",   "Qwen3.8-Flash 高性价比"),
    ("ali/qwen3-vl-plus",                "阿里 Qwen",  "alternate",   "Qwen3-VL-Plus 视觉专精"),
    ("bytedance/doubao-seed-2-1-pro",    "字节豆包",   "recommended", "Seed-2.1 Pro，Coding/Agent 旗舰"),
    ("bytedance/doubao-seed-2-1-turbo",  "字节豆包",   "alternate",   "Seed-2.1 Turbo 均衡版"),
    ("moonshot/kimi-k3",                 "月之暗面",   "recommended", "Kimi K3，2.8T 参数旗舰"),
    ("moonshot/kimi-k2.7-code",          "月之暗面",   "alternate",   "Kimi K2.7 Code"),
    ("x-ai/grok-4.6",                    "xAI",        "recommended", "Grok 4.6，最新旗舰（2M 上下文）"),
    ("x-ai/grok-4.5",                    "xAI",        "alternate",   "Grok 4.5"),
    ("bigmodel/glm-5v-turbo",            "智谱 GLM",   "recommended", "GLM-5V-Turbo，多模态 Coding 基座"),
    ("minimax/minimax-m3",               "MiniMax",    "recommended", "MiniMax M3 旗舰"),
    ("intern/intern-s2-preview",         "Intern",     "recommended", "Intern-S2 Preview（元数据漏报，实测可发图）"),
    ("intern/internvl3.5",               "Intern",     "alternate",   "InternVL3.5（元数据漏报，实测可发图）"),
    ("agnes/agnes-2.5-flash",            "Agnes",      "recommended", "Agnes 2.5 Flash（元数据未标注）"),
    ("meta/llama-4-scout",               "Meta",       "recommended", "Llama 4 Scout（唯一在售 Meta 视觉模型）"),
]

# --- probe verdicts that prove "metadata claims vision but cannot really see images" ---
KNOWN_FALSE_POSITIVE = {
    "longcat/longcat-2.0": "实测明确回复「I can't see an image」，元数据误报",
    "xiaomi/mimo-v2.5-pro": "接口 404：No endpoints found that support image input",
    "stepfun/step-3.5-flash-2603": "接口 400：模型不支持图片输入",
    "baidu/ernie-4.5-turbo-vl-preview": "接口 401：当前 key 无该模型访问权限",
    "tencent/hy4-preview": "两次发图均返回空响应，无法确认可用",
}


def verdict(res):
    if not res:
        return "not-probed", None
    if res.get("error"):
        return "error", res["error"]
    txt = f"{res.get('text') or ''}\n{res.get('reasoning') or ''}"
    low = txt.lower()
    if "can't see an image" in low or "cannot see an image" in low or "看不到图" in txt:
        return "no-vision", "模型自述看不到图片"
    code_ok, color_ok = "7291" in txt, "red" in low
    misread = bool(re.search(r"7[0-9]{2,3}", txt)) and not code_ok
    if code_ok and color_ok:
        return "verified", None
    if code_ok or color_ok or misread:
        return "vision-ok", "读到了图片内容（输出格式/细节不完美）"
    return "inconclusive", "未返回可识别内容"


def main():
    raw = json.load(open(RAW))
    probe = json.load(open(PROBE)) if os.path.exists(PROBE) else {}
    items = []
    for mid, vendor, tier, note in CURATED:
        m = raw.get(mid)
        if not m:
            print(f"!! missing in metadata: {mid}")
            continue
        p = probe.get(mid)
        v, vnote = verdict(p)
        arch = m.get("architecture") or {}
        price = m.get("pricing") or {}
        items.append({
            "id": mid, "name": m.get("name"), "vendor": vendor, "tier": tier, "note": note,
            "api_company": m.get("company"),
            "input_modalities": arch.get("input") or "(元数据未标注)",
            "context_window": m.get("context_window"), "max_tokens": m.get("max_tokens"),
            "input_price": price.get("input_price"), "output_price": price.get("output_price"),
            "currency": price.get("currency"),
            "metadata_vision": "image" in (arch.get("input") or ""),
            "probe_verdict": v, "probe_note": vnote,
            "probe_latency": (p or {}).get("latency"),
            "probe_reply": ((p or {}).get("text") or (p or {}).get("reasoning") or "")[:160],
            "probe_error": (p or {}).get("error"),
        })

    json.dump({"items": items, "excluded_false_positive": KNOWN_FALSE_POSITIVE},
              open(os.path.join(HERE, "data", "shortlist.json"), "w"), ensure_ascii=False, indent=2)

    # markdown
    rec = [i for i in items if i["tier"] == "recommended"]
    alt = [i for i in items if i["tier"] != "recommended"]
    lines = ["# 各厂商最新旗舰「可发图」模型候选清单", "",
             f"共 {len(items)} 个候选（推荐 {len(rec)} / 备选 {len(alt)}），"
             f"其中 {sum(1 for i in items if i['probe_verdict'] in ('verified','vision-ok'))} 个已实测通过发图。", ""]
    for title, group in (("推荐：各厂商最新旗舰", rec), ("备选：同代其它型号", alt)):
        lines += [f"## {title}", "",
                  "| 厂商 | 模型 id | 输入模态 | 上下文 | 价格(进/出 CNY) | 发图实测 | 备注 |",
                  "|---|---|---|---|---|---|---|"]
        for i in group:
            badge = {"verified": "✅ 已读图", "vision-ok": "⚠️ 部分正确",
                     "no-vision": "❌ 不能发图", "error": "❌ 调用失败",
                     "inconclusive": "❌ 无有效响应"}.get(i["probe_verdict"], "— 未测")
            ctx = i["context_window"] or 0
            ctx = f"{ctx/1e6:.1f}M" if ctx >= 1e6 else f"{ctx//1000}K"
            lines.append(f"| {i['vendor']} | `{i['id']}` | {i['input_modalities']} | {ctx} | "
                         f"{i['input_price']}/{i['output_price']} | {badge} | {i['note']} |")
        lines.append("")
    lines += ["## 元数据误报（声称支持图片，实测不支持）", ""]
    for k, v in KNOWN_FALSE_POSITIVE.items():
        lines.append(f"- `{k}` — {v}")
    open(os.path.join(HERE, "shortlist.md"), "w").write("\n".join(lines))
    print(f"shortlist.json / shortlist.md -> {len(items)} candidates")

    html = HTML.replace("__DATA__", json.dumps(items, ensure_ascii=False)) \
               .replace("__EXCLUDED__", json.dumps(KNOWN_FALSE_POSITIVE, ensure_ascii=False))
    open(os.path.join(HERE, "shortlist.html"), "w").write(html)
    print("shortlist.html")


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>各厂商最新旗舰可发图模型筛选</title>
<style>
 :root{--bg:#0e1116;--panel:#161b22;--line:#252c36;--fg:#e6edf3;--mut:#8b949e;--ok:#3fb950;--warn:#d29922;--err:#f85149;--acc:#4493f8}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
 header{position:sticky;top:0;background:rgba(14,17,22,.97);border-bottom:1px solid var(--line);padding:14px 22px;z-index:5}
 h1{margin:0;font-size:17px}
 .sub{color:var(--mut);font-size:12px;margin-top:4px}
 .bar{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
 input[type=search],select{background:#0d1117;border:1px solid var(--line);color:var(--fg);padding:7px 10px;border-radius:7px;font-size:13px}
 input[type=search]{min-width:240px}
 button{background:#21262d;border:1px solid var(--line);color:var(--fg);padding:7px 12px;border-radius:7px;cursor:pointer;font-size:13px}
 button:hover{border-color:var(--acc)} button.primary{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
 main{max-width:1400px;margin:0 auto;padding:16px 22px 90px}
 h2{font-size:14px;color:var(--acc);border-bottom:1px solid var(--line);padding-bottom:6px;margin:22px 0 10px}
 .row{display:grid;grid-template-columns:30px 130px minmax(230px,1.4fr) 150px 90px 110px 130px 1fr;gap:10px;align-items:center;
      padding:8px 10px;border:1px solid transparent;border-radius:9px}
 .row:hover{background:var(--panel);border-color:var(--line)}
 .row.sel{background:#12261a;border-color:#2ea04366}
 .row.head{color:var(--mut);font-size:12px;font-weight:600}
 code{font:12px ui-monospace,Menlo,monospace;color:#c9d1d9}
 .mut{color:var(--mut);font-size:12px}
 .badge{font-size:11px;padding:2px 7px;border-radius:20px;border:1px solid;display:inline-block;white-space:nowrap}
 .b-ok{color:var(--ok);border-color:#2ea04366;background:#2ea0431a}
 .b-vo{color:var(--warn);border-color:#d2992266;background:#d299221a}
 .b-no{color:var(--err);border-color:#f8514966;background:#f851491a}
 .b-un{color:var(--mut);border-color:var(--line)}
 input[type=checkbox]{width:16px;height:16px;accent-color:var(--acc)}
 #selbar{position:fixed;bottom:0;left:0;right:0;background:#161b22f2;border-top:1px solid var(--line);padding:12px 22px;display:flex;gap:12px;align-items:center}
 #out{font:12px ui-monospace,monospace;color:var(--ok);flex:1;overflow:auto;white-space:nowrap}
 .warnbox{background:#f851491a;border:1px solid #f8514966;border-radius:9px;padding:10px 14px;margin-top:14px;font-size:12.5px;color:#ffb0aa}
</style></head><body>
<header>
  <h1>各厂商<b>最新旗舰</b>「可直接发图」模型筛选</h1>
  <div class="sub">数据源：路由器 <code>/v1/models</code> 元数据 + 真实发图探针实测（图片内容：红色圆 + 绿色方块 + 编码 7291）。推荐项已默认勾选，可自由增删后复制模型 id。</div>
  <div class="bar">
    <input type="search" id="q" placeholder="搜索模型 / 厂商…">
    <select id="vend"><option value="">全部厂商</option></select>
    <select id="vd">
      <option value="">全部实测状态</option>
      <option value="verified">✅ 已读图</option>
      <option value="vision-ok">⚠️ 部分正确</option>
      <option value="bad">❌ 不可用（不能发图/失败）</option>
    </select>
    <button id="onlyrec">只看推荐</button>
    <button id="clear">清空</button>
    <button class="primary" id="copy">复制选中 id</button>
  </div>
</header>
<main>
  <div class="row head"><div></div><div>厂商</div><div>模型</div><div>输入模态</div><div>上下文</div><div>价格 进/出</div><div>发图实测</div><div>说明</div></div>
  <div id="list"></div>
  <div class="warnbox" id="warn"></div>
</main>
<div id="selbar"><span class="mut">已选 <b id="c">0</b>：</span><span id="out">—</span><button class="primary" id="copy2">复制</button></div>
<script>
const DATA=__DATA__, EX=__EXCLUDED__;
const good=v=>v==='verified'||v==='vision-ok';
const sel=new Set(JSON.parse(localStorage.getItem('ssy_sel')||'null')||DATA.filter(d=>d.tier==='recommended'&&good(d.probe_verdict)).map(d=>d.id));
const save=()=>localStorage.setItem('ssy_sel',JSON.stringify([...sel]));
const ctx=n=>!n?'—':n>=1e6?(n/1e6).toFixed(1)+'M':Math.round(n/1000)+'K';
const VB={verified:['b-ok','✅ 已读图'],'vision-ok':['b-vo','⚠️ 部分正确'],'no-vision':['b-no','❌ 不能发图'],
          error:['b-no','❌ 调用失败'],inconclusive:['b-no','❌ 无响应'],'not-probed':['b-un','— 未测']};
const selV=document.getElementById('vend');
[...new Set(DATA.map(d=>d.vendor))].sort().forEach(v=>selV.add(new Option(v,v)));
function render(){
  const q=document.getElementById('q').value.toLowerCase(), v=selV.value, vd=document.getElementById('vd').value;
  const onlyrec=document.getElementById('onlyrec').dataset.on==='1';
  const rows=DATA.filter(d=>{
    if(v&&d.vendor!==v)return false;
    if(q&&!(d.id+d.name+d.vendor+d.note).toLowerCase().includes(q))return false;
    if(onlyrec&&d.tier!=='recommended')return false;
    if(vd==='bad'&&good(d.probe_verdict))return false;
    if(vd&&vd!=='bad'&&d.probe_verdict!==vd)return false;
    return true;
  });
  document.getElementById('list').innerHTML=rows.map(d=>{
    const [cls,lab]=VB[d.probe_verdict]||VB['not-probed'];
    const isSel=sel.has(d.id);
    return `<label class="row ${isSel?'sel':''}">
      <input type="checkbox" data-id="${d.id}" ${isSel?'checked':''}>
      <div class="mut">${d.vendor}</div>
      <div><code>${d.id}</code><div class="mut">${d.name||''}</div></div>
      <div class="mut">${d.input_modalities}</div>
      <div class="mut">${ctx(d.context_window)}</div>
      <div class="mut">${d.input_price}/${d.output_price}</div>
      <div><span class="badge ${cls}">${lab}</span>${d.probe_latency?`<div class="mut">${d.probe_latency}s</div>`:''}</div>
      <div class="mut">${d.note}${d.probe_error?'<br><span style="color:#f85149">'+d.probe_error.slice(0,90)+'</span>':''}</div>
    </label>`;
  }).join('')||'<p class="mut">无匹配项</p>';
  document.querySelectorAll('input[type=checkbox]').forEach(cb=>{cb.onchange=()=>{
    cb.checked?sel.add(cb.dataset.id):sel.delete(cb.dataset.id);save();counts();render();};});
}
function counts(){document.getElementById('c').textContent=sel.size;
  document.getElementById('out').textContent=[...sel].join(' ')||'—';}
const cp=t=>navigator.clipboard.writeText(t).then(()=>alert('已复制:\n'+t)).catch(()=>prompt('复制:',t));
document.getElementById('q').oninput=render; selV.onchange=render; document.getElementById('vd').onchange=render;
document.getElementById('onlyrec').onclick=e=>{const b=e.currentTarget;b.dataset.on=b.dataset.on==='1'?'0':'1';
  b.textContent=b.dataset.on==='1'?'显示全部':'只看推荐';render();};
document.getElementById('clear').onclick=()=>{sel.clear();save();counts();render();};
document.getElementById('copy').onclick=()=>cp([...sel].join('\n'));
document.getElementById('copy2').onclick=()=>cp([...sel].join('\n'));
document.getElementById('warn').innerHTML='<b>元数据误报（声称可发图，实测不可用，已从候选中剔除）：</b><br>'+
  Object.entries(EX).map(([k,v])=>`• <code>${k}</code> — ${v}`).join('<br>');
counts();render();
</script></body></html>
"""

if __name__ == "__main__":
    main()
