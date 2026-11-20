# -*- coding: utf-8 -*-
"""产物自检：dist/index.html 引用的静态资源哈希是否与 dist/assets 里的实际文件一致。

dist 是部署产物，必须与 src 同步提交。改完 src 却忘了重建 dist（或重建时
src 还在改动中），就会留下「引用旧哈希」的混版——页面能开，但换了新样式。

用法：
    python _tools/dist_check.py           # 检查 dist/（默认）
    python _tools/dist_check.py --dist <目录>

退出码：0 一致；1 有不一致或文件缺失。
"""
import hashlib
import os
import re
import sys

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console
use_utf8_console()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_RE = re.compile(r"assets/([\w.\-]+)\?v=([a-f0-9]+)")


def main():
    dist = os.path.join(ROOT, "dist")
    if "--dist" in sys.argv:
        i = sys.argv.index("--dist")
        if i + 1 >= len(sys.argv):
            print("[dist-check] --dist 需要一个目录参数")
            return 1
        dist = os.path.abspath(sys.argv[i + 1])

    index = os.path.join(dist, "index.html")
    if not os.path.exists(index):
        print("[dist-check] 找不到 %s，先跑 python build.py" % index)
        return 1

    html = open(index, encoding="utf-8").read()
    refs = sorted(set(REF_RE.findall(html)))
    if not refs:
        print("[dist-check] index.html 里没有静态资源引用，检查是否解析失败")
        return 1

    bad = []
    for name, ver in refs:
        path = os.path.join(dist, "assets", name)
        if not os.path.exists(path):
            bad.append((name, ver, "文件缺失"))
            continue
        actual = hashlib.sha1(open(path, "rb").read()).hexdigest()[:8]
        if actual != ver:
            bad.append((name, ver, "实际 " + actual))

    print("[dist-check] 引用 %d 个资源，%s" % (len(refs), "全部一致" if not bad else "有 %d 处不一致" % len(bad)))
    for name, ver, why in bad:
        print("  ✗ %-14s 引用 %s / %s" % (name, ver, why))
    if bad:
        print("[dist-check] 重建 dist 时要确保用的是将要提交的那份 src")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
