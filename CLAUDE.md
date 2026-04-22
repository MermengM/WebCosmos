# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

WebCosmos 是一个以**静态 HTML** 为主的小工具集合仓库。每个工具是独立 HTML 文件，内嵌 CSS 和 JS，浏览器直接打开即可使用，无需构建流程。通过 GitHub Pages 部署。

## 仓库结构

- `index.html` — 主页，工具导航入口，控制各工具的显示/隐藏
- 根目录放 HTML 工具文件（如 `sub2api_to_cpa.html`、`text_compare.html`）
- `Python/` 放 Python 脚本
- `Python/.venv/` 是 Python 虚拟环境，已加入 `.gitignore`

## 开发约定

- **HTML 工具**：单文件架构，所有 CSS/JS 内联，外部依赖用 CDN。每个工具自包含，不拆分文件
- **新增工具流程**：
  1. 创建独立 HTML 文件
  2. 在 `index.html` 的 `tools` 数组中添加条目（设置 `name`、`description`、`file`、`visible`）
  3. 在 `readme.md` 目录表中添加条目
- **显示控制**：修改 `index.html` 中 `tools` 数组里对应工具的 `visible` 字段（`true`/`false`）

## 常用命令

无构建/测试/lint 流程。HTML 文件直接用浏览器打开。


## 技术栈
- HTML 工具：原生 HTML5 + CSS3 + ES6+ JS，CDN 引入 JSZip v3.10.1
