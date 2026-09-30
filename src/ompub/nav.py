"""生成章节导航。

顺序通读的笔记库，每篇末尾加一行「上一章 / 下一章 / 返回总览」，
读起来才连贯。生成的是**标准 Markdown 链接**，GitHub 与 Obsidian 都能跳。
"""

from __future__ import annotations

from typing import List, Optional

from .model import Note
from .wikilink import link_path

_TEMPLATE = "---\n\n> {prev} ｜ {next} ｜ {home}\n"


def _link(note: Optional[Note], missing: str) -> str:
    """单条导航链接；没有时用占位文本（不生成死链）。"""
    if note is None:
        return missing
    return f"[{note.title}]({link_path(note.name)})"


def build_nav(
    notes: List[Note],
    index: int,
    overview: Optional[Note] = None,
    prev_text: str = "上一章：",
    next_text: str = "下一章：",
) -> str:
    """为第 ``index`` 篇笔记生成导航块。

    Args:
        notes: 排好序的笔记列表（通常是整个 vault）。
        index: 当前笔记在列表中的位置。
        overview: 总览/索引页；为 None 时不输出「返回总览」。
        prev_text / next_text: 前缀文案。

    Returns:
        一段 Markdown；首尾都在列表两端时只输出可用的部分。
    """
    prev_note = notes[index - 1] if index - 1 >= 0 else None
    next_note = notes[index + 1] if index + 1 < len(notes) else None

    parts = []
    if prev_note is not None:
        parts.append(prev_text + _link(prev_note, "（已是第一篇）"))
    if next_note is not None:
        parts.append(next_text + _link(next_note, "（已是最后一篇）"))
    if overview is not None:
        parts.append(f"[返回总览]({link_path(overview.name)})")

    if not parts:
        return ""
    return "---\n\n> " + " ｜ ".join(parts) + "\n"


def strip_nav(body: str) -> str:
    """去掉上一次生成的导航块，避免重复追加。

    判断依据：以 ``---`` 开头、后面紧跟以 ``> `` 开头的引用行。
    """
    lines = body.rstrip().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("> "):
            continue
        if lines[i].strip() == "---" and i + 1 < len(lines):
            return "\n".join(lines[:i]).rstrip() + "\n"
        break
    return body
