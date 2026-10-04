import re
import urllib.parse
from playwright.sync_api import sync_playwright


def universal_clean_query(query: str) -> str:
    """Universal Regex Təmizləyicisi: Axtarışın keyfiyyətini aşağı salan artıq sözləri,

    ölçü biriklərini, parfüm/cinsiyyət tiplərini və xüsusi simvolları təmizləyir.
    """
    if not query:
        return ""

    cleaned = query.lower()

    # 1. Mötərizə daxilindəki yazıları sil
    cleaned = re.sub(r"\(.*?\)|\[.*?\]", "", cleaned)

    # 2. Həcm, yaddaş və ölçü vahidlərini sil (ml, gb, mah, kg və s.)
    cleaned = re.sub(
        r"\b\d+\s*(ml|l|g|kg|gb|tb|cm|mm|m|oz|mah|w|hz)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # 3. Parfüm və kosmetika terminlərini sil
    cleaned = re.sub(
        r"\b(edt|edp|cologne|parfum|parfüm|eau de|essence|refill|tester)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # 4. Cinsiyyət və paket sözlərini sil
    cleaned = re.sub(
        r"\b(erkek|kadın|unisex|men|women|man|woman|set|paket|kit)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # 5. Xüsusi simvolları boşluqla əvəz et
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)

    # 6. Artıq boşluqları təmizlə
    words = cleaned.split()
    return " ".join(words).strip()


def is_similar(query: str, title: str) -> bool:
    cleaned_query = universal_clean_query(query)
    if not cleaned_query or not title:
        return True

    query_words = set(cleaned_query.split())
    title_lower = title.lower()

    # Rəqəm uyğunluğu
    query_numbers = set(re.findall(r"\d+", cleaned_query))
    for num in query_numbers:
        if num not in title_lower:
            return False

    matches = [word for word in query_words if word in title_lower]
    if not query_words:
        return True
    
    match_ratio = len(matches) / len(query_words)
    
    # Qısa sorğularda (1-2 söz) 1 sözün tapılması kifayətdir, uzunlarda nisbət 0.35-ə endirilir
    if len(query_words) <= 2:
        return len(matches) >= 1
    return match_ratio >= 0.35

def search_google_and_scrape(product_name: str, current_url: str = None):
    search_keyword = universal_clean_query(product_name) or product_name
    encoded_query = urllib.parse.quote(search_keyword)
    search_url = f"https://www.trendyol.com/sr?q={encoded_query}"
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="tr-TR",
            viewport={"width": 1366, "height": 768},
            extra_http_headers={
                "Accept-Language": "tr-TR,tr;q=0.9",
                "Referer": "https://www.google.com/"
            }
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            print(f"[PLAYWRIGHT] Trendyol-da axtarış edilir: {search_keyword}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            page.evaluate("window.scrollTo(0, 400)")
            page.wait_for_timeout(1000)

            cards = page.query_selector_all("div.p-card-wrppr, div[data-id], div[class*='p-card-chld'], div.product-card")

            for card in cards:
                a_tag = card.query_selector("a")
                if not a_tag:
                    continue

                href = a_tag.get_attribute("href") or ""
                if not href or "sponsor" in href.lower() or "advertisement" in href.lower():
                    continue

                product_url = f"https://www.trendyol.com{href}" if href.startswith("/") else href

                if current_url and len(current_url) > 25 and current_url in product_url:
                    continue

                try:
                    card_text = card.evaluate("el => el.innerText") or ""
                except Exception:
                    card_text = ""

                if not card_text or not is_similar(product_name, card_text):
                    continue

                price_val = None
                price_elem = card.query_selector(".prc-box-dscntd, [class*='price'], [class*='prc'], .price-promoted, div[class*='Price']")
                if price_elem:
                    try:
                        raw_price = price_elem.evaluate("el => el.innerText")
                        raw_price = raw_price.replace(".", "").replace(",", ".").replace("TL", "").replace("₺", "").strip()
                        extracted = re.findall(r"\d+\.?\d*", raw_price)
                        if extracted:
                            price_val = float(extracted[0])
                    except Exception:
                        pass

                img_elem = card.query_selector("img")
                image_url = ""
                if img_elem:
                    image_url = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""

                if price_val and product_url:
                    results.append({
                        "platform_name": "Trendyol",
                        "competitor_url": product_url,
                        "price": price_val,
                        "currency": "TRY",
                        "image_url": image_url,
                        "comments": []
                    })
                    break

            if not results:
                print("[PLAYWRIGHT] Trendyol məhsul və ya qiymət tapıla bilmədi.")

        except Exception as e:
            print(f"[PLAYWRIGHT XƏTASI Trendyol]: {e}")
        finally:
            browser.close()

    return results

def scrape_umico(product_name: str):
    search_keyword = universal_clean_query(product_name) or product_name
    encoded_query = urllib.parse.quote(search_keyword)
    search_url = f"https://umico.az/search/{encoded_query}"
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            no_viewport=True,
            locale="az-AZ",
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () =>"
            " undefined})"
        )

        try:
            print(f"[PLAYWRIGHT] Umico-da axtarış edilir: {search_keyword}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            product_cards = page.query_selector_all(
                "a[href*='/product/'], div[class*='ProductCard']"
            )

            for card in product_cards:
                href = card.get_attribute("href") or ""
                if not href:
                    a_elem = card.query_selector("a[href*='/product/']")
                    if a_elem:
                        href = a_elem.get_attribute("href") or ""

                if not href:
                    continue

                product_url = (
                    f"https://umico.az{href}" if href.startswith("/") else href
                )
                try:
                    card_text = card.inner_text() or ""
                except Exception:
                    card_text = ""      

                

                if not card_text.strip() or not is_similar(product_name, card_text):
                    continue

                price_match = re.search(
                    r"(\d+[\.,]\d{2})\s*(?:₼|AZN)", card_text
                )
                price_val = None
                if price_match:
                    price_val = float(price_match.group(1).replace(",", "."))
                else:
                    price_elem = card.query_selector(
                        "[class*='Price'], [class*='price']"
                    )
                    if price_elem:
                       try:
                           raw_p = price_elem.evaluate("el => el.innerText").replace(",", ".")
                           extracted = re.findall(r"\d+\.\d{2}|\d+", raw_p)
                           if extracted:
                               price_val = float(extracted[0])
                       except Exception:
                             pass
                       
                           
                if price_val:
                    img_elem = card.query_selector("img")
                    image_url = ""
                    if img_elem:
                        image_url = (
                            img_elem.get_attribute("src")
                            or img_elem.get_attribute("data-src")
                            or img_elem.get_attribute("srcset")
                            or ""
                        )
                        if image_url.startswith("//"):
                            image_url = f"https:{image_url}"
                    # DİNAMİK RƏY HİSSƏSİ (Hardcoded mətn silindi)
                    comment_nodes = card.query_selector_all("[class*='review'], [class*='rating'], [class*='comment']")
                    comments = []
                    for c in comment_nodes:
                        try:
                            txt = c.evaluate("el => el.innerText").strip()
                            if txt and not txt.replace('.', '').isdigit() and "reytinq" not in txt.lower(): # yalnız rəqəm deyilsə rəy kimi götür
                                comments.append(txt)
                        except Exception:
                            pass
                        

                    results.append({
                        "platform_name": "Umico",
                        "competitor_url": product_url,
                        "price": price_val,
                        "currency": "AZN",
                        "image_url": image_url,
                        "comments": comments[:3]  # Rəy yoxdursa boş array [] verəcək
                    })
                    break

        except Exception as e:
            print(f"[PLAYWRIGHT XƏTASI Umico]: {e}")
        finally:
            browser.close()

    return results


def scrape_alinino(product_name: str):
    search_keyword = universal_clean_query(product_name) or product_name
    encoded_query = urllib.parse.quote(search_keyword)
    search_url = f"https://alinino.az/search?q={encoded_query}"
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True ,args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            product_cards = page.query_selector_all(
                ".product-card, .product-item, .grid__item"
            )

            for product_card in product_cards:
                try:
                    card_text = product_card.evaluate("el => el.innerText") or ""
                except Exception:
                    card_text = ""

                if not card_text.strip():
                    continue

                link_elem = product_card.query_selector("a") or product_card
                href = link_elem.get_attribute("href") or ""
                if not href:
                    continue

                product_url = (
                    f"https://alinino.az{href}"
                    if href.startswith("/")
                    else href
                )

                price_elem = product_card.query_selector(
                    ".price, .price-item, [class*='price']"
                )
                price_val = None

                if price_elem:
                    price_str = (
                        price_elem.inner_text()
                        .replace(",", ".")
                        .replace("AZN", "")
                        .replace("₼", "")
                        .strip()
                    )
                    extracted = re.findall(
                        r"\d+\.\d{2}|\d+\.\d+|\d+", price_str
                    )
                    if extracted:
                        price_val = float(extracted[0])

                if not price_val:
                    price_match = re.search(
                        r"(\d+[\.,]\d{2})\s*(?:₼|AZN)", card_text
                    )
                    if price_match:
                        price_val = float(
                            price_match.group(1).replace(",", ".")
                        )

                if price_val and price_val > 0:
                    img_elem = product_card.query_selector("img")
                    image_url = ""
                    if img_elem:
                        src = (
                            img_elem.get_attribute("src")
                            or img_elem.get_attribute("data-src")
                            or ""
                        )
                        image_url = f"https:{src}" if src.startswith("//") else src

                    comment_nodes = product_card.query_selector_all(
                        "[class*='review']"
                    )
                    comments = [
                        c.inner_text().strip()
                        for c in comment_nodes
                        if c.inner_text() and c.inner_text().strip()
                    ][:3]
                    
                    results.append({
                        "platform_name": "Alinino",
                        "competitor_url": product_url,
                        "price": price_val,
                        "currency": "AZN",
                        "image_url": image_url,
                        "comments": comments,
                    })
                    break

        except Exception as e:
            print(f"[PLAYWRIGHT XƏTASI Alinino]: {e}")
        finally:
            browser.close()

    return results

def scrape_amazon(product_name: str, current_url: str = None):
    search_keyword = universal_clean_query(product_name) or product_name
    encoded_query = urllib.parse.quote(search_keyword)
    search_url = f"https://www.amazon.com/s?k={encoded_query}"
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1366, "height": 768},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": "https://www.google.com/"
            }
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            print(f"[PLAYWRIGHT] Amazon-da axtarış edilir: {search_keyword}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # Məhsul kartları
            product_cards = page.query_selector_all("div[data-component-type='s-search-result']")

            for card in product_cards:
                # Başlıq və Link
                a_tag = card.query_selector("h2 a, a.a-link-normal.s-no-outline, a.a-link-normal.s-underline-text")
                if not a_tag:
                    continue

                href = a_tag.get_attribute("href") or ""
                if not href or "slredirect" in href or "spa/mkw" in href:
                    continue

                product_url = f"https://www.amazon.com{href}" if href.startswith("/") else href

                if current_url and len(current_url) > 25 and current_url in product_url:
                    continue

                try:
                    card_text = card.evaluate("el => el.innerText") or ""
                except Exception:
                    card_text = ""

                if not is_similar(product_name, card_text):
                    continue

                # Qiymət çıxarılışı
                price_val = None
                price_elem = card.query_selector("span.a-price, .a-price-whole")
                if price_elem:
                    try:
                        raw_price = price_elem.evaluate("el => el.innerText").replace("\n", ".").replace("$", "").replace(",", "").strip()
                        extracted = re.findall(r"\d+\.?\d*", raw_price)
                        if extracted:
                            price_val = float(extracted[0])
                    except Exception:
                        pass

                img_elem = card.query_selector("img.s-image")
                image_url = img_elem.get_attribute("src") if img_elem else ""

                if price_val and product_url:
                    results.append({
                        "platform_name": "Amazon",
                        "competitor_url": product_url,
                        "price": price_val,
                        "currency": "USD",
                        "image_url": image_url,
                        "comments": []
                    })
                    break

            if not results:
                print("[PLAYWRIGHT] Amazon-da məhsul və ya qiymət tapıla bilmədi.")

        except Exception as e:
            print(f"[PLAYWRIGHT XƏTASI Amazon]: {e}")
        finally:
            browser.close()

    return results


def scrape_ebay(product_name: str, current_url: str = None):
    search_keyword = universal_clean_query(product_name) or product_name
    encoded_query = urllib.parse.quote(search_keyword)
    search_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}"
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = context.new_page()

        try:
            print(f"[PLAYWRIGHT] eBay-də axtarış edilir: {search_keyword}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Sırf real axtarış siyahısının elementlərini seçirik
            product_cards = page.query_selector_all("ul.srp-results > li.s-item")

            for card in product_cards:
                # Reklam/Banner başlığı olan s-item-ləri atlayırıq
                title_elem = card.query_selector(".s-item__title")
                if not title_elem:
                    continue

                title_text = title_elem.evaluate("el => el.innerText") or ""
                if not title_text or "shop on ebay" in title_text.lower():
                    continue

                if not is_similar(product_name, title_text):
                    continue

                a_tag = card.query_selector("a.s-item__link")
                if not a_tag:
                    continue

                href = a_tag.get_attribute("href") or ""
                if not href or "itm/123456" in href:
                    continue

                product_url = href.split("?")[0]

                if current_url and len(current_url) > 25 and current_url in product_url:
                    continue

                price_val = None
                price_elem = card.query_selector(".s-item__price")
                if price_elem:
                    try:
                        raw_price = price_elem.evaluate("el => el.innerText").replace(",", "").strip()
                        extracted = re.findall(r"\d+\.?\d*", raw_price)
                        if extracted:
                            price_val = float(extracted[0])
                    except Exception:
                        pass

                img_elem = card.query_selector("img")
                image_url = img_elem.get_attribute("src") if img_elem else ""

                if price_val and product_url:
                    results.append({
                        "platform_name": "eBay",
                        "competitor_url": product_url,
                        "price": price_val,
                        "currency": "USD",
                        "image_url": image_url,
                        "comments": []
                    })
                    break  # İlk düzgün məhsulu tapdıqda dövrədən çıxırıq

            if not results:
                print("[PLAYWRIGHT] eBay-də məhsul və ya qiymət tapıla bilmədi.")

        except Exception as e:
            print(f"[PLAYWRIGHT XƏTASI eBay]: {e}")
        finally:
            browser.close()

    return results


def scrape_aliexpress(product_name: str, current_url: str = None):
    search_keyword = universal_clean_query(product_name) or product_name
    encoded_query = urllib.parse.quote(search_keyword)
    search_url = f"https://www.aliexpress.com/w/wholesale-{encoded_query}.html"
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1366, "height": 768}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            print(f"[PLAYWRIGHT] AliExpress-də axtarış edilir: {search_keyword}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
            page.wait_for_timeout(3000)

            page.evaluate("window.scrollTo(0, 800)")
            page.wait_for_timeout(1500)

            # AliExpress axtarış kartı linkləri
            items = page.query_selector_all("a[href*='/item/']")

            for a_tag in items:
                href = a_tag.get_attribute("href") or ""
                if not href:
                    continue

                product_url = f"https:{href}" if href.startswith("//") else href
                product_url = product_url.split("?")[0]

                if current_url and len(current_url) > 25 and current_url in product_url:
                    continue

                try:
                    card_text = a_tag.evaluate("el => el.innerText") or ""
                    # Valideyn kart mətnini yoxlayırıq
                    if not card_text or len(card_text.strip()) < 5:
                        parent = a_tag.query_selector("xpath=..")
                        if parent:
                            card_text = parent.evaluate("el => el.innerText") or ""
                except Exception:
                    card_text = ""

                if not card_text or not is_similar(product_name, card_text):
                    continue

                price_val = None
                price_match = re.search(r"(?:[\$\Custom₼AZN]|US\s*\$)\s*(\d+[\.,]\d{2}|\d+)", card_text)
                if price_match:
                    price_val = float(price_match.group(1).replace(",", "."))

                img_elem = a_tag.query_selector("img")
                image_url = ""
                if img_elem:
                    src = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""
                    image_url = f"https:{src}" if src.startswith("//") else src

                if price_val and product_url:
                    results.append({
                        "platform_name": "AliExpress",
                        "competitor_url": product_url,
                        "price": price_val,
                        "currency": "USD",
                        "image_url": image_url,
                        "comments": []
                    })
                    break

            if not results:
                print("[PLAYWRIGHT] AliExpress-də məhsul və ya qiymət tapıla bilmədi.")

        except Exception as e:
            print(f"[PLAYWRIGHT XƏTASI AliExpress]: {e}")
        finally:
            browser.close()

    return results