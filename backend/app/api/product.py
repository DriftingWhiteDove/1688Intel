import os
from fastapi import APIRouter, HTTPException
from ..models.schemas import ProductAnalyzeRequest, ProductReport
from ..services.scraper import ProductScraper, COOKIE_FILE
from ..services.analyzer import ProductAnalyzer

router = APIRouter()


@router.get("/cookie-status")
async def cookie_status():
    exists = os.path.exists(COOKIE_FILE)
    count = 0
    if exists:
        try:
            import json
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                count = len(json.load(f))
        except Exception:
            pass
    return {"configured": exists, "cookie_count": count}


@router.post("/analyze")
async def analyze_product(req: ProductAnalyzeRequest):
    if not ("1688.com" in req.url and "/offer/" in req.url):
        raise HTTPException(400, "请输入有效的 1688 商品链接（格式：detail.1688.com/offer/xxx.html）")

    scraper = ProductScraper()
    try:
        raw_data = await scraper.full_analysis(req.url)
    except Exception as e:
        raise HTTPException(502, f"抓取商品数据失败: {str(e)}")

    # 未配置 Cookie 时返回引导
    if raw_data.get("_warning") == "no_cookies":
        raise HTTPException(400, {
            "code": "no_cookies",
            "message": "请先导出 1688 登录 Cookie",
            "guide": "打开 Chrome → 登录 1688.com → F12 → Application → Cookies → 全选复制 → 保存到 backend/cookies.json"
        })

    if raw_data.get("_warning") == "cookie_expired":
        raise HTTPException(400, {
            "code": "cookie_expired",
            "message": "Cookie 已过期，请重新导出"
        })

    analyzer = ProductAnalyzer()
    report = analyzer.generate_report(raw_data)

    return report
