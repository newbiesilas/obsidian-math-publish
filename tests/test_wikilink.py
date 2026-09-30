"""双链转换测试。

重点验证两件事：该转的转对，不该转的（代码块、失效链接）一个都不动。
"""

from ompub.wikilink import convert, find, link_path, slugify

ALWAYS = lambda _name: True  # noqa: E731 —— 测试用：假装所有目标都存在
NONE = lambda _name: False  # noqa: E731


def test_find_解析各字段():
    links = find("见 [[01-极限]] 与 [[02-导数|导数那篇]] 还有 [[笔记#小节|锚点]]")
    assert len(links) == 3
    assert links[0].target == "01-极限"
    assert links[1].alias == "导数那篇"
    assert links[2].heading == "小节"
    assert links[2].alias == "锚点"


def test_convert_基本链接():
    out, issues = convert("见 [[01-极限]]", ALWAYS)
    assert out == "见 [01-极限](01-极限.md)"
    assert issues == []


def test_convert_别名():
    out, _ = convert("见 [[02-导数|导数那篇]]", ALWAYS)
    assert out == "见 [导数那篇](02-导数.md)"


def test_convert_小节锚点():
    out, _ = convert("见 [[02-导数#中值定理]]", ALWAYS)
    assert out == "见 [02-导数#中值定理](02-导数.md#中值定理)"


def test_convert_空格转码():
    """GitHub 链接里空格必须编码，否则跳转会断。"""
    out, _ = convert("[[18.06 Part 1 线性代数]]", ALWAYS)
    assert out == "[18.06 Part 1 线性代数](18.06%20Part%201%20线性代数.md)"


def test_convert_失效链接保留原样():
    """目标不存在时绝不猜链接，保留原文并报告。"""
    text = "见 [[不存在的笔记]]"
    out, issues = convert(text, NONE)
    assert out == text
    assert len(issues) == 1
    assert issues[0].kind == "wikilink"
    assert issues[0].fixable is False


def test_convert_嵌入链接不自动转():
    text = "![[figure.png]]"
    out, issues = convert(text, ALWAYS)
    assert out == text
    assert len(issues) == 1
    assert "嵌入" in issues[0].message


def test_convert_跳过围栏代码块():
    """代码块里的 [[...]] 是示例代码，转换会破坏原意。"""
    text = "```python\n# [[示例]]\nprint(1)\n```\n\n真的 [[01-极限]]"
    out, issues = convert(text, ALWAYS)
    assert "[[示例]]" in out
    assert "[01-极限](01-极限.md)" in out
    assert issues == []


def test_convert_跳过行内代码():
    text = "语法是 `[[笔记]]`，例如 [[01-极限]]"
    out, issues = convert(text, ALWAYS)
    assert "`[[笔记]]`" in out
    assert "[01-极限](01-极限.md)" in out


def test_link_path_已有扩展名不重复添加():
    assert link_path("笔记.md") == "笔记.md"
    assert link_path("figure.png") == "figure.png"


def test_slugify_中文与空格():
    assert slugify("中值定理 证明") == "中值定理-证明"
    assert slugify("Section 1.2: Basics") == "section-12-basics"
