"""LaTeX 修复与检查测试。

最关键的一条：表格里的裸竖线必须成对变成 \\lvert / \\rvert，
而普通段落里的竖线绝对不能动。
"""

from ompub.latex import fix, is_table_row, scan

TABLE_BAD = "| 绝对值 | $|x|<1$ |"
TABLE_GOOD = "| 绝对值 | $\\lvert x\\rvert<1$ |"


def test_is_table_row():
    assert is_table_row("| a | b |")
    assert not is_table_row("|---|---|")  # 分隔行不算
    assert not is_table_row("普通段落 |x|")


def test_fix_表格内裸竖线成对替换():
    out, issues = fix("| 公式 | $|x|$ |")
    # 注意 \lvert 后面必须有空格，否则 TeX 会把 \lvertx 当成未定义宏
    assert "\\lvert x\\rvert" in out
    assert any("裸竖线" in i.message for i in issues)


def test_fix_多个绝对值交替配对():
    out, _ = fix("| d | $\\dfrac{|a|}{|b|}$ |")
    assert out.count("\\lvert") == 2
    assert out.count("\\rvert") == 2
    # 第一个 | 变 \lvert，第二个变 \rvert，依次交替
    assert out.index("\\lvert") < out.index("\\rvert")


def test_fix_不动普通段落():
    """段落里的 | 可能是表格或集合分隔符，改了就是帮倒忙。"""
    text = "条件概率写作 $P(A|B)$，不要动。"
    out, issues = fix(text)
    assert out == text
    assert not any("裸竖线" in i.message for i in issues)


def test_fix_保留转义双竖线():
    """\\| 是范数 ‖，语义不同，必须原样保留。"""
    text = "| 范数 | $\\|x\\|$ |"
    out, _ = fix(text)
    assert "\\|x\\|" in out
    assert "\\lvert" not in out


def test_fix_已有的_lvert_不重复处理():
    text = "| 绝对值 | $\\lvert x\\rvert$ |"
    out, issues = fix(text)
    assert out == text
    assert not any("裸竖线" in i.message for i in issues)


def test_fix_奇数竖线不动只警告():
    """条件概率 $P(A|B)$ 只有一个竖线，改了语义就错了：必须原样保留并提醒。"""
    text = "| 条件 | $P(A|B)$ |"
    out, issues = fix(text)
    assert out == text, "奇数个竖线不应自动改写"
    assert "\\lvert" not in out
    assert any("奇数" in i.message for i in issues)


def test_scan_危险宏():
    issues = scan("$$x=1 \\tag{1}$$")
    assert any("\\tag" in i.message for i in issues)


def test_scan_行内公式内侧空格():
    issues = scan("取值 $ x $ 时")
    assert any("空格" in i.message for i in issues)


def test_scan_表格里相邻公式不误报():
    """回归测试：早期版本把两个公式之间的 ' | ' 当成公式，报假问题。"""
    issues = scan("| 函数 | $x^n$ | $nx^{n-1}$ |")
    assert not any("空格" in i.message for i in issues)


def test_scan_奇数美元符号():
    issues = scan("这里 $x 漏了闭合")
    assert any("奇数" in i.message for i in issues)


def test_scan_干净文档无问题():
    issues = scan("# 标题\n\n公式 $\\lvert x\\rvert$ 正常。\n\n$$a^2+b^2=c^2$$")
    assert issues == []
