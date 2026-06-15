# 1688Intel — 1688 电商选品盈利分析工具

基于 FastAPI + DeepSeek 的商品/供应商数据分析系统，帮助中小卖家快速判断"卖这个能不能赚钱"。

## 快速开始

项目代码在 `backend/` 目录下：

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key
uvicorn app.main:app --reload --port 8000
```

详细说明见 [backend/README.md](backend/README.md)。
