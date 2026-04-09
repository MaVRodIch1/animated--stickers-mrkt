#!/usr/bin/env python3
"""
Quick test: create/update ONLY the unupgraded gems pack.
Skips the 3 main packs entirely.

Usage: python test_unupgraded.py
"""
import os
import sys
import asyncio
import logging

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sticker_pack import (
    load_dotenv, load_gift_images, fetch_collections, fetch_ton_rate,
    sync_unupgraded_pack, load_state, save_state,
    UNUPGRADED_SLUGS, BOT_TOKEN, OWNER_ID, ANIMATED,
)
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("test-unupgraded")


async def main():
    bot = Bot(token=BOT_TOKEN)
    me = await bot.get_me()
    log.info(f"Bot: @{me.username}")

    suffix = f"_by_{me.username}"
    pack_name = f"unupgradedgems{suffix}"

    print(f"\n  Testing ONLY unupgraded pack:")
    print(f"  Pack: t.me/addstickers/{pack_name}")
    print(f"  Gifts: {len(UNUPGRADED_SLUGS)}")
    print(f"  Format: {'WebM' if ANIMATED else 'WebP'}\n")

    await load_gift_images(bot)

    state = load_state()

    ton_usd = await fetch_ton_rate()
    collections, expensive_map, exclude_set = await fetch_collections()

    if not collections:
        log.error("No collections from MRKT API (token expired?)")
        await bot.session.close()
        return

    log.info(f"Fetched {len(collections)} collections, TON=${ton_usd:.2f}")

    # Build unupgraded list
    unupgraded_cols = []
    for slug in UNUPGRADED_SLUGS:
        col = expensive_map.get(slug.lower())
        if col:
            unupgraded_cols.append(col)
            log.info(f"  {slug}: {col['floor_price']:.2f} TON")
        else:
            log.warning(f"  {slug}: NOT FOUND in MRKT")

    if unupgraded_cols:
        log.info(f"\nSyncing {len(unupgraded_cols)} unupgraded stickers...")
        await sync_unupgraded_pack(bot, pack_name, unupgraded_cols, ton_usd, state)
        log.info(f"\nDone! Check: https://t.me/addstickers/{pack_name}")
    else:
        log.error("No unupgraded gifts found")

    await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
