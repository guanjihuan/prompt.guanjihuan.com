#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第四轮补修：压到体例上限内的长度与空泛词。"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "prompts")

REPLACE = [
    ("06-security.md",
     "交付入口与风险映射表及改动清单，附注入与路径穿越的测试结果。",
     "交付入口与风险映射表，附注入与路径穿越的测试结果。"),
    ("24-research.md",
     "覆盖主流方法与代表工作，梳理未解决问题、争议点与近几年趋势，按统一维度比较假设与证据。",
     "覆盖主流方法与代表工作，梳理未解决问题、争议点与趋势，按统一维度比较假设与证据。"),
    ("27-paper-parts.md",
     "根据实际贡献补齐致谢与作者贡献，署名与致谢只采用已确认的信息。记录资助、讨论协助和计算资源支持，作者贡献按类型写清责任人，公开前征得本人同意。",
     "根据实际贡献补齐致谢与作者贡献，署名只采用已确认的信息。记录资助、讨论协助和计算资源支持，作者贡献按类型写清责任人，公开前征得同意。"),
    ("31-review.md",
     "先自审[稿件]再逐轮修改，每轮只处理[具体方向]上高优先级的问题。按对结论的影响排序问题，改后复核受影响的论证与数据。最多迭代[N]轮，无实质改进即停止并保留逐轮记录，",
     "先自审[稿件]再逐轮修改，每轮只处理[具体方向]的高优先级问题。按对结论的影响排序问题，改后复核受影响的论证与数据。最多迭代[N]轮，无实质改进即停止并保留记录，"),
    ("35-agent.md",
     "## 编写系统提示词与角色设定\n"
     "<!-- id: p-",
     "## 编写智能体的角色与总要求\n"
     "<!-- id: p-"),
    ("35-agent.md",
     "<!-- s: 为[场景]写系统提示词：目标、边界与输出格式。 -->",
     "<!-- s: 为[场景]写智能体的角色与总要求：目标、边界与输出格式。 -->"),
    ("35-agent.md",
     "让智能体在[场景]里稳定按同一套要求工作。写清角色目标、可做与不可做的边界、已知信息与缺省假设，规定输出结构与不确定时的表达方式。交付系统提示词与使用说明，标出与其他提示词冲突的规则。",
     "让智能体在[场景]里稳定按同一套要求工作。写清角色目标、可做与不可做的边界、已知信息与缺省假设，规定输出结构与不确定时的表达方式。交付总要求文本与使用说明，标出与其他提示词冲突的规则。"),
]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    cache = {}
    errors = []
    for fn, old, new in REPLACE:
        p = os.path.join(SRC, fn)
        txt = cache.get(fn) or read(p)
        n = txt.count(old)
        if n != 1:
            errors.append("%s: 命中 %d 次 -> %r" % (fn, n, old[:40]))
            continue
        cache[fn] = txt.replace(old, new)
    for fn, txt in cache.items():
        write(os.path.join(SRC, fn), txt)
    for e in errors:
        print("ERROR " + e)
    print("补修完成：%d 处" % len(REPLACE))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
