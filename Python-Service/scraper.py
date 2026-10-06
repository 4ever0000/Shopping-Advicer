"""Shopping Advisor - Playwright (async) skreyp mühərriki.

Əsas dəyişikliklər:
  * Bütün platformalar TƏK brauzerdə, ayrı context-lərdə, asyncio.gather ilə paralel işləyir
  * Hər platformaya ayrıca timeout; biri çöksə qalanlar qayıdır
  * Sabit, brauzer versiyasına uyğun User-Agent (fake_useragent çıxarıldı)
  * Boş nəticədə screenshot + HTML + başlıq yazılır (blok yoxsa selektor problemi bilinsin)
  * Blok aşkarlananda platforma müvəqqəti dayandırılır (spam sorğu blokları artırır)
  * Sorğu təmizləmə, is_similar, qiymət və URL məntiqi yenidən yazıldı
"""
import asyncio
import math
import os
import re
import time
import unicodedata
import urllib.parse

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# ---------------------------------------------------------------- Konfiqurasiya
HEADFUL = os.getenv("SCRAPER_HEADFUL", "0") == "1"  # Docker-də xvfb ilə 1
CHANNEL = os.getenv("SCRAPER_CHANNEL") or None  # məs. "chrome" (real Chrome qurulubsa)
DEBUG_DIR = os.getenv("SCRAPER_DEBUG_DIR", "/tmp/scraper_debug")
PLATFORM_TIMEOUT = int(os.getenv("SCRAPER_PLATFORM_TIMEOUT", "28"))
MAX_CONCURRENCY = int(os.getenv("SCRAPER_MAX_CONCURRENCY", "6"))
BLOCK_COOLDOWN = int(os.getenv("SCRAPER_BLOCK_COOLDOWN", "300"))  # saniyə; 0 = söndür
# Birmarket və Umico eyni şirkətdir, məhsul ID-ləri eynidir -> eyni məhsul sayılır
TREAT_BIRMARKET_AS_UMICO = True


class BlockedError(Exception):
    pass


# ---------------------------------------------------------------- Mətn köməkçiləri
def fold(text: str) -> str:
    """Kiçik hərf + diakritiksiz (ə->e, ı->i, ö->o, ş->s ...)."""
    text = (text or "").lower().replace("ə", "e").replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t.endswith("s") else t


def _tokens(text: str):
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", fold(text))]


SITE_NAMES = {
    "birmarket", "umico", "alinino", "trendyol", "amazon", "ebay", "aliexpress",
    "kontakt", "irshad", "irsad", "bakuelectronics", "temu", "tapaz",
}
# Başlıqdakı marketinq səs-küyü (fold edilmiş formada)
NOISE = {
    "qiymeti", "qiymet", "qiymetleri", "satisi", "satis", "almaq", "ucuz", "endirim",
    "endirimle", "kredit", "kreditle", "catdirilma", "sifaris", "onlayn", "online",
    "magaza", "azerbaycan", "buy", "price", "prices", "sale", "shop", "store",
    "kampaniya", "ve", "muellif", "yazici", "nesriyyat",
}
# Oxşarlıq yoxlamasında nəzərə alınmayan sözlər
STOP = {_stem(w) for w in (
    "the", "an", "and", "or", "of", "for", "with", "by", "in", "on", "to", "at", "from",
    "ve", "ile", "ucun", "bir", "de", "da", "kitab",
)}
# Sorğuda yoxdursa, başlıqda olması yanlış məhsul deməkdir
ACCESSORY = {_stem(w) for w in (
    "case", "cover", "charger", "protector", "strap", "cable", "adapter", "holder",
    "stand", "skin", "tempered", "glass", "sticker", "mount", "bracket", "keychain",
)}
VARIANT = {_stem(w) for w in (
    "deluxe", "anniversary", "collector", "collectors", "bundle", "lot", "replica",
    "broken", "parts",
)}
MODEL_SUFFIX = {_stem(w) for w in ("pro", "max", "plus", "ultra", "mini", "lite")}


def extract_title(raw: str) -> str:
    """'Məhsul ✅ qiymət | Birmarket' -> 'Məhsul ✅ qiymət' (sayt adı hissəsini atır)."""
    text = raw or ""
    parts = [p.strip() for p in re.split(r"\s*[|•·]\s*|\s+[–—]\s+", text) if p.strip()]
    for p in parts:
        if fold(re.sub(r"[^\w]", "", p)) not in SITE_NAMES:
            return p
    return text


def universal_clean_query(query: str) -> str:
    """Səhifə başlığından təmiz axtarış sorğusu çıxarır (idempotentdir)."""
    if not query:
        return ""
    text = extract_title(query).lower()
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", text)  # mötərizələr
    text = re.sub(r"\b\d+\s*(ml|oz)\b", " ", text)  # parfüm həcmi
    text = re.sub(
        r"\b(edt|edp|cologne|parfum|parfüm|eau de|essence|refill|tester|unisex|paket)\b",
        " ", text,
    )
    text = re.sub(r"[^\w\s]", " ", text)  # emoji, durğu işarələri
    words = [w for w in text.split() if fold(w) not in NOISE and fold(w) not in SITE_NAMES]
    return " ".join(words).strip()


def to_global_query(q: str) -> str:
    """Amazon/eBay/AliExpress üçün: diakritiksiz + Azərbaycan dilində kateqoriya sözləri atılır."""
    drop = {"kitab"}
    toks = [t for t in re.findall(r"[a-z0-9]+", fold(q)) if t not in drop]
    return " ".join(toks)


def _number_in_title(tok: str, title_f: str) -> bool:
    parts = re.findall(r"[a-z]+|\d+", tok)
    pat = r"(?<![a-z0-9])" + r"\s*".join(re.escape(p) for p in parts) + r"(?![a-z0-9])"
    return re.search(pat, title_f) is not None


def is_similar(query: str, title: str) -> bool:
    q = universal_clean_query(query)
    if not q or not title:
        return True
    q_tokens = [t for t in _tokens(q) if t not in STOP and (len(t) > 1 or t.isdigit())]
    if not q_tokens:
        return True
    title_f = fold(title)
    t_tokens = set(_tokens(title))
    q_set = set(q_tokens)
    has_digit = lambda s: any(ch.isdigit() for ch in s)  # noqa: E731

    # 1) model/yaddaş kimi rəqəmli tokenlər mütləq uyğun olmalıdır
    for tok in q_tokens:
        if has_digit(tok) and not _number_in_title(tok, title_f):
            return False
    # 2) aksesuar/variant sözləri sorğuda yoxdursa, başlıqda olmamalıdır
    if (t_tokens & ACCESSORY) - q_set:
        return False
    if (t_tokens & VARIANT) - q_set:
        return False
    if any(has_digit(t) for t in q_tokens) and (t_tokens & MODEL_SUFFIX) - q_set:
        return False
    # 3) söz uyğunluğu: ≤2 söz -> hamısı, daha çoxda ən azı 60%
    words = [t for t in q_tokens if not has_digit(t)]
    if not words:
        return True
    hits = sum(1 for w in words if w in t_tokens)
    needed = len(words) if len(words) <= 2 else math.ceil(len(words) * 0.6)
    return hits >= needed


# ---------------------------------------------------------------- Qiymət köməkçiləri
_NUM = r"\d[\d.,\u00a0\u202f]*"
_CURRENCIES = [
    ("TRY", r"(?:₺|\bTL\b|\bTRY\b)"),
    ("AZN", r"(?:₼|\bAZN\b)"),
    ("USD", r"(?:US\s*\$|\$|\bUSD\b)"),
    ("EUR", r"(?:€|\bEUR\b)"),
    ("GBP", r"(?:£|\bGBP\b)"),
]


def parse_amount(text: str):
    """'1.299,90' -> 1299.9 ; '1,299.90' -> 1299.9 ; '29,45' -> 29.45 ; '$35.68' -> 35.68"""
    if not text:
        return None
    m = re.search(_NUM, text)
    if not m:
        return None
    raw = m.group(0).replace("\u00a0", "").replace("\u202f", "").rstrip(".,")
    if not raw:
        return None
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        head, tail = raw.rsplit(",", 1)
        raw = head.replace(",", "") + ("." + tail if len(tail) <= 2 else tail)
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    elif "." in raw:
        head, tail = raw.split(".")
        if len(tail) == 3 and head not in ("", "0"):
            raw = head + tail
    try:
        return float(raw)
    except ValueError:
        return None


def find_prices(text: str):
    """[(mövqe, məbləğ, valyuta)] - mətndəki valyuta işarəli qiymətlər."""
    out = []
    for cur, mk in _CURRENCIES:
        for m in re.finditer(rf"(?:{mk})\s*({_NUM})|({_NUM})\s*(?:{mk})", text or "", flags=re.I):
            amount = parse_amount(m.group(1) or m.group(2))
            if amount and amount > 0:
                out.append((m.start(), amount, cur))
    return sorted(out)


def pick_price(text: str, allowed, mode: str = "first"):
    """(məbləğ, valyuta) və ya None. mode='min' köhnə/endirimli qiymətdə endirimlini seçir."""
    found = [(a, c) for _, a, c in find_prices(text) if c in allowed]
    if not found:
        return None
    cur = found[0][1]
    amounts = [a for a, c in found if c == cur]
    return (min(amounts) if mode == "min" else amounts[0]), cur


# ---------------------------------------------------------------- URL köməkçiləri
_KEY_PATTERNS = [
    r"/dp/([A-Z0-9]{10})",          # Amazon
    r"/itm/(?:[^/?]+/)?(\d{9,})",   # eBay
    r"/item/(\d+)",                 # AliExpress
    r"-p-(\d+)",                    # Trendyol
]


def _norm_url(u: str):
    p = urllib.parse.urlparse(u or "")
    host = p.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return host, p.path.rstrip("/")


def is_same_page(current_url: str, candidate: str) -> bool:
    """İstifadəçinin hazırda baxdığı məhsulu nəticələrdən kənarlaşdırır."""
    if not current_url or len(current_url) < 12 or not candidate:
        return False
    ch, cp = _norm_url(current_url)
    xh, xp = _norm_url(candidate)
    if ch == xh and cp == xp:
        return True
    for pat in _KEY_PATTERNS:
        a, b = re.search(pat, current_url), re.search(pat, candidate)
        if a and b and a.group(1) == b.group(1):
            return True
    if TREAT_BIRMARKET_AS_UMICO and {ch, xh} <= {"birmarket.az", "umico.az"}:
        a, b = re.search(r"/product/(\d+)", cp), re.search(r"/product/(\d+)", xp)
        return bool(a and b and a.group(1) == b.group(1))
    return False


def abs_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href or "")


# ---------------------------------------------------------------- Brauzer idarəsi
_pw = None
_browser = None
_lock = asyncio.Lock()
_STATE = {}      # platforma -> storage_state (cookie-lər saxlanılır, hər dəfə sıfırdan başlamır)
_COOLDOWN = {}   # platforma -> blok bitmə vaxtı


async def get_browser():
    global _pw, _browser
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        if _pw is None:
            _pw = await async_playwright().start()
        args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--window-size=1366,768",
        ]
        try:
            _browser = await _pw.chromium.launch(headless=not HEADFUL, channel=CHANNEL, args=args)
            print(f"[BROWSER] başladı (headful={HEADFUL}, channel={CHANNEL}, v{_browser.version})")
        except Exception as e:
            if not HEADFUL:
                raise
            print(f"[BROWSER] headful alınmadı ({e}); headless-ə keçilir")
            _browser = await _pw.chromium.launch(headless=True, channel=CHANNEL, args=args)
        return _browser


async def shutdown():
    global _pw, _browser
    try:
        if _browser:
            await _browser.close()
        if _pw:
            await _pw.stop()
    except Exception:
        pass
    _browser = _pw = None


async def new_context(platform: str, locale: str, accept_lang: str):
    browser = await get_browser()
    major = (browser.version or "131").split(".")[0]
    # Brauzer versiyasına və Linux platformasına uyğun UA (random UA bot siqnalıdır)
    ua = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{major}.0.0.0 Safari/537.36"
    )
    kwargs = dict(
        user_agent=ua,
        viewport={"width": 1366, "height": 768},
        locale=locale,
        timezone_id="Asia/Baku",
        extra_http_headers={"Accept-Language": accept_lang},
    )
    if _STATE.get(platform):
        kwargs["storage_state"] = _STATE[platform]
    ctx = await browser.new_context(**kwargs)

    async def _route(route):
        if route.request.resource_type in ("media", "font"):
            await route.abort()
        else:
            await route.continue_()

    await ctx.route("**/*", _route)
    return ctx


_BLOCK_MARKERS = (
    "captcha", "robot check", "are you a human", "pardon our interruption",
    "access denied", "verify you are human", "unusual traffic", "just a moment",
    "slide to verify", "/punish", "_____tmd_____", "checking your browser",
    "attention required", "security check", "automated access",
)


def looks_blocked(title: str, html: str) -> bool:
    t = (title or "").lower()
    h = (html or "")[:200000].lower()
    return any(m in t for m in _BLOCK_MARKERS) or any(m in h for m in _BLOCK_MARKERS)


async def dump_debug(page, platform: str, note: str) -> bool:
    """Boş nəticədə: başlıq, URL, screenshot, HTML. Blok olub-olmadığını qaytarır."""
    blocked = False
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        title = await page.title()
        html = await page.content()
        blocked = looks_blocked(title, html)
        await page.screenshot(path=os.path.join(DEBUG_DIR, f"{platform}.png"))
        with open(os.path.join(DEBUG_DIR, f"{platform}.html"), "w", encoding="utf-8") as f:
            f.write(html[:400000])
        print(
            f"[DEBUG {platform}] {note} | title='{title[:80]}' | url={page.url[:120]} "
            f"| html={len(html)} | blok_şübhəsi={blocked}"
        )
    except Exception as e:
        print(f"[DEBUG {platform}] dump xətası: {e}")
    return blocked


async def safe_text(el) -> str:
    if not el:
        return ""
    try:
        return (await el.inner_text()) or ""
    except Exception:
        return ""


async def img_url(el, base: str) -> str:
    if not el:
        return ""
    for name in ("src", "data-src", "srcset"):
        try:
            v = await el.get_attribute(name)
        except Exception:
            v = None
        if not v or v.strip().startswith("data:"):
            continue
        v = v.strip()
        if re.search(r"\s", v):
            v = v.split(",")[0].split()[0]
        return abs_url(base, v)
    return ""


def _item(platform, url, price, currency, image, comments=None):
    return {
        "platform_name": platform,
        "competitor_url": url,
        "price": price,
        "currency": currency,
        "image_url": image,
        "comments": comments or [],
    }


async def _run_page(platform, url, locale, accept_lang, wait_selector, parser,
                    settle=1500, scroll=0, cookies=None):
    """Ümumi qəlib: context aç -> səhifəni yüklə -> parser -> boşdursa debug."""
    ctx = await new_context(platform, locale, accept_lang)
    try:
        if cookies:
            await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        await stealth_async(page)
        print(f"[PLAYWRIGHT] {platform}: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if wait_selector:
            try:
                await page.wait_for_selector(wait_selector, timeout=12000)
            except Exception:
                pass
        await page.wait_for_timeout(settle)
        if scroll:
            await page.evaluate(f"window.scrollTo(0, {scroll})")
            await page.wait_for_timeout(1000)

        stats = {"cards": 0}
        results = await parser(page, stats)
        print(f"[{platform}] kart={stats['cards']} qəbul={len(results)}")
        if results:
            try:
                _STATE[platform] = await ctx.storage_state()
            except Exception:
                pass
        else:
            blocked = await dump_debug(page, platform, f"kart={stats['cards']}")
            if stats["cards"] == 0 and blocked:
                raise BlockedError(platform)
        return results
    finally:
        await ctx.close()


# ---------------------------------------------------------------- Platforma parserləri
async def scrape_trendyol(query, current_url=""):
    url = f"https://www.trendyol.com/sr?q={urllib.parse.quote(query)}"

    async def parser(page, stats):
        cards = await page.query_selector_all(
            "div.p-card-wrppr, div[class*='p-card-chld'], div.product-card"
        )
        if not cards:  # ehtiyat: Trendyol məhsul linkləri '-p-<id>' formasındadır
            cards = await page.query_selector_all("a[href*='-p-']")
        stats["cards"] = len(cards)
        for el in cards:
            a, href = el, await el.get_attribute("href")
            if not href:
                a = await el.query_selector("a[href]")
                href = (await a.get_attribute("href")) if a else ""
            if not href or "sponsor" in href.lower() or "advert" in href.lower():
                continue
            p_url = abs_url("https://www.trendyol.com", href)
            if is_same_page(current_url, p_url):
                continue
            text = await safe_text(el)
            if not text or not is_similar(query, text):
                continue
            price = pick_price(text, {"TRY"}, mode="min")
            if not price:
                continue
            image = await img_url(await el.query_selector("img"), "https://www.trendyol.com")
            return [_item("Trendyol", p_url, price[0], "TRY", image)]
        return []

    return await _run_page(
        "Trendyol", url, "tr-TR", "tr-TR,tr;q=0.9,en;q=0.8",
        "div.p-card-wrppr, a[href*='-p-']", parser, scroll=400,
    )


async def scrape_umico(query, current_url=""):
    url = f"https://umico.az/search/{urllib.parse.quote(query)}"

    async def parser(page, stats):
        cards = await page.query_selector_all("a[href*='/product/'], div[class*='ProductCard']")
        stats["cards"] = len(cards)
        for card in cards:
            href = await card.get_attribute("href") or ""
            if not href:
                a = await card.query_selector("a[href*='/product/']")
                href = (await a.get_attribute("href")) if a else ""
            if not href:
                continue
            p_url = abs_url("https://umico.az", href)
            if is_same_page(current_url, p_url):
                continue
            text = await safe_text(card)
            if not text.strip() or not is_similar(query, text):
                continue
            price = pick_price(text, {"AZN"}, mode="first")
            value = price[0] if price else None
            if value is None:
                pe = await card.query_selector("[class*='Price'], [class*='price']")
                value = parse_amount(await safe_text(pe)) if pe else None
            if not value:
                continue
            image = await img_url(await card.query_selector("img"), "https://umico.az")
            comments = []
            for c in await card.query_selector_all(
                "[class*='review'], [class*='rating'], [class*='comment']"
            ):
                txt = (await safe_text(c)).strip()
                if txt and not txt.replace(".", "").isdigit() and "reytinq" not in txt.lower():
                    comments.append(txt)
            return [_item("Umico", p_url, value, "AZN", image, comments[:3])]
        return []

    return await _run_page(
        "Umico", url, "az-AZ", "az-AZ,az;q=0.9",
        "a[href*='/product/']", parser, settle=2000,
    )


async def scrape_alinino(query, current_url=""):
    url = f"https://alinino.az/search?q={urllib.parse.quote(query)}"

    async def parser(page, stats):
        cards = await page.query_selector_all(".product-card, .product-item, .grid__item")
        stats["cards"] = len(cards)
        for card in cards:
            text = await safe_text(card)
            if not text.strip() or not is_similar(query, text):
                continue
            a = await card.query_selector("a[href]")
            href = (await a.get_attribute("href")) if a else (await card.get_attribute("href"))
            if not href:
                continue
            p_url = abs_url("https://alinino.az", href)
            if is_same_page(current_url, p_url):
                continue
            pe = await card.query_selector(".price, .price-item, [class*='price']")
            ptxt = await safe_text(pe) if pe else ""
            price = pick_price(ptxt, {"AZN"}) or pick_price(text, {"AZN"})
            value = price[0] if price else parse_amount(ptxt)
            if not value or value <= 0:
                continue
            image = await img_url(await card.query_selector("img"), "https://alinino.az")
            comments = []
            for c in await card.query_selector_all("[class*='review']"):
                txt = (await safe_text(c)).strip()
                if txt:
                    comments.append(txt)
            return [_item("Alinino", p_url, value, "AZN", image, comments[:3])]
        return []

    return await _run_page(
        "Alinino", url, "az-AZ", "az-AZ,az;q=0.9",
        ".product-card, .product-item, .grid__item", parser,
    )


async def scrape_amazon(query, current_url=""):
    url = f"https://www.amazon.com/s?k={urllib.parse.quote(query)}"

    async def parser(page, stats):
        cards = await page.query_selector_all("div[data-component-type='s-search-result']")
        stats["cards"] = len(cards)
        organic = sponsored = None
        for card in cards:
            asin = (await card.get_attribute("data-asin")) or ""
            if not re.fullmatch(r"[A-Z0-9]{10}", asin):
                continue
            p_url = f"https://www.amazon.com/dp/{asin}"  # sspa/click yönləndirməsi əvəzinə təmiz link
            if is_same_page(current_url, p_url):
                continue
            h2 = await card.query_selector("h2")
            title = (await safe_text(h2)) if h2 else (await safe_text(card))
            if not is_similar(query, title):
                continue
            pe = await card.query_selector(".a-price:not(.a-text-price) .a-offscreen")
            price = parse_amount(await pe.text_content()) if pe else None
            if not price:
                continue
            is_sp = bool(await card.query_selector("span.puis-sponsored-label-text")) or (
                "sponsored" in (await safe_text(card)).lower()
            )
            item = _item("Amazon", p_url, price, "USD",
                         await img_url(await card.query_selector("img.s-image"), "https://www.amazon.com"))
            if is_sp:
                sponsored = sponsored or item
            else:
                organic = item
                break
        best = organic or sponsored
        return [best] if best else []

    return await _run_page(
        "Amazon", url, "en-US", "en-US,en;q=0.9",
        "div[data-component-type='s-search-result']", parser,
    )


async def scrape_ebay(query, current_url=""):
    url = f"https://www.ebay.com/sch/i.html?_nkw={urllib.parse.quote(query)}"

    async def parser(page, stats):
        # eBay köhnə 'li.s-item' və yeni 'li.s-card' düzənini işlədir
        cards = await page.query_selector_all("li.s-card, li.s-item")
        stats["cards"] = len(cards)
        for card in cards:
            text = await safe_text(card)
            if not text.strip() or "shop on ebay" in text.lower():
                continue
            a = await card.query_selector("a[href*='/itm/']")
            if not a:
                continue
            href = await a.get_attribute("href") or ""
            if not href or "itm/123456" in href:
                continue
            p_url = href.split("?")[0]
            if is_same_page(current_url, p_url):
                continue
            te = await card.query_selector(".s-card__title, .s-item__title")
            title = (await safe_text(te)) if te else text.split("\n")[0]
            title = re.sub(r"(?i)^new listing\s*", "", title)
            if not is_similar(query, title):
                continue
            pe = await card.query_selector(".s-card__price, .s-item__price")
            price = pick_price(await safe_text(pe) if pe else text, {"USD"})
            if not price:
                continue
            image = await img_url(await card.query_selector("img"), "https://www.ebay.com")
            return [_item("eBay", p_url, price[0], "USD", image)]
        return []

    return await _run_page(
        "eBay", url, "en-US", "en-US,en;q=0.9",
        "li.s-card, li.s-item", parser,
    )


async def scrape_aliexpress(query, current_url=""):
    url = f"https://www.aliexpress.com/w/wholesale-{urllib.parse.quote(query)}.html"
    # Qiyməti USD/qlobal saytda göstərməyə məcbur edən cookie
    cookies = [{
        "name": "aep_usuc_f",
        "value": "site=glo&c_tp=USD&region=US&b_locale=en_US",
        "domain": ".aliexpress.com",
        "path": "/",
    }]

    async def parser(page, stats):
        anchors = await page.query_selector_all("a[href*='/item/']")
        stats["cards"] = len(anchors)
        seen = set()
        for a in anchors:
            href = await a.get_attribute("href") or ""
            p_url = abs_url("https://www.aliexpress.com", href).split("?")[0]
            if not href or p_url in seen:
                continue
            seen.add(p_url)
            if is_same_page(current_url, p_url):
                continue
            text = await safe_text(a)
            if not text.strip() or not is_similar(query, text):
                continue
            price, scope = None, a
            for xp in ("", "xpath=..", "xpath=../.."):  # qiymət bəzən valideyn kartdadır
                scope = a if not xp else await a.query_selector(xp)
                price = pick_price(await safe_text(scope), {"USD", "AZN"})
                if price:
                    break
            if not price:
                continue
            image = await img_url(await a.query_selector("img"), "https://www.aliexpress.com")
            return [_item("AliExpress", p_url, price[0], price[1], image)]
        return []

    return await _run_page(
        "AliExpress", url, "en-US", "en-US,en;q=0.9",
        "a[href*='/item/']", parser, settle=3000, scroll=800, cookies=cookies,
    )


# ---------------------------------------------------------------- Orkestrasiya
async def run_platform(name, factory, sem):
    until = _COOLDOWN.get(name, 0)
    if time.time() < until:
        print(f"[SKIP] {name}: blok səbəbindən {int(until - time.time())} san. dayandırılıb")
        return []
    async with sem:
        t0 = time.time()
        try:
            res = await asyncio.wait_for(factory(), timeout=PLATFORM_TIMEOUT)
            print(f"[OK] {name}: {len(res)} nəticə, {time.time() - t0:.1f}s")
            return res
        except BlockedError:
            _COOLDOWN[name] = time.time() + BLOCK_COOLDOWN
            print(f"[BLOCKED] {name}: bloklandı, {BLOCK_COOLDOWN}s dayandırılır (debug faylına bax)")
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] {name}: {PLATFORM_TIMEOUT}s-də bitmədi")
        except Exception as e:
            print(f"[ERROR] {name}: {type(e).__name__}: {e}")
    return []


async def search_all(raw_query: str, current_url: str = ""):
    base = universal_clean_query(raw_query) or (raw_query or "").strip()
    global_q = to_global_query(base) or base
    print(f"[QUERY] yerli='{base}' | qlobal='{global_q}'")
    jobs = [
        ("Trendyol", lambda: scrape_trendyol(base, current_url)),
        ("Umico", lambda: scrape_umico(base, current_url)),
        ("Alinino", lambda: scrape_alinino(base, current_url)),
        ("Amazon", lambda: scrape_amazon(global_q, current_url)),
        ("eBay", lambda: scrape_ebay(global_q, current_url)),
        ("AliExpress", lambda: scrape_aliexpress(global_q, current_url)),
    ]
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    chunks = await asyncio.gather(*(run_platform(n, f, sem) for n, f in jobs))
    return [item for chunk in chunks for item in chunk]