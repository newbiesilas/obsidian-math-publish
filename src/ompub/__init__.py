"""ompub —— Obsidian 数学笔记发布工具。

把 Obsidian vault 里的数学笔记整理成 GitHub 能正常渲染的 Markdown：

- 双链 ``[[笔记]]`` 转成标准 Markdown 链接；
- 修掉表格里会被 GFM 截断的 LaTeX（裸竖线 ``|`` → ``\\lvert \\rvert``）；
- 统一 YAML frontmatter，补默认字段；
- 生成章节导航与索引页。

模块分层（由下至上）：::

    frontmatter / wikilink / latex   ← 纯文本处理，无副作用，最容易测
    model / vault                    ← 数据结构与文件读取
    nav / toc / report               ← 基于整个 vault 的编排
    cli                              ← 命令行入口

设计原则：**文本处理函数保持纯函数**（输入字符串、输出字符串），
这样单元测试不需要碰文件系统，也是这个项目最好下手的地方。
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
