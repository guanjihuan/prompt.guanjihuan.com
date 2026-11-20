# -*- coding: utf-8 -*-
"""从本机日志提取全部提示词，按频次与项目分布统计。

产物（counts.json / projects.json / top.txt / top_proj.txt）都写在 _tools/ 下，
已加入 .gitignore：其中含本机项目路径与使用频次，不进版本库。
"""
import collections, json, os, re, sys

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console
use_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logload

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_tools")


def norm(s):
    s = re.sub(r"^/loop\s*", "", s.strip())
    s = re.sub(r"\s+", " ", s)
    return s.strip()


raw = logload.load_prompts()
projcnt = collections.Counter(p for p, _ in raw)

cnt = collections.Counter(norm(c) for _, c in raw)

with open(os.path.join(OUT, "counts.json"), "w", encoding="utf-8") as f:
    json.dump(cnt.most_common(), f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "projects.json"), "w", encoding="utf-8") as f:
    json.dump(projcnt.most_common(), f, ensure_ascii=False, indent=1)

with open(os.path.join(OUT, "top.txt"), "w", encoding="utf-8") as f:
    for s, n in cnt.most_common(400):
        f.write(f"[{n}] {s}\n\n")

with open(os.path.join(OUT, "top_proj.txt"), "w", encoding="utf-8") as f:
    for s, n in projcnt.most_common(120):
        f.write(f"[{n}] {s}\n\n")

print("prompts", len(raw), "unique", len(cnt), "projects", len(projcnt))
print("count>=2:", sum(1 for _, n in cnt.items() if n >= 2))
print("count>=5:", sum(1 for _, n in cnt.items() if n >= 5))
