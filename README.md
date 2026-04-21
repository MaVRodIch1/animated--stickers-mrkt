# MRKT Animated Stickers

Auto-updating Telegram **animated** sticker pack system for the **MRKT** gift marketplace.
Stickers display live floor prices (USD, TON, Stars), 24h price changes, supply, and gift thumbnails.
Packs refresh every 60 seconds.

Система автообновляемых **анимированных** Telegram-стикерпаков для маркетплейса подарков **MRKT**.
Стикеры отображают актуальные floor-цены (USD, TON, Stars), изменение за 24ч, supply и картинку подарка.
Обновление каждые 60 секунд.

---

## Table of Contents / Оглавление

1. [What you get](#what-you-get--что-вы-получаете)
2. [Quick start](#quick-start--быстрый-старт)
3. [Getting API keys](#getting-api-keys--получение-api-ключей)
4. [Running the system](#running-the-system--запуск-системы)
5. [Pack structure](#pack-structure--структура-паков)
6. [Managing unupgraded gifts](#managing-unupgraded-gifts--управление-неулучшенными-подарками)
7. [Adding custom gift images](#adding-custom-gift-images--добавление-кастомных-картинок)
8. [Maintenance scenarios](#maintenance-scenarios--типичные-сценарии-обслуживания)
9. [Troubleshooting](#troubleshooting--решение-проблем)
10. [Project structure](#project-structure--структура-проекта)
11. [Configuration](#configuration--конфигурация)
12. [External APIs](#external-apis--внешние-api)

---

## What you get / Что вы получаете

- **3 main sticker packs** (50 stickers each = 150 total) — top MRKT collections by floor price
- **1 unupgraded pack** (up to 10 stickers) — gifts that haven't been upgraded yet (custom curated list)
- **Animated WebM stickers** (3 sec, 30 fps) with 7 distinct animation effects
- **Static WebP fallback** if ffmpeg is not installed
- **Auto-refresh every 60 seconds** — prices, 24h change, supply
- **24h change calculation** from local price history (no need for extra API)
- **Stale sticker cleanup** — automatically removes stickers for gifts no longer in scope
- **Quick test mode** — `test_unupgraded.py` updates only the unupgraded pack

---

## Quick start / Быстрый старт

```bash
# 1. Clone & enter project
cd mrkt_sticker

# 2. Install Python deps
pip install -r requirements.txt

# 3. Install ffmpeg (required for animated stickers)
# Windows: winget install ffmpeg
# Ubuntu:  sudo apt install ffmpeg
# macOS:   brew install ffmpeg

# 4. Create .env and fill in the keys (see below)
cp .env.example .env

# 5. Run the main system — creates & maintains all 4 packs
python sticker_pack.py
```

---

## Getting API keys / Получение API-ключей

Fill these into `.env` in the `mrkt_sticker/` folder:

### 1. `TELEGRAM_BOT_TOKEN` — Telegram Bot token

- Open **@BotFather** in Telegram
- `/newbot` → choose name → choose username ending in `bot`
- Copy the token (format: `1234567890:ABC-DEF...`)

### 2. `OWNER_USER_ID` — your Telegram user ID

- Open **@userinfobot** in Telegram
- It replies with your numeric ID

This must be the account that owns the sticker packs. The bot creates packs on behalf of this user.

### 3. `MRKT_CONTEST_KEY` — MRKT Contest API key

- **Request the key from the MRKT team.** It is delivered as a UUID.
- The key is sent in every request as header `X-CONTEST-KEY`.
- Endpoint: `https://contest.tgmrkt.io/contest/v1/gifts-collections`
- Rate limit: cached 60 sec by server. Our client polls every 60 sec.

### 4. `DUNE_API_KEY` — Dune Analytics API key (for supply data)

- Register at https://dune.com
- Settings → API → Create new API key

### 5. (Optional) `TELEGRAM_API_ID` / `TELEGRAM_API_HASH`

Only needed if you want to run `find_gift_ids.py --mtproto` to discover new gift document IDs.

- Go to https://my.telegram.org/apps
- Create an application, copy `api_id` and `api_hash`

---

## Running the system / Запуск системы

### Main mode — run all 4 packs continuously

```bash
python sticker_pack.py
```

On first run it will ask:
- Pack name prefix (e.g. `mrkt`) — becomes `mrkt1_by_<bot>`, `mrkt2_by_<bot>`, `mrkt3_by_<bot>`
- Pack title — visible name shown in Telegram (e.g. `MRKT Gifts`)

After that it runs forever, refreshing all 4 packs every 60 seconds.

### Test mode — unupgraded pack only

```bash
python test_unupgraded.py
```

Updates only the unupgraded pack. Useful when:
- You changed `UNUPGRADED_SLUGS` and want to verify
- You added new images to `gift_overrides/`
- You don't want to wait ~4 minutes for all 150 main stickers

### Generating design mockups (not for production)

```bash
python generate_designs.py
```

Creates 8 PNG mockups of different sticker designs for preview purposes.

---

## Pack structure / Структура паков

The system maintains **4 sticker packs**:

| Pack | Size | Contents | URL format |
|---|---|---|---|
| Main 1 | 50 | Top 50 collections by floor price | `t.me/addstickers/<prefix>1_by_<bot>` |
| Main 2 | 50 | Collections 51–100 | `t.me/addstickers/<prefix>2_by_<bot>` |
| Main 3 | 50 | Collections 101–150 | `t.me/addstickers/<prefix>3_by_<bot>` |
| Unupgraded | up to 10 | Curated list of un-upgraded gifts | `t.me/addstickers/unupgradedmrkt_by_<bot>` |

**Unupgraded gifts are excluded from main packs** (to avoid duplicates). Only the cheaper "regular" version of a gift appears in the unupgraded pack; the upgraded (more expensive) version appears in the main packs if it's separately listed on MRKT.

---

## Managing unupgraded gifts / Управление неулучшенными подарками

The list of unupgraded gifts is a Python list in `mrkt_sticker/sticker_pack.py`:

```python
UNUPGRADED_SLUGS = [
    "trojanhorse", "mask", "coffin", "gravestone",
    "durovsboots", "durovscoat", "ufcbox",
    "khabibspapakha", "durovsfigurine", "airplane",
]
```

**Slug rule:** lowercase, alphanumeric only. `"Plush Pepe"` → `"plushpepe"`, `"Durov's Cap"` → `"durovscap"`.

### Remove a gift from the unupgraded pack
(e.g. when it becomes widely upgraded)

1. Open `mrkt_sticker/sticker_pack.py`
2. Delete the slug from `UNUPGRADED_SLUGS`
3. Restart the main script — `python sticker_pack.py`
4. The unupgraded pack auto-cleans: removed gift's sticker is deleted
5. The gift automatically appears in one of the main packs (if its floor price qualifies)

### Add a new unupgraded gift

1. Add the slug to `UNUPGRADED_SLUGS`
2. (Optional) Put a custom image at `mrkt_sticker/gift_overrides/<slug>.webp`
   → Needed if the gift ID isn't in `SLUG_TO_GIFT_ID` (so auto-download fails)
3. Restart — sticker appears in the unupgraded pack, disappears from main packs

---

## Adding custom gift images / Добавление кастомных картинок

Some gifts (especially unupgraded ones) don't have a known sticker document_id and can't be auto-downloaded from `api.changes.tg`. For these, drop a custom image into `mrkt_sticker/gift_overrides/`.

### Rules

- **Filename:** `<slug>.webp`, `<slug>.png`, or `<slug>.jpg`
- **Recommended size:** 512×512 px
- **Transparent background** for best appearance (WebP/PNG)
- Slug matches the collection name (lowercase, alphanumeric only)

### Image loading priority (highest first)

1. `gift_overrides/<slug>.webp|png|jpg` — manual override (committed to repo)
2. `gift_cache/<slug>.png` — disk cache (auto-downloaded, git-ignored)
3. `api.changes.tg/original/<gift_id>.png` — downloaded if neither exists

### Example

To add a custom image for `airplane`:
```bash
# Put a 512x512 transparent WebP/PNG here:
mrkt_sticker/gift_overrides/airplane.webp
```

Next run will use this image automatically.

---

## Maintenance scenarios / Типичные сценарии обслуживания

### The MRKT Contest API key expired / got revoked

Request a new key from the MRKT team and update `MRKT_CONTEST_KEY` in `.env`. Restart the script.

### You want to rename a pack
Change the pack name in `sticker_pack.py` (search for `f"{prefix}1_by_..."`) or delete `sticker_state.json` and let the script recreate packs under new names on next run.

### A sticker pack got corrupted / is full of stale stickers

1. Delete the pack via **@Stickers** bot in Telegram: `/delpack`
2. Delete `mrkt_sticker/sticker_state.json`
3. Restart → pack is recreated from scratch

### You want to push a "fresh" design change to all stickers

Just edit `sticker_image.py`. Next 60-sec cycle will replace every sticker with the new design. No manual clean-up needed.

### Migrating to a new bot

1. Create a new bot via **@BotFather**, put its token into `.env`
2. Delete `mrkt_sticker/sticker_state.json` (old packs are owned by the old bot)
3. Restart — new bot creates new packs

### Adding a brand-new collection that just launched on MRKT

Usually nothing is needed — the script picks up all collections from the Contest API by floor price. Custom image is optional.

### The unupgraded pack only has 2 stickers after restart

This happens if the old pack has leftover stickers and `sticker_state.json` lost state. The code has a stale cleanup step that removes untracked stickers on each run — just let it run one more cycle, or delete the pack and restart.

---

## Troubleshooting / Решение проблем

| Symptom | Cause | Fix |
|---|---|---|
| `API returned 401` | Invalid/missing `MRKT_CONTEST_KEY` | Check the key in `.env`; request a new one from MRKT team |
| `STICKERSET_INVALID` | Pack was just deleted but Telegram backend is still catching up | Wait 2-3 minutes and retry; or rename the pack |
| `change_24h` always 0 | Price history not accumulated yet | Normal for first ~24h; rolling history is built up live |
| Sticker has emoji instead of gift image | Slug not in `SLUG_TO_GIFT_ID` AND no override file | Add custom image to `gift_overrides/<slug>.webp` |
| Pack has too many stickers (stale) | Old run with different config | Delete pack in @Stickers (`/delpack`) + delete `sticker_state.json`, restart |
| `Unclosed client session` on Ctrl+C | Normal cleanup warning on shutdown | Ignore — harmless |
| First run asks for pack name every time | `sticker_state.json` is missing/empty | Normal on first run; it's saved after creation |
| `ffmpeg: command not found` | ffmpeg not installed | Install via winget/apt/brew; or accept static WebP fallback |
| Bot doesn't have permission to create packs | The bot is not owned by `OWNER_USER_ID` | Double-check that `OWNER_USER_ID` is the actual owner account |

---

## Project structure / Структура проекта

```
mrkt_sticker/
├── sticker_pack.py          # MAIN — pack manager, update loop, config
├── sticker_image.py         # Frame renderer + ffmpeg WebM encoder
├── mrkt_parser.py           # MRKT Contest API client (prices + 24h history)
├── bot.py                   # Optional interactive bot (/price, /list, ...)
├── test_unupgraded.py       # Quick test — updates ONLY unupgraded pack
├── generate_designs.py      # Dev tool — renders 8 design mockups
├── find_gift_ids.py         # Dev tool — discover gift document IDs
├── fix_images.py            # Dev tool — fixes broken images
├── requirements.txt         # aiogram, aiohttp, Pillow, telethon
├── .env.example             # Template for all API keys
├── .env                     # Real credentials (git-ignored)
├── gift_overrides/          # Manual image overrides (committed)
│   ├── ionicdryer.webp
│   ├── skystilettos.webp
│   └── ... (one per gift)
├── gift_cache/              # Auto-downloaded CDN images (git-ignored)
├── sticker_state.json       # Runtime state (git-ignored)
└── mrkt_price_history.json  # 26h rolling price history for 24h change (git-ignored)
```

---

## Configuration / Конфигурация

### Key constants in `sticker_pack.py`

| Constant | Default | Purpose |
|---|---|---|
| `NUM_PACKS` | 3 | Number of main packs |
| `MAX_STICKERS` | 50 | Per-pack sticker limit (Telegram max) |
| `UPDATE_INTERVAL` | 60 | Seconds between refresh cycles |
| `UNUPGRADED_SLUGS` | list of 10 | Slugs included in the unupgraded pack |
| `SLUG_TO_GIFT_ID` | dict | Maps slug → sticker document_id for CDN image download |

### Key constants in `sticker_image.py`

| Constant | Default | Purpose |
|---|---|---|
| `ANIM_FPS` | 30 | Animation framerate |
| `ANIM_DURATION` | 3 | Animation length (sec) |
| `STAR_USD` | 0.015 | Conversion rate Stars → USD |
| `W`, `H` | 512 | Sticker dimensions |
| `CORNER` | 48 | Card corner radius (px) |

### Key constants in `mrkt_parser.py`

| Constant | Default | Purpose |
|---|---|---|
| `HISTORY_WINDOW_SEC` | 26 × 3600 | How long price samples are kept |
| `CHANGE_24H_TARGET_SEC` | 24 × 3600 | Target age of the sample for % change |
| `NANO_TON` | 10⁹ | Nano-TON → TON conversion |

---

## External APIs / Внешние API

| API | Endpoint | Purpose | Auth |
|---|---|---|---|
| MRKT Contest | `contest.tgmrkt.io/contest/v1/gifts-collections` | Floor prices (nanoTons) | `X-CONTEST-KEY` header |
| Dune Analytics | `api.dune.com/api/v1/query/{id}/results` | Supply data (total/remaining) | `X-Dune-API-Key` header |
| Binance | `api.binance.com/api/v3/ticker/price` | TON/USD rate | none |
| changes.tg | `api.changes.tg/original/{gift_id}.png` | Gift thumbnails | none |
| Telegram Bot API | via aiogram | Sticker pack CRUD | Bot token |

### Why not use the authenticated MRKT mini-app API?

The previous version used `api.tgmrkt.io/api/v1/gifts/collections` which required a user session token extracted from DevTools. That token expired every few hours. The Contest API is a first-class server-to-server endpoint with a long-lived UUID key and is supported by MRKT for exactly this use case.

---

## Animations / Анимации

Each animated sticker (3 seconds, 30 fps, WebM VP9) includes:

| Animation | Description |
|---|---|
| **Neon pulse line** | Bright traveling spot along pulse line at top |
| **Border glow** | Gallery-style glow around frame, color by trend (green/red/gold) |
| **Breathing glow** | Soft gold glow under gift image fading in/out |
| **Letter shimmer** | Golden wave traveling through collection name letters |
| **Floating particles** | Sparkles drifting up (growth) or down (drop) |
| **Heartbeat** | ECG-style line drawn progressively behind price |
| **Gift float** | Gentle vertical bobbing of gift thumbnail |

Animation color coding:
- **Green** — price up 24h
- **Red** — price down 24h
- **Gold** — price stable (<0.1% change)

---

## Dependencies / Зависимости

### Python

| Package | Version | Purpose |
|---|---|---|
| `aiogram` | >=3.0 | Telegram Bot API (async) |
| `aiohttp` | >=3.9 | HTTP client for MRKT/Dune/Binance |
| `Pillow` | >=10.0 | Frame rendering |
| `telethon` | >=1.30 | Only for optional `find_gift_ids.py --mtproto` |

### System

| Dependency | Required | Purpose |
|---|---|---|
| **ffmpeg** | For animated mode | Encodes PNG frames → VP9 WebM. Without it — automatic fallback to static WebP. |

---

## What each sticker shows / Что показывает каждый стикер

- **Collection name** — formatted from slug, e.g. `"plushpepe"` → `"PLUSH PEPE"`, with animated golden shimmer
- **Gift thumbnail** — 140×140 image, with gentle float animation
- **USD price** — colored by trend: green (up), red (down), white (stable)
- **24h change badge** — pill with arrow and percentage (▲ +5.2% / ▼ -3.1%)
- **TON price** — blue text
- **Stars price** — orange text (USD ÷ 0.015)
- **Supply** — total items count (from Dune)
- **Date/time** — current UTC timestamp
- **MRKT watermark** — diagonal background text
- **Border glow** — animated, color matches price trend

---

## License / Лицензия

Private project. All rights reserved. / Закрытый проект. Все права защищены.
