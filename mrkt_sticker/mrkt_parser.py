#!/usr/bin/env python3
"""
MRKT Price Parser — fetches gift floor prices from MRKT marketplace API.

API: https://api.tgmrkt.io
Auth: access_token from MRKT mini app session

Usage:
    # Fetch prices (needs MRKT_ACCESS_TOKEN in .env):
    python mrkt_parser.py

    # Get access token via Telegram login:
    python mrkt_parser.py --login

    # Show raw API response:
    python mrkt_parser.py --raw

Setup:
    1. Add to .env:
       TELEGRAM_API_ID=your_api_id       (from https://my.telegram.org/apps)
       TELEGRAM_API_HASH=your_api_hash
       MRKT_ACCESS_TOKEN=your_token       (get via --login or browser DevTools)
    2. pip install telethon aiohttp
"""

import os
import re
import json
import asyncio
import logging
from urllib.parse import urlparse, parse_qs, unquote

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

API_ID = int(os.environ.get("TELEGRAM_API_ID", "0"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mrkt_session")

MRKT_API = "https://api.tgmrkt.io"
MRKT_ORIGIN = "https://cdn.tgmrkt.io"
MRKT_ACCESS_TOKEN = os.environ.get("MRKT_ACCESS_TOKEN", "")

NANO_TON = 1_000_000_000  # 1 TON = 10^9 nanoTON


# ─── API Headers ─────────────────────────────────────────────────

def _headers(token=None):
    t = token or MRKT_ACCESS_TOKEN
    return {
        "Authorization": t,
        "Content-Type": "application/json",
        "Origin": MRKT_ORIGIN,
        "Referer": f"{MRKT_ORIGIN}/",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    }


# ─── Fetch floor prices ─────────────────────────────────────────

async def fetch_mrkt_prices(token=None):
    """Fetch gift floor prices from MRKT API.

    Returns list of dicts compatible with sticker_pack.py:
    [{"slug": "plushpepe", "floor_price": 7550.0, "change_24h": 0.0, "supply": 0}, ...]
    """
    t = token or MRKT_ACCESS_TOKEN
    if not t:
        log.error("MRKT_ACCESS_TOKEN not set. Add to .env or run: python mrkt_parser.py --login")
        return []

    async with aiohttp.ClientSession(headers=_headers(t)) as session:
        # GET /api/v1/gifts/collections — main endpoint with floor prices
        try:
            async with session.get(
                f"{MRKT_API}/api/v1/gifts/collections",
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    log.error(f"API returned {resp.status}")
                    return []
                data = await resp.json()
        except Exception as e:
            log.error(f"API request failed: {e}")
            return []

    items = _unwrap(data)
    if not items:
        log.warning("No collections in API response")
        return []

    log.info(f"MRKT API: {len(items)} collections")

    # Some collections appear twice (e.g. regular + upgraded khabibspapakha).
    # Keep ALL entries — deduplicate later by use case.
    result = []
    for item in items:
        title = item.get("title") or ""
        slug = _name_to_slug(title)
        if not slug:
            continue

        if item.get("isHidden"):
            continue

        floor_nano = item.get("floorPriceNanoTons") or 0
        floor = floor_nano / NANO_TON if floor_nano else 0

        if floor <= 0:
            continue

        prev_nano = item.get("previousDayFloorPriceNanoTons") or 0
        if prev_nano and prev_nano > 0:
            change_24h = round(((floor_nano - prev_nano) / prev_nano) * 100, 2)
        else:
            change_24h = 0.0

        result.append({
            "slug": slug,
            "floor_price": floor,
            "change_24h": change_24h,
            "supply": 0,
            "_source": "mrkt",
        })

    return sorted(result, key=lambda c: -(c["floor_price"]))


def get_upgraded_prices(prices):
    """From a list of prices, keep the MOST EXPENSIVE entry per slug.

    Upgraded versions of gifts are more expensive than regular ones.
    """
    best = {}
    for p in prices:
        slug = p["slug"]
        if slug not in best or p["floor_price"] > best[slug]["floor_price"]:
            best[slug] = p
    return best


async def fetch_all_endpoints(token=None):
    """Fetch and display raw data from all known MRKT API endpoints."""
    t = token or MRKT_ACCESS_TOKEN
    if not t:
        print("ERROR: Set MRKT_ACCESS_TOKEN in .env")
        return

    endpoints = [
        ("POST", "/api/v1/gifts/models", {}),
        ("POST", "/api/v1/gifts/models", {"limit": 500}),
        ("GET", "/api/v1/sticker-sets/collections", None),
        ("GET", "/api/v1/gifts/collections", None),
        ("GET", "/api/v1/collections", None),
        ("GET", "/api/v1/gifts/floor", None),
        ("GET", "/api/v1/market/floor", None),
        ("GET", "/api/v1/gifts", None),
    ]

    async with aiohttp.ClientSession(headers=_headers(t)) as session:
        for method, path, body in endpoints:
            url = f"{MRKT_API}{path}"
            try:
                if method == "POST":
                    async with session.post(url, json=body,
                                            timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        status = resp.status
                        text = await resp.text()
                elif method == "GET":
                    async with session.get(url,
                                           timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        status = resp.status
                        text = await resp.text()

                size = len(text)
                print(f"\n{'='*60}")
                print(f"{method} {path} → {status} ({size} bytes)")

                if status == 200:
                    try:
                        data = json.loads(text)
                        items = _unwrap(data)
                        if items:
                            print(f"Items: {len(items)}")
                            print(f"First item keys: {list(items[0].keys())}")
                            print(f"Sample: {json.dumps(items[0], indent=2, ensure_ascii=False)[:500]}")
                        elif isinstance(data, dict):
                            print(f"Keys: {list(data.keys())}")
                            print(f"Preview: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                        else:
                            print(f"Type: {type(data).__name__}")
                            print(f"Preview: {text[:300]}")
                    except json.JSONDecodeError:
                        print(f"Not JSON: {text[:200]}")
                else:
                    print(f"Body: {text[:200]}")

            except Exception as e:
                print(f"\n{method} {path} → ERROR: {e}")


# ─── Login via Telegram ──────────────────────────────────────────

async def login():
    """Get MRKT access token by opening WebApp via Telegram."""
    if not API_ID or not API_HASH:
        print("ERROR: Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")
        print("Get them at https://my.telegram.org/apps")
        return

    from telethon import TelegramClient, functions, types

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.start()

    try:
        entity = await client.get_entity("mrkt")
        print(f"Bot: {entity.first_name}")

        # Get WebView URL with auth data
        result = await client(functions.messages.RequestWebViewRequest(
            peer=entity,
            bot=entity,
            platform='android',
            url='https://mrkt.tg'
        ))

        web_url = result.url
        print(f"\nWebApp URL obtained")

        # Extract tgWebAppData from URL
        fragment = urlparse(web_url).fragment
        params = parse_qs(fragment)
        tg_data = params.get("tgWebAppData", [""])[0]

        if not tg_data:
            print("Could not extract tgWebAppData")
            print(f"Full URL: {web_url}")
            return

        print(f"tgWebAppData extracted")

        # Use tgWebAppData to authenticate with MRKT API
        async with aiohttp.ClientSession() as session:
            # Try auth endpoint
            auth_endpoints = [
                "/api/v1/auth/telegram",
                "/api/v1/auth/webapp",
                "/api/v1/auth",
                "/api/v1/users/auth",
                "/api/v1/login",
            ]

            auth_headers = {
                "Content-Type": "application/json",
                "Origin": MRKT_ORIGIN,
                "Referer": f"{MRKT_ORIGIN}/",
                "Accept": "application/json",
            }

            for endpoint in auth_endpoints:
                url = f"{MRKT_API}{endpoint}"

                # Try different auth body formats
                bodies = [
                    {"initData": tg_data},
                    {"webAppData": tg_data},
                    {"data": tg_data},
                    {"tgWebAppData": tg_data},
                    {"auth": tg_data},
                ]

                for body in bodies:
                    try:
                        async with session.post(url, json=body, headers=auth_headers,
                                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                # Look for access token in response
                                token = (data.get("access_token") or
                                         data.get("accessToken") or
                                         data.get("token") or
                                         data.get("session") or "")

                                if token:
                                    print(f"\n{'='*60}")
                                    print(f"SUCCESS! Access token obtained via {endpoint}")
                                    print(f"Token: {token}")
                                    print(f"\nAdd to .env:")
                                    print(f"MRKT_ACCESS_TOKEN={token}")
                                    print(f"{'='*60}")
                                    return
                                else:
                                    log.debug(f"{endpoint}: 200 but no token in: {list(data.keys())}")
                            elif resp.status != 404:
                                log.debug(f"{endpoint}: {resp.status}")
                    except Exception:
                        continue

            # If auto-auth failed, show manual instructions
            print(f"\n{'='*60}")
            print("Auto-auth didn't find the right endpoint.")
            print("\nGet token manually:")
            print("1. Open @mrkt in Telegram → Open App")
            print("2. In browser: F12 → Network → any request to api.tgmrkt.io")
            print("3. Copy the 'authorization' header value")
            print("4. Add to .env: MRKT_ACCESS_TOKEN=your-token-here")
            print(f"{'='*60}")

    finally:
        await client.disconnect()


# ─── Helpers ─────────────────────────────────────────────────────

def _unwrap(data):
    """Unwrap API response to get the items list."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "items", "gifts", "collections", "models", "result"):
            if isinstance(data.get(key), list):
                return data[key]
        # Maybe the response IS the list wrapped in pagination
        if "total" in data and isinstance(data.get("items"), list):
            return data["items"]
    return []


def _name_to_slug(name):
    """Convert collection name to slug: 'Plush Pepe' -> 'plushpepe'."""
    if not name:
        return ""
    # Remove special chars, keep only alphanumeric
    return re.sub(r'[^a-z0-9]', '', name.lower())


# ─── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG if "--verbose" in sys.argv else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    if "--login" in sys.argv:
        print("MRKT Login — getting access token via Telegram\n")
        asyncio.run(login())

    elif "--raw" in sys.argv:
        print("MRKT Raw API — testing all endpoints\n")
        asyncio.run(fetch_all_endpoints())

    else:
        async def main():
            prices = await fetch_mrkt_prices()
            if prices:
                print(json.dumps(prices, indent=2, ensure_ascii=False))
                print(f"\nTotal: {len(prices)} collections")
            else:
                print("No data. Check MRKT_ACCESS_TOKEN in .env")
                print("Run: python mrkt_parser.py --login")

        asyncio.run(main())
