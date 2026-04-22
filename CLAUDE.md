# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

WebCosmos 是一个以**静态 HTML** 为主的小工具集合仓库。每个工具是独立 HTML 文件，内嵌 CSS 和 JS，浏览器直接打开即可使用，无需构建流程。

## 仓库结构

- 根目录放 HTML 工具文件（如 `sub2api_to_cpa.html`）
- `Python/` 放 Python 脚本（当前有一个 API 压测脚本）
- `Python/.venv/` 是 Python 虚拟环境，已加入 `.gitignore`

## 开发约定

- **HTML 工具**：单文件架构，所有 CSS/JS 内联，外部依赖用 CDN（如 JSZip）。每个工具自包含，不拆分文件
- **Python 脚本**：放在 `Python/` 目录下，依赖通过 `.venv` 管理
- 新增工具后在 `readme.md` 的目录表中添加条目

## 常用命令

无构建/测试/lint 流程。HTML 文件直接用浏览器打开。

Python 压测脚本运行方式：
```bash
cd Python
# 激活虚拟环境后
python codex_stress_test.py
# 脚本配置（base_url、api_key、model 等）直接硬编码在 __main__ 块中
```

## 技术栈

- HTML 工具：原生 HTML5 + CSS3 + ES6+ JS，CDN 引入 JSZip v3.10.1
- Python 脚本：requests、openai SDK，用 ThreadPoolExecutor 做并发压测
