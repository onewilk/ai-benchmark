#!/usr/bin/env python3
"""Declare image input for selected models in the DSH settings file.

DSH gates image input on the model's declared modalities (pi-ai catalog, which
is stale for brand-new models). The pi-ai provider schema supports an explicit
`input:` field on a model entry that overrides the catalog, so we add it for the
models we verified accept images through the router.

Idempotent: re-running only reports "already declared".
Usage:
  python3 patch_settings_input.py            # dry-run (show diff)
  python3 patch_settings_input.py --apply    # write + timestamped backup
"""
import os, re, shutil, sys, time

import config

SETTINGS = str(config.SETTINGS_FILE)

# Final benchmark set: every participant gets an explicit declaration so the
# harness gate is uniform across models (a router route without catalog data
# so an undeclared model can never receive an image regardless of real ability).
TARGETS = [
    "openai/gpt-5.6-sol",
    "anthropic/claude-opus-5",
    "google/gemini-3.8-flash",
    "deepseek/deepseek-v4.1-flash",
    "ali/qwen3.8-max-0902",
    "bytedance/doubao-seed-2-1-pro",
    "moonshot/kimi-k3",
    "bigmodel/glm-5.3-flash",
]
DECL = "input: [text, image]"


def patch(text):
    lines = text.splitlines(keepends=True)
    out, changes, missing = [], [], []
    i = 0
    seen = set()
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.match(r"^(\s*)- id:\s*(\S+)\s*$", line)
        if m and m.group(2) in TARGETS:
            indent, mid = m.group(1), m.group(2)
            seen.add(mid)
            # look ahead over this entry's fields
            j = i + 1
            field_indent = None
            while j < len(lines) and re.match(r"^\s*- id:", lines[j]) is None:
                if lines[j].strip() and field_indent is None:
                    field_indent = re.match(r"^(\s*)", lines[j]).group(1)
                if re.match(r"^\s*input:", lines[j]):
                    changes.append((mid, "already declared"))
                    break
                j += 1
            else:
                j = len(lines)
            if j < len(lines) and re.match(r"^\s*input:", lines[j]):
                # already there: copy through untouched
                while i + 1 < len(lines) and re.match(r"^\s*- id:", lines[i + 1]) is None:
                    i += 1
                    out.append(lines[i])
                i += 1
                continue
            field_indent = field_indent or (indent + "  ")
            # insert right after the entry's `name:` line, else right after `- id:`
            insert_at = i
            k = i + 1
            while k < len(lines) and re.match(r"^\s*- id:", lines[k]) is None:
                if re.match(r"^\s*name:", lines[k]):
                    insert_at = k
                    break
                k += 1
            out.append(f"{field_indent}{DECL}\n")
            changes.append((mid, "declared"))
            # splice the remaining fields of this entry after the inserted line
            k = i + 1
            while k < len(lines) and re.match(r"^\s*- id:", lines[k]) is None:
                out.append(lines[k])
                k += 1
            i = k
            continue
        i += 1
    missing = [t for t in TARGETS if t not in seen]
    return "".join(out), changes, missing


def prune(text):
    """Remove our declaration from any model outside TARGETS."""
    lines = text.splitlines(keepends=True)
    out, removed, cur = [], [], None
    for line in lines:
        m = re.match(r"^\s*- id:\s*(\S+)\s*$", line)
        if m:
            cur = m.group(1)
        if DECL in line and cur not in TARGETS:
            removed.append(cur)
            continue
        out.append(line)
    return "".join(out), removed


def declared_models(text):
    cur, found = None, set()
    for line in text.splitlines():
        m = re.match(r"\s*- id:\s*(\S+)\s*$", line)
        if m:
            cur = m.group(1)
        if DECL in line and cur:
            found.add(cur)
    return found


def main():
    apply = "--apply" in sys.argv
    do_prune = "--prune" in sys.argv
    text = open(SETTINGS).read()
    new, changes, missing = patch(text)
    print(f"settings: {SETTINGS}")
    for mid, what in changes:
        print(f"  {'~' if what == 'already declared' else '+'} {mid:<40} {what}")
    if missing:
        print("  !! not found in settings:", ", ".join(missing))
    if do_prune:
        new, removed = prune(new)
        for mid in removed:
            print(f"  - {mid:<40} pruned (left the benchmark set)")
    if new == text:
        print("no change needed.")
        return
    declared = declared_models(new)
    print(f"\ndeclared models after patch: {len(declared)} -> {sorted(declared)}")
    if not apply:
        print("\n(dry-run) re-run with --apply to write.")
        return
    if declared != set(TARGETS):
        print("refusing to write: declared set != target set")
        sys.exit(1)
    backup = f"{SETTINGS}.bak-benchmark-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(SETTINGS, backup)
    open(SETTINGS, "w").write(new)
    print(f"written. backup -> {backup}")


if __name__ == "__main__":
    main()
