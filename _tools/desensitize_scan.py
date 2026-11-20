# -*- coding: utf-8 -*-
"""脱敏与通用性扫描：找出仍然绑定具体课题、工具、期刊、路径、身份的表述。"""
import os, re, sys, collections

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console
use_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promptlib

# 需要泛化的类别词：领域专名 / 工具专名 / 机构 / 身份 / 路径
PATTERNS = {
 "期刊/会议专名": r"PRL|PRB|PR[A-Z]|Phys\.? Rev|Nature|Science|Advanced Materials|Nature Communications|PRX|Nature Physics",
 "arXiv/预印本": r"arXiv",
 "学科专名": r"物理图像|物理概念|物理图像和图像|物理量|热力学|量子|拓扑|非平衡格林函数|NEGF|TCAD|紧束缚|半经典|介观|凝聚态|磁性|能带|拓扑相|斯格明子|石墨烯|特斯拉阀",
 "工具/平台专名": r"CLAUDE\.md|Claude|Anthropic|ChatGPT|GPT-\d|Gemini|Copilot|Memory|Write|Edit|Read|Grep|Glob|WebFetch|WebSearch|NotebookEdit|CronCreate|ScheduleWakeup|Bash|Playwright|Chrome DevTools",
 "路径与本机": r"(?<![A-Za-z])[A-Za-z]:[\\/](?!/)|/tmp/|/Users/|/home/|\\\\data\\\\|\.claude|AppData|anaconda|node_modules",
 "身份与机构": r"关济寰|Ji-Huan|Guan|Micius|郑州|实验室|课题组",
 "内部代号": r"tcad-|negf|prl-|semidv|web-statistics|claude-\d+",
}

items = promptlib.load()

print("条目总数:", len(items))
print()
total_hits = 0
for label, pat in PATTERNS.items():
    hits = []
    for it in items:
        # 标题、正文、标签、简洁表达一起扫——专名可能藏在标签或简洁表达里
        blob = promptlib.scan_blob(it)
        # 方括号占位符和「（如 …）」示例允许出现专名，扫描时排除。
        scanned = re.sub(r"\[[^\]\n]*\]|（(?:如|例如)[^）\n]*）", "", blob)
        if label == "期刊/会议专名":
            # 期刊名零容忍：占位符与示例里也不允许出现真实期刊名。
            scanned = blob
        found = sorted(set(m.group(0) for m in re.finditer(pat, scanned)))
        if found:
            hits.append((it["cat"], it["title"], found, blob))
    total_hits += len(hits)
    print("=== %s ：%d 条" % (label, len(hits)))
    for cat, title, found, blob in hits:
        print("   [%-14s] %-22s  %s" % (cat, title, "、".join(found)))
    print()

sys.exit(1 if total_hits else 0)
