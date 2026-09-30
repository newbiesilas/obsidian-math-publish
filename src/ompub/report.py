"""把检查结果整理成人能读的报告。

命令行输出遵循一个原则：**先说结论，再说细节**。
扫描完先给一行总计，再按类别列问题，否则一长串输出没人看。
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from .model import Issue, group_by_kind

KIND_LABEL = {
    "wikilink": "双链",
    "latex": "公式",
    "frontmatter": "Frontmatter",
    "other": "其他",
}


def summarize(issues: Sequence[Issue]) -> str:
    """一行总计，例如 ``共 7 处问题：公式 5 · 双链 2（3 处可自动修复）``。"""
    if not issues:
        return "未发现问题。"
    grouped = group_by_kind(list(issues))
    parts = [
        f"{KIND_LABEL.get(k, k)} {len(v)}" for k, v in sorted(grouped.items(), key=lambda x: -len(x[1]))
    ]
    fixable = sum(1 for i in issues if i.fixable)
    tail = f"（{fixable} 处可自动修复）" if fixable else ""
    return f"共 {len(issues)} 处问题：" + " · ".join(parts) + tail


def format_issues(issues: Sequence[Issue], limit_per_kind: int = 20) -> str:
    """按类别分组输出，每类最多 ``limit_per_kind`` 条。"""
    if not issues:
        return ""
    grouped: Dict[str, List[Issue]] = group_by_kind(list(issues))
    out: List[str] = []
    for kind, items in sorted(grouped.items(), key=lambda x: -len(x[1])):
        out.append(f"\n【{KIND_LABEL.get(kind, kind)}】{len(items)} 处")
        for it in items[:limit_per_kind]:
            out.append("  " + str(it).replace("\n", "\n  "))
        if len(items) > limit_per_kind:
            out.append(f"  … 其余 {len(items) - limit_per_kind} 处略")
    return "\n".join(out)
