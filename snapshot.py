import asyncio
import csv
import os
import re
from datetime import datetime, timezone

from playwright.async_api import async_playwright

CHART_URL = "https://www.tradingview.com/chart/SGmz3Icc/"
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
            await page.goto(CHART_URL, wait_until="domcontentloaded", timeout=60_000)

            # Dismiss cookie/consent banner if present
            for label in ("Accept all", "Accept", "I agree"):
                try:
                    await page.get_by_role("button", name=label).click(timeout=2_000)
                    break
                except Exception:
                    pass

            # Give the chart JS time to render and update the <title>
            await page.wait_for_timeout(6_000)

            # --- Strategy 1: page <title> ---
            # TradingView sets the title to e.g. "2387.50 ▲ XAUUSD — TradingView"
            title = await page.title()
            m = re.match(r"^([\d,]+\.?\d*)", title)
            if m:
                return m.group(1).replace(",", "")

            # --- Strategy 2: DOM selectors (class names change with TV deploys) ---
            for selector in (
                '[class*="lastPrice"]',
                '[class*="last-"]',
                '[data-field="last_price"]',
                '[class*="priceWrapper"] span',
            ):
                try:
                    el = page.locator(selector).first
                    text = await el.inner_text(timeout=3_000)
                    if text and re.search(r"[\d.]+", text):
                        return text.strip().replace(",", "")
                except Exception:
                    pass

        finally:
            await browser.close()

    return None


def append_row(price: str | None) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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
