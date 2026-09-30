"""生成索引页（README / 总览）。

索引页是别人进仓库后看到的第一屏：一张表列出全部笔记，
附带每篇的标题与标签，方便直接跳进去。
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from .model import Note
from .wikilink import link_path


def _tags_of(note: Note) -> str:
    """取出标签，拼成 ``标签1 · 标签2``。"""
    tags = note.frontmatter.get("tags")
    if isinstance(tags, list):
        return " · ".join(str(t) for t in tags)
    if isinstance(tags, str) and tags:
        return tags
    return "—"


def _summary_of(note: Note, limit: int = 60) -> str:
    """取正文第一句有实质内容的行作为摘要。

    跳过标题、引用块、分隔线和空行——``> [!abstract]`` 这类 callout
    内容更适合做摘要，但为简单起见只取第一个普通段落。
    """
    for line in note.body.split("\n"):
        s = line.strip()
        # 公式块与表格不适合做摘要，跳过
        if not s or s.startswith(("#", ">", "---", "|", "```", "$$")):
            continue
        s = s.replace("**", "").replace("`", "")
        return s[:limit] + ("…" if len(s) > limit else "")
    return "—"


def build_index(
    notes: Sequence[Note],
    title: str = "笔记索引",
    intro: str = "",
    extra_sections: Optional[List[str]] = None,
) -> str:
    """生成索引页 Markdown。

    Args:
        notes: 要列入的笔记（应保持自然序）。
        title: 页面标题。
        intro: 标题下方的一段说明，可为空。
        extra_sections: 追加在表格之后的自定义段落。
    """
    lines: List[str] = [f"# {title}", ""]
    if intro:
        lines.extend([intro, ""])

    lines.extend(
        [
            "| # | 笔记 | 摘要 | 标签 |",
            "|:--:|------|:----:|:----:|",
        ]
    )
    for i, note in enumerate(notes, start=1):
        link = f"[{note.title}]({link_path(note.name)})"
        lines.append(f"| {i} | {link} | {_summary_of(note)} | {_tags_of(note)} |")

    lines.append("")
    for section in extra_sections or []:
        lines.extend([section, ""])

    return "\n".join(lines).rstrip() + "\n"
