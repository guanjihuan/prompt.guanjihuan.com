# -*- coding: utf-8 -*-
"""
migrate2.py — 语义级合并：把重复/近重复的条目合并为一条，并改写重叠措辞。
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "prompts")
T = re.compile(r"^##\s+(.*\S)\s*$")

# 删除：整条移除
DELETE = [
    ("03-code-check.md", "全面检查，有错就修"),
    ("03-code-check.md", "通读一遍找问题"),
    ("03-code-check.md", "确认全项目无错误"),
    ("12-ui.md", "响应式与暗色模式"),
    ("12-ui.md", "重新设计并自测所有界面"),
    ("25-verify.md", "数值与量纲自洽"),
    ("25-verify.md", "算法与公式核查"),
    ("17-docs.md", "README 重要信息前置"),
    ("17-docs.md", "README 补全部署步骤"),
    ("19-slide.md", "生成 HTML 幻灯片"),
    ("33-misc.md", "全部完成后停止循环"),
]

# 替换：旧标题 -> (新标题, 新正文, 新标签或 None)
REPLACE = {
    ("03-code-check.md", "全面检查项目并修复"): (
        "全面检查项目并修复",
        "全面检查项目，如果有问题，及时修复；如果有不合理的设计，及时优化。"
        "检查要覆盖到位：错误、不合理之处、遗漏的分支、坏味道都要查出来，发现即改。",
        "检查,修复,优化"),
    ("12-ui.md", "打开界面实测并优化"): (
        "打开界面实测并重设计",
        "还是存在很多问题，你自己打开界面，详细测试每个操作界面，"
        "对每个界面做详细的重新设计与优化，并测试所有功能。",
        "UI,设计,测试"),
    ("25-verify.md", "重点核查公式与代码"): (
        "重点核查公式与代码",
        "详细检查下，尤其是公式和代码，不要有任何问题，需要严格检查、多计算和测试等。"
        "代码里的算法实现是否与公式一致，也要一并核对。",
        "核查,公式,代码"),
    ("25-verify.md", "单位与量纲一致性"): (
        "单位与量纲一致性检查",
        "统一全文的单位与量纲：同一物理量在不同章节是否用了不同单位？换算是否正确？"
        "单位符号的大小写与间距是否规范（SI 规范）？坐标轴标注与表格数值是否一致？"
        "量纲是否自洽，极限情况下的行为是否符合预期？",
        "核查,单位,量纲"),
    ("17-docs.md", "README 兼顾开发与使用"): (
        "README 兼顾开发与使用",
        "全面阅读项目，根据实际情况更新 README，让开发者和使用者都能各取所需："
        "使用者关心怎么跑起来、怎么用；开发者关心架构、目录与扩展方式。",
        "README,文档"),
    ("17-docs.md", "更新并优化 README"): (
        "更新并优化 README",
        "根据项目的实际情况更新 README，然后优化下 README，需要用户友好的。"
        "先核对 README 里的命令、路径与默认值是否与代码一致，再决定改哪一段。",
        "README,文档"),
    ("08-git.md", "提交前先说明边界"): (
        "提交前先说明边界",
        "我准备提交这批改动，先说明我改动的文件范围和改动意图，避免误提交别人在途修改的文件。"
        "提交时只提交我明确列出的文件，不要用全量暂存。",
        "git,协作,提交"),
    ("18-comm.md", "说明协作边界"): (
        "多方分工确认",
        "和团队里其他人协作前，先对齐各自负责的部分、交付物和交接点："
        "谁做哪一块、什么时候给谁、以什么形式交付，避免重复劳动与互相覆盖。",
        "协作,分工,确认"),
    ("23-paper.md", "附录与补充材料组织"): (
        "附录的叙事与交叉引用",
        "整理附录与补充材料：正文放不下的推导、额外数据、参数表、方法细节放进去，"
        "并给它们自己的叙事顺序；附录内部与正文的交叉引用要一一对应，不能有悬空引用。",
        "论文,附录,交叉引用"),
    ("23-paper.md", "补充材料单独成文"): (
        "补充材料单独成文",
        "把正文放不下的内容整理成独立的补充材料 .tex：结构清晰、有自己的叙事顺序，"
        "与正文交叉引用一致；补充材料也要能独立读懂。",
        "论文,补充材料"),
    ("24-polish.md", "精简文字"): (
        "学术化精炼一段文字",
        "润色这段文字，使语言更学术、更精炼，减少冗余表达，术语保持一致。",
        "润色,精简,学术"),
    ("19-slide.md", "生成 pptx 幻灯片"): (
        "生成幻灯片",
        "做一个 PPT，主题是 [主题]，文件格式为 [pptx / HTML]。",
        "PPT,幻灯片"),
    ("33-misc.md", "完成后停止循环"): (
        "完成后停止循环",
        "全部完成后，停止循环。",
        "收尾,循环"),
    ("04-refactor.md", "设计文件结构"): (
        "设计文件结构",
        "帮忙整理和设计好文件结构，做好文件夹分类，重要代码和测试代码分开放，"
        "产物与临时文件单独归置。",
        "重构,目录,分类"),
}


def main():
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(SRC, fn)
        lines = open(path, encoding="utf-8").read().split("\n")

        out = []
        cur = None
        buf = []
        entries = []
        for l in lines:
            m = T.match(l)
            if m:
                if cur:
                    entries.append((cur, buf))
                cur = m.group(1)
                buf = []
            elif cur is not None:
                buf.append(l)
            else:
                out.append(l)
        if cur:
            entries.append((cur, buf))

        kept = []
        changed = False
        for title, body in entries:
            if (fn, title) in DELETE:
                changed = True
                print("  删除  %-18s %s" % (fn[:16], title))
                continue
            if (fn, title) in REPLACE:
                nt, nb, tags = REPLACE[(fn, title)]
                changed = True
                print("  替换  %-18s %s -> %s" % (fn[:16], title, nt))
                out.append("## " + nt)
                out.append("<!-- t: %s -->" % tags)
                out.append(nb)
                out.append("")
                continue
            out.append("## " + title)
            out.extend(body)

        if changed:
            text = "\n".join(out)
            text = re.sub(r"\n{3,}", "\n\n", text).rstrip("\n") + "\n"
            open(path, "w", encoding="utf-8").write(text)

    # 统计
    n = 0
    for fn in os.listdir(SRC):
        if fn.endswith(".md"):
            n += len(re.findall(r"^## ", open(os.path.join(SRC, fn), encoding="utf-8").read(), re.M))
    print("当前条目总数:", n)


if __name__ == "__main__":
    main()
