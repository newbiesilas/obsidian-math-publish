"""命令行入口。

两个子命令::

    ompub check <vault>              # 只体检，不动文件
    ompub build <vault> <out>        # 整理后输出到新目录

设计取向：**check 与 build 共用同一套检查逻辑**，build 只是多做一步"修"。
这样"修完之后还有没有问题"可以直接用 check 复验。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from . import __version__
from .frontmatter import ensure_tags, normalize
from .latex import fix as latex_fix
from .latex import scan as latex_scan
from .model import Issue, Note
from .nav import build_nav, strip_nav
from .report import format_issues, summarize
from .toc import build_index
from .vault import Vault
from .wikilink import convert as link_convert


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("vault", help="Obsidian vault 目录")
    p.add_argument("-q", "--quiet", action="store_true", help="只输出结论")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ompub",
        description="把 Obsidian 数学笔记整理成 GitHub 上能正常渲染的 Markdown",
    )
    parser.add_argument("-V", "--version", action="version", version=f"ompub {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="检查笔记中的问题（不修改任何文件）")
    _add_common(p_check)

    p_build = sub.add_parser("build", help="整理并输出到目标目录")
    p_build.add_argument("vault", help="Obsidian vault 目录")
    p_build.add_argument("out", help="输出目录（不会改动原 vault）")
    p_build.add_argument("--no-links", action="store_true", help="不转换双链")
    p_build.add_argument("--no-latex", action="store_true", help="不修复公式竖线")
    p_build.add_argument("--no-nav", action="store_true", help="不生成章节导航")
    p_build.add_argument("--no-index", action="store_true", help="不生成索引页")
    p_build.add_argument("--index-name", default="README", help="索引页文件名（默认 README）")
    p_build.add_argument("--index-title", default="笔记索引", help="索引页标题")
    p_build.add_argument("--tag", action="append", default=[], help="追加标签，可重复使用")
    p_build.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="追加 frontmatter 缺省字段，如 --set lang=zh-CN",
    )
    p_build.add_argument("-q", "--quiet", action="store_true", help="只输出结论")

    return parser


def _parse_sets(pairs: Sequence[str]) -> Dict[str, str]:
    """``--set k=v`` 列表 → 字典。忽略没有等号的非法输入。"""
    out: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        if k.strip():
            out[k.strip()] = v.strip()
    return out


def collect(vault: Vault, rel_of) -> List[Issue]:
    """对 vault 全量体检，返回问题列表（不修改）。"""
    issues: List[Issue] = []
    for note in vault.notes:
        rel = rel_of(note)
        issues.extend(latex_scan(note.body, file=rel))
        _, link_issues = link_convert(note.body, vault.exists, file=rel)
        issues.extend(link_issues)
        if not note.frontmatter:
            issues.append(
                Issue(
                    kind="frontmatter",
                    file=rel,
                    line=0,
                    message="缺少 YAML frontmatter，建议加 tags 等元信息",
                    fixable=True,
                )
            )
    return issues


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.vault)
    if not root.is_dir():
        print(f"错误：目录不存在 {root}", file=sys.stderr)
        return 2

    vault = Vault(root)
    issues = collect(vault, vault.rel)

    print(f"扫描 {len(vault.notes)} 篇笔记：{summarize(issues)}")
    if issues and not args.quiet:
        print(format_issues(issues))
    # 有问题但都可修 → 退出码 0；存在需人工处理的问题 → 1，方便接 CI
    blocking = [i for i in issues if not i.fixable]
    return 1 if blocking else 0


def cmd_build(args: argparse.Namespace) -> int:
    root, out_root = Path(args.vault), Path(args.out)
    if not root.is_dir():
        print(f"错误：目录不存在 {root}", file=sys.stderr)
        return 2

    vault = Vault(root)
    defaults = _parse_sets(args.set)
    out_root.mkdir(parents=True, exist_ok=True)

    # 索引页不参与章节序列，否则它会出现在自己的"上一章"里
    order = [n for n in vault.notes if n.name != args.index_name]
    overview = Note(path=out_root / f"{args.index_name}.md", frontmatter={"title": args.index_title})

    fixed_links = fixed_latex = 0
    issues: List[Issue] = []

    for i, note in enumerate(vault.notes):
        rel = vault.rel(note)
        body = note.body

        if not args.no_links:
            body, link_issues = link_convert(body, vault.exists, file=rel)
            issues.extend(link_issues)
            fixed_links += body.count("](")  # 粗略计数：生成的链接数

        if not args.no_latex:
            body, latex_issues = latex_fix(body, file=rel)
            fixed_latex += sum(1 for it in latex_issues if it.fixable)
            issues.extend(latex_issues)

        fm = normalize(note.frontmatter, defaults)
        if args.tag:
            fm = ensure_tags(fm, list(args.tag))

        if not args.no_nav and note.name != args.index_name:
            idx = order.index(note)
            body = strip_nav(body).rstrip() + "\n\n" + build_nav(order, idx, overview)

        target = out_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(Note(path=target, frontmatter=fm, body=body).render(), encoding="utf-8")

    # 源库里可能本来就有一篇同名笔记（示例库就有 README.md），
    # 直接覆盖会让人莫名其妙丢内容，所以记下来、稍后提示。
    index_clash = False
    if not args.no_index:
        index_clash = any(n.name == args.index_name for n in vault.notes)
        index_path = out_root / f"{args.index_name}.md"
        index_path.write_text(
            build_index(order, title=args.index_title), encoding="utf-8"
        )

    print(f"已输出 {len(vault.notes)} 篇笔记 → {out_root}")
    if not args.no_links:
        print(f"  双链转链接：{fixed_links} 处")
    if not args.no_latex:
        print(f"  公式修复：{fixed_latex} 处")
    if not args.no_nav:
        print(f"  章节导航：{len(order)} 篇")
    if not args.no_index:
        print(f"  索引页：{args.index_name}.md")
        if index_clash:
            print("    注意：源库已有同名文件，已被覆盖；想保留请用 --index-name 改名")

    remaining = [i for i in issues if not i.fixable]
    print("检查：" + summarize(remaining if remaining else []))
    if remaining and not args.quiet:
        print(format_issues(remaining))
    return 1 if remaining else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return cmd_check(args)
    if args.command == "build":
        return cmd_build(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
