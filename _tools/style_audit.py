# -*- coding: utf-8 -*-
"""文案质量审计：找出表达上真正有问题的条目。"""
import os, re, sys, collections

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console
use_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promptlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DELIVER = re.compile(r"(交付|保存|输出|生成|给出|写|产出|导出|提交|返回|列|整理|提供|打印|编译|存档|归档|建|做|画|检查|修复|优化|审查|核对|对比|统计|分析|解释|讲解|设计|实现|重构|部署|配置)")

items = [dict(cat=it["cat"], title=it["title"], body=it["content"])
         for it in promptlib.load()]

def sents(b):
    return [s for s in re.split(r"[。！？\n]", b) if s.strip()]

def clen(s):
    return len(re.sub(r"[，、；：,;:]", "", s))

rows = []
for it in items:
    b = it["body"]
    ss = sents(b)
    # 「多X」枚举重复
    enum = re.findall(r"多[一-龥]{1,2}", b)
    enum_dup = len(enum) - len(set(enum))
    # 顿号连排的同质短语（≥5 项且每项 2-4 字）
    runs = re.findall(r"(?:[一-龥]{2,4}、){4,}[一-龥]{2,4}", b)
    # 第 1 句只是标题复述：标题用字全在第 1 句里，且只比标题多几个字
    first = ss[0].strip() if ss else ""
    first_core = re.sub(r"[^一-鿿]", "", first)
    title_core = re.sub(r"[^一-鿿]", "", it["title"])
    echo = bool(first_core and title_core) and \
        all(c in first_core for c in title_core) and \
        len(first_core) - len(title_core) <= 3
    rows.append(dict(
        it=it,
        n=len(ss),
        maxlen=max([clen(s) for s in ss] or [0]),
        chars=len(b),
        enum_dup=enum_dup,
        runs=len(runs),
        deliver=bool(DELIVER.search(b)),
        echo=echo,
    ))

def show(title, pred, key, desc, limit=14):
    sel = [r for r in rows if pred(r)]
    sel.sort(key=key, reverse=True)
    print("\n=== %s （%d 条）" % (desc, len(sel)))
    for r in sel[:limit]:
        it = r["it"]
        print("  [%s] %s" % (it["cat"], it["title"]))
        print("      %s" % it["body"][:150].replace("\n", " "))

show("A", lambda r: r["maxlen"] >= 55, lambda r: r["maxlen"],
     "A. 单句过长（读起来会喘不过气）")
show("B", lambda r: r["enum_dup"] >= 2, lambda r: r["enum_dup"],
     "B. 同质枚举重复（「多调研、多推导、多…」）")
show("C", lambda r: r["runs"] >= 1, lambda r: r["runs"],
     "C. 顿号长串罗列")
show("D", lambda r: not r["deliver"], lambda r: r["chars"],
     "D. 没说清要交付什么")
show("E", lambda r: r["n"] <= 1 and r["chars"] < 28, lambda r: r["chars"],
     "E. 过于简略（可能缺信息）")
show("F", lambda r: r["echo"], lambda r: r["chars"],
     "F. 第 1 句只是标题复述（没说清需求与目标）")

# 卡口口径：A/C/F 是硬伤直接计入；B/E 是风格倾向只统计不拦截；
# D 的「交付」词表较宽，漏报多，同样只统计不拦截。
violations = sum(1 for r in rows if r["maxlen"] >= 55 or r["runs"] >= 1 or r["echo"])

print("\n\n=== 统计 ===")
print("条目 %d  平均字数 %.0f  平均句数 %.1f" % (
    len(rows), sum(r["chars"] for r in rows)/len(rows), sum(r["n"] for r in rows)/len(rows)))
ls = sorted(r["chars"] for r in rows)
print("字数 中位数 %d  最短 %d  最长 %d" % (ls[len(ls)//2], ls[0], ls[-1]))
print("单句 >=55 字: %d 条" % sum(1 for r in rows if r["maxlen"] >= 55))
print("枚举重复 >=2: %d 条" % sum(1 for r in rows if r["enum_dup"] >= 2))
print("顿号长串: %d 条" % sum(1 for r in rows if r["runs"] >= 1))
print("无交付动词: %d 条" % sum(1 for r in rows if not r["deliver"]))
print("过短(<28字,<=1句): %d 条" % sum(1 for r in rows if r["n"] <= 1 and r["chars"] < 28))
print("第 1 句复述标题: %d 条" % sum(1 for r in rows if r["echo"]))

with open(os.path.join(ROOT, "_tools", "style_audit.txt"), "w", encoding="utf-8") as f:
    for r in sorted(rows, key=lambda x: -(x["maxlen"] + x["enum_dup"] * 10)):
        it = r["it"]
        f.write("[%s] %s | 句%d 最长%d 字%d 枚举%d\n    %s\n\n"
                % (it["cat"], it["title"], r["n"], r["maxlen"], r["chars"], r["enum_dup"],
                   it["body"].replace("\n", " ")))

sys.exit(1 if violations else 0)
