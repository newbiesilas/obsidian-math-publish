# ompub

把 Obsidian 里的数学笔记，整理成 GitHub 上**真的能正常渲染**的 Markdown。

![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![deps](https://img.shields.io/badge/dependencies-zero-brightgreen)
![tests](https://img.shields.io/badge/tests-45%20passed-brightgreen)

---

## 目录

- [它解决什么问题](#它解决什么问题)
- [安装](#安装)
- [怎么用](#怎么用)
- [命令与参数](#命令与参数)
- [四个典型场景](#四个典型场景)
- [输出怎么读](#输出怎么读)
- [它不做什么](#它不做什么)
- [项目结构](#项目结构)
- [测试](#测试)
- [许可](#许可)

---

## 它解决什么问题

数学笔记从 Obsidian 搬到 GitHub，有三类问题**每次都会遇到**。这不是假设——下面每一条都是在真实笔记里踩出来的。

### 1. 双链变成死文本

Obsidian 里能点的 `[[02-导数与微分]]`，发到 GitHub 上就是一串方括号，谁也点不动。

```diff
- 参见 [[02-导数与微分]] 里的夹逼定理
+ 参见 [导数与微分](02-导数与微分.md) 里的夹逼定理
```

### 2. 表格里的公式被腰斩（最隐蔽的一个）

GFM 表格解析器**先于** MathJax 工作。它看到 `$|x|<1$` 里的竖线，会当成列分隔符——一行被切成好几列，公式只剩半截，自然渲染不出来：

| 你写的 | GitHub 实际解析到的单元格 |
|--------|--------------------------|
| `\| 绝对值 \| $\|x\|<1$ \|` | `$` ← 到这儿就断了 |
| `\| 绝对值 \| $\lvert x\rvert<1$ \|` | 完整 |

ompub 会把表格公式里的裸竖线成对换成 `\lvert` / `\rvert`。

> 为什么不能简单替换成 `\|`：MathJax 里 `\|` 是**双竖线** ‖（范数），语义不一样。

### 3. 笔记散着，没有入口

十几篇笔记丢进仓库，读者不知道从哪开始、篇与篇什么关系。ompub 会生成：

- 每篇末尾的导航：`> 上一章：[极限与连续](...) ｜ 下一章：[导数与微分](...) ｜ [返回总览](README.md)`
- 一张索引页，列出全部笔记的标题、摘要与标签

### 顺带还能查出你自己看不出来的隐患

| 隐患 | 说明 |
|------|------|
| 失效双链 | `[[不存在的笔记]]` —— 点了只会 404 |
| GitHub 不支持的宏 | `\tag`、`\label`、`\ref`、`\newcommand`、`\require` 等，MathJax 不加载 |
| 公式内侧空格 | `$ x $` 不会被渲染，必须写成 `$x$` |
| 没闭合的 `$` | 全篇 `$` 出现奇数次，多半是漏了一个 |

---

## 安装

需要 Python 3.9 或更高版本，**零第三方依赖**。

```bash
git clone https://github.com/Silas-Peng/obsidian-math-publish.git
cd obsidian-math-publish
pip install -e .           # 装完就能用 ompub 命令
```

不想安装也能直接跑（开发调试时方便）：

```bash
PYTHONPATH=src python -m ompub.cli check ./vault
```

---

## 怎么用

### 第一步：先体检，不动文件

```bash
ompub check ./vault
```

真实输出（这是仓库里 `examples/sample-vault` 的实际结果，它故意埋了问题）：

```
扫描 3 篇笔记：共 4 处问题：公式 3 · 双链 1（2 处可自动修复）

【公式】3 处
  01-极限与连续.md:13  表格内 2 处裸竖线会截断公式 [可自动修复]
        > | 绝对值 | $|x|<1$ 时收敛 | **这里会被截断** |
  02-导数与微分.md:6  \tag 在 GitHub MathJax 无效（无公式编号），请删除
        > $$f'(x_0)=\lim_{h\to 0}\frac{f(x_0+h)-f(x_0)}{h} \tag{1}$$

【双链】1 处
  README.md:8  双链目标不存在：不存在的笔记
        > [[不存在的笔记]]
```

`check` **不修改任何文件**，只告诉你哪里有问题。

### 第二步：整理输出到新目录

```bash
ompub build ./vault ./out
```

```
已输出 3 篇笔记 → ./out
  双链转链接：4 处
  公式修复：2 处
  章节导航：2 篇
  索引页：README.md
    注意：源库已有同名文件，已被覆盖；想保留请用 --index-name 改名
检查：共 1 处问题：双链 1          ← 剩下的需要你自己处理

【双链】1 处
  README.md:8  双链目标不存在：不存在的笔记
```

**原 vault 一个字节都不会改**，结果全在 `./out`。处理完剩下的那一处，就可以发布了。

### 第三步：看看产物

修复后的表格行：

```markdown
| 绝对值 | $\lvert x\rvert<1$ 时收敛 | **这里会被截断** |
```

自动生成的索引页 `./out/README.md`：

```markdown
# 笔记索引

| # | 笔记 | 摘要 | 标签 |
|:--:|------|:----:|:----:|
| 1 | [极限与连续](01-极限与连续.md) | 两个重要极限： | 数学分析 · 极限 |
| 2 | [导数与微分](02-导数与微分.md) | 上式的 \tag{1} 在 GitHub 上不会渲染…… | 数学分析 · 导数 |
```

然后 `git push` 就行。

---

## 命令与参数

```bash
ompub check <vault> [-q]

ompub build <vault> <out> [选项]
```

| 参数 | 作用 |
|------|------|
| `-q, --quiet` | 只输出结论，不列详细清单 |
| `--no-links` | 不转换双链 |
| `--no-latex` | 不修复公式竖线 |
| `--no-nav` | 不生成章节导航 |
| `--no-index` | 不生成索引页 |
| `--index-name README` | 索引页文件名（默认 `README`） |
| `--index-title 笔记索引` | 索引页标题 |
| `--tag 数学` | 给所有笔记补标签，可重复 |
| `--set lang=zh-CN` | 补 frontmatter 缺省字段，可重复 |
| `-V, --version` | 查看版本 |

`--set` 和 `--tag` 只补**笔记里没有的**字段，不会覆盖你已有的内容。

两个容易忽略的点：

- 索引页默认叫 `README.md`。**如果源库里本来就有一篇 `README.md`，它会被生成的索引页覆盖**（命令行会提醒）。想保留原文就换个名字：`--index-name 总览`。
- `--no-index` 只是不生成索引页；源库里的同名文件仍会作为普通笔记被复制过去。

---

## 四个典型场景

### 场景一：把笔记库发到 GitHub

```bash
ompub build ./vault ./docs-site
cd docs-site && git init && git add . && git commit -m "docs: 发布笔记"
git remote add origin <你的仓库地址> && git push -u origin main
```

### 场景二：发布前体检，或接 CI

`check` 的退出码有语义，可以直接用在 CI 里：

```bash
ompub check ./vault
echo $?    # 0 = 没问题或已自动修好；1 = 还有要人工处理的；2 = 参数/路径错误
```

GitHub Actions 示例：

```yaml
- name: 检查笔记
  run: |
    pip install -e .
    ompub check ./vault
```

### 场景三：批量补标签和元信息

```bash
ompub build ./vault ./out --tag 数学笔记 --tag 公开 --set lang=zh-CN --set source=Obsidian
```

输出笔记的 frontmatter 会补上 `tags: [数学笔记, 公开]`、`lang: zh-CN`、`source: Obsidian`。

### 场景四：只修公式，别的都不动

```bash
ompub build ./vault ./out --no-links --no-nav --no-index
```

---

## 输出怎么读

**报告格式**：`文件:行号  问题描述  [可自动修复]`

- 标了 `[可自动修复]` 的，`build` 会直接改好；
- 没标的需要你自己看——比如 `\tag` 该删还是改、失效双链指向的笔记是不是忘了复制。

**退出码**：

| 码 | 含义 |
|:--:|------|
| 0 | 没有问题，或问题都已自动修好 |
| 1 | 还有需要人工处理的问题 |
| 2 | 路径不存在、参数写错 |

**问题类别**：`公式`（latex）、`双链`（wikilink）、`Frontmatter`。

---

## 它不做什么

诚实说明边界，免得你抱错期待：

- **不处理图片附件**：`![[图片.png]]` 只会提醒你确认，不会复制文件
- **不导出 PDF**：需要的话可以自己接 pandoc
- **不猜失效链接**：目标不存在就保留原文并报告，绝不编一个可能 404 的地址
- **不改普通段落里的竖线**：那里的 `|` 可能是集合分隔符或条件概率，改错比不改更糟
- **不懂嵌套 frontmatter**：只支持标量和单层列表（够用了；需要嵌套就换 PyYAML）

---

## 项目结构

```
src/ompub/
├── frontmatter.py   极简 YAML 解析与序列化（零依赖）
├── wikilink.py      双链 → Markdown 链接
├── latex.py         公式竖线修复 + 隐患检查
├── model.py         Note / Issue 数据结构
├── vault.py         扫描目录、判断双链是否存在
├── nav.py           章节导航
├── toc.py           索引页
├── report.py        报告格式化
└── cli.py           命令行入口
```

**分层原则**：`frontmatter` / `wikilink` / `latex` 是纯函数（字符串进、字符串出），不碰文件系统。所以测试里直接喂字符串就能验，不用造临时文件——这也是这个项目最好下手改的地方。

几个刻意的设计取舍：

| 决定 | 为什么 |
|------|--------|
| 零依赖，自己解析 YAML | 换来 `pip install -e .` 后立刻能跑 |
| 奇数个竖线一律不改 | `P(A\|B)` 是条件概率，改成 `\lvert` 语义就错了 |
| `\lvert` 后面留空格 | 否则变成 `\lvertx`，TeX 会当成未定义宏报错 |
| 代码块里的 `[[...]]` 不动 | 那通常是示例代码 |

---

## 测试

```bash
pip install -e ".[dev]"
PYTHONPATH=src pytest
```

45 个用例，覆盖解析、转换、边界情况与端到端流程。其中几个是从真实 bug 来的回归测试：

- `test_fix_表格内裸竖线成对替换` —— 验证 `\lvert ` 的空格不能少
- `test_scan_表格里相邻公式不误报` —— 早期版本把两个公式之间的 ` | ` 当成公式内容
- `test_fix_奇数竖线不动只警告` —— 条件概率不能被改写

---

## 许可

MIT
