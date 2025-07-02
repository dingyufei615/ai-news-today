import glob
import os
import re
import time
from datetime import datetime
from pathlib import Path

import feedparser
import markdown2
import requests
from flask import Flask, jsonify, render_template, request, abort
from markupsafe import Markup

# 定义关键字并清洗标题
keyword_pattern = r'(大佬|佬友们|佬友|佬们|大佬们|佬)'

def sanitize_url_for_path(url):
    """将URL消毒，用作目录名。"""
    # 移除协议
    sanitized = re.sub(r'^https?://', '', url)
    # 将无效字符替换为下划线
    sanitized = re.sub(r'[/:?*<>|"\\]', '_', sanitized)
    # 避免太长的文件名
    return sanitized[:100]


def fetch_and_parse_feed(url):
    """
    获取并解析RSS源。
    处理潜在的解析错误。
    """
    print(f"正在从以下地址获取新闻: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        # 使用 requests 获取的内容，而不是让 feedparser 自己去获取，以绕过 Content-Type 检查
        feed = feedparser.parse(response.content)
    except requests.exceptions.RequestException as e:
        print(f"获取源时出错: {e}")
        return None

    if feed.bozo:
        print(f"解析源时出错: {feed.bozo_exception}")
        return None

    return feed


def save_news_item(entry, base_dir=Path("."), feed_dir=None):
    """
    将单个新闻条目保存到文件中，按来源和日期进行组织。
    如果同名文章已存在，则跳过。
    返回一个布尔值，指示是否保存了新文件。
    """
    storage_path = base_dir
    if feed_dir:
        storage_path = base_dir / feed_dir

    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        date_str = published_date.strftime("%Y-%m-%d")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    date_dir = storage_path / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    title = entry.get("title", "无标题")

    cleaned_title = re.sub(keyword_pattern, '', title)

    # 检查当天是否已存在同名文章
    for existing_file in date_dir.glob("*.md"):
        try:
            with open(existing_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                cleaned_first_line = re.sub(keyword_pattern, '', first_line)

                if cleaned_first_line == f"# {cleaned_title}":
                    print(f"新闻条目 '{title}' 在 {date_str} 已存在，跳过。")
                    return False
        except Exception as e:
            print(f"检查文件 {existing_file} 时出错: {e}")

    file_count = len(list(date_dir.glob("*.md")))
    filename = f"news_{file_count + 1}.md"
    filepath = date_dir / filename

    # 尝试获取完整内容，如果失败则回退到摘要
    if 'content' in entry and entry.content:
        news_content = entry.content[0].value
    else:
        news_content = entry.get("summary", "无摘要")

    # 清洗内容中的关键字
    cleaned_news_content = re.sub(keyword_pattern, '', news_content)

    # 使用Markdown格式构建内容
    content = f"# {cleaned_title}\n\n"
    if 'published_date' in locals():
        content += f"**发布日期**: {published_date.strftime('%Y-%m-%d')}\n\n"
    else:
        content += "**发布日期**: N/A\n\n"
    content += "---\n\n"
    content += f"{cleaned_news_content}\n"

    try:
        filepath.write_text(content, encoding="utf-8")
        print(f"已将新闻条目保存至 {filepath}")
        return True
    except IOError as e:
        print(f"保存文件 {filepath} 时出错: {e}")
        return False


# --- Flask App ---

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "rss-content"


def get_article_path(filepath):
    """安全地构建文章路径并防止目录遍历。"""
    # 安全性：防止目录遍历攻击
    # 将请求的相对路径与基础目录结合，并解析为绝对路径
    abs_path = Path(os.path.abspath(os.path.join(BASE_DIR, filepath)))

    # 确保解析后的路径仍然在项目的基础目录内
    if os.path.commonpath([abs_path, BASE_DIR]) != str(BASE_DIR):
        abort(400, "无效的路径。")
    return abs_path


@app.route('/')
def index():
    """提供管理主页。"""
    return render_template('index.html')


@app.route('/article/<path:filepath>')
def view_article(filepath):
    """提供一个公开页面来查看单篇文章。"""
    # 使用与API相同的路径安全检查
    path = get_article_path(filepath)
    if not path.is_file():
        abort(404, "文章未找到。")

    content_md = path.read_text(encoding='utf-8')

    # 从Markdown内容中提取标题
    title_match = re.search(r'^#\s*(.*)', content_md, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "文章"

    # 将Markdown转换为HTML
    html_content = markdown2.markdown(content_md, extras=["fenced-code-blocks", "tables"])

    return render_template('article.html', title=title, content=Markup(html_content))


@app.route('/api/articles', methods=['GET'])
def list_articles():
    """列出指定RSS源下已保存的新闻文章，按日期分组。"""
    feed_url = request.args.get('feed_url')
    if not feed_url:
        return jsonify({})

    feed_dir_name = sanitize_url_for_path(feed_url)
    source_dir = CONTENT_DIR / feed_dir_name

    if not source_dir.is_dir():
        return jsonify({})

    articles_by_date = {}
    # 在指定源目录内搜索日期目录下的 news_*.md 文件
    search_pattern = str(source_dir / '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' / 'news_*.md')
    md_files = glob.glob(search_pattern)

    for md_file_path in md_files:
        md_file = Path(md_file_path)
        date_str = md_file.parent.name  # This is YYYY-MM-DD

        if date_str not in articles_by_date:
            articles_by_date[date_str] = []

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                # 读取第一行作为标题
                first_line = f.readline().strip()
                if first_line.startswith('# '):
                    title = first_line[2:]
                else:
                    title = '无标题'

            relative_path = os.path.relpath(md_file, BASE_DIR)
            articles_by_date[date_str].append({
                'path': relative_path.replace('\\', '/'),  # 确保使用Unix风格的路径分隔符
                'title': title,
            })
        except Exception as e:
            print(f"读取文件 {md_file} 时出错: {e}")

    # 对每个日期内的文章按路径排序，确保一致性
    for date_str in articles_by_date:
        articles_by_date[date_str].sort(key=lambda x: x['path'])

    # 按日期降序排序字典
    sorted_articles = dict(sorted(articles_by_date.items(), reverse=True))

    return jsonify(sorted_articles)


@app.route('/api/article/<path:filepath>', methods=['GET'])
def get_article(filepath):
    """获取单篇文章的内容。"""
    path = get_article_path(filepath)
    if not path.is_file():
        abort(404, "文章未找到。")

    content = path.read_text(encoding='utf-8')
    return jsonify({'raw': content})


@app.route('/api/article/<path:filepath>', methods=['PUT'])
def update_article(filepath):
    """更新文章内容。"""
    path = get_article_path(filepath)
    if not path.is_file():
        abort(404, "文章未找到。")

    data = request.json
    if 'content' not in data:
        abort(400, "请求中缺少 'content'。")

    try:
        path.write_text(data['content'], encoding='utf-8')
        return jsonify({'message': '文章更新成功。'})
    except IOError as e:
        abort(500, f"写入文件时出错: {e}")


@app.route('/api/article/<path:filepath>', methods=['DELETE'])
def delete_article(filepath):
    """删除一篇文章。"""
    path = get_article_path(filepath)
    if not path.is_file():
        abort(404, "文章未找到。")

    try:
        os.remove(path)
        return jsonify({'message': '文章删除成功。'})
    except OSError as e:
        abort(500, f"删除文件时出错: {e}")


@app.route('/api/rss_feeds', methods=['GET'])
def get_rss_feeds():
    """获取配置的RSS源列表。"""
    feeds_str = os.environ.get("RSS_FEEDS", "https://sanhua.himrr.com/daily-news/feed")
    feeds = [url.strip() for url in feeds_str.split(',') if url.strip()]
    return jsonify(feeds)


@app.route('/api/fetch', methods=['POST'])
def fetch_new_articles():
    """从指定的RSS源触发抓取新文章。"""
    data = request.json
    feed_url = data.get('url')
    if not feed_url:
        abort(400, "请求中缺少 'url'。")

    feed_dir_name = sanitize_url_for_path(feed_url)
    feed = fetch_and_parse_feed(feed_url)

    if not feed or not feed.entries:
        return jsonify({"message": "未找到新闻条目或获取源失败。"}), 404

    count = 0
    for entry in feed.entries:
        if save_news_item(entry, base_dir=CONTENT_DIR, feed_dir=feed_dir_name):
            count += 1

    return jsonify({"message": f"成功获取 {count} 个新新闻条目。"})


def build_wecom_markdown_payload(markdown_content, article_path):
    """从文件内容构建企业微信 markdown_v2 消息。"""
    # WeCom的markdown_v2格式要求内容中不能直接包含HTML。
    # 我们需要将文件中的HTML部分转换为markdown_v2支持的格式。

    parts = markdown_content.split('---\n\n', 1)
    header = parts[0]
    body_html = parts[1] if len(parts) > 1 else ''

    # 将HTML粗略地转换为Markdown
    body_md = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', body_html, flags=re.DOTALL)
    body_md = re.sub(r'<img [^>]*src="([^"]+)"[^>]*>', r'![](\1)', body_md)
    body_md = re.sub(r'<(?:b|strong)>(.*?)</(?:b|strong)>', r'**\1**', body_md, flags=re.IGNORECASE | re.DOTALL)
    body_md = re.sub(r'<(?:i|em)>(.*?)</(?:i|em)>', r'*\1*', body_md, flags=re.IGNORECASE | re.DOTALL)
    body_md = re.sub(r'<li>(.*?)</li>', r'- \1\n', body_md, flags=re.IGNORECASE | re.DOTALL)
    body_md = re.sub(r'<br\s*/?>', '\n', body_md, flags=re.IGNORECASE)
    body_md = re.sub(r'</?(?:p|ul|ol|div|blockquote|h[1-6])[^>]*>', '\n', body_md, flags=re.IGNORECASE)
    body_md = re.sub(r'<[^>]+>', '', body_md)
    body_md = re.sub(r'\n{3,}', '\n\n', body_md).strip()

    # 组合最终的markdown
    final_markdown = f"{header}\n\n---\n\n{body_md}"
    encoded_markdown = final_markdown.encode('utf-8')
    markdown_len = len(encoded_markdown)

    app_base_url = os.environ.get("APP_BASE_URL", "").strip('/')

    # 定义企业微信消息的最大长度和我们偏好的预览长度
    WECOM_MAX_LEN = 4096
    PREFERRED_LEN = 1024  # 超过此长度则考虑截断并添加链接，以改善阅读体验

    # 检查是否应该截断并添加“阅读全文”链接
    if app_base_url and markdown_len > PREFERRED_LEN:
        read_more_link = f'\n\n[...点击查看全文]({app_base_url}/article/{article_path})'
        link_len = len(read_more_link.encode('utf-8'))

        # 确定内容部分的最大长度
        # 如果原文已经超过了微信的绝对限制，则截断到绝对限制；否则，截断到我们的偏好长度。
        if markdown_len > WECOM_MAX_LEN:
            max_content_len = PREFERRED_LEN - link_len
        else:
            max_content_len = PREFERRED_LEN - link_len

        if max_content_len < 0:
            max_content_len = 0

        truncated_encoded = encoded_markdown[:max_content_len]
        final_markdown_text = truncated_encoded.decode('utf-8', 'ignore')

        # 避免在截断时破坏 Markdown 结构，回退到最后一个换行符
        # 仅当换行符存在于截断后字符串的后半部分时才这样做，以避免删除过多内容。
        last_newline_pos = final_markdown_text.rfind('\n')
        if last_newline_pos > len(final_markdown_text) * 0.5:
            final_markdown_text = final_markdown_text[:last_newline_pos]

        final_markdown = final_markdown_text.strip() + read_more_link

    # 如果没有配置URL，但内容依然超长，则进行硬截断
    elif markdown_len > WECOM_MAX_LEN:
        suffix = '... (内容过长被截断)'
        suffix_len = len(suffix.encode('utf-8'))
        max_content_len = WECOM_MAX_LEN - suffix_len

        truncated_encoded = encoded_markdown[:max_content_len]
        final_markdown_text = truncated_encoded.decode('utf-8', 'ignore')

        # 同样应用安全截断逻辑
        last_newline_pos = final_markdown_text.rfind('\n')
        if last_newline_pos > len(final_markdown_text) * 0.5:
            final_markdown_text = final_markdown_text[:last_newline_pos]

        final_markdown = final_markdown_text.strip() + suffix

    return {
        "msgtype": "markdown_v2",
        "markdown_v2": {
            "content": final_markdown
        }
    }


def send_to_wecom(payload):
    """发送消息到企业微信机器人。"""
    webhook_key = os.environ.get("WECOM_ROBOT_WEBHOOK")
    if not webhook_key:
        print("错误：环境变量 WECOM_ROBOT_WEBHOOK 未设置。")
        return False, "环境变量 WECOM_ROBOT_WEBHOOK 未设置。"
    webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + webhook_key

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("errcode") == 0:
                print("成功发送到企业微信。")
                return True, "发送成功。"
            else:
                errmsg = result.get('errmsg', '未知错误')
                print(f"发送到企业微信失败: {errmsg}")
                return False, f"发送到企业微信失败: {errmsg}"
        else:
            print(f"请求企业微信API出错，状态码: {response.status_code}, 内容: {response.text}")
            return False, f"请求企业微信API出错: HTTP {response.status_code}"

    except requests.exceptions.RequestException as e:
        print(f"请求企业微信时出错: {e}")
        return False, f"请求企业微信时出错: {e}"


@app.route('/api/push_to_wecom', methods=['POST'])
def push_to_wecom():
    """将指定日期和源的新闻逐条推送到企业微信。"""
    data = request.json
    push_date_str = data.get('date')
    feed_url = data.get('feed_url')

    if not push_date_str or not feed_url:
        abort(400, "请求中缺少 'date' 或 'feed_url'。")

    feed_dir_name = sanitize_url_for_path(feed_url)
    search_pattern = str(CONTENT_DIR / feed_dir_name / push_date_str / 'news_*.md')
    md_files = sorted(glob.glob(search_pattern))

    if not md_files:
        return jsonify({"message": f"日期 {push_date_str} 没有来自该源的可推送新闻。"}), 404

    success_count = 0
    failure_count = 0
    last_error = ""

    for md_file in md_files:
        try:
            content_raw = Path(md_file).read_text(encoding='utf-8')
            relative_path = os.path.relpath(md_file, BASE_DIR).replace('\\', '/')
            payload = build_wecom_markdown_payload(content_raw, relative_path)

            success, message = send_to_wecom(payload)
            if success:
                success_count += 1
            else:
                failure_count += 1
                last_error = message
            # 增加一个3秒的延时，避免触发企业微信的频率限制（20条/分钟）
            time.sleep(3)

        except Exception as e:
            failure_count += 1
            last_error = str(e)
            print(f"处理或发送文件 {md_file} 时出错: {e}")

    if failure_count == 0:
        return jsonify({"message": f"成功推送 {success_count} 条新闻。"})
    else:
        error_message = f"推送完成，{success_count} 条成功，{failure_count} 条失败。"
        if last_error:
            error_message += f" 最后一条错误信息: {last_error}"
        return jsonify({'message': error_message}), 500


if __name__ == "__main__":
    # 如果 'templates' 目录不存在，则创建它
    (BASE_DIR / 'templates').mkdir(exist_ok=True)
    app.run(host='0.0.0.0', port=5001)
