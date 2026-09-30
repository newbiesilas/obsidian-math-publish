"""极简 YAML frontmatter 解析与序列化。

为什么要自己写而不是直接用 PyYAML？

- 笔记的 frontmatter 几乎只有**标量**与**单层列表**两种形态；
- 零依赖意味着 ``pip install -e .`` 之后立刻能跑，不必先解决依赖；
- 自己写一遍能真正理解 frontmatter 的结构。

局限（代码里也有注释标注）：不支持嵌套字典、多行字符串、锚点等。
如果你的 vault 用到这些，请换 PyYAML——这是刻意的取舍，不是遗漏。

支持三种写法：

.. code-block:: yaml

    title: 线性代数                 # 标量
    tags:                           # 块式列表
      - 数学
      - 笔记
    aliases: [LA, 线代]             # 内联列表
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_DELIM = re.compile(r"^---\s*$")


def split_frontmatter(text: str) -> Tuple[str, str]:
    """把文档拆成 (frontmatter 原文, 正文)。

    没有 frontmatter 时返回 ``("", 原文)``。
    只认文件**开头**的 ``---`` 块，正文中间的分隔线不算。
    """
    if not text:
        return "", ""

    lines = text.split("\n")
    # 第一行必须是 ---（允许前面有 BOM）
    if not _DELIM.match(lines[0].lstrip("\ufeff")):
        return "", text

    for i in range(1, len(lines)):
        if _DELIM.match(lines[i]):
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])

    # 开始有 --- 却没闭合，视为没有 frontmatter，避免误吞正文
    return "", text


def _coerce(value: str) -> object:
    """把字符串转成合适的 Python 类型。

    只处理三种常见字面量，其余一律当字符串——笔记里的中文标题、
    日期写法很多，保守处理更安全。
    """
    s = value.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~", ""):
        return None
    # 纯整数 / 浮点
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_inline_list(value: str) -> List[object]:
    """解析 ``[a, b, c]`` 形式的内联列表。"""
    inner = value.strip()[1:-1]
    items = [p.strip() for p in inner.split(",")]
    return [_coerce(i) for i in items if i]


def parse(raw: str) -> Dict[str, object]:
    """解析 frontmatter 原文为字典（保持键的原始顺序）。"""
    data: Dict[str, object] = {}
    if not raw.strip():
        return data

    current_key: str | None = None
    for line in raw.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue

        stripped = line.strip()

        # 块式列表项：  - xxx
        if stripped.startswith("- ") and current_key is not None:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(_coerce(stripped[2:]))  # type: ignore[union-attr]
            continue

        m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*:\s*(.*)$", line)
        if not m:
            continue  # 嵌套结构：不支持，整行跳过

        key, value = m.group(1), m.group(2).strip()
        current_key = key
        if value.startswith("[") and value.endswith("]"):
            data[key] = _parse_inline_list(value)
        elif value == "":
            data[key] = []  # 先占位，后续 - 项会填充
        else:
            data[key] = _coerce(value)

    return data


def _fmt_value(value: object) -> str:
    """标量转 YAML 文本。含特殊字符时加引号。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    # 只有真正会引起歧义的情况才加引号：空串、以特殊字符开头、
    # 含 ": "（会被当成嵌套键）或 " #"（会被当成注释）。
    # 像 zh-CN、数学笔记 这类值保持原样，读起来更干净。
    if s == "" or s[0] in "#[]{},&*!|>%@`\"'" or ": " in s or " #" in s:
        return '"%s"' % s.replace('"', '\\"')
    return s


def dump(data: Dict[str, object]) -> str:
    """把字典序列化为 frontmatter 文本（含首尾 ``---``）。"""
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            if not value:
                lines.append("%s: []" % key)
            else:
                lines.append("%s:" % key)
                lines.extend("  - %s" % _fmt_value(v) for v in value)
        else:
            lines.append("%s: %s" % (key, _fmt_value(value)))
    lines.append("---")
    return "\n".join(lines)


def normalize(
    data: Dict[str, object], defaults: Dict[str, object] | None = None
) -> Dict[str, object]:
    """补齐缺省字段，**不覆盖**已有值。

    Args:
        data: 原 frontmatter。
        defaults: 缺省字段，如 ``{"lang": "zh-CN", "license": "CC BY-NC-SA 4.0"}``。

    Returns:
        新字典（不改原对象）。
    """
    out = dict(data)
    for key, value in (defaults or {}).items():
        if key not in out or out[key] in (None, "", []):
            out[key] = value
    return out


def ensure_tags(data: Dict[str, object], extra: List[str]) -> Dict[str, object]:
    """把 ``extra`` 里的标签并入 ``tags``，去重且保持顺序。"""
    out = dict(data)
    existing = out.get("tags")
    tags: List[str] = []
    if isinstance(existing, list):
        tags = [str(t) for t in existing]
    elif isinstance(existing, str) and existing:
        tags = [existing]
    for t in extra:
        if t not in tags:
            tags.append(t)
    if tags:
        out["tags"] = tags
    return out
