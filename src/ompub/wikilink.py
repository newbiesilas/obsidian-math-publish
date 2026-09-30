"""Obsidian 双链 ``[[...]]`` → 标准 Markdown 链接。

为什么需要这一步：Obsidian 的双链只在自己的库里能跳，发到 GitHub 上
就是一串死文本。转换后两边都能点。

语法覆盖：

====================  ==============================
``[[笔记]]``          ``[笔记](笔记.md)``
``[[笔记|显示]]``     ``[显示](笔记.md)``
``[[笔记#小节]]``     ``[笔记#小节](笔记.md#小节)``
``[[笔记#小节|显示]]`` ``[显示](笔记.md#小节)``
``![[图片.png]]``     嵌入，不自动转换（需人工确认）
====================  ==============================

代码块里的 ``[[...]]`` 是示例代码，不能动——所以转换前先算出"保护区"。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .model import Issue

# 组：1=是否嵌入 2=目标 3=#小节(含#) 4=小节 5=|别名(含|) 6=别名
WIKILINK_RE = re.compile(r"(!?)\[\[([^\]\|#\n]+?)(#([^\]\|#\n]+))?(\|([^\]\n]+?))?\]\]")


@dataclass
class Wikilink:
    """一处双链。"""

    raw: str
    target: str
    heading: Optional[str] = None
    alias: Optional[str] = None
    embedded: bool = False
    start: int = 0
    end: int = 0


def find(text: str) -> List[Wikilink]:
    """列出文本中所有双链（含代码块内的，由调用方决定是否处理）。"""
    links: List[Wikilink] = []
    for m in WIKILINK_RE.finditer(text):
        links.append(
            Wikilink(
                raw=m.group(0),
                target=m.group(2).strip(),
                heading=m.group(4).strip() if m.group(4) else None,
                alias=m.group(6).strip() if m.group(6) else None,
                embedded=m.group(1) == "!",
                start=m.start(),
                end=m.end(),
            )
        )
    return links


def _protected_spans(text: str) -> List[Tuple[int, int]]:
    """返回不该被改写的区间：围栏代码块与行内代码。

    逐行扫描而不是用正则，是因为围栏代码块的配对要按行判断，
    正则处理嵌套缩进很容易出错。
    """
    spans: List[Tuple[int, int]] = []
    offset = 0
    fence: Optional[str] = None
    start = 0
    for line in text.split("\n"):
        stripped = line.strip()
        if fence is None:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence = stripped[:3]
                start = offset
        elif stripped.startswith(fence):
            spans.append((start, offset + len(line)))
            fence = None
        offset += len(line) + 1
    if fence is not None:  # 没闭合的围栏：到末尾都算代码块
        spans.append((start, len(text)))

    for m in re.finditer(r"`[^`\n]+`", text):
        spans.append((m.start(), m.end()))
    return spans


def _in_spans(pos: int, spans: List[Tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in spans)


def link_path(target: str) -> str:
    """笔记名 → 相对链接路径。

    只把空格编码成 ``%20``。中文刻意保留原文：GitHub 能正常跳转，
    全部百分号编码反而让链接在源码里没法读。
    """
    p = target.strip()
    if not p.lower().endswith((".md", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".pdf")):
        p += ".md"
    return p.replace(" ", "%20")


def slugify(heading: str) -> str:
    """小节标题 → GitHub 锚点（小写、空格转连字符、去标点）。"""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", s)
    return re.sub(r"\s+", "-", s).strip("-")


def convert(
    text: str,
    exists: Callable[[str], bool],
    file: str = "",
) -> Tuple[str, List[Issue]]:
    """把双链替换成 Markdown 链接。

    Args:
        text: 原文。
        exists: 判断目标笔记是否存在的回调（由 vault 提供）。
        file: 当前文件名，仅用于生成 Issue。

    Returns:
        (新文本, 问题列表)。失效链接与嵌入链接会**保留原样**并记入问题，
        绝不猜一个可能 404 的地址。
    """
    spans = _protected_spans(text)
    issues: List[Issue] = []
    pieces: List[str] = []
    cursor = 0

    for link in find(text):
        if _in_spans(link.start, spans):
            continue  # 示例代码，跳过

        pieces.append(text[cursor : link.start])

        if link.embedded:
            issues.append(
                Issue(
                    kind="wikilink",
                    file=file,
                    line=text.count("\n", 0, link.start) + 1,
                    message="嵌入链接 ![[...]] 不自动转换，请确认目标文件已随仓库发布",
                    snippet=link.raw,
                    fixable=False,
                )
            )
            pieces.append(link.raw)
        elif not exists(link.target):
            issues.append(
                Issue(
                    kind="wikilink",
                    file=file,
                    line=text.count("\n", 0, link.start) + 1,
                    message=f"双链目标不存在：{link.target}",
                    snippet=link.raw,
                    fixable=False,
                )
            )
            pieces.append(link.raw)
        else:
            anchor = "#" + slugify(link.heading) if link.heading else ""
            label = link.alias or (link.target + (f"#{link.heading}" if link.heading else ""))
            pieces.append(f"[{label}]({link_path(link.target)}{anchor})")

        cursor = link.end

    pieces.append(text[cursor:])
    return "".join(pieces), issues
