---
title: 示例笔记库
tags:
  - 示例
---

# 示例笔记库

用来演示 ompub 的效果：

- [[01-极限与连续]] —— 表格里有裸竖线，build 会自动修
- [[02-导数与微分]] —— 含 `\tag` 与代码块里的假双链
- [[不存在的笔记]] —— 演示失效双链如何处理

跑一遍试试：

```bash
ompub check examples/sample-vault
ompub build examples/sample-vault /tmp/out
```
