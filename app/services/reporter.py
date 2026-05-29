"""
报告生成器

将分析结果输出为 HTML/PDF 报告，方便导出和分享。
"""

from datetime import datetime
from typing import Optional
from ..models.schemas import ProductReport, VendorReport

REPORT_HTML = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8">
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #1a1a2e; font-size: 20px; }}
.score {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-weight: bold; }}
.score-high {{ background: #d4edda; color: #155724; }}
.score-mid {{ background: #fff3cd; color: #856404; }}
.score-low {{ background: #f8d7da; color: #721c24; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
.risk {{ padding: 4px 8px; border-radius: 4px; margin: 4px 0; }}
.risk-high {{ background: #f8d7da; }}
.risk-medium {{ background: #fff3cd; }}
.risk-low {{ background: #d1ecf1; }}
</style></head><body>
<h1>{title}</h1>
<p>生成时间：{time}</p>
{body}
</body></html>"""


def gen_product_report_html(report: ProductReport) -> str:
    score_class = "score-high" if report.ai_score >= 70 else ("score-mid" if report.ai_score >= 40 else "score-low")

    body = f"""
    <h2>AI 推荐评分：<span class="score {score_class}">{report.ai_score}/100</span></h2>
    <p>{report.ai_summary}</p>

    <h3>商品信息</h3>
    <table>
        <tr><td>标题</td><td>{report.title}</td></tr>
        <tr><td>价格区间</td><td>¥{report.price_min} - ¥{report.price_max}</td></tr>
        <tr><td>评价数</td><td>{report.review_count}</td></tr>
        <tr><td>评分</td><td>{report.avg_rating or '暂无'}</td></tr>
    </table>
    """

    if report.risk_flags:
        body += "<h3>风险提示</h3>"
        for f in report.risk_flags:
            level_class = f"risk-{f.level}"
            body += f'<div class="risk {level_class}"><strong>[{f.level.upper()}] {f.item}</strong><br>{f.detail}</div>'

    if report.profit_estimate:
        body += f"""
    <h3>利润估算</h3>
    <table>
        <tr><td>进货价</td><td>¥{report.profit_estimate.purchase_price}</td></tr>
        <tr><td>参考售价</td><td>¥{report.profit_estimate.reference_selling_price}</td></tr>
        <tr><td>备注</td><td>{report.profit_estimate.notes}</td></tr>
    </table>
    """

    return REPORT_HTML.format(
        title="1688 商品分析报告",
        time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        body=body,
    )


def gen_vendor_report_html(report: VendorReport) -> str:
    score_class = "score-high" if report.trust_score >= 70 else ("score-mid" if report.trust_score >= 40 else "score-low")

    body = f"""
    <h2>供应商信用评分：<span class="score {score_class}">{report.trust_score}/100</span></h2>
    <p>{report.ai_assessment}</p>

    <h3>基本信息</h3>
    <table>
        <tr><td>店铺名</td><td>{report.shop_name}</td></tr>
    </table>
    """

    if report.company_info:
        info = report.company_info
        body += f"""
    <h3>工商信息</h3>
    <table>
        <tr><td>公司名</td><td>{info.company_name}</td></tr>
        <tr><td>注册资本</td><td>{info.reg_capital or '暂无'}</td></tr>
        <tr><td>成立时间</td><td>{info.establish_date or '暂无'}</td></tr>
        <tr><td>法定代表人</td><td>{info.legal_person or '暂无'}</td></tr>
        <tr><td>统一社会信用代码</td><td>{info.credit_code or '暂无'}</td></tr>
    </table>
    """

    body += f"""
    <h3>刷单检测</h3>
    <p>{report.fake_review_warning}</p>
    """

    return REPORT_HTML.format(
        title="1688 供应商背调报告",
        time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        body=body,
    )
