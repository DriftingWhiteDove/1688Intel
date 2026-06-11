# 1688Intel — 1688 电商选品盈利分析工具

FastAPI + DeepSeek + Playwright 商品/供应商数据分析系统。

## 快速命令

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000   # 启动服务
pip install -r requirements.txt                        # 安装依赖
```

## 项目结构

```
1688Intel/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口 + 生命周期
│   │   ├── api/
│   │   │   ├── product.py   # 商品分析路由
│   │   │   └── vendor.py    # 供应商评估路由
│   │   ├── core/
│   │   │   ├── config.py    # 环境变量配置 (Pydantic Settings)
│   │   │   └── database.py  # SQLAlchemy + aiosqlite 异步引擎
│   │   ├── models/
│   │   │   └── schemas.py   # Pydantic 数据模型
│   │   ├── services/
│   │   │   ├── scraper.py   # Playwright + httpx 数据抓取 (Cookie注入)
│   │   │   ├── analyzer.py  # DeepSeek AI 分析逻辑
│   │   │   └── reporter.py  # HTML 报告生成
│   │   ├── static/          # 静态资源
│   │   └── templates/       # Jinja2 页面模板
│   ├── .env                 # API Key 等敏感配置 (不提交)
│   ├── cookies.json         # 1688 Cookie (不提交)
│   ├── data/                # SQLite 数据库文件
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   └── plans/               # 设计文档
└── frontend/                # (预留)
```

## 架构规则

### 数据流
```
用户输入商品链接 → API 路由 → Scraper (Playwright 抓取 1688) → Analyzer (DeepSeek 分析) → 结构化报告
```

### 关键约束
- **Cookie 认证**: 1688 数据抓取依赖浏览器 Cookie 注入 (cookies.json)，启动前需通过 start_chrome.ps1 或 start_edge.ps1 登录导出
- **AI 分析**: DeepSeek API (OpenAI 兼容接口)，通过 `utils/api.py` 统一调用，所有 AI 调用需做超时和降级处理
- **数据库**: SQLAlchemy + aiosqlite，异步 session，数据库文件在 data/ 目录
- **定时任务**: APScheduler 管理周期抓取任务

## 代码规范

### Python
- `async/await` 异步风格
- Pydantic v2 数据校验
- Loguru 日志，统一 logger
- 类型注解全覆盖
- 抓取逻辑与业务逻辑分离 (services/scraper.py vs analyzer.py)

### API 设计
- RESTful 风格，`/api/v1/` 前缀
- 统一响应格式 `{"code": 0, "data": ..., "message": "ok"}`
- 错误处理: HTTPException + 全局异常处理器

### 边界情况
- Cookie 过期 → 返回明确提示引导重新导出
- API Key 未配置 → 启动时检测并报错
- 商品链接无效 → 快速失败 + 友好提示
- 网络超时 → 重试 2 次后降级返回缓存数据
- 数据库初始化 → 自动建表

## 设计风格
- 后端项目, 前端仅 Jinja2 模板 + 原生 HTML/CSS
- 报告风格: 信息密度高, 结构化布局, 适合 PC 端阅读
- 配色延用 ShopDataViz 的 Ant Design 蓝色系 `#4096ff`
