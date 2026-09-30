"""frontmatter 模块测试。

跑法（仓库根目录）：``PYTHONPATH=src pytest``
"""

from ompub.frontmatter import (
    dump,
    ensure_tags,
    normalize,
    parse,
    split_frontmatter,
)


def test_split_正常拆分():
    raw = "---\ntitle: 测试\ntags:\n  - a\n---\n\n正文在这里"
    fm, body = split_frontmatter(raw)
    assert "title: 测试" in fm
    assert body.strip() == "正文在这里"


def test_split_无_frontmatter():
    text = "# 标题\n\n没有 frontmatter"
    fm, body = split_frontmatter(text)
    assert fm == ""
    assert body == text


def test_split_未闭合视为无():
    """只有开头 --- 没有结尾时，不能把正文吞掉。"""
    text = "---\ntitle: 测试\n\n正文"
    fm, body = split_frontmatter(text)
    assert fm == ""
    assert body == text


def test_parse_标量与类型转换():
    data = parse("title: 线性代数\ncount: 12\nratio: 1.5\ndraft: false")
    assert data["title"] == "线性代数"
    assert data["count"] == 12
    assert data["ratio"] == 1.5
    assert data["draft"] is False


def test_parse_块式列表():
    data = parse("tags:\n  - 数学\n  - 笔记\naliases:\n  - LA")
    assert data["tags"] == ["数学", "笔记"]
    assert data["aliases"] == ["LA"]


def test_parse_内联列表():
    assert parse("aliases: [LA, 线代]")["aliases"] == ["LA", "线代"]


def test_parse_带引号():
    assert parse('title: "含: 冒号的标题"')["title"] == "含: 冒号的标题"


def test_dump_与_parse_往返():
    original = {"title": "测试", "tags": ["a", "b"], "count": 3}
    # 去掉首尾的 --- 再解析，验证序列化没有丢信息
    inner = "\n".join(dump(original).split("\n")[1:-1])
    assert parse(inner) == original


def test_normalize_不覆盖已有值():
    data = {"title": "原标题", "tags": ["已有"]}
    out = normalize(data, {"title": "默认标题", "lang": "zh"})
    assert out["title"] == "原标题"
    assert out["lang"] == "zh"
    assert out["tags"] == ["已有"]
    assert data["title"] == "原标题"  # 原对象不被改动


def test_normalize_补空值():
    """已有但为空的字段也该被补上。"""
    out = normalize({"tags": []}, {"tags": ["默认"]})
    assert out["tags"] == ["默认"]


def test_ensure_tags_去重且保序():
    out = ensure_tags({"tags": ["数学"]}, ["笔记", "数学"])
    assert out["tags"] == ["数学", "笔记"]


def test_dump_普通值不加多余引号():
    """只有真会引起歧义的值才加引号，zh-CN 这种保持原样。"""
    text = dump({"lang": "zh-CN", "title": "数学笔记", "note": "含: 冒号"})
    assert "lang: zh-CN" in text
    assert "title: 数学笔记" in text
    assert 'note: "含: 冒号"' in text


def test_ensure_tags_标量转列表():
    out = ensure_tags({"tags": "数学"}, ["笔记"])
    assert out["tags"] == ["数学", "笔记"]
