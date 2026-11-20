# -*- coding: utf-8 -*-
"""覆盖度审计（已归档）：日志中的提示词 vs 已收录提示词库，找出未覆盖的任务方向。

按 5 字 n-gram 重合率判断一条日志提示词在库里有没有对应的条目。

**为什么归档**：库内条目都被改写成统一的「需求句式」，与日志原话的字面重合
天然偏低——实测 6842 条唯一提示词里，阈值取 0.55 判出 6839 条「未覆盖」，
而把阈值一路降到 0.0 也只降到 6449 条。这个信号量的是文风差异，不是主题覆盖，
噪声远大于信息。任务方向覆盖改由 gaps.py 的关键词探测负责（当前 0 缺口）。

留在这里备查：若将来改用语义相似度而非字面 n-gram，可以从这里接着做。

用法：
    python _tools/archive/coverage.py
"""
import collections, os, re, sys

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from console_utf8 import use_utf8_console
use_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logload

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "prompts")

# 低于这个重合率算「库里没有对应条目」
THRESHOLD = 0.55


def norm(s):
    s = re.sub(r"^/loop\s*", "", s.strip())
    return re.sub(r"[\s，。、；：,.;:!?！？「」“”\"'()（）\[\]【】<>—\-…·|/\\]+", "", s).lower()


def ngrams(s, n=5):
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


libg = ngrams(norm(logload.lib_text(SRC)))

logs = [c for _, c in logload.load_prompts()]
cnt = collections.Counter(norm(c) for c in logs)

low = []
for s, n in cnt.items():
    if len(s) < 12:
        continue
    g = ngrams(s)
    if not g:
        continue
    hit = len(g & libg) / len(g)
    if hit < THRESHOLD:
        low.append((n, hit, s))

low.sort(key=lambda x: (-x[0], x[1]))
print(f"日志唯一提示词: {len(cnt)}  低覆盖(<{THRESHOLD}): {len(low)}\n")
with open(os.path.join(ROOT, "_tools", "lowcov.txt"), "w", encoding="utf-8") as f:
    for n, h, s in low:
        f.write(f"[{n}|{h:.2f}] {s}\n")
for n, h, s in low[:120]:
    print(n, f"{h:.2f}", s[:130])
