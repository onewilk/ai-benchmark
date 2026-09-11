#!/usr/bin/env python3
"""集中配置：整个 benchmark 的可调参数只在根目录的 `.env` 里定义一次。

配置优先级（高 → 低）：
  1. 根目录 `.env`
  2. 进程环境变量
  3. 本机 DSH 自动探测（可选，用于零配置跑通；绝不写入仓库）

可用变量（全部可选，除跑探针需要路由地址与 key）：

  BENCH_BASE_URL      OpenAI 兼容路由根地址，例：https://your-router.example.com/v1
  BENCH_API_KEY       该路由的 API key（只读，不落盘）
  BENCH_PROVIDER      DSH 中的 provider id（脚本与报告里作为调用参数/展示名）
  DSH_HOME            DSH 家目录，默认 ~/.dsh
  BENCH_SESSIONS_DIR  DSH 会话转录目录，默认 $DSH_HOME/sessions

用法：
    from config import BASE_URL, API_KEY, PROVIDER, SESSIONS_DIR, SETTINGS_FILE
或按需调用 get_base_url() / get_api_key()（带 DSH 兜底与明确报错）。
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def _parse_env_file(path):
    """Minimal KEY=VALUE parser: comments, blanks, optional quotes, optional `export`."""
    out = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.split(" #", 1)[0].strip().strip('"').strip("'")
        out[key.strip()] = val
    return out


ENV = _parse_env_file(ENV_FILE)


def get(name, default=None):
    """`.env` 优先，其次进程环境变量，最后默认值。"""
    if ENV.get(name):
        return ENV[name]
    if os.environ.get(name):
        return os.environ[name]
    return default


# ---- 路径类（有默认值，通常无需修改） ----
DSH_HOME = Path(get("DSH_HOME", "~/.dsh")).expanduser()
SETTINGS_FILE = DSH_HOME / "settings.yaml"
CREDENTIALS_FILE = DSH_HOME / ".credentials.yaml"
SESSIONS_DIR = Path(get("BENCH_SESSIONS_DIR", str(DSH_HOME / "sessions"))).expanduser()
DATA_DIR = ROOT / "data"
PAPER_DIR = DATA_DIR / "paper"
QUESTIONS_DIR = PAPER_DIR / "questions"
PROBES_DIR = ROOT / "probes"

# ---- 展示/调用用的 provider id（不涉及密钥与地址） ----
PROVIDER = get("BENCH_PROVIDER", "<your-provider>")


def _detect_from_dsh():
    """从本机 DSH 配置推断 (baseURL, apiKeyEnv, key)，避免把密钥写进仓库。

    返回第一个同时声明了 baseURL 与 apiKeyEnv 的 provider；找不到则返回 (None, None, None)。
    """
    try:
        import yaml
    except ImportError:
        return None, None, None
    if not SETTINGS_FILE.exists():
        return None, None, None
    try:
        cfg = yaml.safe_load(SETTINGS_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return None, None, None
    providers = ((cfg.get("llm-pi-ai") or {}).get("providers")) or {}
    for _pid, prov in providers.items():
        url = (prov or {}).get("baseURL")
        env_name = (prov or {}).get("apiKeyEnv")
        if not url or not env_name:
            continue
        key = None
        if CREDENTIALS_FILE.exists():
            try:
                refs = (yaml.safe_load(CREDENTIALS_FILE.read_text(encoding="utf-8")) or {}).get("refs") or {}
                key = refs.get(env_name)
            except Exception:
                key = None
        return url, env_name, key
    return None, None, None


def get_base_url():
    """探针用的 chat/completions 端点。"""
    url = get("BENCH_BASE_URL")
    if not url:
        detected, _env_name, _key = _detect_from_dsh()
        url = detected
    return url


def get_api_key():
    """探针用的 API key（只从 .env / 环境变量 / 本机 DSH 凭证读取，绝不写入仓库）。"""
    key = get("BENCH_API_KEY")
    if not key:
        _url, _env_name, detected = _detect_from_dsh()
        key = detected
    return key


def require_base_url():
    url = get_base_url()
    if not url:
        raise SystemExit(
            "未配置路由地址。请在仓库根目录的 .env 里填写：\n"
            "  BENCH_BASE_URL=https://your-router.example.com/v1\n"
            "（或设置同名环境变量；该值不会被提交）")
    return url.rstrip("/")


def require_api_key():
    key = get_api_key()
    if not key:
        raise SystemExit(
            "未配置 API key。请在仓库根目录的 .env 里填写：\n"
            "  BENCH_API_KEY=your-key-here\n"
            "（或设置同名环境变量；该值不会被提交）")
    return key


if __name__ == "__main__":
    # 便于自检：只显示是否已配置与来源，不打印任何密钥内容
    print(f".env 文件: {ENV_FILE}  {'存在' if ENV_FILE.exists() else '不存在'}")
    print(f"BENCH_BASE_URL: {'已配置' if get_base_url() else '未配置'}")
    print(f"BENCH_API_KEY : {'已配置（长度 %d）' % len(get_api_key()) if get_api_key() else '未配置'}")
    print(f"BENCH_PROVIDER: {PROVIDER}")
    print(f"DSH_HOME      : {DSH_HOME}")
    print(f"SESSIONS_DIR  : {SESSIONS_DIR}  {'存在' if SESSIONS_DIR.exists() else '不存在'}")
    print(f"QUESTIONS_DIR : {QUESTIONS_DIR}  {'存在' if QUESTIONS_DIR.exists() else '不存在'}")
