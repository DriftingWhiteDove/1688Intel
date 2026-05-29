# 1688Intel — 1688 电商选品盈利分析工具

基于 FastAPI + DeepSeek 的商品/供应商数据分析系统，帮助中小卖家快速判断"卖这个能不能赚钱"。

## 功能

- **商品分析**：输入 1688 商品链接，AI 自动分析利润空间、市场竞争、供应商可靠性、市场需求
- **供应商信用评估**：分析供应商资质、经营年限、诚信通状态、工商信息
- **AI 智能评分**：综合多维度数据给出 0-100 推荐分，附带优劣势分析和风险提示
- **利润估算**：基于 1688 进价与淘宝市场价格对比，自动计算预估利润与利润率
- **HTML 报告导出**：分析结果可导出为结构化 HTML 报告

## 技术栈

| 层 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| AI 引擎 | DeepSeek API (OpenAI 兼容接口) |
| 数据抓取 | Playwright + httpx + Cookie 注入 |
| 数据存储 | SQLAlchemy + aiosqlite |
| 定时任务 | APScheduler |
| 前端 | Jinja2 + HTML |
| 工具 | Loguru, Pydantic |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API 密钥
# 复制 .env.example 为 .env，填入 DeepSeek API Key
cp .env.example .env

# 3. 配置 1688 Cookie（可选，用于抓取数据）
# 导出 1688.com 登录 Cookie 保存到 cookies.json
# 详见 export_cookies_guide.md

# 4. 启动服务
python -m uvicorn app.main:app --reload --port 8000

# 或使用 start.bat（Windows）
start.bat

# 5. 打开浏览器访问
# http://localhost:8000
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/product/analyze` | POST | 分析 1688 商品链接 |
| `/api/v1/vendor/check` | POST | 评估供应商信用 |
| `/api/v1/product/cookie-status` | GET | 检查 Cookie 配置状态 |
| `/api/health` | GET | 健康检查 |

## 项目结构

```
backend/
├── app/
│   ├── api/          # 路由层
│   ├── core/         # 配置与数据库
│   ├── models/       # 数据模型 & Schema
│   ├── services/     # 业务逻辑（爬虫、分析、报告）
│   ├── static/       # 静态资源
│   └── templates/    # 前端模板
├── data/             # SQLite 数据库
├── cookies.json      # 1688 登录 Cookie（需自行配置）
└── requirements.txt
```
