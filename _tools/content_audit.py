# -*- coding: utf-8 -*-
"""内容审计：标题、标签、段落、详略表达、标题雷同与正文近重复。"""
import os, re, difflib, itertools, sys

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console
use_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promptlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

items = promptlib.load()

out = []
w = out.append
w("=== 条目总数: %d ===\n" % len(items))

# ---- 1. 标题长度 ----
w("--- 标题长度分布 ---")
lens = sorted(len(it["title"]) for it in items)
w("中位数 %d  平均 %.1f  最长 %d  最短 %d" % (
    lens[len(lens)//2], sum(lens)/len(lens), lens[-1], lens[0]))
bad_titles = [it for it in items if not 6 <= len(it["title"]) <= 12]
w("不在 6~12 字范围的标题 %d 条：" % len(bad_titles))
for it in sorted(bad_titles, key=lambda x: (len(x["title"]), x["cat"], x["title"])):
    w("  %2d [%s] %s" % (len(it["title"]), it["cat"], it["title"]))

# ---- 2. 结构、标签与详略表达 ----
w("\n--- 结构、标签与详略表达 ---")
bad_tags = [it for it in items if not 2 <= len(it["tags"]) <= 3]
w("标签不是 2~3 个：%d 条" % len(bad_tags))
for it in bad_tags:
    w("  [%s] %s：%s" % (it["cat"], it["title"], ", ".join(it["tags"])))
bad_paras = [it for it in items if "\n" in it["content"]]
w("详细正文不是一个自然段：%d 条" % len(bad_paras))
for it in bad_paras:
    w("  [%s] %s" % (it["cat"], it["title"]))
bad_shorts = [it for it in items if it["short"] and
              (it["short"] == it["content"] or len(it["short"]) >= len(it["content"]) or
               len(it["short"]) > 60)]
w("简洁表达重复、未缩短或超过 60 字：%d 条" % len(bad_shorts))
for it in bad_shorts:
    w("  [%s] %s（简洁 %d 字 / 详细 %d 字）" %
      (it["cat"], it["title"], len(it["short"]), len(it["content"])))
w("简洁表达总数：%d" % sum(bool(it["short"]) for it in items))

# ---- 3. 标题雷同（去标点后互为子串/高度相似）----
w("\n--- 标题高度相似对（>=0.72）---")
def norm(s): return re.sub(r"[，。、；：,.;:!?\s（）()\[\]「」]", "", s)
pairs = []
for a, b in itertools.combinations(items, 2):
    na, nb = norm(a["title"]), norm(b["title"])
    if na == nb:
        pairs.append((1.0, a, b)); continue
    r = difflib.SequenceMatcher(None, na, nb).ratio()
    if r >= 0.72:
        pairs.append((r, a, b))
pairs.sort(key=lambda x: -x[0])
for r, a, b in pairs:
    w("  %.2f  [%s] %s   <=>   [%s] %s" % (r, a["cat"], a["title"], b["cat"], b["title"]))

# ---- 4. 正文近重复 ----
w("\n--- 正文近重复对（相似度 >= 0.62）---")
dpairs = []
for a, b in itertools.combinations(items, 2):
    ca, cb = a["content"], b["content"]
    if min(len(ca), len(cb)) < 30: continue
    r = difflib.SequenceMatcher(None, ca, cb).ratio()
    if r >= 0.62:
        dpairs.append((r, a, b))
dpairs.sort(key=lambda x: -x[0])
w("共 %d 对" % len(dpairs))
for r, a, b in dpairs:
    w("  %.2f  [%s] %s  <=>  [%s] %s" % (r, a["cat"], a["title"], b["cat"], b["title"]))

# ---- 5. 标题与正文首句雷同（冗余展示）----
w("\n--- 标题与正文首句高度重合（>=0.55）---")
n = 0
for it in items:
    first = it["content"].split("\n")[0]
    if len(first) < 8: continue
    r = difflib.SequenceMatcher(None, norm(it["title"]), norm(first)).ratio()
    if r >= 0.55:
        n += 1
        w("  %.2f  %s | %s" % (r, it["title"], first[:50]))
w("合计 %d 条" % n)

open(os.path.join(ROOT, "_tools", "content_audit.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:40]))
print("\n... 完整报告见 _tools/content_audit.txt")

# 卡口口径（与 README 的「发现问题时返回非 0」一致）：
# 结构硬伤 —— 正文不是一个自然段、简洁表达与正文重复或不短于正文 —— 直接拦截；
# 标题长度、标签数、标题/正文相似对是体例参考，出现在报告里但不拦截。
structural_violations = len(bad_paras) + len(bad_shorts)
sys.exit(1 if structural_violations else 0)
