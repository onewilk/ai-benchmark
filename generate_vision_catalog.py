#!/usr/bin/env python3
"""Build the vision-capable model catalog from a router's /models metadata.

Inputs : data/all_models_raw.json   (router /models metadata)
         probes/probe_results.json  (live image probes)
Outputs: data/vision_models.json    (machine readable catalog)
         vision_models.html         (interactive picker)
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "all_models_raw.json")
PROBE = os.path.join(HERE, "probes", "probe_results.json")


def verdict_of(res):
    """Classify a probe result into a vision verdict."""
    if not res:
        return "not-probed", None
    if res.get("error"):
        return "error", res["error"]
    txt = (res.get("text") or "")
    low = txt.lower()
    code_ok = "7291" in txt
    color_ok = "red" in low
    misread = bool(re.search(r"7[0-9]{3}", txt)) and not code_ok
    if code_ok and color_ok:
        return "verified", None
    if code_ok or color_ok or misread:
        return "vision-ok", None          # clearly saw the image, imperfect output
    return "inconclusive", None


def main():
    raw = json.load(open(RAW))
    probe = json.load(open(PROBE)) if os.path.exists(PROBE) else {}

    catalog = []
    for mid, m in raw.items():
        arch = m.get("architecture") or {}
        inputs = arch.get("input") or ""
        meta_vision = "image" in inputs
        p = probe.get(mid)
        v, err = verdict_of(p)
        probed_vision = v in ("verified", "vision-ok")
        if not meta_vision and not probed_vision:
            continue
        price = m.get("pricing") or {}
        catalog.append({
            "id": mid,
            "name": m.get("name"),
            "company": m.get("company") or "Other",
            "input_modalities": inputs or "(未标注)",
            "output_modalities": arch.get("output") or "",
            "context_window": m.get("context_window"),
            "max_tokens": m.get("max_tokens"),
            "input_price": price.get("input_price"),
            "output_price": price.get("output_price"),
            "image_price": price.get("image_price"),
            "currency": price.get("currency") or "CNY",
            "metadata_vision": meta_vision,
            "probe_verdict": v,
            "probe_ok": probed_vision,
            "probe_latency": (p or {}).get("latency"),
            "probe_text": ((p or {}).get("text") or "")[:200] if p else None,
            "probe_error": err,
            "source": "metadata+probe" if meta_vision and probed_vision
                      else "probe-only" if probed_vision else "metadata-only",
        })

    catalog.sort(key=lambda r: (r["company"], r["id"]))
    json.dump(catalog, open(os.path.join(HERE, "data", "vision_models.json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"catalog: {len(catalog)} models "
          f"(metadata {sum(1 for c in catalog if c['metadata_vision'])}, "
          f"probe-verified {sum(1 for c in catalog if c['probe_ok'])})")

    by_company = {}
    for c in catalog:
        by_company.setdefault(c["company"], []).append(c)
    rows = "\n".join(
        f'<option value="{v}">{v} ({len(by_company[v])})</option>'
        for v in sorted(by_company)
    )
    data_js = json.dumps(catalog, ensure_ascii=False)
    companies_js = json.dumps({k: [c["id"] for c in v] for k, v in by_company.items()},
                              ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__DATA__", data_js).replace("__COMPANIES__", companies_js).replace("__VENDOR_OPTIONS__", rows)
    open(os.path.join(HERE, "vision_models.html"), "w").write(html)
    print("html   -> vision_models.html")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>多模态(可发图)模型清单</title>
<style>
  :root{--bg:#0e1116;--panel:#161b22;--line:#252c36;--fg:#e6edf3;--mut:#8b949e;
        --ok:#3fb950;--warn:#d29922;--err:#f85149;--acc:#4493f8;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
  header{position:sticky;top:0;z-index:9;background:rgba(14,17,22,.96);border-bottom:1px solid var(--line);padding:14px 20px}
  h1{margin:0 0 4px;font-size:17px}
  .sub{color:var(--mut);font-size:12px}
  .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
  input[type=search],select{background:#0d1117;border:1px solid var(--line);color:var(--fg);padding:7px 10px;border-radius:7px;font-size:13px}
  input[type=search]{min-width:280px}
  button{background:#21262d;border:1px solid var(--line);color:var(--fg);padding:7px 12px;border-radius:7px;cursor:pointer;font-size:13px}
  button:hover{border-color:var(--acc)}
  button.primary{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
  main{padding:16px 20px 80px;max-width:1400px;margin:0 auto}
  section{margin-bottom:22px}
  h2{font-size:14px;color:var(--acc);border-bottom:1px solid var(--line);padding-bottom:6px;margin:18px 0 10px;position:sticky;top:118px;background:var(--bg)}
  .row{display:grid;grid-template-columns:32px minmax(220px,1.3fr) 1.2fr 110px 120px 96px 150px;gap:10px;align-items:center;
       padding:7px 10px;border:1px solid transparent;border-radius:8px}
  .row:hover{background:var(--panel);border-color:var(--line)}
  .row.sel{background:#12261a;border-color:#2ea04366}
  .row.head{color:var(--mut);font-size:12px;font-weight:600;position:sticky;top:160px;background:var(--bg)}
  code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:#c9d1d9}
  .mut{color:var(--mut);font-size:12px}
  .badge{font-size:11px;padding:2px 7px;border-radius:20px;border:1px solid;white-space:nowrap;display:inline-block}
  .b-ok{color:var(--ok);border-color:#2ea04366;background:#2ea0431a}
  .b-vo{color:var(--warn);border-color:#d2992266;background:#d299221a}
  .b-no{color:var(--mut);border-color:var(--line)}
  .b-er{color:var(--err);border-color:#f8514966;background:#f851491a}
  .src{font-size:11px;color:var(--mut)}
  .src.p{color:#d2a8ff}
  input[type=checkbox]{width:16px;height:16px;accent-color:var(--acc)}
  #selbar{position:fixed;bottom:0;left:0;right:0;background:#161b22ee;border-top:1px solid var(--line);
          padding:12px 20px;display:flex;gap:12px;align-items:center;backdrop-filter:blur(6px)}
  #selout{font:12px ui-monospace,monospace;color:var(--ok);flex:1;overflow:auto;white-space:nowrap}
  .hidden{display:none!important}
</style>
</head>
<body>
<header>
  <h1>支持多模态(可直接发图)的模型清单</h1>
  <div class="sub">数据源：模型路由的 <code>/v1/models</code> 元数据(<code>architecture.input</code>) + 真实发图探针实测。
    共 <b id="total"></b> 个候选模型，勾选你想要的模型即可导出 id（选择保存在本地浏览器）。</div>
  <div class="bar">
    <input type="search" id="q" placeholder="搜索模型 id / 名称 / 厂商…">
    <select id="vendor"><option value="">全部厂商</option>__VENDOR_OPTIONS__</select>
    <select id="verdict">
      <option value="">全部验证状态</option>
      <option value="verified">✅ 实测已读图</option>
      <option value="vision-ok">⚠️ 实测部分正确</option>
      <option value="metadata-only">仅元数据声明(未实测通过)</option>
      <option value="error">❌ 调用失败</option>
    </select>
    <button id="selview">只看已选 (<span id="cnt">0</span>)</button>
    <button id="clear">清空选择</button>
    <button class="primary" id="copy">复制选中 id</button>
  </div>
</header>
<main>
  <div class="row head">
    <div></div><div>模型</div><div>输入模态</div><div>上下文</div><div>输出上限</div><div>价格(in/out)</div><div>发图实测</div>
  </div>
  <div id="list"></div>
</main>
<div id="selbar">
  <span class="mut">已选 <b id="cnt2">0</b> 个：</span>
  <span id="selout">—</span>
  <button id="copy2" class="primary">复制</button>
</div>
<script>
const DATA = __DATA__;
const store = JSON.parse(localStorage.getItem('ssy_pick') || '[]');
const sel = new Set(store);
const fmtCtx = n => n>=1e6 ? (n/1e6)+'M' : n>=1000 ? Math.round(n/1000)+'K' : n;
const vb = {verified:['b-ok','✅ 已读图'],'vision-ok':['b-vo','⚠️ 部分正确'],
            'metadata-only':['b-no','— 未通过'],error:['b-er','❌ 失败'],'not-probed':['b-no','— 未测'],inconclusive:['b-er','❌ 未见图']};
function verdict(r){
  if(r.probe_verdict==='verified'||r.probe_verdict==='vision-ok') return vb[r.probe_verdict];
  if(r.probe_verdict==='error') return vb.error;
  if(r.probe_verdict && r.probe_verdict!=='not-probed') return vb.inconclusive;
  return vb['metadata-only'];
}
function render(){
  const q=document.getElementById('q').value.toLowerCase();
  const v=document.getElementById('vendor').value;
  const vd=document.getElementById('verdict').value;
  const onlySel=document.getElementById('selview').dataset.on==='1';
  const groups={};
  DATA.forEach(r=>{
    if(v && r.company!==v) return;
    if(q && !(r.id+r.name+r.company).toLowerCase().includes(q)) return;
    const isSel=sel.has(r.id);
    if(onlySel && !isSel) return;
    if(vd==='metadata-only' && r.probe_ok) return;
    if(vd && vd!=='metadata-only' && r.probe_verdict!==vd) return;
    (groups[r.company]=groups[r.company]||[]).push(r);
  });
  let html='';
  Object.keys(groups).sort().forEach(c=>{
    html+=`<section><h2>${c} · ${groups[c].length}</h2>`;
    groups[c].forEach(r=>{
      const [cls,label]=verdict(r);
      const isSel=sel.has(r.id);
      html+=`<label class="row ${isSel?'sel':''}">
        <input type="checkbox" data-id="${r.id}" ${isSel?'checked':''}>
        <div><code>${r.id}</code><div class="mut">${r.name||''}</div></div>
        <div class="mut">${r.input_modalities}</div>
        <div class="mut">${fmtCtx(r.context_window)}</div>
        <div class="mut">${fmtCtx(r.max_tokens)}</div>
        <div class="mut">${r.input_price}/${r.output_price}</div>
        <div><span class="badge ${cls}">${label}</span>
          <div class="src ${r.source==='probe-only'?'p':''}">${r.source==='probe-only'?'元数据漏报+实测通过':(r.source==='metadata+probe'?'元数据+实测':'仅元数据')}</div>
          ${r.probe_latency?`<div class="mut">${r.probe_latency}s</div>`:''}
        </div>
      </label>`;
    });
    html+='</section>';
  });
  document.getElementById('list').innerHTML=html||'<p class="mut">没有匹配的模型。</p>';
  document.querySelectorAll('input[type=checkbox]').forEach(cb=>{
    cb.onchange=()=>{ cb.checked?sel.add(cb.dataset.id):sel.delete(cb.dataset.id);
      localStorage.setItem('ssy_pick',JSON.stringify([...sel])); updateCounts(); render(); };
  });
}
function updateCounts(){
  document.getElementById('cnt').textContent=sel.size;
  document.getElementById('cnt2').textContent=sel.size;
  document.getElementById('selout').textContent=[...sel].join(', ')||'—';
}
document.getElementById('q').oninput=render;
document.getElementById('vendor').onchange=render;
document.getElementById('verdict').onchange=render;
document.getElementById('selview').onclick=e=>{
  const el=e.currentTarget; el.dataset.on=el.dataset.on==='1'?'0':'1';
  el.textContent=el.dataset.on==='1'?`显示全部 (${DATA.length})`:`只看已选 (${sel.size})`; render();
};
document.getElementById('clear').onclick=()=>{sel.clear();localStorage.setItem('ssy_pick','[]');updateCounts();render();};
const copyTxt=t=>navigator.clipboard.writeText(t).then(()=>alert('已复制：\n'+t)).catch(()=>prompt('手动复制：',t));
document.getElementById('copy').onclick=()=>copyTxt([...sel].join('\n'));
document.getElementById('copy2').onclick=()=>copyTxt([...sel].join('\n'));
document.getElementById('total').textContent=DATA.length;
updateCounts(); render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
