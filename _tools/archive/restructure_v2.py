#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性迁移：合并重叠条目 + 重排分类。

- 按 MERGES 把用途重叠的条目并入主条目（主条目保留稳定 id，被并条目 id 作废）。
- 按 CATS 把条目分配到新的分类文件，写出新的 frontmatter（id/name/icon/desc/section/order）。
- 条目的 id、标签、简洁表达、正文原样保留，文案重写由后续人工/子代理完成。

用法：python _tools/archive/restructure_v2.py [--dry]
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "prompts")

# 主条目 id -> 被并入的条目 id 列表（顺序即吸收顺序）
MERGES = {
    "p001": ["p006"],          # 实现新增功能 -> 描述项目并实现
    "p003": ["p128"],          # 多端一致的功能 -> 实现客户端与网页端
    "p004": ["p158"],          # 集中请求决策确认 -> 澄清项目需求
    "p005": ["p017"],          # 相近方向合并 -> 治理臃肿项目
    "p012": ["p016"],          # 项目整体体检与建议 -> 全面检查项目并修复
    "p025": ["p060"],          # 清理死代码与无用依赖 -> 简化代码实现
    "p031": ["p014"],          # 走查全部功能流程 -> 执行端到端验证
    "p039": ["p134"],          # 网站性能与体验 -> 减少首屏加载
    "p050": ["p052"],          # 新分支并提交 -> 提交相关改动
    "p059": ["p309"],          # 移出无关文件到归档处 -> 归档废弃内容
    "p081": ["p313"],          # 打包发布并写发行说明 -> 发布并支持回滚
    "p091": ["p090"],          # 界面细节打磨 -> 提升用户友好性
    "p094": ["p095"],          # 实现并验证深色模式 -> 主题与皮肤切换
    "p141": ["p311", "p312"],  # 合并并精简文档集 / 删减冗余并补齐缺口 -> 精简 README 套话
    "p145": ["p140"],          # 更新并优化 README -> 文档与代码一致性检查
    "p147": ["p314"],          # 精简示例代码 -> 设计可运行示例
    "p154": ["p-7f284f7d3bd7f2e4"],  # 按目标受众改写内容 -> 调整沟通措辞
    "p177": ["p178"],          # 撰写带推导的综述 -> 写一篇文献综述
    "p186": ["p248"],          # 基于研究基础选题 -> 头脑风暴研究方向
    "p187": ["p295"],          # 分类评估候选课题 -> 评估选题的价值
    "p195": ["p197"],          # 以核心结论组织全文 -> 搭建论文提纲
    "p198": ["p214"],          # 均衡各节篇幅 -> 控制论文篇幅
    "p223": ["p224"],          # 独立核查不受原文影响 -> 从底层原理反查
    "p239": ["p243"],          # 排查拒稿风险 -> 开展审稿人视角评审
    "p297": ["p298"],          # 回复全部执行 -> 回复继续执行
    "p300": ["p299", "p307"],  # 完成后停止循环 / 项目结项收尾 -> 完成收尾并停止
    "p302": ["p308"],          # 核查改动是否有遗漏 -> 重新检查一遍
    "p306": ["p-4d35a23489ce4ef6"],  # 核查事实与来源 -> 严格核查事实与推断
}

# 分类定义：id -> (name, icon, desc, section, order, [条目 id...])
CATS = [
    ("project", "立项与需求", "◆", "从想法到方案：描述需求、给出约束、先出方案再动手",
     "通用工程", 1,
     ["p001", "p002", "p003", "p004", "p005", "p007"]),
    ("code-check", "代码质量检查", "✓", "全量巡检、缺陷定位、差异评审与结构审查",
     "通用工程", 2,
     ["p012", "p013", "p015", "p018", "p019", "p020"]),
    ("refactor", "重构与架构", "▤", "模块化、结构优化、核心逻辑提取、删繁就简",
     "通用工程", 3,
     ["p023", "p024", "p025", "p026", "p027", "p028"]),
    ("test", "测试与验证", "◐", "补测试、造数据、跑测试、修失败、端到端与回归验证",
     "通用工程", 4,
     ["p029", "p030", "p031", "p032", "p033", "p034",
      "p-43610bb4b5e15e90", "p035"]),
    ("perf", "性能与优化", "▲", "瓶颈定位、缓存与并发、资源与体积优化",
     "通用工程", 5,
     ["p036", "p038", "p039", "p040", "p041"]),
    ("security", "安全与隐私", "⛨", "敏感信息清理、权限收紧、输入校验与合规自查",
     "通用工程", 6,
     ["p043", "p044", "p046", "p047", "p048", "p049"]),
    ("deps", "依赖与供应链", "⬢", "依赖升级、体积审计、漏洞与许可证风险",
     "通用工程", 7,
     ["p021", "p042", "p045"]),
    ("git", "版本与提交", "⑂", "提交、分支、PR 描述、历史整理、协作避让",
     "通用工程", 8,
     ["p050", "p051", "p053", "p054", "p055", "p057"]),
    ("cleanup", "清理与归档", "⌫", "结项收尾、清临时文件、清死代码、归档废弃内容",
     "通用工程", 9,
     ["p058", "p059", "p061", "p310"]),
    ("api", "接口设计", "⇄", "接口约定、鉴权、校验、分页批量、幂等与错误响应",
     "通用工程", 10,
     ["p062", "p063", "p064", "p065", "p068", "p-9fcbca908f981547", "p072",
      "p070", "p-9ac16ebad91538ce", "p069"]),
    ("data-store", "数据与并发", "⬦", "数据建模、索引、迁移、并发一致性与异步处理",
     "通用工程", 11,
     ["p066", "p067", "p071", "p-3f05ff66bdf7c2da", "p-b92b6803325d6afa"]),
    ("build-release", "构建与发布", "⚑", "CI 流水线、容器镜像、版本打包与发布",
     "通用工程", 12,
     ["p073", "p074", "p075", "p081"]),
    ("runtime", "运行与运维", "⚙", "域名证书、健康监控、容错限流、备份与故障排查",
     "通用工程", 13,
     ["p076", "p077", "p078", "p-9c77c42cf1885f9e", "p079", "p080", "p082",
      "p083", "p084", "p085"]),
    ("ui-visual", "界面与视觉", "◨", "视觉统一、布局、主题、无障碍、动效与多端适配",
     "界面与产品", 14,
     ["p086", "p087", "p088", "p089", "p091", "p092", "p093", "p094", "p096",
      "p097", "p098", "p099", "p100"]),
    ("ui-interaction", "交互与表单", "⌨", "弹窗抽屉、表单校验与错误提示、撤销重做",
     "界面与产品", 15,
     ["p-ac107e41b07bfc5d", "p101", "p102"]),
    ("list-search", "列表与检索", "⌗", "搜索、排序、筛选、分页、批量选择、标签与收藏",
     "界面与产品", 16,
     ["p103", "p104", "p105", "p106", "p107", "p108", "p109", "p110", "p111",
      "p112", "p-3168d81d0a0ee015"]),
    ("i18n", "国际化与本地化", "⌸", "多语言文案、语言切换、复数动态文案、日期数字单位、RTL",
     "界面与产品", 17,
     ["p113", "p114", "p115", "p116", "p117", "p118", "p119", "p120",
      "p-877be4e9022940a1"]),
    ("product", "产品功能补全", "◱", "关于页、404、落地页、订阅、评论、分享与反馈",
     "界面与产品", 18,
     ["p121", "p122", "p123", "p124", "p125", "p-c0m7f2a19b4e6d3", "p126",
      "p127", "p-a05dcffc7b23996c"]),
    ("web", "网站与可视化", "⬚", "静态站重构、可视化网页、公式动画、交互画布、SEO",
     "界面与产品", 19,
     ["p130", "p131", "p132", "p133", "p135", "p137", "p139"]),
    ("docs", "文档与说明", "≡", "README、设计文档、教程、示例、翻译与资料总结",
     "文档与表达", 20,
     ["p141", "p142", "p143", "p144", "p145", "p146", "p147", "p150", "p151",
      "p152", "p-54927342dd418789", "p-b6527e8bee891619", "p-7eb2c34e8253fa01"]),
    ("comm", "沟通与协作", "☏", "邮件通知、会议纪要与议程、进度汇报与协作边界",
     "文档与表达", 21,
     ["p153", "p154", "p155", "p156", "p157", "p159", "p160", "p161", "p162",
      "p-a21eb985ecd6228d"]),
    ("slide", "演示与幻灯片", "◧", "生成幻灯片、风格切换、逻辑组织、页面标题",
     "文档与表达", 22,
     ["p163", "p164", "p166", "p167", "p168", "p169"]),
    ("teach", "教学与学习", "✧", "概念讲解、出题解答、学习路线、分层提示与效果检验",
     "文档与表达", 23,
     ["p170", "p171", "p172", "p173", "p174", "p-9e75832737beddb4", "p176"]),
    ("research", "文献调研与综述", "⌕", "文献综述、参考文献核验、调研报告、观点梳理",
     "学术研究", 24,
     ["p177", "p179", "p180", "p181", "p182", "p183", "p184", "p185"]),
    ("topic", "研究方向与选题", "★", "头脑风暴可发表方向，评估创新性与可行性",
     "学术研究", 25,
     ["p186", "p187", "p188", "p189", "p190", "p191", "p296"]),
    ("paper", "论文结构与撰写", "¶", "提纲、章节撰写、摘要、引言、讨论与篇幅控制",
     "学术研究", 26,
     ["p192", "p193", "p194", "p195", "p196", "p198", "p199", "p200", "p203",
      "p204", "p205"]),
    ("paper-parts", "论文要素与产出", "✍", "图注表注、关键词、标题、致谢贡献与编译产出",
     "学术研究", 27,
     ["p201", "p202", "p206", "p207", "p208", "p209", "p210"]),
    ("polish", "润色与学术风格", "✎", "期刊风格审阅、语言自然化、结构平衡、排版修复",
     "学术研究", 28,
     ["p211", "p212", "p213", "p215", "p216", "p217", "p218", "p219"]),
    ("verify", "严谨性核查", "⊕", "原理、公式、代码、计算、数据的严格正确性检查",
     "学术研究", 29,
     ["p220", "p221", "p222", "p223", "p225", "p226", "p227", "p228", "p229",
      "p230", "p231", "p306"]),
    ("figure", "绘图与图表", "◫", "学术级绘图、图的自解释性、流程图与多面板规范",
     "学术研究", 30,
     ["p232", "p233", "p234", "p235", "p236", "p237", "p238"]),
    ("review", "审稿与自查", "❖", "以审稿人身份挑毛病、给建设性意见、自我迭代",
     "学术研究", 31,
     ["p239", "p240", "p241", "p242", "p244", "p245"]),
    ("grant", "项目书与基金", "▣", "申请书审稿视角修改、实验方案优化、可行性论证",
     "学术研究", 32,
     ["p246", "p247", "p249", "p250", "p251", "p252", "p253"]),
    ("repro", "计算流程与复现", "⟳", "计算抽象为通用流程、逐步留痕、断点续跑、结果存档",
     "学术研究", 33,
     ["p254", "p255", "p256", "p257", "p258", "p259", "p260", "p261", "p262"]),
    ("data-analysis", "数据分析与统计", "▦", "批量抓取与归类、趋势分析、清洗、图表结论",
     "学术研究", 34,
     ["p263", "p264", "p265", "p266", "p267", "p268", "p269", "p270", "p271",
      "p272"]),
    ("agent", "智能体与工作流", "⌬", "项目规范、技能与命令、提示词评测、上下文交接与自动化",
     "智能体与节奏", 35,
     ["p273", "p274", "p275", "p276", "p277", "p278", "p279", "p280", "p281",
      "p282", "p283", "p284", "p285", "p-0516287c23175975"]),
    ("authz", "授权与自主执行", "◎", "明确授权边界，让智能体自主推进而非频繁回头确认",
     "智能体与节奏", 36,
     ["p009", "p010", "p011"]),
    ("loop", "循环工作指令", "↻", "可追加到相匹配任务尾部的指令块：自动循环、版本管理",
     "智能体与节奏", 37,
     ["p286", "p287", "p288", "p289", "p-e418db87a387eaba", "p290", "p291",
      "p292", "p293", "p294"]),
    ("misc", "节奏与确认口令", "⌁", "推进、确认、收尾、停止任务、循环次数控制等高频短指令",
     "智能体与节奏", 38,
     ["p297", "p300", "p301", "p302", "p303", "p304", "p305",
      "p-cf902dd93db5b0e7"]),
]

TITLE_RE = re.compile(r"^##\s+(.*\S)\s*$")
ID_RE = re.compile(r"^<!--\s*id:\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*-->\s*$", re.I)
TAG_RE = re.compile(r"^<!--\s*t:\s*(.*?)\s*-->\s*$", re.I)
SHORT_RE = re.compile(r"^<!--\s*s:\s*(.*?)\s*-->\s*$", re.I)


def parse(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n")
    lines = raw.split("\n")
    items, cur = [], None
    for line in lines:
        if line.startswith("## "):
            m = TITLE_RE.match(line)
            if m:
                if cur:
                    items.append(cur)
                cur = {"title": m.group(1), "id": "", "tags": [], "short": "",
                       "body": []}
                continue
        if cur is None:
            continue
        if (m := ID_RE.match(line)):
            cur["id"] = m.group(1)
            continue
        if (m := TAG_RE.match(line)):
            cur["tags"] = [t.strip() for t in m.group(1).split(",") if t.strip()]
            continue
        if (m := SHORT_RE.match(line)):
            cur["short"] = m.group(1).strip()
            continue
        cur["body"].append(line.rstrip())
    if cur:
        items.append(cur)
    for it in items:
        it["content"] = "\n".join(it["body"]).strip("\n")
    return items


def render(it):
    out = ["## " + it["title"], "<!-- id: %s -->" % it["id"]]
    out.append("<!-- t: %s -->" % ", ".join(it["tags"]))
    if it["short"]:
        out.append("<!-- s: %s -->" % it["short"])
    out.append("")
    out.append(it["content"])
    return "\n".join(out)


def main():
    dry = "--dry" in sys.argv
    entries = {}
    snapshot = {}
    for fn in sorted(os.listdir(SRC)):
        if fn.endswith(".md"):
            for it in parse(os.path.join(SRC, fn)):
                if it["id"] in entries:
                    raise SystemExit("id 重复: " + it["id"])
                entries[it["id"]] = it

    # 合并
    absorbed = {}
    for keep, gone in MERGES.items():
        for g in gone:
            if g not in entries:
                raise SystemExit("被并条目不存在: " + g)
            absorbed[g] = keep
            snapshot[g] = (entries[g]["title"], entries[g]["content"])
            del entries[g]

    # 分配到新分类
    assigned, seen = {}, set()
    for cat_id, name, icon, desc, section, order, ids in CATS:
        for pid in ids:
            if pid not in entries:
                raise SystemExit("分类 %s 引用了不存在的条目: %s" % (cat_id, pid))
            if pid in seen:
                raise SystemExit("条目被分配到多个分类: " + pid)
            seen.add(pid)
            assigned.setdefault(cat_id, []).append(pid)
    missing = set(entries) - seen
    extra = seen - set(entries)
    if missing or extra:
        raise SystemExit("分配不完整：未分配 %s / 未知 %s" % (sorted(missing), sorted(extra)))

    # 写出
    for fn in sorted(os.listdir(SRC)):
        if fn.endswith(".md"):
            os.remove(os.path.join(SRC, fn))
    for idx, (cat_id, name, icon, desc, section, order, ids) in enumerate(CATS, 1):
        path = os.path.join(SRC, "%02d-%s.md" % (idx, cat_id))
        head = [
            "---",
            "id: %s" % cat_id,
            "name: %s" % name,
            "icon: \"%s\"" % icon,
            "desc: %s" % desc,
            "section: %s" % section,
            "order: %d" % order,
            "---",
            "",
        ]
        body = "\n\n".join(render(entries[pid]) for pid in ids)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(head) + body + "\n")
        print("写出 %s（%d 条）" % (os.path.basename(path), len(ids)))

    # 记录被并条目原文，供文案重写时吸收
    notes = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "merged_absorbed.md")
    with open(notes, "w", encoding="utf-8") as f:
        f.write("# 被并入其它条目的原文（重写时需吸收其独有要点）\n\n")
        for keep, gone in MERGES.items():
            for g in gone:
                title, content = snapshot[g]
                f.write("## %s（主） <- %s（被并）\n\n" % (keep, g))
                f.write("主条目原标题：%s\n\n" % entries[keep]["title"])
                f.write("被并条目原标题：%s\n\n" % title)
                f.write("被并条目原正文：%s\n\n" % content)
    print("合计 %d 条，%d 个分类" % (len(entries), len(CATS)))


if __name__ == "__main__":
    main()
