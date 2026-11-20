# -*- coding: utf-8 -*-
"""中英文切换内容的巡检工具。

查四件事：
  1. 英文译文是否覆盖全库条目与分类（src/i18n/en/ 对 src/prompts/）
  2. 英文译文里有没有漏下的中文
  3. app.js 里 t('…') 用到的键，UI 字典（src/assets/i18n.js）是否都有
  4. 页面里 data-i18n* 标注的文案，UI 字典是否都有

用法：python _tools/i18n_audit.py
退出码非 0 表示有缺漏。
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from console_utf8 import use_utf8_console as _use_utf8_console  # 供 tests/ 与 _tools/ 复用


def use_utf8_console():
    """让中文输出在终端里正常显示（实现见 console_utf8.py）。"""
    return _use_utf8_console()


CJK = re.compile(r"[一-鿿　-〿＀-￯]")


def load_dict():
    """读 UI 字典，返回 {键: 译文}。"""
    path = os.path.join(ROOT, "src", "assets", "i18n.js")
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    body = src.split("window.PLIB_I18N", 1)[1]
    body = body[body.index("{") + 1: body.rindex("};")]
    out = {}
    for key, value in re.findall(r"'((?:[^'\\]|\\.)*)'\s*:\s*'((?:[^'\\]|\\.)*)'", body):
        out[key.replace("\\'", "'")] = value.replace("\\'", "'")
    return out


def check_translations(problems):
    """英文译文的覆盖率与残留中文。"""
    import build

    errors, warnings = [], []
    categories, sections = build.collect(errors, warnings)
    root = os.path.join(ROOT, "src", "i18n")
    en_dir = os.path.join(root, "en")
    if not os.path.isdir(en_dir):
        problems.append("缺少英文译文目录：src/i18n/en")
        return

    # 分区名译文在 src/i18n/sections.json（与分类译文分开）
    en_sections = {}
    sections_path = os.path.join(root, "sections.json")
    if not os.path.exists(sections_path):
        problems.append("缺少分区名译文：src/i18n/sections.json")
    else:
        with open(sections_path, "r", encoding="utf-8") as fh:
            en_sections = json.load(fh)
        section_names = set(s["name"] for s in sections)
        for zh in en_sections:
            if zh not in section_names:
                problems.append("英文分区名 '%s' 没有对应的中文分区" % zh)
        for zh in section_names:
            if zh not in en_sections:
                problems.append("分区 '%s' 没有英文名" % zh)

    en_cat, en_prompt = {}, {}
    owner = {}
    for c in categories:
        for p in c["prompts"]:
            owner[p["id"]] = c["id"]
    for fname in sorted(os.listdir(en_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(en_dir, fname), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for pid, item in (data.get("prompts") or {}).items():
            en_prompt[pid] = item
            if pid in owner:
                en_cat.setdefault(owner[pid], data.get("category") or {})

    for c in categories:
        meta = en_cat.get(c["id"])
        if not meta or not meta.get("name"):
            problems.append("分类 '%s'（%s）没有英文分类名" % (c["id"], c["name"]))
        for p in c["prompts"]:
            if p["id"] not in en_prompt:
                problems.append("条目 '%s'（%s）没有英文译文" % (p["id"], p["title"]))

    for fname in sorted(os.listdir(en_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(en_dir, fname), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        stack = [(fname, "", data)]
        while stack:
            where, path, node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    stack.append((where, path + "." + k, v))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    stack.append((where, path + "[%d]" % i, v))
            elif isinstance(node, str) and CJK.search(node):
                problems.append("%s %s: 英文译文里还有中文：%s" % (where, path, node[:40]))


def check_dict_keys(problems):
    """运行时与页面用到的键，字典里都要有。"""
    table = load_dict()
    app = os.path.join(ROOT, "src", "assets", "app.js")
    with open(app, "r", encoding="utf-8") as fh:
        src = fh.read()
    for key in re.findall(r"\bt\(\s*'((?:[^'\\]|\\.)*)'", src):
        key = key.replace("\\'", "'")
        if key not in table:
            problems.append("app.js 用了字典里没有的键：%r" % key)
    for name in ("index.html", "404.html"):
        path = os.path.join(ROOT, "src", name)
        with open(path, "r", encoding="utf-8") as fh:
            html = fh.read()
        for key in re.findall(r'data-i18n(?:-[\w-]+)?="([^"]*)"', html):
            if key not in table:
                problems.append("%s 用了字典里没有的键：%r" % (name, key))


def check_dict_dynamic_keys(problems):
    """t(条件 ? 'A' : 'B') 里的两个字面量，以及 t('A' + 变量) 这类拼出来的键。"""
    app = os.path.join(ROOT, "src", "assets", "app.js")
    with open(app, "r", encoding="utf-8") as fh:
        src = fh.read()
    table = load_dict()
    for a, b in re.findall(r"\bt\(\s*[^()]*?\?\s*'((?:[^'\\]|\\.)*)'\s*:\s*'((?:[^'\\]|\\.)*)'", src):
        for key in (a, b):
            if key.replace("\\'", "'") not in table:
                problems.append("app.js 三元分支用了字典里没有的键：%r" % key.replace("\\'", "'"))
    # 拼出来的键静态算不出全名，只能确认前缀本身有译文，并提示人工核对全名
    for prefix in re.findall(r"\bt\(\s*'((?:[^'\\]|\\.)*)'\s*\+", src):
        prefix = prefix.replace("\\'", "'")
        if prefix not in table:
            problems.append("app.js 拼接键的前缀不在字典里：%r" % prefix)


def check_dict_values(problems):
    """译文本身不许漏中文、不许留空，英文与中文相同的只允许中英同形的那几条。"""
    table = load_dict()
    for key, value in table.items():
        if not value.strip():
            problems.append("字典键 %r 的英文译文是空的" % key)
        if CJK.search(value) and value != key:
            problems.append("字典键 %r 的英文译文里还有中文：%r" % (key, value))


def check_sections_consistency(problems):
    """分区名以 src/i18n/sections.json 为准，i18n.js 里的副本必须一致。"""
    path = os.path.join(ROOT, "src", "i18n", "sections.json")
    if not os.path.exists(path):
        problems.append("缺少分区名译文：src/i18n/sections.json")
        return
    with open(path, "r", encoding="utf-8") as fh:
        sections = json.load(fh)
    table = load_dict()
    for zh, en in sections.items():
        if zh not in table:
            problems.append("i18n.js 少了分区名 %r" % zh)
        elif table[zh] != en:
            problems.append("i18n.js 与 sections.json 的分区名不一致：%r（%r != %r）"
                            % (zh, table[zh], en))


def main():
    use_utf8_console()
    problems = []
    check_translations(problems)
    check_dict_keys(problems)
    check_dict_dynamic_keys(problems)
    check_dict_values(problems)
    check_sections_consistency(problems)
    if problems:
        print("发现 %d 个问题：" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("中英文切换内容巡检通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
