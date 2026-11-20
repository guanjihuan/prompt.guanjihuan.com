#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按 src/prompts/ 的实际内容，重生成 README 里的规模数字与分区表。

这个脚本曾按旧版 README 的结构整段替换表格；README 改版后整段替换已不适用，
现在改成只改三处数字：开头的条目数、分类数，以及分区表「条数」列——
分区名与「覆盖」列的说明文字仍由人手写，脚本不动。

用法：
    python _tools/archive/readme_counts.py           # 重生成
    python _tools/archive/readme_counts.py --check   # 只核对，不改文件
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "prompts")
README = os.path.join(ROOT, "README.md")

FM_RE = re.compile(r"^---\s*$")
TITLE_RE = re.compile(r"^##\s+(.*\S)\s*$")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def collect():
    cats = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        lines = read(os.path.join(SRC, fn)).split("\n")
        meta, body = {}, []
        state = "fm"
        for line in lines:
            if state == "fm":
                if FM_RE.match(line):
                    if meta:
                        state = "body"
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
                continue
            body.append(line)
        n = len([l for l in body if TITLE_RE.match(l)])
        cats.append({
            "section": meta.get("section", "未分组"),
            "order": int(meta.get("order", 99)),
            "name": meta.get("name", ""),
            "icon": meta.get("icon", ""),
            "desc": meta.get("desc", ""),
            "n": n,
        })
    cats.sort(key=lambda c: (c["order"], c["name"]))
    return cats


def rewrite(txt, cats):
    """把 txt 里的三处数字换成实际值；分区名与说明文字保持原样。"""
    sections = []
    for c in cats:
        if not sections or sections[-1][0] != c["section"]:
            sections.append((c["section"], []))
        sections[-1][1].append(c)

    total = sum(c["n"] for c in cats)
    by_section = {sec: sum(i["n"] for i in items) for sec, items in sections}

    # 开头：这里收录了 N 条
    txt = re.sub(r"(这里收录了 )\d+( 条)", lambda m: "%s%d%s" % (m.group(1), total, m.group(2)), txt, count=1)
    # 分类数：N 个分类覆盖
    txt = re.sub(r"(\d+ 个分类覆盖)", lambda m: "%d 个分类覆盖" % len(cats), txt, count=1)
    # 分区表「条数」列
    def fix_row(m):
        sec = m.group(1)
        return "| %s | %d |" % (sec, by_section.get(sec, int(m.group(2))))
    txt = re.sub(r"^\| (\S+) \| (\d+) \|", fix_row, txt, flags=re.M)
    return txt


def main():
    check_only = "--check" in sys.argv
    cats = collect()
    txt = read(README)
    new = rewrite(txt, cats)
    total = sum(c["n"] for c in cats)
    if new == txt:
        print("README 数字与库内实际一致（%d 条 / %d 分类）" % (total, len(cats)))
        return 0
    if check_only:
        print("README 数字与库内实际不一致（实际 %d 条 / %d 分类），"
              "跑 python _tools/archive/readme_counts.py 重生成" % (total, len(cats)))
        return 1
    write(README, new)
    print("README 已重生成：%d 条 / %d 分类" % (total, len(cats)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
