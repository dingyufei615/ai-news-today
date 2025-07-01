# RSS 内容管理和推送系统

这是一个基于 Flask 的 Web 应用，用于从 RSS 源获取新闻文章，进行管理，并将其推送到企业微信（WeCom）。

## 功能特性

- 从可配置的 RSS 源列表获取文章。
- 将文章以 Markdown 格式保存在本地，按来源和日期进行组织。
- 提供一个简单的 Web 界面来查看、编辑和删除已保存的文章。
- 将选定的文章以图文卡片的形式推送到企业微信机器人。

## 技术栈

- 后端: Python, Flask
- 前端: HTML, CSS, JavaScript (无框架)
- 数据持久化: 文件系统 (Markdown 文件)

## 安装与配置

### 前提条件

- Python 3.6+
- pip

### 本地安装

1.  **克隆仓库**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **配置环境变量**

    为了运行应用，需要设置以下环境变量。建议创建一个 `.env` 文件。

    - `RSS_FEEDS`: (必需) 以逗号分隔的 RSS 源 URL 列表。
      - 示例: `RSS_FEEDS=https://sanhua.himrr.com/daily-news/feed,https://www.ruanyifeng.com/blog/atom.xml`
    - `WECOM_ROBOT_WEBHOOK`: (必需) 企业微信机器人的 Webhook Key（仅 Key 部分，不是完整 URL）。
      - 示例: `WECOM_ROBOT_WEBHOOK=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

    **`.env` 文件示例:**
    ```
    RSS_FEEDS=https://sanhua.himrr.com/daily-news/feed
    WECOM_ROBOT_WEBHOOK=your-wecom-webhook-key
    ```
    应用运行时会自动从项目根目录的 `.env` 文件加载这些变量。

## 运行应用

1.  **启动 Web 服务**
    ```bash
    python main.py
    ```

2.  **访问应用**
    在浏览器中打开 `http://127.0.0.1:5001`。

## 使用 Docker 运行

项目中已包含 `Dockerfile`，可以方便地进行容器化部署。

1.  **构建 Docker 镜像**
    ```bash
    docker build -t rss-pusher .
    ```

2.  **运行 Docker 容器**

    -   **使用 `--env-file` (推荐)**:
        首先，确保您的配置在 `.env` 文件中。
        ```bash
        docker run -d -p 5001:5001 \
          -v "$(pwd)/rss-content":/app/rss-content \
          --env-file .env \
          --name rss-pusher-container \
          rss-pusher
        ```

    -   **直接传递环境变量**:
        ```bash
        docker run -d -p 5001:5001 \
          -v "$(pwd)/rss-content":/app/rss-content \
          -e RSS_FEEDS="https://sanhua.himrr.com/daily-news/feed" \
          -e WECOM_ROBOT_WEBHOOK="your-wecom-webhook-key" \
          --name rss-pusher-container \
          rss-pusher
        ```

    - **说明**:
        - `-d`: 后台运行容器。
        - `-p 5001:5001`: 将主机的 5001 端口映射到容器的 5001 端口。
        - `-v "$(pwd)/rss-content":/app/rss-content`: 将本地的 `rss-content` 目录挂载到容器中，以持久化保存新闻文章。
        - `--env-file .env`: 从 `.env` 文件加载环境变量。
        - `--name rss-pusher-container`: 为容器命名。

## 目录结构

```
.
├── main.py           # Flask 应用主文件
├── requirements.txt  # Python 依赖
├── templates/
│   └── index.html    # 前端页面
├── rss-content/      # (运行时生成) 保存 RSS 内容的目录
├── Dockerfile        # Docker 配置文件
└── README.md         # 本文档
```
