# MRKT Animated Stickers

Auto-updating Telegram **animated** sticker pack system for the **MRKT** gift marketplace.
Stickers display live floor prices (USD, TON, Stars), 24h price changes, supply, and gift thumbnails.
Animated effects: neon pulse line, breathing border glow, floating particles, heartbeat, gift float.
Packs refresh every 60 seconds.

Система автообновляемых **анимированных** Telegram-стикерпаков для маркетплейса подарков **MRKT**.
Стикеры отображают актуальные floor-цены (USD, TON, Stars), изменение за 24ч, supply и картинку подарка.
Анимация: неоновый пульс, дышащее свечение рамки, парящие частицы, heartbeat, покачивание подарка.
Обновление каждые 60 секунд.

---

## How it works / Как это работает


giftstat API ──> floor prices, 24h change, supply
Binance API ──> TON/USD rate
changes.tg ──> gift images (by MTProto gift ID)
|
v
+---------------------+
| sticker_image.py | <- renders 512x512 frames with Pillow
| | encodes to WebM VP9 via ffmpeg
+----------+----------+
|
v
+---------------------+
| sticker_pack.py | <- creates/updates 3 Telegram sticker packs
| | (50 stickers each), loop every 60s
+----------+----------+
|
v
+---------------------+
| bot.py | <- interactive bot: /sticker, /animated,
| | /static, /price, /list
+---------------------+


If ffmpeg is not installed, the system automatically falls back to static WebP stickers.

Если ffmpeg не установлен, система автоматически откатывается на статичные WebP-стикеры.

---

## Animations / Анимации

Each animated sticker (3 seconds, 30fps, WebM VP9) includes:

| Animation | Description (EN) | Описание (RU) |
|---|---|---|
| **Neon pulse line** | Bright traveling spot along pulse line at top | Яркая бегущая точка по линии пульса вверху |
| **Border glow** | Gallery-style glow around frame, color by trend (green/red/gold) | Свечение рамки в стиле галереи, цвет по тренду |
| **Breathing glow** | Soft gold glow under gift image fading in/out | Мягкое свечение под картинкой подарка |
| **Letter shimmer** | Golden wave traveling through collection name letters | Золотая волна по буквам названия коллекции |
| **Floating particles** | Sparkles drifting up (growth) or down (drop) | Частицы вверх (рост) или вниз (падение) |
| **Heartbeat** | ECG-style line drawn progressively behind price | Линия пульса, рисующаяся за ценой |
| **Gift float** | Gentle vertical bobbing of gift thumbnail | Плавное покачивание картинки подарка |

---

## Project structure / Структура проекта


mrkt_sticker/
├── sticker_image.py # Animated frame renderer + ffmpeg WebM encoder
├── sticker_pack.py # Pack manager (3x50, auto-update every 60s)
├── bot.py # Telegram bot commands
├── fix_images.py # Downloads missing gift images from giftstat CDN
├── requirements.txt # aiogram, aiohttp, Pillow
├── .env.example # Template for bot token and owner ID
├── .env # Credentials (git-ignored)
├── gift_overrides/ # Manual image overrides (priority over API)
│ ├── ionicdryer.webp
│ └── skystilettos.webp
├── gift_cache/ # Auto-downloaded images (git-ignored)
└── sticker_state.json # Runtime state (git-ignored)


---

## Setup & run / Установка и запуск

### 1. Install dependencies / Установка зависимостей

```bash
cd mrkt_sticker
pip install -r requirements.txt

2. Install ffmpeg / Установка ffmpeg
# Windows
winget install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

3. Create .env / Создание .env
cp .env.example .env

Edit .env / Отредактируйте .env:

TELEGRAM_BOT_TOKEN=<from @BotFather>
OWNER_USER_ID=<from @userinfobot>

4. Run / Запуск
# Auto-updating sticker packs (main mode)
python sticker_pack.py

# Interactive bot
python bot.py

# Fix missing gift images
python fix_images.py

On first run, sticker_pack.py will ask for pack name and title, then download all gift images and start the update loop.

При первом запуске sticker_pack.py спросит имя и название пака, затем скачает все картинки подарков и запустит цикл обновления.

What each sticker shows / Что показывает каждый стикер
Collection name — formatted from slug (e.g. "PLUSH PEPE") with animated golden shimmer
Gift thumbnail — 140x140 image from changes.tg API, with gentle float animation
USD price — colored by trend: green (growth), red (drop), white (stable)
24h change badge — pill with arrow and percentage
TON price — blue text
Stars price — orange text
Supply — total items count
Date/time — current UTC timestamp
MRKT watermark — diagonal background text
Border glow — animated, color matches price trend
Key constants / Ключевые константы
Constant	Value	Location	Purpose
NUM_PACKS	3	sticker_pack.py	Sticker packs count
MAX_STICKERS	50	sticker_pack.py	Per pack limit (Telegram max)
UPDATE_INTERVAL	60s	sticker_pack.py	Refresh cycle
ANIM_FPS	30	sticker_image.py	Animation framerate
ANIM_DURATION	3s	sticker_image.py	Animation length
STAR_USD	0.015	sticker_image.py	Stars to USD rate
W, H	512x512	sticker_image.py	Sticker dimensions
CORNER	48px	sticker_image.py	Card corner radius
Dependencies / Зависимости
Python
Package	Version	Purpose
aiogram	>=3.0	Telegram Bot API framework (async)
aiohttp	>=3.9	Async HTTP client for API calls
Pillow	>=10.0	Image rendering (frame generation)
System
Dependency	Required	Purpose
ffmpeg	For animated mode	Encodes PNG frames to VP9 WebM. Without it — falls back to static WebP.
External APIs / Внешние API
API	Endpoint	Data
giftstat	api.giftstat.app/current/collections/floor	Floor prices + 24h change
giftstat	api.giftstat.app/current/collections	Supply data
Binance	api.binance.com/api/v3/ticker/price	TON/USD rate
changes.tg	api.changes.tg/original/{gift_id}.png	Gift images
giftstat CDN	ddejfvww7sqtk.cloudfront.net/...	Override images for broken entries
Telegram	Bot API via aiogram	Sticker pack CRUD
Image loading priority / Приоритет загрузки картинок
gift_overrides/<slug>.{png,webp,jpg} — manual overrides (committed to repo)
gift_cache/<slug>.png — disk cache (auto-downloaded, git-ignored)
Download from api.changes.tg/original/{gift_id}.png — if neither exists
License / Лицензия
Private project. All rights reserved. / Закрытый проект. Все права защищены.

