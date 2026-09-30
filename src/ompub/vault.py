"""读取 Obsidian vault：把目录里的一堆 .md 变成 :class:`Note` 列表。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set

from .frontmatter import parse, split_frontmatter
from .model import Note

# 这些目录里通常没有笔记，扫描时跳过（也避免把 .obsidian 的配置 md 当笔记）
SKIP_DIRS = {
    ".git",
    ".obsidian",
    ".github",
    ".venv",
    "node_modules",
    "__pycache__",
    "assets",
    "attachments",
    "Excalidraw",
}


def natural_key(name: str) -> tuple:
    """自然排序键：``第2章`` 排在 ``第10章`` 前面。

    直接字符串排序会把 10 排在 2 前面，中文笔记里章序号很常见，
    所以这里把数字段拆出来按数值比较。
    """
    parts = re.split(r"(\d+)", name)
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parts)


def iter_markdown(root: Path) -> List[Path]:
    """递归列出所有 .md 文件（跳过隐藏与无关目录）。"""
    found: List[Path] = []
    for path in root.rglob("*.md"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        if rel.name.startswith("."):
            continue
        found.append(path)
    return sorted(found, key=lambda p: natural_key(str(p.relative_to(root))))


class Vault:
    """一个笔记库。

    Attributes:
        root: vault 根目录。
        notes: 按自然序排好的笔记。
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.notes: List[Note] = []
        self._by_name: Dict[str, Note] = {}
        self.load()

    def load(self) -> None:
        """扫描并解析全部笔记。"""
        self.notes = []
        self._by_name = {}
        for path in iter_markdown(self.root):
            try:
                raw = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            fm_raw, body = split_frontmatter(raw)
            note = Note(
                path=path,
                frontmatter=parse(fm_raw),
                body=body,
            )
            note._rel = str(path.relative_to(self.root))  # type: ignore[attr-defined]
            self.notes.append(note)
            self._by_name.setdefault(note.name.lower(), note)

    @property
    def names(self) -> Set[str]:
        """全部笔记名（小写），用于双链匹配。"""
        return set(self._by_name)

    def exists(self, target: str) -> bool:
        """判断双链目标是否存在（忽略大小写，允许省略 .md）。"""
        key = target.strip().lower()
        if key.endswith(".md"):
            key = key[:-3]
        return key in self._by_name

    def rel(self, note: Note) -> str:
        """笔记相对 vault 根的路径（报告里显示用）。"""
        try:
            return str(note.path.relative_to(self.root))
        except ValueError:
            return note.path.name
