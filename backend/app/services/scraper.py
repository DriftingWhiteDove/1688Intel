"""
1688 数据抓取模块

策略：
  1. Cookie 注入：用户提供浏览器导出的 1688 登录 Cookie → 绕过反爬
  2. 页面解析：提取 window.__INIT_DATA 中的商品数据
  3. API 签名：获取供应商工商信息（已有 sign 算法）
"""

import re
import json
import hashlib
import time
import os
import urllib.parse
from typing import Optional

import httpx
from loguru import logger

APP_KEY = "12574478"
JS_VERSION = "2.7.0"
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "cookies.json")


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _gen_sign(_m_h5_tk: str, timestamp: int, data: str) -> str:
    pre = f"{_m_h5_tk.split('_')[0]}&{timestamp}&{APP_KEY}&{data}"
    return _md5(pre)


def _jsonp_to_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        return json.loads(m.group())
    raise ValueError("JSONP parse failed")


def _extract_member_id(url: str) -> Optional[str]:
    m = re.search(r"memberId=([^&]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"shop/(\d+)", url)
    if m:
        return f"b2b-{m.group(1)}"
    # https://shopxxx.1688.com/
    m = re.search(r"shop(\d+)\.1688\.com", url)
    if m:
        return f"b2b-{m.group(1)}"
    return None


def _extract_offer_id(url: str) -> Optional[str]:
    """从商品 URL 提取 offerId"""
    m = re.search(r"/offer/(\d+)", url)
    if m:
        return m.group(1)
    return None


def _load_cookies() -> list:
    """加载 cookies.json 并标准化格式供 Playwright 使用"""
    path = COOKIE_FILE
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load cookies: {e}")
        return []

    # 标准化：Cookie-Editor 的 sameSite → Playwright 接受的格式
    SAMESITE_MAP = {
        "no_restriction": "None",  # Cookie-Editor → Playwright
        "lax": "Lax",
        "strict": "Strict",
        "unspecified": "None",
    }
    cleaned = []
    for c in raw:
        if not c.get("name") or c.get("value") is None:
            continue
        item = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".1688.com"),
            "path": c.get("path", "/"),
        }
        ss = c.get("sameSite", "")
        if ss and ss.lower() in SAMESITE_MAP:
            item["sameSite"] = SAMESITE_MAP[ss.lower()]
        if c.get("httpOnly"):
            item["httpOnly"] = True
        if c.get("secure"):
            item["secure"] = True
        cleaned.append(item)
    return cleaned


def _cookies_to_header(cookies: list) -> str:
    """将 cookie 列表转为 header 字符串"""
    if not cookies:
        return ""
    pairs = []
    for c in cookies:
        if c.get("name") and c.get("value"):
            pairs.append(f"{c['name']}={c['value']}")
    return "; ".join(pairs)


# ══════════════════════════════════════════
#  搜索关键词提取
# ══════════════════════════════════════════

_SEARCH_STOP_WORDS = [
    "批发", "厂家", "直销", "一件代发", "代发", "现货", "供应",
    "厂家直销", "批发价", "经销", "招商", "加盟", "OEM", "ODM",
    "热销", "爆款", "推荐", "新款", "2024", "2025", "2026",
    "工厂", "生产", "定制", "定做", "logo", "印字", "阿里巴巴",
]


def extract_search_keywords(title: str) -> str:
    """从商品标题提取搜索关键词（去营销词，提取核心产品名）"""
    if not title:
        return ""
    cleaned = title
    for word in _SEARCH_STOP_WORDS:
        cleaned = cleaned.replace(word, " ")
    cleaned = re.sub(r'[\s,，、。.·\[\]【】()（）\-_]+', ' ', cleaned)
    cleaned = cleaned.strip()
    cleaned = re.sub(r'\s+', '', cleaned)
    # 取前 12 字符作为搜索关键词（太长搜不到内容）
    if len(cleaned) > 12:
        cleaned = cleaned[:12]
    return cleaned.strip()


# ══════════════════════════════════════════
#  商品抓取（CDP 模式 — 连接用户真实 Chrome）
# ══════════════════════════════════════════

CDP_PORT = 9222


async def _get_cdp_page():
    """连接用户正在运行的 Edge/Chrome（需 --remote-debugging-port=9222）"""
    from playwright.async_api import async_playwright
    cm = async_playwright()
    p = await cm.__aenter__()
    try:
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        context = browser.contexts[0]
        page = await context.new_page()
        return cm, browser, page
    except Exception:
        await cm.__aexit__(None, None, None)
        return None, None, None


class ProductScraper:

    async def scrape_product(self, url: str) -> dict:
        result = {"url": url}
        offer_id = _extract_offer_id(url)
        if offer_id:
            result["offer_id"] = offer_id

        # 方式A：CDP 模式（优先）
        cm, browser, page = await _get_cdp_page()
        if page:
            result["_mode"] = "cdp"
            try:
                await self._scrape_with_page(page, url, result)
            finally:
                await browser.close()
                await cm.__aexit__(None, None, None)
            return result

        # 方式B：Playwright + Cookie（后备）
        cookies = _load_cookies()
        if not cookies:
            logger.warning("CDP 未连接且无 Cookie。使用方式：双击 start_with_chrome.bat")
            result["_warning"] = "no_cookies"
            return result

        result["_mode"] = "playwright"
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                no_viewport=True, locale="zh-CN", timezone_id="Asia/Shanghai"
            )
            await context.add_cookies(cookies)
            page = await context.new_page()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            try:
                await self._scrape_with_page(page, url, result)
            finally:
                await browser.close()

        return result

    async def _scrape_with_page(self, page, url: str, result: dict):
        """通用页面抓取逻辑"""
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
        except Exception as e:
            logger.warning(f"page load: {e}")

        result["url"] = page.url

        if "punish" in page.url:
            result["_warning"] = "blocked_by_waf"
            result["title"] = await page.title()
            logger.warning("1688 WAF 拦截了请求")
            return

        # 提取数据（新架构：context.result.data → 旧架构：__INIT_DATA）
        try:
            ctx_data = await page.evaluate("() => window.context?.result?.data")
            if ctx_data:
                self._parse_context_data(result, ctx_data)
        except Exception:
            pass

        if not result.get("title"):
            try:
                init_data = await page.evaluate("() => window.__INIT_DATA")
                if init_data:
                    self._parse_init_data(result, init_data)
            except Exception:
                pass

        # 标题 fallback
        if not result.get("title"):
            try:
                t = await page.title()
                result["title"] = t.replace("_1688", "").replace("1688.com", "").strip()
            except Exception:
                result["title"] = ""

        # 页面价格选择器 fallback
        if not result.get("price_min"):
            for sel in [".price-text", ".offer-price", ".price", "[class*=price]"]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        text = await el.text_content()
                        prices = re.findall(r"[\d.]+", text or "")
                        if prices:
                            nums = sorted(float(p) for p in prices)
                            result["price_min"] = nums[0]
                            result["price_max"] = nums[-1]
                            break
                except Exception:
                    continue

    def _parse_context_data(self, result: dict, data: dict) -> None:
        """解析 window.context.result.data（1688 新架构）"""
        try:
            pt = data.get("productTitle", {}).get("fields", {})
            title = pt.get("title") or pt.get("subject")
            if title:
                result["title"] = title

            # 月销量
            sale_num = pt.get("saleNum") or pt.get("monthlySales") or pt.get("saleCount")
            if sale_num:
                result["monthly_sales"] = sale_num

            # 价格（从 SKU 映射取）
            mp = data.get("mainPrice", {}).get("fields", {}).get("finalPriceModel", {})
            sku_map = mp.get("tradeWithoutPromotion", {}).get("skuMapOriginal")
            if sku_map:
                prices = []
                items = sku_map if isinstance(sku_map, list) else list(sku_map.values())
                for sku in items:
                    p = sku.get("price") or sku.get("discountPrice")
                    if p:
                        prices.append(float(p))
                if prices:
                    result["price_min"] = min(prices)
                    result["price_max"] = max(prices)

            # 主图
            imgs = data.get("gallery", {}).get("fields", {}).get("offerImgList", [])
            if imgs:
                result["image"] = imgs[0]

            self._extract_shop_info(result, pt)
            self._extract_evaluation_data(result, pt)
            self._extract_shipping_info(result, mp)
        except Exception as e:
            logger.warning(f"parse context.data: {e}")

    def _extract_shop_info(self, result: dict, pt: dict) -> None:
        """提取供应商信息"""
        try:
            shop = pt.get("shopInfo", {})
            if not shop:
                return
            info = {
                "shop_name": shop.get("shopName", "") or shop.get("companyName", ""),
                "star_level": int(shop.get("starLevel", 0) or 0),
                "trust_pass": bool(shop.get("isTP") or shop.get("hasTP", False)),
                "gold_medal": bool(shop.get("goldMedal", False)),
                "years_in_business": int(shop.get("yearsInBusiness", 0) or 0),
                "shop_type": shop.get("shopType", ""),
                "location": shop.get("location", ""),
            }
            result["supplier_info"] = info
            if shop.get("authCompanyName"):
                result["_company_name"] = shop["authCompanyName"]
        except Exception as e:
            logger.warning(f"extract shopInfo: {e}")

    def _extract_evaluation_data(self, result: dict, pt: dict) -> None:
        """提取评价数据"""
        try:
            rate = pt.get("rateInfo", {})
            if not rate:
                return
            total = int(rate.get("total", 0) or rate.get("count", 0) or rate.get("totalCount", 0))
            good = int(rate.get("goodCount", 0) or rate.get("good", 0))
            middle = int(rate.get("middleCount", 0) or rate.get("middle", 0))
            bad = int(rate.get("badCount", 0) or rate.get("bad", 0))
            has_image = int(rate.get("hasImageCount", 0) or 0)
            has_followup = int(rate.get("hasFollowupCount", 0) or 0)

            # 从 commonTagNodeList 提取详细计数
            if not good and not middle and not bad:
                for tag in rate.get("commonTagNodeList", []):
                    name = str(tag.get("name", ""))
                    count = int(tag.get("count", 0))
                    if "全部" in name:
                        total = count
                    elif "好评" in name or name == "好":
                        good = count
                    elif "中评" in name or "中" in name:
                        middle = count
                    elif "差评" in name or "差" in name:
                        bad = count
                    elif "有图" in name:
                        has_image = count
                    elif "追评" in name:
                        has_followup = count

            result["evaluation_summary"] = {
                "total_reviews": total,
                "good_count": good,
                "middle_count": middle,
                "bad_count": bad,
                "has_image_count": has_image,
                "has_followup_count": has_followup,
            }
        except Exception as e:
            logger.warning(f"extract rateInfo: {e}")

    def _extract_shipping_info(self, result: dict, mp: dict) -> None:
        """提取运费信息"""
        try:
            info = {"has_freight": False, "freight_template_name": "", "volume_price_tiers": []}
            freight = mp.get("freightInfo", {}) or mp.get("freight", {})
            if freight:
                info["has_freight"] = True
                info["freight_template_name"] = freight.get("templateName", "") or freight.get("name", "")
            volume = mp.get("volumePriceInfo", []) or mp.get("volumePrice", [])
            if volume:
                tiers = []
                items = volume if isinstance(volume, list) else list(volume.values())
                for tier in items[:10]:
                    qty = int(tier.get("num", tier.get("quantity", tier.get("startNum", 0))))
                    price = float(tier.get("price", tier.get("discountPrice", tier.get("endPrice", 0))))
                    if qty > 0 and price > 0:
                        tiers.append({"quantity": qty, "price": price})
                info["volume_price_tiers"] = tiers
            result["shipping_info"] = info
        except Exception as e:
            logger.warning(f"extract shipping: {e}")

    def _parse_init_data(self, result: dict, data: dict) -> None:
        """解析 window.__INIT_DATA（1688 旧架构，备选）"""
        try:
            offer = data.get("offer") or data.get("globalData", {}).get("offer") or {}
            if not offer:
                for key in ["detail", "item", "product", "data"]:
                    if isinstance(data.get(key), dict):
                        offer = data[key]
                        break
            if not offer.get("subject"):
                offer = data.get("globalData", {})

            result["title"] = offer.get("subject") or result.get("title", "")

            price_range = offer.get("priceRange") or offer.get("price") or {}
            if isinstance(price_range, dict):
                result["price_min"] = float(price_range.get("startPrice", price_range.get("min", 0)))
                result["price_max"] = float(price_range.get("endPrice", price_range.get("max", 0)))
            elif isinstance(price_range, (int, float)):
                result["price_min"] = result["price_max"] = float(price_range)

            sku = offer.get("skuModel") or data.get("globalData", {}).get("skuModel") or {}
            if not result.get("price_min") and sku:
                prices = [s.get("price", 0) for s in sku.get("skuList", []) if s.get("price")]
                if prices:
                    result["price_min"] = min(prices)
                    result["price_max"] = max(prices)

            result["monthly_sales"] = offer.get("monthlySales") or offer.get("saleCount")
            result["image"] = offer.get("image") or offer.get("picUrl") or ""
        except Exception as e:
            logger.warning(f"parse __INIT_DATA: {e}")

    # ── 完整分析编排 ──

    async def full_analysis(self, url: str) -> dict:
        """完整分析：抓取商品 + 搜索 1688 同行 + 搜索淘宝市场价"""
        result = {"url": url}
        offer_id = _extract_offer_id(url)
        if offer_id:
            result["offer_id"] = offer_id

        cm, browser, page = await _get_cdp_page()
        if not page:
            # 后备：Playwright + Cookie，仅抓取商品页
            cookies = _load_cookies()
            if not cookies:
                result["_warning"] = "no_cookies"
                return result
            result["_mode"] = "playwright"
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(no_viewport=True, locale="zh-CN", timezone_id="Asia/Shanghai")
                await context.add_cookies(cookies)
                page = await context.new_page()
                try:
                    await self._scrape_with_page(page, url, result)
                finally:
                    await browser.close()
            return result

        result["_mode"] = "cdp"
        try:
            await self._scrape_with_page(page, url, result)
            keywords = extract_search_keywords(result.get("title", ""))
            result["_search_keywords"] = keywords

            if keywords:
                ctx = page.context
                # 搜索 1688 同行
                sp = await ctx.new_page()
                try:
                    await self._search_1688_competitors(sp, keywords, result)
                finally:
                    await sp.close()
                # 搜索淘宝市场价
                tp = await ctx.new_page()
                try:
                    await self._search_taobao_prices(tp, keywords, result)
                except Exception as e:
                    logger.warning(f"taobao search failed: {e}")
                    result.setdefault("taobao_market", {})["_error"] = str(e)
                finally:
                    await tp.close()
        finally:
            await browser.close()
            await cm.__aexit__(None, None, None)
        return result

    # ── 1688 同行搜索 ──

    async def _search_1688_competitors(self, page, keywords: str, result: dict) -> None:
        """搜索 1688 同款，获取竞争数量和价格区间"""
        if not keywords:
            return
        search_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={urllib.parse.quote(keywords)}"
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)
        except Exception as e:
            logger.warning(f"1688 search page load: {e}")
            return
        if "punish" in page.url:
            return

        comp = {}
        # 提取搜索结果总数
        try:
            count_text = await page.evaluate("""
                () => {
                    const el = document.querySelector('.offer-list-summary .count')
                        || document.querySelector('.result-count')
                        || document.querySelector('[class*="total"]');
                    return el ? el.textContent.trim() : null;
                }
            """)
            if count_text:
                nums = re.findall(r'[\d,]+', count_text)
                if nums:
                    comp["total_suppliers"] = int(nums[0].replace(",", ""))
        except Exception:
            pass

        # 提取搜索结果页的价格区间
        try:
            prices = await page.evaluate("""
                () => {
                    const nums = [];
                    document.querySelectorAll('.offer-price, [class*="price"]').forEach(el => {
                        const m = el.textContent.trim().match(/[\\d.]+/);
                        if (m) nums.push(parseFloat(m[0]));
                    });
                    return nums;
                }
            """)
            if prices and len(prices) > 1:
                valid = [p for p in prices if p >= 1.0]
                if len(valid) > 1:
                    comp["price_range_min"] = min(valid)
                    comp["price_range_max"] = max(valid)
                elif len(valid) == 1:
                    comp["price_range_min"] = comp["price_range_max"] = valid[0]
        except Exception:
            pass

        if comp:
            comp["search_keywords"] = keywords
            result["competition"] = comp

    # ── 淘宝市场价搜索 ──

    async def _search_taobao_prices(self, page, keywords: str, result: dict) -> None:
        """搜索淘宝同款，获取市场零售价"""
        if not keywords:
            return
        search_url = f"https://s.taobao.com/search?q={urllib.parse.quote(keywords)}"
        tb = {"search_url": search_url}
        result["taobao_market"] = tb

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
        except Exception as e:
            tb["_error"] = f"page_load: {e}"
            return

        url_lower = page.url
        if "login.taobao.com" in url_lower or "passport" in url_lower:
            tb["_error"] = "login_required"
            return
        if "sec" in url_lower or "captcha" in url_lower:
            tb["_error"] = "captcha"
            return

        # 从页面 JS 数据提取
        try:
            items = await page.evaluate("""
                () => {
                    try {
                        const data = window.__INIT_DATA__ || window.g_page_config || window.__INIT_STATE__;
                        if (data) {
                            let list = [];
                            if (data.mods && data.mods.itemlist && data.mods.itemlist.data && data.mods.itemlist.data.auctions)
                                list = data.mods.itemlist.data.auctions;
                            else if (data.itemList) list = data.itemList;
                            else if (data.items) list = data.items;
                            else if (Array.isArray(data)) list = data;
                            return list.slice(0, 20).map(item => ({
                                price: parseFloat(item.price || item.viewPrice || item.payPrice || 0),
                                sales: parseInt(item.sales || item.saleCount || item.payCount || item.monthlySales || 0)
                            }));
                        }
                    } catch(e) {}
                    return null;
                }
            """)
            if items and len(items) > 0:
                prices = [i["price"] for i in items if i["price"] > 0]
                sales = [i["sales"] for i in items if i["sales"] > 0]
                tb["total_listings"] = len(items)
                if prices:
                    tb["min_price"] = round(min(prices), 2)
                    tb["max_price"] = round(max(prices), 2)
                    tb["average_price"] = round(sum(prices) / len(prices), 2)
                if sales:
                    tb["total_sales_count"] = sum(sales)
                tb["_extraction"] = "js_data"
                return
        except Exception:
            pass

        # DOM 解析后备（Taobao 客户端渲染，CSS module class 名不定）
        try:
            items = await page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();
                    // 找到所有包含 ¥ 的叶节点，往上回溯到卡片容器取完整文本
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    const priceNodes = [];
                    while (walker.nextNode()) {
                        const t = walker.currentNode.textContent.trim();
                        if (t === '¥' || t === '￥') {
                            priceNodes.push(walker.currentNode);
                        }
                    }
                    for (const node of priceNodes) {
                        let el = node.parentElement;
                        let containerText = '';
                        for (let i = 0; i < 8; i++) {
                            if (!el) break;
                            containerText = el.textContent;
                            // 卡片容器特征：包含价格和销量文本
                            if (containerText.includes('付款') && containerText.includes('¥')) {
                                break;
                            }
                            el = el.parentElement;
                        }
                        if (!containerText || seen.has(containerText)) continue;
                        seen.add(containerText);
                        const priceMatch = containerText.match(/[¥￥]\\s*(\\d+\\.?\\d*)/);
                        if (!priceMatch) continue;
                        const price = parseFloat(priceMatch[1]);
                        if (price <= 0 || price > 99999) continue;
                        let sales = 0;
                        const sm = containerText.match(/(\\d+)\\s*[+]\\s*人付款/);
                        if (sm) sales = parseInt(sm[1]);
                        results.push({price, sales});
                    }
                    return results.slice(0, 30);
                }
            """)
            if items and len(items) > 0:
                prices = sorted([i["price"] for i in items if i["price"] > 0])
                sales = [i["sales"] for i in items if i["sales"] > 0]
                tb["total_listings"] = len(items)
                if len(prices) >= 3:
                    # 去掉最高最低各 10% 的异常值
                    trim = max(1, len(prices) // 10)
                    core = prices[trim:-trim] if trim > 0 else prices
                    tb["min_price"] = round(core[0], 2)
                    tb["max_price"] = round(core[-1], 2)
                    tb["average_price"] = round(sum(core) / len(core), 2)
                elif prices:
                    tb["min_price"] = round(prices[0], 2)
                    tb["max_price"] = round(prices[-1], 2)
                    tb["average_price"] = round(sum(prices) / len(prices), 2)
                if sales:
                    tb["total_sales_count"] = sum(sales)
                tb["_extraction"] = "dom"
                return
        except Exception:
            pass

        tb["_error"] = "no_data_extracted"

class VendorScraper(ProductScraper):
    pass

    async def scrape_vendor(self, url: str) -> dict:
        member_id = _extract_member_id(url)
        if not member_id:
            raise ValueError("无法从 URL 提取店铺 ID")

        result = {"member_id": member_id, "shop_name": "", "company_info": None}

        cookies = _load_cookies()
        if not cookies:
            logger.warning("未找到 cookies.json，供应商查询需要 1688 登录 Cookie")
            return result

        try:
            from playwright.async_api import async_playwright

            shop_page_urls = [
                url,
                f"https://m.1688.com/winport/{member_id}.html",
            ]

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(locale="zh-CN")
                await context.add_cookies(cookies)
                page = await context.new_page()

                for target_url in shop_page_urls:
                    try:
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(3000)
                        title = await page.title()
                        result["shop_name"] = title.replace("_1688", "").replace("阿里巴巴", "").strip()
                        if result["shop_name"]:
                            break
                    except Exception:
                        continue

                # 尝试从页面提取工商信息
                for sel in [".company-info", ".shop-info", "[class*=company]", "[class*=credit]"]:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            text = await el.text_content()
                            if text and len(text) > 10:
                                result["_page_company_text"] = text.strip()[:500]
                    except Exception:
                        continue

                # 尝试从 __INIT_DATA 提取
                try:
                    init_data = await page.evaluate("() => window.__INIT_DATA")
                    if init_data:
                        result["_init_data"] = True
                except Exception:
                    pass

                await browser.close()
        except Exception as e:
            logger.warning(f"vendor scrape failed: {e}")

        return result
