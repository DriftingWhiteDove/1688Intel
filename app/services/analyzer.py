"""
AI 分析引擎

使用 DeepSeek API 对抓取的原始数据进行智能分析。
"""

import json
from typing import Optional
from openai import OpenAI

from ..core.config import settings
from ..models.schemas import (
    ProductReport, ProfitEstimate, RiskFlag,
    SupplierInfo, ShippingInfo, EvaluationSummary,
    CompetitionInfo, TaobaoMarketData,
    VendorReport, CompanyInfo,
)


def _get_client() -> Optional[OpenAI]:
    if not settings.deepseek_api_key:
        return None
    return OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)


SYSTEM_PROMPT_PRODUCT = """你是一个专业的 1688 选品盈利分析师。根据提供的完整数据（商品信息、供应商信息、1688竞争数据、淘宝市场数据），综合判断"卖这个能不能赚钱"。

输出 JSON 格式：
{
  "ai_score": "整数 0-100，70+强烈推荐，40-69可考虑，<40不推荐",
  "ai_summary": "一句话总结该品是否值得做以及核心原因",
  "pros": ["优点1", "优点2"],
  "cons": ["缺点1", "缺点2"],
  "actionable_advice": "具体可操作的下一步行动建议",
  "risk_flags": [
    {"level": "low/medium/high", "item": "风险名称", "detail": "说明"}
  ],
  "profit_suggestion": {
    "purchase_price": 1688进货价（数字，参考price_min）,
    "reference_selling_price": 建议零售价（数字，参考淘宝市场均价）,
    "estimated_shipping_cost": 估算运费（数字）,
    "estimated_profit": 预估单品利润（数字）,
    "profit_margin": "利润率百分比数字（如 25.5）",
    "note": "利润分析详细说明，包括与淘宝同类商品的价格对比、利润空间判断"
  }
}

关键分析维度：
1. 利润空间：1688进价 vs 淘宝同款售价，扣除运费和平台费用后是否还有合理利润
2. 市场竞争：1688上同款供应商数量（竞争烈度），淘宝上在售数量
3. 供应商可靠性：星级、诚信通、金牌卖家、经营年限、所在地
4. 市场需求：月销量、评价数量、淘宝搜索结果的销量

规则：
- 所有价格字段必须是数字，不能是字符串
- 只输出 JSON，不要多余的说明"""

SYSTEM_PROMPT_VENDOR = """你是一个 1688 供应商信用分析师。根据提供的供应商数据，输出 JSON 格式的分析报告：
{
  "trust_score": 0-100的整数,
  "fake_review_warning": "是否存在刷单嫌疑及依据",
  "ai_assessment": "综合评估建议"
}
只输出 JSON，不要多余的说明。"""


# ══════════════════════════════════════════
#  商品分析
# ══════════════════════════════════════════

class ProductAnalyzer:

    def generate_report(self, raw: dict) -> ProductReport:
        ai = self._ai_analysis(raw)

        supplier = None
        si = raw.get("supplier_info")
        if si:
            supplier = SupplierInfo(
                shop_name=si.get("shop_name", ""),
                star_level=si.get("star_level", 0),
                trust_pass=si.get("trust_pass", False),
                gold_medal=si.get("gold_medal", False),
                years_in_business=si.get("years_in_business", 0),
                shop_type=si.get("shop_type", ""),
                location=si.get("location", ""),
            )

        shipping = None
        ssi = raw.get("shipping_info")
        if ssi:
            shipping = ShippingInfo(
                has_freight=ssi.get("has_freight", False),
                freight_template_name=ssi.get("freight_template_name", ""),
                volume_price_tiers=ssi.get("volume_price_tiers", []),
            )

        ev = None
        es = raw.get("evaluation_summary")
        if es:
            ev = EvaluationSummary(
                total_reviews=es.get("total_reviews", 0),
                good_count=es.get("good_count", 0),
                middle_count=es.get("middle_count", 0),
                bad_count=es.get("bad_count", 0),
                has_image_count=es.get("has_image_count", 0),
                has_followup_count=es.get("has_followup_count", 0),
            )

        comp = None
        ci = raw.get("competition")
        if ci:
            comp = CompetitionInfo(
                total_suppliers=ci.get("total_suppliers", 0),
                price_range_min=ci.get("price_range_min", 0),
                price_range_max=ci.get("price_range_max", 0),
                search_keywords=ci.get("search_keywords", ""),
            )

        tb = None
        td = raw.get("taobao_market")
        if td and td.get("average_price", 0) > 0:
            tb = TaobaoMarketData(
                average_price=td.get("average_price", 0),
                min_price=td.get("min_price", 0),
                max_price=td.get("max_price", 0),
                total_listings=td.get("total_listings", 0),
                total_sales_count=td.get("total_sales_count", 0),
                search_url=td.get("search_url", ""),
            )

        return ProductReport(
            url=raw.get("url", ""),
            title=raw.get("title", ""),
            price_min=raw.get("price_min", 0),
            price_max=raw.get("price_max", 0),
            monthly_sales=raw.get("monthly_sales"),
            review_count=raw.get("review_count", 0),
            avg_rating=raw.get("avg_rating"),
            ai_score=ai.get("ai_score", 50),
            ai_summary=ai.get("ai_summary", "暂无分析"),
            actionable_advice=ai.get("actionable_advice", ""),
            profit_estimate=self._build_profit(ai.get("profit_suggestion"), raw),
            risk_flags=[RiskFlag(**f) for f in ai.get("risk_flags", [])],
            supplier_info=supplier,
            shipping_info=shipping,
            evaluation_summary=ev,
            competition=comp,
            taobao_market=tb,
        )

    def _ai_analysis(self, raw: dict) -> dict:
        client = _get_client()
        if not client:
            return self._fallback(raw)

        try:
            resp = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_PRODUCT},
                    {"role": "user", "content": json.dumps(raw, ensure_ascii=False)},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(text)
        except Exception as e:
            return self._fallback(raw, str(e))

    def _fallback(self, raw: dict, error: str = "") -> dict:
        return {
            "ai_score": 50,
            "ai_summary": f"AI 分析暂不可用{'(' + error + ')' if error else ''}",
            "risk_flags": [],
            "profit_suggestion": None,
            "actionable_advice": "",
        }

    def _build_profit(self, suggestion: Optional[dict], raw: dict) -> Optional[ProfitEstimate]:
        if not suggestion:
            return None

        def to_float(v) -> float:
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        purchase = to_float(suggestion.get("purchase_price", 0))
        selling = to_float(suggestion.get("reference_selling_price", 0))
        shipping = to_float(suggestion.get("estimated_shipping_cost", 0))

        # 平台费用估算：~5% 平台佣金 + ~2% 营销成本
        platform_fees = selling * 0.07
        total_cost = purchase + shipping + platform_fees
        gross_profit = selling - purchase
        net_profit = selling - total_cost
        gross_margin = (gross_profit / selling * 100) if selling > 0 else 0
        net_margin = (net_profit / selling * 100) if selling > 0 else 0

        return ProfitEstimate(
            purchase_price=purchase,
            reference_selling_price=selling,
            estimated_shipping_cost=round(shipping, 2),
            taobao_fees=round(platform_fees, 2),
            estimated_profit=round(gross_profit, 2),
            profit_margin=round(gross_margin, 1),
            net_profit=round(net_profit, 2),
            net_margin=round(net_margin, 1),
            notes=str(suggestion.get("note", "")),
        )


# ══════════════════════════════════════════
#  供应商分析
# ══════════════════════════════════════════

class VendorAnalyzer:

    def generate_report(self, raw: dict) -> VendorReport:
        ai = self._ai_analysis(raw)
        company = raw.get("company_info")

        return VendorReport(
            shop_name=raw.get("shop_name", ""),
            company_info=CompanyInfo(**company) if company else None,
            trust_score=ai.get("trust_score", 50),
            fake_review_warning=ai.get("fake_review_warning", "暂无数据"),
            ai_assessment=ai.get("ai_assessment", "暂无分析"),
        )

    def _ai_analysis(self, raw: dict) -> dict:
        client = _get_client()
        if not client:
            return self._fallback()

        try:
            resp = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_VENDOR},
                    {"role": "user", "content": json.dumps(raw, ensure_ascii=False)},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(text)
        except Exception:
            return self._fallback()

    def _fallback(self) -> dict:
        return {
            "trust_score": 50,
            "fake_review_warning": "AI 分析暂不可用",
            "ai_assessment": "无法获取 AI 评估，请检查 API 配置",
        }
