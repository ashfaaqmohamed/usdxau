import csv
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

CSV_FILE = "prices.csv"
# Free public SwissQuote feed — no API key required
SQ_URL = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD"


def fetch_price() -> str | None:
    req = urllib.request.Request(SQ_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    prices = data[0]["spreadProfilePrices"][0]
    mid = (prices["bid"] + prices["ask"]) / 2
    return str(round(mid, 3))


def append_row(price: str | None) -> None:
    tz_gmt2 = timezone(timedelta(hours=2))
    now = datetime.now(tz_gmt2).strftime("%Y-%m-%dT%H:%M:%S+02:00")
    needs_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if needs_header:
            writer.writerow(["timestamp_gmt2", "xauusd"])
        writer.writerow([now, price if price else "N/A"])
    print(f"{now}  XAUUSD = {price or 'N/A'}")


if __name__ == "__main__":
    price = fetch_price()
    append_row(price)
