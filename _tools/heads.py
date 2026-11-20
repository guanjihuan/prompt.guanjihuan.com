# -*- coding: utf-8 -*-
"""按“指令开头”聚类日志提示词，暴露任务方向。"""
import collections, os, re, sys

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console
use_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def head(s, n=8):
    s = re.sub(r"^/loop\s*", "", s.strip())
    s = re.sub(r"^[\s，。、；：,.;:!?！？]+", "", s)
    return s[:n]


raw = [c for _, c in logload.load_prompts()]
groups = collections.defaultdict(list)
for c in raw:
    groups[head(c)].append(c)

rows = []
for h, lst in groups.items():
    # 只保留有实质内容的一组
    substantive = [x for x in lst if len(x) >= 14]
    rows.append((len(substantive), h, substantive))
rows.sort(key=lambda r: -r[0])

with open(os.path.join(ROOT, "_tools", "heads.txt"), "w", encoding="utf-8") as f:
    for n, h, lst in rows:
        if n < 2:
            continue
        f.write(f"### [{n}] {h}\n")
        seen = set()
        for x in lst:
            k = x[:40]
            if k in seen:
                continue
            seen.add(k)
            f.write(f"    - {x[:180]}\n")
        f.write("\n")

print("groups:", len(rows))
print("groups with >=2:", sum(1 for r in rows if r[0] >= 2))
print("groups with >=5:", sum(1 for r in rows if r[0] >= 5))
print("groups with >=15:", sum(1 for r in rows if r[0] >= 15))
