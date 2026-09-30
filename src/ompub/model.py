"""数据结构：笔记（Note）与问题（Issue）。

这一层只放数据，不放逻辑，方便其他模块互相引用而不产生循环依赖。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class Note:
    """一篇笔记。

    Attributes:
        path: 源文件路径。
        frontmatter: 解析后的 YAML frontmatter（键顺序保持原文顺序）。
        body: 正文（不含 frontmatter）。
    """

    path: Path
    frontmatter: Dict[str, object] = field(default_factory=dict)
    body: str = ""

    @property
    def title(self) -> str:
        """笔记标题：优先 frontmatter 的 title，否则用文件名（去扩展名）。"""
        t = self.frontmatter.get("title")
        if isinstance(t, str) and t.strip():
            return t.strip()
        return self.path.stem

    @property
    def name(self) -> str:
        """用于链接匹配的名字（文件名主干）。"""
        return self.path.stem

    def render(self) -> str:
        """把 frontmatter 与正文重新拼成完整 Markdown。

        具体的 YAML 序列化由 :mod:`ompub.frontmatter` 负责，这里只做拼接，
        避免 model 反向依赖处理模块。
        """
        from .frontmatter import dump  # 局部导入：避免模块级循环依赖

        if not self.frontmatter:
            return self.body
        return dump(self.frontmatter) + "\n" + self.body


@dataclass
class Issue:
    """一处检查发现的问题。

    Attributes:
        kind: 问题类别，如 ``wikilink`` / ``latex`` / ``frontmatter``。
        file: 相对路径字符串，便于报告里直接打印。
        line: 行号（从 1 开始）；不确定时为 0。
        message: 人话说明。
        snippet: 触发问题的原文片段。
        fixable: 是否可由 ``build`` 自动修复。
    """

    kind: str
    file: str
    line: int
    message: str
    snippet: str = ""
    fixable: bool = False

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        flag = " [可自动修复]" if self.fixable else ""
        base = f"{loc}  {self.message}{flag}"
        if self.snippet:
            base += f"\n      > {self.snippet.strip()[:100]}"
        return base


def group_by_kind(issues: List[Issue]) -> Dict[str, List[Issue]]:
    """按类别分组，报告输出时用。"""
    grouped: Dict[str, List[Issue]] = {}
    for it in issues:
        grouped.setdefault(it.kind, []).append(it)
    return grouped
