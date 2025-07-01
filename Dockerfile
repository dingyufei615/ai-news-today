# 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码到工作目录
COPY . .

# 创建用于存储 RSS 内容的目录，并将其声明为卷
# .gitignore 中已忽略 rss-content，所以 COPY . . 不会复制它
RUN mkdir -p /app/rss-content
VOLUME /app/rss-content

# 声明应用监听的端口
EXPOSE 5001

# 运行应用的命令
CMD ["python", "main.py"]
