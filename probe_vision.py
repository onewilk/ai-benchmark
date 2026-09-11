#!/usr/bin/env python3
"""Probe an OpenAI-compatible model router with a real image.

Verifies end-to-end multimodal input *outside* DSH: does the model itself accept
an image, independent of any harness-side capability declaration?

Configuration is deliberately read from the environment, never hard-coded, so a
credential or a private gateway URL can never be committed by accident:

配置（全部集中在仓库根目录的 .env，见 .env.example）：
  BENCH_BASE_URL  你的 OpenAI 兼容路由根地址
  BENCH_API_KEY   该路由的 API key
留空时会尝试从本机 DSH 配置自动探测。

Usage:
  python3 probe_vision.py model_id [model_id ...]
Writes results to probes/probe_results.json
"""
import base64, json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

import config

IMG = str(config.PROBES_DIR / "capability_test.png")
PROMPT = "Look at this image and reply with exactly two lines:\n1) the numeric code shown\n2) the colour of the circle\nNo extra words."






def _call(model, key, b64, limit_param, timeout):
    body = {
        "model": model,
        limit_param: 400,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    }
    req = urllib.request.Request(
        config.require_base_url() + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
    text = msg.get("content") or ""
    if isinstance(text, list):
        text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    return text.strip(), reasoning.strip(), data.get("usage", {}), time.time() - t0


def probe(model, key, timeout=90):
    b64 = base64.b64encode(open(IMG, "rb").read()).decode()
    last_err = None
    for attempt in range(2):
        param = "max_tokens"
        try:
            text, reasoning, usage, dt = _call(model, key, b64, param, timeout)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")[:300]
            if "max_tokens" in raw and "not supported" in raw:
                try:
                    text, reasoning, usage, dt = _call(model, key, b64, "max_completion_tokens", timeout)
                except urllib.error.HTTPError as e2:
                    return {"model": model, "ok": False, "latency": round(time.time(), 2), "text": "", "reasoning": "",
                            "usage": {}, "error": f"HTTP {e2.code}: {e2.read().decode(errors='replace')[:300]}"}
            else:
                return {"model": model, "ok": False, "latency": 0.0, "text": "", "reasoning": "",
                        "usage": {}, "error": f"HTTP {e.code}: {raw}"}
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            continue
        # empty content -> one retry, then fall back to the reasoning channel
        if not text and not reasoning and attempt == 0:
            continue
        combined = text or reasoning
        ok = "7291" in combined and "red" in combined.lower()
        return {"model": model, "ok": ok, "latency": round(dt, 2), "text": text[:300],
                "reasoning": reasoning[:300], "usage": usage, "error": None,
                "note": "reasoning-only" if (not text and reasoning) else None}
    return {"model": model, "ok": False, "latency": 0.0, "text": "", "reasoning": "",
            "usage": {}, "error": last_err or "empty response from model"}


def main():
    models = sys.argv[1:]
    key = config.require_api_key()
    out = {}
    workers = int(os.environ.get("MAXW", "6"))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(lambda m: probe(m, key), models):
            out[res["model"]] = res
            flag = "OK " if res["ok"] else "FAIL"
            print(f"[{flag}] {res['model']:<42} {res['latency']:>6.1f}s  "
                  f"{(res['error'] or res['text'].replace(chr(10), ' | '))[:110]}")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probes", "probe_results.json")
    prev = json.load(open(path)) if os.path.exists(path) else {}
    prev.update(out)
    json.dump(prev, open(path, "w"), ensure_ascii=False, indent=2)
    print(f"\nsaved -> {path}")


if __name__ == "__main__":
    main()
