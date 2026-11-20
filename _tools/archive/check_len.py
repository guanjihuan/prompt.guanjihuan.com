#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""改写后自检：打印每个条目的标题、正文字数、简洁表达字数，并标出常见问题。

用法：python _tools/archive/check_len.py [文件名 ...]
不带参数时检查 src/prompts/ 下全部文件。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "prompts")

TITLE_RE = re.compile(r"^##\s+(.*\S)\s*$")
ID_RE = re.compile(r"^<!--\s*id:\s*(.*?)\s*-->\s*$", re.I)
TAG_RE = re.compile(r"^<!--\s*t:\s*(.*?)\s*-->\s*$", re.I)
SHORT_RE = re.compile(r"^<!--\s*s:\s*(.*?)\s*-->\s*$", re.I)

VAGUE = ["全面", "系统", "深入", "高效", "精细", "完善", "优化", "确保",
         "有效", "良好", "充分", "合理", "大幅"]
NEG = ["不", "无", "非", "未", "别", "勿"]
FILLER = ["便于", "有据可依", "一目了然", "以便", "从而", "得以"]


def _dun_runs(text):
    """返回每一处顿号连排的条目数（一段连续的顿号串联算一处）。"""
    runs = []
    for m in re.finditer(r"[^，。；：！？,;:!?\s]*(?:、[^，。；：！？,;:!?\s]*)+", text):
        runs.append(m.group(0).split("、"))
    return runs


def check(path):
    lines = open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    items, cur = [], None
    for line in lines:
        if TITLE_RE.match(line):
            if cur:
                items.append(cur)
            cur = {"title": TITLE_RE.match(line).group(1), "id": "", "short": "",
                   "body": []}
            continue
        if cur is None:
            continue
        if (m := ID_RE.match(line)):
            cur["id"] = m.group(1)
            continue
        if (m := TAG_RE.match(line)):
            continue
        if (m := SHORT_RE.match(line)):
            cur["short"] = m.group(1).strip()
            continue
        cur["body"].append(line)
    if cur:
        items.append(cur)

    rel = os.path.basename(path)
    for it in items:
        body = "\n".join(it["body"]).strip()
        n = len(body)
        sents = [s for s in re.split(r"[。！？]", body) if s.strip()]
        flags = []
        if n < 55:
            flags.append("正文过短")
        if n > 100:
            flags.append("正文过长")
        if len(sents) < 2:
            flags.append("句子太少")
        if len(sents) > 4:
            flags.append("句子太多")
        if it["short"] and len(it["short"]) >= n:
            flags.append("简洁版不短于正文")
        if it["short"] and len(it["short"]) > 38:
            flags.append("简洁版过长")
        if "\n" in body.strip():
            flags.append("正文多行")
        hits = [w for w in VAGUE if w in body]
        if hits:
            flags.append("空泛词:" + "/".join(hits))
        f = [w for w in FILLER if w in body]
        if f:
            flags.append("铺垫语:" + "/".join(f))
        if any(len(run) > 4 for run in _dun_runs(body)):
            flags.append("顿号过多")
        print("%-14s %-16s %3d字 %2d句 s=%-3s %s" % (
            rel, it["title"][:16], n, len(sents),
            (len(it["short"]) if it["short"] else "-"),
            ("⚠ " + "，".join(flags)) if flags else "ok"))


def main():
    files = sys.argv[1:]
    if not files:
        files = [os.path.join(SRC, fn) for fn in sorted(os.listdir(SRC))
                 if fn.endswith(".md")]
    for p in files:
        check(p if os.path.isabs(p) else os.path.join(SRC, p))


if __name__ == "__main__":
    main()
