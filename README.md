# 朝夕 News · ZhaoXiNews

基于 Vue 3、FastAPI 和 MySQL 的新闻阅读应用，支持收藏、浏览历史和带来源的 AI 问答。

- 站内新闻问答支持主题和日期筛选，流式返回时间线及站内原文链接。
- 收藏总结默认覆盖最近 10 篇，可按主题和收藏日期筛选。
- 个人资料库支持 UTF-8 TXT 和有文字层的 PDF，按登录账号隔离。问答引用文件名和页码或片段编号。
- 智能模式可以组合新闻、收藏和资料检索。Agent 由 LangChain 编排，Chroma 持久化资料索引。

## 目录

| 路径 | 用途 |
| --- | --- |
| `ZhaoXiNews-backend` | FastAPI、数据库迁移和后端依赖 |
| `ZhaoXiNews-fronted` | Vue 3 / Vite 前端 |
| `ai-agent` | FastAPI 使用的 Agent 与资料检索 Python 包 |
| `examples` | 可选的虚构演示新闻和可上传的 TXT |

## 本地启动

环境使用 Python 3.13、Node.js 24 和 MySQL 8.x。Redis 用于新闻缓存。启用 AI 问答和资料入库需要自己的 DashScope API Key。

### 1. 初始化 MySQL

从仓库根目录进入 MySQL 客户端，连接本机 MySQL 后依次执行下面的命令。应用连接账户需要对 `zhaoxi_news` 具有读写权限。

```sql
CREATE DATABASE IF NOT EXISTS zhaoxi_news CHARACTER SET utf8mb4;
USE zhaoxi_news;
SOURCE ZhaoXiNews-backend/migrations/000_initial_schema.sql;
SOURCE ZhaoXiNews-backend/migrations/001_ai_documents.sql;
```

需要演示数据时，在同一客户端执行 `SOURCE examples/demo_news.sql;`。这会添加两篇标注为虚构的新能源报道。已有相同结构的数据库可直接执行资料表迁移。

### 2. 启动后端

在 PowerShell 中运行下面的命令。依赖安装需从后端目录执行，以便找到旁边的 `ai-agent` 包。

```powershell
cd ZhaoXiNews-backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑后端 `.env`，填写 `DATABASE_URL` 中的数据库账户和密码，以及 `DASHSCOPE_API_KEY`。连接串里的用户名和密码包含特殊字符时使用 URL 百分号编码。`REDIS_URL` 默认连接本机 Redis。保存后启动后端。

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. 启动前端

在另一个终端，从仓库根目录运行以下命令。

```powershell
cd ZhaoXiNews-fronted
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

前端默认连接 `http://127.0.0.1:8000`。如果更改地址或端口，在前端 `.env` 设置 `VITE_API_BASE_URL`，并在后端 `.env` 的 `CORS_ORIGINS` 中配置前端来源。

## 试用 AI 问答

1. 打开 [本机首页](http://127.0.0.1:5173/)，注册并登录。
2. 导入演示新闻后，在「新能源演示」分类里收藏一篇报道。
3. 在 [AI 问答](http://127.0.0.1:5173/aichat) 的「管理资料」中上传 [新能源资料库联调样例.txt](examples/新能源资料库联调样例.txt)。
4. 文件可检索后，在「智能选择」中提问「总结我最近的收藏，再引用上传的新能源测试报告说明样车甲的电池容量」。检查参考来源里的新闻链接和文件片段编号。

资料索引默认保存在后端 `data/ai_chroma`，也可配置 `AI_CHROMA_DIR`。运行本地 Chroma 时使用单个后端进程。上传的文件会切分后交给 DashScope 生成向量，回答时会向 DashScope 提供命中的片段。

真实 `.env`、数据库记录和资料索引仅保存在自己的运行环境中。仓库内的 `.env.example` 可作为配置模板。
