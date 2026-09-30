"""LaTeX 兼容修复与检查。

核心问题（也是写这个工具的原因）：**GFM 表格解析器先于 MathJax 工作**。
表格单元格里写 ``$|x|$``，那个竖线会被当成列分隔符，整行被切成两半，
公式只剩 ``$`` 开头的一截，自然渲染不出来。

实测对照：

============================================  =====================
写法                                          渲染结果
============================================  =====================
``$d=\\dfrac{|Ax_0+D|}{\\sqrt{A^2}}$``        被截断，渲染失败
``$d=\\dfrac{\\lvert Ax_0+D\\rvert}{\\sqrt{A^2}}$``  正常
============================================  =====================

注意不能简单替换成 ``\\|``：MathJax 里 ``\\|`` 是**双竖线**（范数 ‖），语义变了。
必须按绝对值成对替换成 ``\\lvert`` / ``\\rvert``。
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .model import Issue

# GitHub MathJax 默认不支持或行为不确定的宏。
# 命中不等于一定错，只是提醒人工确认——所以都用 warning 级别。
DANGEROUS_MACROS = [
    (r"\\tag\b", r"\tag 在 GitHub MathJax 无效（无公式编号），请删除"),
    (r"\\label\b", r"\label 无交叉引用可配，建议删除"),
    (r"\\eqref\b", r"\eqref 无法解析引用，请改写成具体编号或删除"),
    (r"\\ref\{", r"\ref 无法解析引用，请改写成具体编号"),
    (r"\\newcommand\b", r"\newcommand 需 MathJax 扩展，GitHub 不加载"),
    (r"\\renewcommand\b", r"\renewcommand 需 MathJax 扩展，GitHub 不加载"),
    (r"\\require\b", r"\require 需 MathJax 扩展，GitHub 不加载"),
    (r"\\def\b", r"\def 需 MathJax 扩展，建议改用 \mathrm 或直接展开"),
    (r"\\notag\b", r"\notag 无效，请删除"),
    (r"\\nonumber\b", r"\nonumber 无效，请删除"),
    (r"\\begin\{equation\*?\}", r"equation 环境无编号支持，建议改用 \\[ ... \\] 或 aligned"),
]

_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_INLINE_MATH = re.compile(r"(?<!\$)\$(?!\$)((?:[^$\n]|\\\$)+?)(?<!\\)\$(?!\$)")


def is_table_row(line: str) -> bool:
    """判断是否表格行。

    排除 ``|---|:---|`` 这类分隔行（只由 | - : 空格组成）。
    """
    if not _TABLE_ROW.match(line):
        return False
    return not set(line.strip()) <= set("|-: ")


def _count_bare_pipes(segment: str) -> int:
    """统计片段里的裸竖线（``\\|`` 不算）。

    逐字符扫描而不是 ``str.count``：``\\|`` 里的竖线是有意写的双竖线，
    不能计入，否则会误判奇偶。
    """
    n = 0
    i = 0
    while i < len(segment):
        if segment[i] == "\\":
            i += 2
            continue
        if segment[i] == "|":
            n += 1
        i += 1
    return n


def _protect_pipes(segment: str) -> Tuple[str, int, bool]:
    """把公式片段里的裸竖线成对替换为 ``\\lvert`` / ``\\rvert``。

    Returns:
        (新片段, 替换个数, 是否为奇数个竖线)

    两个关键细节：

    1. **左侧要带尾随空格** —— ``|x|`` 若直接换成 ``\\lvertx\\rvert``，
       TeX 会把 ``\\lvertx`` 当成一个宏名而报错，必须写成 ``\\lvert x\\rvert``。
    2. **奇数个竖线一律不改** —— 大概率是条件概率 ``P(A|B)`` 这类用法，
       不是绝对值；改了语义就错了，交给人工确认更安全。
    """
    count = _count_bare_pipes(segment)
    if count == 0:
        return segment, 0, False
    if count % 2 == 1:
        return segment, 0, True

    out: List[str] = []
    i = 0
    use_left = True
    while i < len(segment):
        ch = segment[i]
        if ch == "\\":
            # 转义序列原样保留：\| 是有意写的双竖线，\lvert 已经安全
            out.append(segment[i : i + 2])
            i += 2
            continue
        if ch == "|":
            out.append("\\lvert " if use_left else "\\rvert")
            use_left = not use_left
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), count, False


def fix(text: str, file: str = "") -> Tuple[str, List[Issue]]:
    """修掉表格里会被截断的竖线。

    只动**表格行内的行内公式**，正文其他地方不动——``|`` 在普通段落里
    可能是表格、条件概率或集合分隔符，改错了比不改更糟。
    """
    issues: List[Issue] = []
    lines = text.split("\n")
    total = 0

    for idx, line in enumerate(lines, start=1):
        if not is_table_row(line) or "$" not in line:
            continue

        odd_here = False

        def _sub(m: "re.Match[str]") -> str:
            nonlocal total, odd_here
            new, n, odd = _protect_pipes(m.group(1))
            total += n
            odd_here = odd_here or odd
            # 奇数时 new 就是原文，等于不改，只在下面记一条待确认
            return "$" + new + "$"

        new_line = _INLINE_MATH.sub(_sub, line)
        if new_line != line:
            lines[idx - 1] = new_line
            issues.append(
                Issue(
                    kind="latex",
                    file=file,
                    line=idx,
                    message=f"表格内 {_count_pipes(line)} 处裸竖线已替换为 \\lvert \\rvert",
                    snippet=line.strip()[:100],
                    fixable=True,
                )
            )
        if odd_here:
            issues.append(
                Issue(
                    kind="latex",
                    file=file,
                    line=idx,
                    message="该行公式里竖线数量为奇数（可能不是绝对值），已跳过不修改，请人工确认",
                    snippet=lines[idx - 1].strip()[:100],
                    fixable=False,
                )
            )

    _ = total  # 统计值目前只在 Issue 文案里体现，保留变量便于后续扩展
    return "\n".join(lines), issues


def _count_pipes(line: str) -> int:
    """统计一行里**公式内部**的裸竖线数量（表格行用）。"""
    return sum(_count_bare_pipes(m.group(1)) for m in _INLINE_MATH.finditer(line))


def scan(text: str, file: str = "") -> List[Issue]:
    """只检查不修改：找出公式相关的隐患。

    检查项：
    1. 危险宏（MathJax 不支持）；
    2. 表格内的裸竖线；
    3. 行内公式 ``$ x $`` 首尾空格（GitHub 不渲染）；
    4. 落单的 ``$``（多半是没闭合）。
    """
    issues: List[Issue] = []
    lines = text.split("\n")

    for idx, line in enumerate(lines, start=1):
        if "$" not in line:
            continue

        for pattern, message in DANGEROUS_MACROS:
            if re.search(pattern, line):
                issues.append(
                    Issue(
                        kind="latex",
                        file=file,
                        line=idx,
                        message=message,
                        snippet=line.strip()[:100],
                        fixable=False,
                    )
                )

        if is_table_row(line) and _count_pipes(line):
            issues.append(
                Issue(
                    kind="latex",
                    file=file,
                    line=idx,
                    message=f"表格内 {_count_pipes(line)} 处裸竖线会截断公式",
                    snippet=line.strip()[:100],
                    fixable=True,
                )
            )

        # 必须用 _INLINE_MATH 配对出的公式来判断首尾空格。
        # 早期版本直接找 "$ ... $"，会把表格里相邻两个公式之间的 " | "
        # 当成公式内容，报出一堆假问题。
        for m in _INLINE_MATH.finditer(line):
            seg = m.group(1)
            if seg != seg.strip():
                issues.append(
                    Issue(
                        kind="latex",
                        file=file,
                        line=idx,
                        message="行内公式 $ 内侧有空格，GitHub 不会渲染，请写成 $x$",
                        snippet="$" + seg + "$",
                        fixable=False,
                    )
                )

    # 落单的 $：全文统计，非偶数大概率是漏写了
    if text.count("$") % 2 == 1:
        issues.append(
            Issue(
                kind="latex",
                file=file,
                line=0,
                message=f"全文 $ 出现奇数次（{text.count('$')}），可能有公式没闭合",
                fixable=False,
            )
        )

    return issues
