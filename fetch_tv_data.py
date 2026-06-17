"""
Closing Price System — TradingView data fetcher
================================================
Pulls live + historical candles for gold and silver from TradingView
(forex.com feed, same as the webinar) across all the timeframes the
system uses, and saves them as CSV files into ./data/

Uses the unofficial tvDatafeed library. NOTE: this is not an official
TradingView API — it can stop working if TradingView changes things,
and sits outside their terms of service. Use at your own discretion.

SETUP (one time):
    pip install --upgrade --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git

RUN:
    python fetch_tv_data.py
"""

import sys
import time
from pathlib import Path

from tvDatafeed import TvDatafeed, Interval

# Retry settings — anonymous tvDatafeed drops its websocket intermittently,
# so each fetch is retried with a fresh connection before giving up.
MAX_ATTEMPTS = 4
RETRY_SLEEP = 4  # seconds between attempts

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SYMBOLS = [
    ("XAUUSD", "OANDA"),   # gold — OANDA provides tick volume; FOREXCOM does not
    ("XAGUSD", "OANDA"),   # silver
]

# Timeframe -> (tvDatafeed interval, number of candles to fetch)
TIMEFRAMES = {
    "monthly": (Interval.in_monthly, 120),   # ~10 years
    "weekly":  (Interval.in_weekly,  260),   # ~5 years
    "daily":   (Interval.in_daily,   500),   # ~2 years
    "4h":      (Interval.in_4_hour,  1500),  # ~1 year
    "1h":      (Interval.in_1_hour,  1500),  # ~3 months
}

OUT_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------
def connect() -> TvDatafeed:
    return TvDatafeed()


def main() -> None:
    tv = connect()
    OUT_DIR.mkdir(exist_ok=True)

    failures = []  # (symbol, tf) pairs that never returned data

    for symbol, exchange in SYMBOLS:
        for tf_name, (interval, n_bars) in TIMEFRAMES.items():
            print(f"Fetching {symbol} {tf_name} ({n_bars} bars)...", end=" ", flush=True)
            df = None
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    df = tv.get_hist(
                        symbol=symbol,
                        exchange=exchange,
                        interval=interval,
                        n_bars=n_bars,
                    )
                except Exception as exc:  # noqa: BLE001
                    print(f"[try {attempt} error: {exc}]", end=" ", flush=True)
                    df = None

                if df is not None and not df.empty:
                    break  # success

                # Failed this attempt — reconnect and retry (the websocket
                # is usually dead at this point), unless we're out of tries.
                if attempt < MAX_ATTEMPTS:
                    print(f"[try {attempt} no data, reconnecting]", end=" ", flush=True)
                    time.sleep(RETRY_SLEEP)
                    try:
                        tv = connect()
                    except Exception as exc:  # noqa: BLE001
                        print(f"[reconnect failed: {exc}]", end=" ", flush=True)

            if df is None or df.empty:
                # IMPORTANT: do not overwrite the existing CSV with nothing —
                # but make the failure LOUD so stale data is never silent.
                print(f"FAILED after {MAX_ATTEMPTS} attempts -> keeping previous "
                      f"{symbol}_{tf_name}.csv (NOW STALE)")
                failures.append((symbol, tf_name))
                continue

            out = OUT_DIR / f"{symbol}_{tf_name}.csv"
            df.to_csv(out)
            last = df.iloc[-1]
            print(f"OK -> {out.name}  (last close: {last['close']:.2f})")

    print("\nDone. CSVs are in:", OUT_DIR)
    if failures:
        flist = ", ".join(f"{s}_{tf}" for s, tf in failures)
        print(f"⚠ STALE FILES (fetch failed, old data left in place): {flist}")
        print("  Re-run the script; if it persists, set TV_USERNAME/TV_PASSWORD for a stabler feed.")
        sys.exit(1)  # non-zero so launchd/cron surfaces the failure
    print("All timeframes refreshed successfully.")
    print("Drop back into the Claude session and I can analyse them.")


if __name__ == "__main__":
    main()
