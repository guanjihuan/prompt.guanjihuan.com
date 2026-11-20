# -*- coding: utf-8 -*-
"""终端编码处理：让中文输出在 Windows 终端里正常显示。

Windows 下 Python 默认按 ANSI 代码页（常见为 GBK）写 stdout，而 Git Bash、
Windows Terminal 与 VSCode 终端按 UTF-8 渲染，中文会变成乱码。只有能确定
终端是 UTF-8 时才切换编码，其余环境保持默认；两种情况都放宽 errors，
避免因为某个字无法编码而中断脚本。

放在仓库根目录，`build.py` 与 `_tools/` 下的审计脚本共用同一份实现。
"""

import os
import sys


def use_utf8_console():
    """把 stdout / stderr 切到 UTF-8（能确定终端编码时），并放宽编码错误。"""
    # pythonw 等环境下 sys.stdout 可能是 None，取 encoding 前先兜住
    enc = getattr(sys.stdout, "encoding", None) or ""
    utf8_terminal = (
        os.environ.get("MSYSTEM")
        or os.environ.get("WT_SESSION")
        or os.environ.get("TERM_PROGRAM") == "vscode"
        or "utf" in enc.lower()
    )
    for stream in (sys.stdout, sys.stderr):
        try:
            if utf8_terminal:
                stream.reconfigure(encoding="utf-8", errors="replace")
            else:
                stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
