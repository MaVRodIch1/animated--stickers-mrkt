#!/usr/bin/env python3
"""
MRKT Price Parser — fetches gift floor prices from the MRKT Contest API.

API: https://contest.tgmrkt.io
Auth: X-CONTEST-KEY header (required)

The Contest API does not return 24h change, so we compute it ourselves by
storing a rolling price history in mrkt_price_history.json and comparing
the current floor to the floor ~24h ago.

Usage:
    # Fetch prices (needs MRKT_CONTEST_KEY in .env):
    python mrkt_parser.py

    # Show raw API response:
    python mrkt_parser.py --raw

Setup:
    1. Add to .env:
       MRKT_CONTEST_KEY=your_contest_api_key
    2. pip install aiohttp
"""

import os
import re
import json
import time
import asyncio
import logging

import aiohttp

log = logging.getLogger("mrkt-parser")

# ─── Load .env ────────────────────────────────────────────────────
def _load_dotenv():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()

# Primary new key name. Fall back to legacy MRKT_ACCESS_TOKEN for backward compat.
MRKT_CONTEST_KEY = os.environ.get("MRKT_CONTEST_KEY") or os.environ.get("MRKT_ACCESS_TOKEN", "")

MRKT_API = "https://contest.tgmrkt.io"
MRKT_ENDPOINT = "/contest/v1/gifts-collections"

NANO_TON = 1_000_000_000  # 1 TON = 10^9 nanoTON

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mrkt_price_history.json")
HISTORY_WINDOW_SEC = 26 * 3600  # keep last 26h of samples
CHANGE_24H_TARGET_SEC = 24 * 3600


# ─── API Headers ─────────────────────────────────────────────────

def _headers(key=None):
    k = key or MRKT_CONTEST_KEY
    return {
        "X-CONTEST-KEY": k,
        "Accept": "application/json",
    }


# ─── Price history (for 24h change calculation) ──────────────────

def _load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Could not read price history: {e}")
        return {}


def _save_history(hist):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(hist, f)
    except Exception as e:
        log.warning(f"Could not save price history: {e}")


def _compute_change_24h(slug, current_price, history, now_ts):
    """Return % change vs closest sample to (now - 24h), or 0.0 if no history."""
    samples = history.get(slug) or []
    if not samples:
        return 0.0

    target_ts = now_ts - CHANGE_24H_TARGET_SEC
    best = None
    best_dt = None
    for sample in samples:
        dt = abs(sample["ts"] - target_ts)
        if best_dt is None or dt < best_dt:
            best = sample
            best_dt = dt

    if not best or best["price"] <= 0:
        return 0.0

    # Require the sample to be at least ~1h away from "now" so that we don't
    # compare current vs itself during the very first cycles.
    if now_ts - best["ts"] < 3600:
        return 0.0

    return round(((current_price - best["price"]) / best["price"]) * 100, 2)


def _update_history(history, slug, price, now_ts):
    samples = history.setdefault(slug, [])
    samples.append({"ts": now_ts, "price": price})
    # Drop samples older than HISTORY_WINDOW_SEC
    cutoff = now_ts - HISTORY_WINDOW_SEC
    history[slug] = [s for s in samples if s["ts"] >= cutoff]


# ─── Fetch floor prices ─────────────────────────────────────────

async def fetch_mrkt_prices(key=None):
    """Fetch gift floor prices from the MRKT Contest API.

    Returns list of dicts compatible with sticker_pack.py:
    [{"slug": "plushpepe", "floor_price": 7550.0, "change_24h": 0.0, "supply": 0}, ...]
    """
    k = key or MRKT_CONTEST_KEY
    if not k:
        log.error("MRKT_CONTEST_KEY not set. Add it to .env.")
        return []

    url = f"{MRKT_API}{MRKT_ENDPOINT}"

    async with aiohttp.ClientSession(headers=_headers(k)) as session:
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 401:
                    log.error("Contest API returned 401 — check MRKT_CONTEST_KEY")
                    return []
                if resp.status != 200:
                    log.error(f"Contest API returned {resp.status}")
                    return []
                data = await resp.json()
        except Exception as e:
            log.error(f"API request failed: {e}")
            return []

    items = _unwrap(data)
    if not items:
        log.warning("No collections in API response")
        return []

    log.info(f"MRKT Contest API: {len(items)} collections")

    history = _load_history()
    now_ts = int(time.time())

    result = []
    for item in items:
        title = item.get("title") or ""
        raw_name = item.get("name") or ""
        slug = _name_to_slug(title) or _name_to_slug(raw_name)
        if not slug:
            continue

        floor_raw = item.get("floorPrice")
        if floor_raw in (None, "", 0, "0"):
            continue
        try:
            floor_nano = int(floor_raw)
        except (TypeError, ValueError):
            continue

        if floor_nano <= 0:
            continue

        floor = floor_nano / NANO_TON

        change_24h = _compute_change_24h(slug, floor, history, now_ts)
        _update_history(history, slug, floor, now_ts)

        result.append({
            "slug": slug,
            "floor_price": floor,
            "change_24h": change_24h,
            "supply": 0,
            "_source": "mrkt",
        })

    _save_history(history)

    return sorted(result, key=lambda c: -(c["floor_price"]))


def get_upgraded_prices(prices):
    """From a list of prices, keep the MOST EXPENSIVE entry per slug.

    Upgraded versions of gifts are more expensive than regular ones.
    (Kept for backward compatibility; the Contest API usually returns
    one entry per slug.)
    """
    best = {}
    for p in prices:
        slug = p["slug"]
        if slug not in best or p["floor_price"] > best[slug]["floor_price"]:
            best[slug] = p
    return best


async def fetch_raw(key=None):
    """Fetch and display raw response from the Contest API."""
    k = key or MRKT_CONTEST_KEY
    if not k:
        print("ERROR: Set MRKT_CONTEST_KEY in .env")
        return

    url = f"{MRKT_API}{MRKT_ENDPOINT}"
    async with aiohttp.ClientSession(headers=_headers(k)) as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                status = resp.status
                text = await resp.text()
        except Exception as e:
            print(f"ERROR: {e}")
            return

    print(f"GET {url} → {status} ({len(text)} bytes)")
    if status != 200:
        print(text[:500])
        return

    try:
        data = json.loads(text)
        items = _unwrap(data)
        if items:
            print(f"Items: {len(items)}")
            print(f"First item keys: {list(items[0].keys())}")
            print(f"Sample: {json.dumps(items[0], indent=2, ensure_ascii=False)}")
    except json.JSONDecodeError:
        print(text[:500])


# ─── Helpers ─────────────────────────────────────────────────────

def _unwrap(data):
    """Unwrap API response to get the items list.

    The Contest API returns a plain array, but we also handle dict-wrapped
    responses for safety.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "items", "gifts", "collections", "models", "result"):
            if isinstance(data.get(key), list):
                return data[key]
        if "total" in data and isinstance(data.get("items"), list):
            return data["items"]
    return []


def _name_to_slug(name):
    """Convert collection name to slug: 'Plush Pepe' -> 'plushpepe'."""
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())


# ─── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG if "--verbose" in sys.argv else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    if "--raw" in sys.argv:
        print("MRKT Contest API — raw response\n")
        asyncio.run(fetch_raw())

    else:
        async def main():
            prices = await fetch_mrkt_prices()
            if prices:
                print(json.dumps(prices, indent=2, ensure_ascii=False))
                print(f"\nTotal: {len(prices)} collections")
            else:
                print("No data. Check MRKT_CONTEST_KEY in .env")

        asyncio.run(main())
