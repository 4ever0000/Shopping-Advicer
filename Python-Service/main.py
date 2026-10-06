import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Body, FastAPI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import scraper

load_dotenv(dotenv_path="../.env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await scraper.shutdown()  # brauzeri düzgün bağla


app = FastAPI(title="Shopping Advisor - Python Search Engine", lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"status": "Python Service Running"}


@app.post("/search")
async def search_competitors(body: dict | None = Body(default=None)):
    body = body or {}
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
        print("[WARNING] Axtarış üçün boş və ya uyğunsuz JSON sorğusu qəbul edildi.")
        return []

    current_url = str(
        body.get("current_url") or body.get("url") or body.get("product_url") or ""
    ).strip()

    results = await scraper.search_all(str(query_text).strip(), current_url)
    print(f"[DEBUG] Ümumi nəticə sayı: {len(results)} -> {results}")
    return results