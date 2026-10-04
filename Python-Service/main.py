import os
import sys
from dotenv import load_dotenv
from fastapi import Body, FastAPI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import scraper

load_dotenv(dotenv_path="../.env")

app = FastAPI(title="Shopping Advisor - Python Search Engine")


@app.get("/")
def read_root():
    return {"status": "Python Service Running"}


@app.post("/search")
def search_competitors(body: dict | None = Body(default=None)):
    if body is None:
        body = {}
    all_competitors = []

    print(f"[DEBUG LOG] Python-a Gələn Raw Body: {body}")

    query_text = (
        body.get("product_name")
        or body.get("productName")
        or body.get("name")
        or body.get("query")
        or body.get("keyword")
        or body.get("text")
        or ""
    )

    if not query_text or not str(query_text).strip():
        print(
            "[WARNING] Axtarış üçün boş və ya uyğunsuz JSON sorğusu qəbul edildi."
        )
        return all_competitors

    query_text = str(query_text).strip()
    cleaned_query = scraper.universal_clean_query(query_text) or query_text
    
    # İstifadəsində olunan canlı səhifənin URL-i
    current_url = str(body.get("current_url") or body.get("url") or body.get("product_url") or "").strip()

    print(
        f"[INFO LOG] Orijinal Sorğu: '{query_text}' | Təmizlənmiş Sorğu: '{cleaned_query}' | Current URL: '{current_url}'"
    )

    # 1. Trendyol axtarışı (current_url parametrilə)
    try:
        trendyol_results = scraper.search_google_and_scrape(cleaned_query, current_url=current_url)
        if trendyol_results:
            all_competitors.extend(trendyol_results)
    except Exception as e:
        print(f"[ERROR] Trendyol skreyp xətası: {e}")

    # 2. Umico axtarışı
    try:
        umico_results = scraper.scrape_umico(cleaned_query)
        if umico_results:
            all_competitors.extend(umico_results)
    except Exception as e:
        print(f"[ERROR] Umico skreyp xətası: {e}")

    # 3. Alinino axtarışı
    try:
        alinino_results = scraper.scrape_alinino(cleaned_query)
        if alinino_results:
            all_competitors.extend(alinino_results)
    except Exception as e:
        print(f"[ERROR] Alinino skreyp xətası: {e}")

    # Amazon axtarışı
    try:
        amazon_results = scraper.scrape_amazon(cleaned_query, current_url=current_url)
        if amazon_results:
            all_competitors.extend(amazon_results)
    except Exception as e:
        print(f"[ERROR] Amazon skreyp xətası: {e}")
    # 4. eBay axtarışı
    try:
        ebay_results = scraper.scrape_ebay(cleaned_query, current_url=current_url)
        if ebay_results:
            all_competitors.extend(ebay_results)
    except Exception as e:
        print(f"[ERROR] eBay skreyp xətası: {e}")

    # 5. AliExpress axtarışı
    try:
        aliexpress_results = scraper.scrape_aliexpress(cleaned_query, current_url=current_url)
        if aliexpress_results:
            all_competitors.extend(aliexpress_results)
    except Exception as e:
        print(f"[ERROR] AliExpress skreyp xətası: {e}")

    # Debug Loglar
    print(
        "[DEBUG] Trendyol Nəticələri:"
        f" {trendyol_results if 'trendyol_results' in locals() else 'Xəta'}"
    )
    print(
        "[DEBUG] Umico Nəticələri:"
        f" {umico_results if 'umico_results' in locals() else 'Xəta'}"
    )
    print(f"[DEBUG] Ümumi Toplanan Bütün Nəticələr: {all_competitors}")

    return all_competitors