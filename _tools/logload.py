# -*- coding: utf-8 -*-
"""读取本机智能体日志的公共部分。

四个日志分析脚本（dump.py / heads.py / gaps.py / coverage.py）都要读同一批
日志，之前各写了一份几乎相同的加载函数，噪声词表还各不相同（有的漏了
`<agent-message`、`<ide_selection`），统计口径对不上。统一到本模块后，
加载逻辑与噪声表只有这一处。

日志目录的定位顺序：
1. 环境变量 `PROMPT_LIB_LOGDIR`
2. 本地配置 `_tools/local_config.json` 里的 `log_dir`（该文件不入版本库）
3. 都没有 → 报一句人话并退出，不猜路径

版本库里不留任何本机绝对路径——换台机器、或者把仓库发出去，
硬编码路径都会变成别人的麻烦。
"""
import json
import os
import sys

# 环境变量名：指向存放本机日志 *.json 的目录
LOGDIR_ENV = "PROMPT_LIB_LOGDIR"

# 本地配置文件（未纳入版本库，见 .gitignore 的 `_tools/*.json`）
LOCAL_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_config.json")

# 噪声前缀：会话框架自动插入的文本，不是用户写的提示词，统计时要滤掉
NOISE = (
    "<task-notification",
    "<system-reminder",
    "<command-name",
    "<ide_opened_file",
    "<ide_selection",
    "<agent-message",
    "<cross-session-message",
    "Continue from where you left off",
    "# Autonomous loop check",
    "Caveat:",
    "[Cross-session",
)


def log_dir():
    """返回日志目录；找不到配置时给出可操作的提示。"""
    d = os.environ.get(LOGDIR_ENV, "").strip()
    if not d and os.path.exists(LOCAL_CONFIG):
        try:
            with open(LOCAL_CONFIG, "r", encoding="utf-8") as f:
                d = (json.load(f).get("log_dir") or "").strip()
        except Exception as e:
            print("读取 %s 失败：%s" % (LOCAL_CONFIG, e), file=sys.stderr)
    if not d:
        raise SystemExit(
            "找不到本机日志目录。两种方式任选其一：\n"
            "  1) 设环境变量 %s=D:\\path\\to\\logs\n"
            "  2) 在 %s 里写 {\"log_dir\": \"D:\\\\path\\\\to\\\\logs\"}"
            % (LOGDIR_ENV, LOCAL_CONFIG)
        )
    if not os.path.isdir(d):
        raise SystemExit("日志目录不存在：%s（改 %s 或 %s 后重试）"
                         % (d, LOGDIR_ENV, LOCAL_CONFIG))
    return d


def load_prompts():
    """读全部日志，返回 [(项目路径, 提示词内容)]，已滤掉框架噪声。"""
    d = log_dir()
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn), "r", encoding="utf-8-sig", errors="replace") as f:
                data = json.loads(f.read(), strict=False)
        except Exception as e:
            print("SKIP", fn, e, file=sys.stderr)
            continue
        for sess in data:
            proj = sess.get("project", "")
            for pr in sess.get("prompts", []):
                c = (pr.get("content") or "").strip()
                if not c or c.startswith(NOISE):
                    continue
                out.append((proj, c))
    return out


def lib_text(src_dir):
    """读入库提示词全文（拼接成一个字符串），供覆盖度比对用。"""
    parts = []
    for fn in sorted(os.listdir(src_dir)):
        if fn.endswith(".md"):
            with open(os.path.join(src_dir, fn), "r", encoding="utf-8") as f:
                parts.append(f.read())
    return "\n".join(parts)
