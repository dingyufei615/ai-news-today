# RSS Pusher

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.x-black.svg)](https://flask.palletsprojects.com/)

一个轻量级的 Web 应用，用于从 RSS 源获取、管理内容，并将其推送到企业微信（WeCom）。

## ✨ 功能特性

-   从多个可配置的 RSS 源获取文章。
-   将文章以 Markdown 格式保存在本地，按来源和日期进行组织。
-   提供简洁的 Web 界面来查看、编辑、删除已保存的文章。
-   支持将指定日期的文章批量推送到企业微信机器人。
-   支持 Docker 快速部署。

## 🛠️ 技术栈

-   **后端**: Python, Flask
-   **前端**: HTML, CSS, JavaScript (无框架)
-   **数据持久化**: 文件系统 (Markdown 文件)

## 🚀 快速开始

### 1. 先决条件

-   Python 3.9+
-   pip

### 2. 克隆与安装

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
pip install -r requirements.txt
```
*请将上面的 URL 替换为您的仓库地址。*

### 3. 环境配置

在项目根目录创建一个 `.env` 文件，并配置以下变量：

```dotenv
# [必需] RSS源URL，多个请用逗号分隔
RSS_FEEDS=https://sanhua.himrr.com/daily-news/feed,https://www.ruanyifeng.com/blog/atom.xml

# [必需] 企业微信机器人的 Webhook Key (仅key部分)
WECOM_ROBOT_WEBHOOK=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# [可选] 应用的公开访问URL，用于在企微消息中生成“阅读全文”链接
APP_BASE_URL=http://your-domain.com:5001
```

### 4. 运行应用

```bash
python main.py
```
启动后，请在浏览器中访问 `http://127.0.0.1:5001`。

## 🐳 使用 Docker 部署

项目已包含 `Dockerfile`，可以方便地进行容器化部署。

### 1. 构建镜像

```bash
docker build -t rss-pusher .
```

### 2. 运行容器

推荐使用 `.env` 文件来管理配置。

```bash
docker run -d -p 5001:5001 \
  -v "$(pwd)/rss-content":/app/rss-content \
  --env-file .env \
  --name rss-pusher-container \
  rss-pusher
```
**参数说明:**
-   `-d`: 后台运行容器。
-   `-p 5001:5001`: 将主机的 5001 端口映射到容器的 5001 端口。
-   `-v "$(pwd)/rss-content":/app/rss-content`: 将本地的 `rss-content` 目录挂载到容器中，以持久化保存文章。
-   `--env-file .env`: 从 `.env` 文件加载环境变量。

## 📁 目录结构

```
.
├── main.py           # Flask 应用主文件
├── requirements.txt  # Python 依赖
├── static/           # 静态资源 (CSS)
├── templates/        # HTML 模板
├── rss-content/      # (运行时生成) 保存 RSS 内容
├── Dockerfile        # Docker 配置文件
└── README.md         # 本文档
```
