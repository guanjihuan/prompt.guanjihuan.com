# -*- coding: utf-8 -*-
"""读取提示词库的公共入口，供三个审计脚本共用。

审计脚本（content_audit.py / style_audit.py / desensitize_scan.py）都要逐条
读 src/prompts/ 下的条目。之前各写了一份解析，规则并不一致：

- build.py 的解析对代码块做了 fence 感知（正文里的 `## ` 不会被误判成新条目），
  三个审计脚本没有——正文里一旦出现代码块，审计会凭空多出几条来；
- 三个脚本对 `<!-- id/t/s -->` 注释的处理各不相同，扫出来的范围也就不同。

统一到本模块后，解析规则只有 build.py 一处：审计看到的，就是构建时看到的。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import build as site_build  # noqa: E402


def load(prompt_dir=None):
    """读全部条目，返回 [{file, cat, title, id, tags, short, note, content}]。

    content 是条目正文（不含 id/t/s/n 注释行），与构建产物里的正文一致。
    """
    prompt_dir = prompt_dir or site_build.PROMPT_DIR
    out = []
    for fn in sorted(os.listdir(prompt_dir)):
        if not fn.endswith(".md"):
            continue
        errors = []
        meta, items = site_build.parse_category(os.path.join(prompt_dir, fn), errors)
        cat = meta.get("name", fn)
        for it in items:
            out.append({
                "file": fn,
                "cat": cat,
                "title": it["title"],
                "id": it["id"],
                "tags": it["tags"],
                "short": it["short"],
                "note": it["note"],
                "content": it["content"],
            })
    return out


def scan_blob(it):
    """条目里所有会被用户看到的文字：标题、正文、标签、简洁表达。

    脱敏扫描用这个整体——专名可能藏在标签或简洁表达里，只扫正文会漏。
    """
    parts = [it["title"], it["content"]]
    parts.extend(it["tags"])
    if it["short"]:
        parts.append(it["short"])
    return "\n".join(parts)
