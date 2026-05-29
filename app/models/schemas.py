from pydantic import BaseModel
from typing import Optional


# ── 请求 ──

class ProductAnalyzeRequest(BaseModel):
    url: str

class VendorCheckRequest(BaseModel):
    url: str


# ── 供应商信息 ──

class SupplierInfo(BaseModel):
    shop_name: str = ""
    star_level: int = 0
    trust_pass: bool = False
    gold_medal: bool = False
    years_in_business: int = 0
    shop_type: str = ""
    location: str = ""

class ShippingInfo(BaseModel):
    has_freight: bool = False
    freight_template_name: str = ""
    volume_price_tiers: list = []

class EvaluationSummary(BaseModel):
    total_reviews: int = 0
    good_count: int = 0
    middle_count: int = 0
    bad_count: int = 0
    has_image_count: int = 0
    has_followup_count: int = 0


# ── 竞争与市场数据 ──

class CompetitionInfo(BaseModel):
    total_suppliers: int = 0
    price_range_min: float = 0
    price_range_max: float = 0
    search_keywords: str = ""

class TaobaoMarketData(BaseModel):
    average_price: float = 0
    min_price: float = 0
    max_price: float = 0
    total_listings: int = 0
    total_sales_count: int = 0
    search_url: str = ""


# ── 响应 ──

class ProfitEstimate(BaseModel):
    purchase_price: float
    reference_selling_price: float
    estimated_shipping_cost: float = 0
    taobao_fees: float = 0
    estimated_profit: float
    profit_margin: float
    net_profit: float = 0
    net_margin: float = 0
    notes: str

class RiskFlag(BaseModel):
    level: str  # low / medium / high
    item: str
    detail: str

class ProductReport(BaseModel):
    url: str
    title: str
    price_min: float
    price_max: float
    monthly_sales: Optional[str] = None
    review_count: Optional[int] = None
    avg_rating: Optional[float] = None
    ai_score: float
    ai_summary: str
    actionable_advice: str = ""
    profit_estimate: Optional[ProfitEstimate] = None
    risk_flags: list[RiskFlag] = []
    supplier_info: Optional[SupplierInfo] = None
    shipping_info: Optional[ShippingInfo] = None
    evaluation_summary: Optional[EvaluationSummary] = None
    competition: Optional[CompetitionInfo] = None
    taobao_market: Optional[TaobaoMarketData] = None

class CompanyInfo(BaseModel):
    company_name: str
    reg_capital: Optional[str] = None
    establish_date: Optional[str] = None
    legal_person: Optional[str] = None
    credit_code: Optional[str] = None

class VendorReport(BaseModel):
    shop_name: str
    company_info: Optional[CompanyInfo] = None
    trust_score: float
    fake_review_warning: str
    ai_assessment: str
