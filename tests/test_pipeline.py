"""端到端测试：拿 examples/sample-vault 真跑一遍 build。

这一层验证"各模块拼起来还能用"，比单元测试更能暴露集成问题
（路径、编码、导航顺序等）。
"""

from pathlib import Path

import pytest

from ompub.cli import main
from ompub.vault import Vault

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "sample-vault"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    code = main(["build", str(EXAMPLES), str(out)])
    return code, out


def test_vault_加载示例库():
    vault = Vault(EXAMPLES)
    assert len(vault.notes) == 3
    assert vault.exists("01-极限与连续")
    assert not vault.exists("不存在的笔记")


def test_build_退出码非零因为存在需人工处理的问题(built):
    """示例库里故意放了 \\tag 和失效双链，所以应当返回 1。"""
    code, _ = built
    assert code == 1


def test_build_输出了全部笔记(built):
    _, out = built
    names = {p.name for p in out.glob("*.md")}
    assert "01-极限与连续.md" in names
    assert "02-导数与微分.md" in names
    assert "README.md" in names  # 索引页


def test_build_修好了表格里的竖线(built):
    _, out = built
    text = (out / "01-极限与连续.md").read_text(encoding="utf-8")
    assert "\\lvert x\\rvert<1" in text
    assert "|x|<1" not in text


def test_build_双链转成可跳转链接(built):
    _, out = built
    text = (out / "01-极限与连续.md").read_text(encoding="utf-8")
    assert "[02-导数与微分](02-导数与微分.md)" in text


def test_build_代码块里的假双链保留(built):
    """示例的 Python 注释里有 [[双链]]，不该被转换。"""
    _, out = built
    text = (out / "02-导数与微分.md").read_text(encoding="utf-8")
    assert "[[双链]]" in text


def test_build_生成了导航(built):
    _, out = built
    text = (out / "01-极限与连续.md").read_text(encoding="utf-8")
    assert "下一章" in text
    assert "返回总览" in text


def test_build_索引页含全部笔记链接(built):
    _, out = built
    text = (out / "README.md").read_text(encoding="utf-8")
    assert "01-极限与连续" in text
    assert "笔记索引" in text


def test_check_能独立运行(tmp_path):
    code = main(["check", str(EXAMPLES), "--quiet"])
    assert code == 1  # 示例库故意有问题
