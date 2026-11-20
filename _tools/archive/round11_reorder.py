# -*- coding: utf-8 -*-
"""第 11 轮：分类重排 + 类内重排 + 少量文案修。
- 分类按生命周期排序，文件名前缀与 frontmatter order 一并校正（id 不动）。
- 类内块重排：13-runtime / 21-comm / 28-polish / 30-figure / 31-review / 33-repro / 35-agent。
- 文案修 4 处：p021 病句、p171 指定主题、p177 指定方向、p266 据数据。
全部 REPLACE/重排要求精确命中，否则报错中止。
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "src" / "prompts"

# 文件名 -> (新文件名, 新 order)
RENAME_ORDER = {
    "01-project.md": ("01-project.md", 1),
    "02-code-check.md": ("02-code-check.md", 2),
    "03-refactor.md": ("03-refactor.md", 3),
    "04-test.md": ("04-test.md", 4),
    "05-perf.md": ("05-perf.md", 5),
    "06-security.md": ("06-security.md", 6),
    "07-deps.md": ("07-deps.md", 7),
    "10-api.md": ("08-api.md", 8),
    "11-data-store.md": ("09-data-store.md", 9),
    "08-git.md": ("10-git.md", 10),
    "12-build-release.md": ("11-build-release.md", 11),
    "13-runtime.md": ("12-runtime.md", 12),
    "09-cleanup.md": ("13-cleanup.md", 13),
    "14-ui-visual.md": ("14-ui-visual.md", 14),
    "15-ui-interaction.md": ("15-ui-interaction.md", 15),
    "17-i18n.md": ("16-i18n.md", 16),
    "16-list-search.md": ("17-list-search.md", 17),
    "18-product.md": ("18-product.md", 18),
    "19-web.md": ("19-web.md", 19),
    "20-docs.md": ("20-docs.md", 20),
    "21-comm.md": ("21-comm.md", 21),
    "22-slide.md": ("22-slide.md", 22),
    "23-teach.md": ("23-teach.md", 23),
    "24-research.md": ("24-research.md", 24),
    "25-topic.md": ("25-topic.md", 25),
    "33-repro.md": ("26-repro.md", 26),
    "34-data-analysis.md": ("27-data-analysis.md", 27),
    "26-paper.md": ("28-paper.md", 28),
    "30-figure.md": ("29-figure.md", 29),
    "28-polish.md": ("30-polish.md", 30),
    "27-paper-parts.md": ("31-paper-parts.md", 31),
    "29-verify.md": ("32-verify.md", 32),
    "31-review.md": ("33-review.md", 33),
    "32-grant.md": ("34-grant.md", 34),
    "35-agent.md": ("35-agent.md", 35),
    "36-authz.md": ("36-authz.md", 36),
    "37-loop.md": ("37-loop.md", 37),
    "38-misc.md": ("38-misc.md", 38),
}

# 类内重排：文件名 -> 新的标题顺序。清单外的标题（并行会话新追加）按原相对顺序插到
# 「锚点」之后：键值末尾用 "*锚点标题" 标记插入点。
BLOCK_ORDER = {
    "12-runtime.md": [
        "搭建本地开发环境",
        "列清多环境配置项",
        "配置反向代理与加密访问",
        "配置域名与证书",
        "配置静态资源缓存策略",
        "配置健康检查与监控",
        "增强服务容错能力",
        "配置定时任务",
        "制定数据备份与恢复方案",
        "排查 404 与资源路径",
        "排查线上故障",
        "编写运维自动化脚本",
        "*编写运维自动化脚本",  # 新追加条目排其后
    ],
    "21-comm.md": [
        "写邮件或通知",
        "改写措辞贴合受众",
        "按结论先行改写",
        "撰写进度汇报",
        "撰写周报月报",
        "多方分工确认",
        "拒答与降级说明",
        "准备会议议程",
        "整理会议纪要",
        "改写为社媒短帖文案",
        "撰写用户访谈提纲",
    ],
    "30-polish.md": [
        "按目标期刊风格审阅全文",
        "学术化改写一段文字",
        "去掉套话与重复",
        "修复全文逻辑跳跃",
        "统一术语与表达",
        "中文转学术英文",
        "修复全文排版",
        "统一参考文献格式",
        "降低文本重复率",
    ],
    "29-figure.md": [
        "绘制学术风格图件",
        "绘制规范示意图",
        "检查图件自解释性",
        "检查流程图与算法实现",
        "规范多面板图排版",
        "统一图组配色主题",
        "规范误差棒与统计呈现",
    ],
    "33-review.md": [
        "评审稿件并排查拒稿风险",
        "迭代自审与修改",
        "撰写同行评审意见",
        "模拟审稿意见与答复",
        "把审稿意见整理成跟踪表",
        "回复真实审稿意见",
        "筛选匹配投稿期刊",
        "撰写投稿信与材料清单",
        "执行投稿前自查",
        "撰写会议摘要与口头报告",
        "准备答辩问答",
    ],
    "26-repro.md": [
        "抽象通用计算流程",
        "整理笔记为可运行脚本",
        "实现参数化运行",
        "记录每步运行信息",
        "实现流程断点续跑",
        "管理缓存与产物",
        "按想法清单迭代",
        "构建可复现环境",
        "校验结果并对标",
        "诊断并修复数值发散",
        "归档计算结果",
        "发布预印本与开放代码数据",
        "*发布预印本与开放代码数据",
    ],
    "35-agent.md": [
        "编写项目规范文件",
        "审查既有配置",
        "编写智能体的角色与总要求",
        "为智能体接入外部工具",
        "把重复流程做成技能",
        "编写提示词卡片",
        "生成任务清单",
        "给智能体检查分级",
        "设计提交前的自动检查",
        "约定智能体的输出结构",
        "设定智能体的交付自检清单",
        "设定智能体预算与超时",
        "设计记忆与上下文方案",
        "生成交接上下文",
        "划分多智能体职责",
        "汇总后台代理的结果",
        "划清协作改动边界",
        "让智能体从失败改进",
        "评测提示词质量",
        "*评测提示词质量",
    ],
}

# (文件名, 旧文本, 新文本)——精确命中且只命中一次
REPLACES = [
    ("07-deps.md",
     "升级要更的依赖到新版本，处理不兼容变更，跑验证并保留回退方案。",
     "把要升级的依赖更新到新版本，处理不兼容变更，跑验证并保留回退方案。"),
    ("24-research.md",
     "写指定方向的综述，用 LaTeX 排版，关键结论给出可复算推导。",
     "围绕研究方向写综述，用 LaTeX 排版，关键结论给出可复算推导。"),
    ("23-teach.md",
     "围绕指定主题命制 10 道难度递增的练习题，覆盖核心概念、基本应用及综合推理。",
     "出 10 道难度递增的练习题，覆盖主题的核心概念、基本应用与综合推理。"),
    ("23-teach.md",
     "出 10 道给定主题的练习题，难度递增，每题给分步解答与常见错误。",
     "围绕要练的主题出 10 道练习题，难度递增，每题给分步解答与常见错误。"),
    ("27-data-analysis.md",
     "据数据给出值得投入的研究方向建议。",
     "基于数据给出值得投入的研究方向建议。"),
]


def reorder_blocks(text, titles):
    """按给定标题顺序重排 ## 块。清单外的新标题按原相对顺序插到 *锚点 之后。"""
    parts = re.split(r"(?=^## )", text, flags=re.M)
    head, blocks = parts[0], parts[1:]
    assert head.lstrip().startswith("---"), "首块不是 frontmatter"
    by_title = {}
    seq = []  # 保留原相对顺序（供清单外条目使用）
    for b in blocks:
        m = re.match(r"## (.+)", b)
        assert m, "块标题解析失败: %r" % b[:40]
        t = m.group(1).strip()
        assert t not in by_title, "标题重复: " + t
        by_title[t] = b
        seq.append(t)
    listed = [t for t in titles if not t.startswith("*")]
    assert set(listed) <= set(by_title), "清单标题缺失: %s" % (set(listed) - set(by_title))
    extra = [t for t in seq if t not in set(listed)]
    out = []
    emitted = set()
    for item in titles:
        if item.startswith("*"):
            anchor = item[1:]
            assert anchor in by_title, "锚点缺失: " + anchor
            if anchor not in emitted:
                out.append(by_title[anchor])
                emitted.add(anchor)
            out.extend(by_title[t] for t in extra)
        elif item in by_title and item not in emitted:
            out.append(by_title[item])
            emitted.add(item)
    assert len(out) == len(by_title), "重排后条目数不符 %d != %d" % (len(out), len(by_title))
    return head + "".join(out)


def set_order(text, order):
    new, n = re.subn(r"(?m)^order: \d+$", "order: %d" % order, text)
    assert n == 1, "order 行命中 %d 次" % n
    return new


def _order_ok(fn, order):
    m = re.search(r"(?m)^order: (\d+)$", (PROMPTS / fn).read_text(encoding="utf-8"))
    return m is not None and int(m.group(1)) == order


# 终名 -> (终名, 终order)：让脚本对"上次已改名"的文件幂等
FINAL_NAMES = {new: (new, order) for new, order in RENAME_ORDER.values()}


def main():
    # 1) 两阶段改名（避免链式冲突），同时改 order。幂等：已是终名/终 order 的跳过。
    files = sorted(p.name for p in PROMPTS.glob("*.md"))
    lookup = {}
    for old in files:
        mapping = RENAME_ORDER.get(old) or FINAL_NAMES.get(old)
        assert mapping, "未知文件: %s" % old
        lookup[old] = mapping
    tmpdir = PROMPTS / "_tmp_round11"
    tmpdir.mkdir()
    for old in files:
        new, order = lookup[old]
        if old == new and _order_ok(new, order):
            continue  # 已是终名且 order 正确
        text = (PROMPTS / old).read_text(encoding="utf-8")
        text = set_order(text, order)
        if BLOCK_ORDER.get(new):
            text = reorder_blocks(text, BLOCK_ORDER[new])
        (tmpdir / new).write_text(text, encoding="utf-8")
        if old != new:
            (PROMPTS / old).unlink()
    for p in sorted(tmpdir.glob("*.md")):
        p.rename(PROMPTS / p.name)
    tmpdir.rmdir()

    # 1b) 终名但块重排未做的文件（上次中断遗留），单独补重排
    for new, titles in BLOCK_ORDER.items():
        p = PROMPTS / new
        text = p.read_text(encoding="utf-8")
        try:
            fixed = reorder_blocks(text, titles)
        except AssertionError:
            raise
        if fixed != text:
            p.write_text(fixed, encoding="utf-8")
            print("[round11] block-reorder applied:", new)

    # 2) 文案 REPLACE
    for fn, old, new in REPLACES:
        p = PROMPTS / fn
        text = p.read_text(encoding="utf-8")
        cnt = text.count(old)
        assert cnt == 1, "%s: %r 命中 %d 次" % (fn, old[:20], cnt)
        p.write_text(text.replace(old, new), encoding="utf-8")

    print("[round11] done: %d files, %d block-reorders, %d replaces" % (
        len(files), len(BLOCK_ORDER), len(REPLACES)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
