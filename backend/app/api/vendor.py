from fastapi import APIRouter, HTTPException
from ..models.schemas import VendorCheckRequest, VendorReport
from ..services.scraper import VendorScraper
from ..services.analyzer import VendorAnalyzer

router = APIRouter()


@router.post("/check", response_model=VendorReport)
async def check_vendor(req: VendorCheckRequest):
    if not ("1688.com" in req.url):
        raise HTTPException(400, "请输入有效的 1688 店铺链接")

    scraper = VendorScraper()
    try:
        raw_data = await scraper.scrape_vendor(req.url)
    except Exception as e:
        raise HTTPException(502, f"抓取店铺数据失败: {str(e)}")

    analyzer = VendorAnalyzer()
    report = analyzer.generate_report(raw_data)

    return report
