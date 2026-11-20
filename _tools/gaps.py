# -*- coding: utf-8 -*-
"""按任务关键词做覆盖度审计：找出日志中高频、但库内未覆盖的方向。

用法：
    python _tools/gaps.py

关键词表 KEYS 是人工维护的任务方向清单；ALIAS 记录「库内用通用说法收录、
但关键词字面不出现」的情况，避免为了凑字面重复写一条提示词。
"""
import os, sys

# 让中文输出在 Git Bash / Windows Terminal / VSCode 终端里正常显示
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console
use_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "prompts")

LIB = logload.lib_text(SRC)
LIB_LOWER = LIB.lower()

KEYS = [
    "公式引用", "交叉引用", "参考文献", "引用", "图注", "表注", "脚注", "排版", "编译", "PDF",
    "摘要", "关键词", "致谢", "作者", "署名", "版权", "许可证", "开源协议", "贡献指南",
    "复现", "可复现", "存档", "留痕", "实验记录", "工作流", "流水线", "断点", "续跑",
    "爬虫", "抓取", "订阅", "RSS", "接口", "API", "后端", "数据库", "缓存", "队列",
    "并发", "异步", "定时", "批处理", "命令行", "环境变量", "容器", "Docker", "部署",
    "CI", "监控", "日志", "埋点", "统计", "仪表盘", "看板",
    "国际化", "多语言", "i18n", "时区", "单位", "坐标", "配色", "深色", "主题", "皮肤",
    "无障碍", "键盘", "快捷键", "暗色", "打印", "导出", "导入", "分页", "筛选", "排序",
    "搜索", "索引", "标签", "分组", "收藏", "评分", "评论", "版本", "回滚", "备份", "迁移",
    "命名规范", "注释", "文档字符串", "类型注解", "静态检查", "lint", "格式化", "覆盖率",
    "依赖", "升级", "安全", "加密", "隐私", "脱敏", "性能", "内存", "泄漏", "并发安全",
    "示例", "demo", "样例", "案例", "教程", "演练", "模板", "脚手架", "占位符",
    "元数据", "SEO", "sitemap", "robots", "域名", "证书", "反向代理", "CDN", "404",
    "动效", "动画", "画布", "拖拽", "缩放", "流程图", "时序图", "架构图",
    "需求", "原型", "线框", "可用性", "文案", "术语", "翻译", "润色",
    "摘要写作", "结论", "引言", "相关工作", "方法", "讨论", "附录", "补充材料",
    "选题", "立项", "开题", "预印本", "投稿", "返修", "回复审稿", "会议",
    "组会", "汇报", "讲座", "教学", "习题", "答辩", "开题报告", "学位",
]

# 同义覆盖：库内用通用说法收录了该能力，关键词字面不同，不算缺口。
# 值可以是多个条目标题，用「、」分开——只要其中一个还在库里就算数。
ALIAS = {
    "Docker": "编写容器配置",
    "demo": "设计并精简可运行示例、预置示例数据",
    "元数据": "拟定论文关键词",
    "sitemap": "提升页面 SEO 表现",
    "暗色": "实现多主题与深色模式",
    "皮肤": "实现多主题与深色模式",
}


def alias_alive(v):
    """ALIAS 指向的条目标题是否还在库里。标题改名后要回来改这里。"""
    return any(t.strip() and t.strip() in LIB for t in v.split("、"))


# ALIAS 失效检查：条目改名后，这张表会静默地说谎（把缺口判成「同义已覆盖」）。
stale = [f"{k} → {v}" for k, v in ALIAS.items() if not alias_alive(v)]
if stale:
    print("! ALIAS 指向的条目已不在库里，请更新 _tools/gaps.py 的 ALIAS 表：")
    for s in stale:
        print("  " + s)
    print()

logs = [c for _, c in logload.load_prompts()]
print(f"日志提示词总数: {len(logs)}\n")
rows = []
for k in KEYS:
    n = sum(1 for c in logs if k.lower() in c.lower())
    if n == 0:
        continue
    covered = k.lower() in LIB_LOWER
    rows.append((n, k, covered))
rows.sort(reverse=True)

out = []
print(f"{'次数':>6}  {'覆盖':<4} 关键词")
for n, k, cov in rows:
    flag = "Y" if cov else ("A" if k in ALIAS else "N")
    out.append(f"[{n:5d}] {flag} {k}")
print("\n".join(out))
open(os.path.join(ROOT, "_tools", "kwcov.txt"), "w", encoding="utf-8").write("\n".join(out))

miss = [k for n, k, c in rows if not c and k not in ALIAS]
print(f"\n未覆盖关键词 {len(miss)} 个: {'、'.join(miss) if miss else '（无）'}")
alias_note = [f"{k} → {v}" for k, v in ALIAS.items() if k in [k2 for n, k2, c in rows if not c]]
if alias_note:
    print("同义已覆盖（字面差异，非缺口）：" + "；".join(alias_note))
