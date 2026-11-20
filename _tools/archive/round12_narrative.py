# -*- coding: utf-8 -*-
"""第 12 轮：并行会话追加后的叙事位置修正（3 个分类的块重排，幂等，锚点兼容新条目）。
- 02-code-check：解读报错前移到定位缺陷之前（入口类在前）。
- 14-ui-visual：修复局部显示（视觉层）排在白屏排查（功能层）之前。
- 18-product：预置示例数据与新手引导相邻；管理员登录与登录注册相邻；简化复杂界面收尾。
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "src" / "prompts"

BLOCK_ORDER = {
    "02-code-check.md": [
        "检查项目并给出改进项",
        "仅审查不修改",
        "解读报错信息并修复",
        "定位并修复缺陷",
        "排查坏味道并修复",
        "排查复杂流程缺陷",
        "评审当前改动",
        "接入静态类型检查",
        "统一格式化与静态检查规则",
        "消除不稳定测试",
        "统一错误处理与日志",
        "*统一错误处理与日志",
    ],
    "14-ui-visual.md": [
        "统一界面视觉与组件状态",
        "减少图标与 AI 感",
        "实测并重新设计界面",
        "重构左右栏布局",
        "实现多主题与深色模式",
        "设计界面动效与过渡",
        "适配窄屏与多端布局",
        "建立组件库与使用文档",
        "统一界面文案与提示语气",
        "调优界面可读性",
        "微调界面细节",
        "修复局部显示问题",
        "排查页面白屏与报错",
        "检查并修复无障碍问题",
        "自定义桌面窗口标题栏",
        "制作桌面悬浮窗小工具",
        "记住窗口与布局状态",
        "*记住窗口与布局状态",
    ],
    "18-product.md": [
        "制作产品落地页",
        "设计登录注册与找回流程",
        "接入第三方登录",
        "配置简单管理员登录",
        "设计新手引导流程",
        "预置示例数据",
        "设计产品设置页面",
        "添加关于页面或区域",
        "实现站内通知与消息中心",
        "实现订阅与退订流程",
        "实现链接分享与复制",
        "实现评论功能",
        "实现用户反馈闭环",
        "实现图片上传与预览处理",
        "实现内容导入与解析",
        "实现订单与支付流程",
        "实现应用数据自动备份",
        "同步本地文件与界面显示",
        "制作 404 错误页面",
        "配置应用与站点图标",
        "简化复杂界面",
        "*简化复杂界面",
    ],
}


def reorder_blocks(text, titles):
    parts = re.split(r"(?=^## )", text, flags=re.M)
    head, blocks = parts[0], parts[1:]
    assert head.lstrip().startswith("---"), "首块不是 frontmatter"
    by_title, seq = {}, []
    for b in blocks:
        m = re.match(r"## (.+)", b)
        t = m.group(1).strip()
        assert t not in by_title, "标题重复: " + t
        by_title[t] = b
        seq.append(t)
    listed = [t for t in titles if not t.startswith("*")]
    assert set(listed) <= set(by_title), "清单标题缺失: %s" % (set(listed) - set(by_title))
    extra = [t for t in seq if t not in set(listed)]
    out, emitted = [], set()
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


def main():
    changed = 0
    for fn, titles in BLOCK_ORDER.items():
        p = PROMPTS / fn
        text = p.read_text(encoding="utf-8")
        fixed = reorder_blocks(text, titles)
        if fixed != text:
            p.write_text(fixed, encoding="utf-8")
            changed += 1
            print("[round12] reordered:", fn)
        else:
            print("[round12] unchanged:", fn)
    print("[round12] done, %d files changed" % changed)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
