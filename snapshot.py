import asyncio
import csv
import json
import os
import re
from datetime import datetime, timezone, timedelta

from playwright.async_api import async_playwright

SYMBOL_URL = "https://www.tradingview.com/symbols/XAUUSD/"
CSV_FILE = "prices.csv"


async def fetch_price() -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        try:
            await page.goto(SYMBOL_URL, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(4_000)

            html = await page.content()

            # --- Strategy 1: JSON-LD structured data (most stable) ---
            # TradingView embeds: {"@type":"Offer","price":"4322.71","priceCurrency":"USD"}
            for script in re.findall(
                r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
                html,
                re.S,
            ):
                try:
                    data = json.loads(script)
                    offers = data.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0]
                    price = offers.get("price")
                    if price:
                        return str(price)
                except Exception:
                    pass

            # --- Strategy 2: regex fallback on raw HTML ---
            m = re.search(r'"price"\s*:\s*"([\d.]+)"', html)
            if m:
                return m.group(1)

        finally:
            await browser.close()

    return None


def append_row(price: str | None) -> None:
    tz_gmt2 = timezone(timedelta(hours=2))
    now = datetime.now(tz_gmt2).strftime("%Y-%m-%dT%H:%M:%S+02:00")
    needs_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if needs_header:
            writer.writerow(["timestamp_utc", "xauusd"])
        writer.writerow([now, price if price else "N/A"])
    print(f"{now}  XAUUSD = {price or 'N/A'}")


if __name__ == "__main__":
    price = asyncio.run(fetch_price())
    append_row(price)
