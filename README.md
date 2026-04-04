# MRKT Animated Stickers

**Auto-updating Telegram ANIMATED sticker pack system for the MRKT gift marketplace.**

Система автообновляемых АНИМИРОВАННЫХ стикерпаков Telegram для маркетплейса подарков MRKT.

---

## How it works / Как это работает

```
Fragment API ──► fetch collections & floor prices
                        │
                        ▼
               ┌────────────────────┐
               │  sticker_pack.py   │
               │  (sync loop 300s)  │
               └────────┬───────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   tonapi.io       gift_overrides/   sticker_image.py
   (TON/USD)       (fixed images)    (render frames)
                                          │
                                          ▼
                                    Pillow (512×512 frames)
                                          │
                                          ▼
                                    ffmpeg (frames → WebM VP9)
                                          │
                                          ▼
                                    512×512 WebM video sticker
                                          │
                                          ▼
                              Telegram Bot API (aiogram 3)
                              ┌───────────────────────┐
                              │  create/update sticker │
                              │  pack with format=     │
                              │  "video" (animated)    │
                              │  or "static" (fallback)│
                              └───────────────────────┘
```

If animated generation fails (e.g. ffmpeg missing), the system automatically falls back to static WebP stickers.

Если генерация анимации не удалась (например, нет ffmpeg), система автоматически откатывается на статичные WebP-стикеры.

---

## Animations / Анимации

Each animated sticker includes the following visual effects:

| Animation         | Description (EN)                                      | Описание (RU)                                  |
|-------------------|------------------------------------------------------|-------------------------------------------------|
| **Pulse line**    | Thin price-chart line that pulses across the sticker | Пульсирующая линия графика цены                |
| **Breathing glow**| Soft glow around the gift image that fades in/out    | Мягкое свечение вокруг картинки подарка        |
| **Floating particles** | Small sparkle particles drifting upward          | Мелкие частицы-искры, летящие вверх            |
| **Heartbeat**     | Rhythmic scale pulse on the gift icon                | Ритмичная пульсация масштаба иконки подарка    |
| **Price pulse**   | Floor price text that subtly scales up and down      | Текст цены, плавно увеличивающийся и уменьшающийся |
| **Gift float**    | Gentle vertical bobbing of the gift image            | Плавное вертикальное покачивание картинки подарка |

Animations are rendered as individual 512x512 PNG frames with Pillow, then encoded into a VP9 WebM video via ffmpeg.

---

## Project structure / Структура проекта

```
mrkt-animated-stickers/
├── README.md                        # This file / этот файл
└── mrkt_sticker/
    ├── .env.example                 # Environment variable template / шаблон переменных окружения
    ├── requirements.txt             # Python dependencies / зависимости Python
    ├── bot.py                       # Telegram bot with /sticker, /animated, /static, /price, /list commands
    ├── sticker_pack.py              # Auto-sync loop: fetches data, generates stickers, updates pack
    ├── sticker_image.py             # Frame renderer + ffmpeg WebM encoder (imported by bot & pack)
    ├── fix_images.py                # Downloads missing gift images from giftstat CDN
    └── gift_overrides/              # Local override images for gifts with broken CDN images
        └── (ionicdryer.webp, etc.)
```

---

## What each file does / Что делает каждый файл

| File | Purpose (EN) | Назначение (RU) |
|------|-------------|------------------|
| `sticker_pack.py` | Main sync loop. Fetches collections from Fragment, TON/USD rate from tonapi, generates animated WebM (or static WebP fallback) stickers, and keeps the Telegram sticker pack in sync via Bot API. Runs every 300 seconds. | Основной цикл синхронизации. Получает коллекции с Fragment, курс TON/USD с tonapi, генерирует анимированные WebM (или статичные WebP) стикеры и обновляет стикерпак через Bot API. Запускается каждые 300 секунд. |
| `bot.py` | Interactive Telegram bot. Handles `/sticker`, `/animated`, `/static`, `/price`, `/list` commands. Uses giftstat API for market data and Binance for TON rate. Generates on-demand stickers. | Интерактивный Telegram-бот. Обрабатывает команды `/sticker`, `/animated`, `/static`, `/price`, `/list`. Использует giftstat API для данных рынка и Binance для курса TON. Генерирует стикеры по запросу. |
| `sticker_image.py` | Renders 512x512 animated frames using Pillow, then encodes them into VP9 WebM via ffmpeg subprocess. Provides `generate_sticker()` function used by both bot and pack manager. | Рендерит кадры 512x512 через Pillow, затем кодирует в VP9 WebM через subprocess ffmpeg. Предоставляет функцию `generate_sticker()`, используемую ботом и менеджером пака. |
| `fix_images.py` | Downloads missing/broken gift images from giftstat CDN into `gift_overrides/`. Fixes known issues with ionicdryer, skystilettos, etc. | Скачивает недостающие/битые картинки подарков с CDN giftstat в `gift_overrides/`. Исправляет известные проблемы с ionicdryer, skystilettos и др. |
| `.env.example` | Template for environment variables (bot token, owner ID). | Шаблон переменных окружения (токен бота, ID владельца). |

---

## Setup & run / Установка и запуск

### Prerequisites / Требования

1. **Python 3.10+**
2. **ffmpeg** -- required for animated WebM sticker generation / требуется для генерации анимированных WebM-стикеров

   ```bash
   # Ubuntu / Debian
   sudo apt install ffmpeg

   # macOS
   brew install ffmpeg

   # Verify / проверка
   ffmpeg -version
   ```

3. **Telegram Bot Token** from [@BotFather](https://t.me/BotFather) / Токен бота от @BotFather

### Installation / Установка

```bash
# Clone / клонирование
git clone https://github.com/your-org/mrkt-animated-stickers.git
cd mrkt-animated-stickers/mrkt_sticker

# Install Python dependencies / установка зависимостей Python
pip install -r requirements.txt

# Copy and fill in environment variables / скопировать и заполнить переменные окружения
cp .env.example .env
# Edit .env with your values / отредактируйте .env своими значениями
```

### Running the sticker pack sync / Запуск синхронизации стикерпака

```bash
# Set required env vars (or put them in .env)
export BOT_TOKEN="your_bot_token"
export PACK_NAME="mrkt_animated_by_yourbot"
export PACK_TITLE="MRKT Animated Gift Prices"
export BOT_USERNAME="yourbot"
export ANIMATED_STICKERS=true     # set to false for static-only mode

python -m mrkt_sticker.sticker_pack
```

### Running the interactive bot / Запуск интерактивного бота

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
python -m mrkt_sticker.bot
```

### Fixing broken gift images / Исправление битых картинок подарков

```bash
python -m mrkt_sticker.fix_images
```

---

## Key constants / Ключевые константы

| Constant | Value | Description |
|----------|-------|-------------|
| `SYNC_INTERVAL` | `300` | Seconds between sticker pack sync cycles / секунд между циклами синхронизации |
| `MAX_STICKERS` | `50` | Telegram limit per sticker pack / лимит Telegram на стикерпак |
| `STICKER_SIZE` | `512` | Sticker dimensions in pixels (512x512) / размер стикера в пикселях |
| `ANIMATED` | `true` | Enable animated WebM generation (env: `ANIMATED_STICKERS`) / включить анимированную генерацию WebM |
| `CACHE_TTL` | `30` | Bot data cache lifetime in seconds / время жизни кеша данных бота |
| `STAR_USD` | `0.015` | Telegram Star to USD conversion rate / курс Telegram Star к USD |

---

## Dependencies / Зависимости

### Python packages / Python-пакеты

| Package | Version | Purpose |
|---------|---------|---------|
| `aiogram` | `>=3.0` | Telegram Bot API framework (async) |
| `aiohttp` | `>=3.9` | Async HTTP client for API calls |
| `Pillow` | `>=10.0` | Image rendering (frame generation) |
| `python-dotenv` | -- | `.env` file loading (used in code, add to requirements if needed) |

### System dependencies / Системные зависимости

| Dependency | Required | Purpose |
|------------|----------|---------|
| **ffmpeg** | Yes (for animated) | Encodes Pillow PNG frames into VP9 WebM video stickers. Without ffmpeg, the system falls back to static WebP stickers. |

---

## External APIs / Внешние API

| API | URL | Used by | Purpose |
|-----|-----|---------|---------|
| **Fragment Collections** | `https://fragment.com/api/v1/getGiftCollections` | `sticker_pack.py` | Fetch all gift collections |
| **Fragment Collection** | `https://fragment.com/api/v1/getGiftCollection` | `sticker_pack.py` | Fetch single collection by slug |
| **tonapi** | `https://tonapi.io/v2/rates` | `sticker_pack.py` | TON/USD exchange rate |
| **giftstat** | `https://api.giftstat.app/current/collections/floor` | `bot.py` | Collection floor prices (bot) |
| **Binance** | `https://api.binance.com/api/v3/ticker/price` | `bot.py` | TON/USDT rate (bot) |
| **giftstat CDN** | `https://ddejfvww7sqtk.cloudfront.net/...` | `fix_images.py` | Correct gift images for broken entries |

---

## Differences from static version (mrkt-sticker) / Отличия от статичной версии

| Feature | `mrkt-sticker` (static) | `mrkt-animated-stickers` (this repo) |
|---------|------------------------|--------------------------------------|
| **Sticker format** | WebP 512x512 (static) | WebM 512x512 VP9 (animated video) |
| **Visual effects** | Static card with price info | Animated: pulse line, breathing glow, floating particles, heartbeat, price pulse, gift float |
| **ffmpeg required** | No | Yes (falls back to static without it) |
| **Sticker type in Bot API** | `format="static"` | `format="video"` (with static fallback) |
| **Frame rendering** | Single Pillow image | Multiple Pillow frames encoded via ffmpeg |
| **Bot commands** | Basic sticker generation | `/sticker` (auto), `/animated` (force video), `/static` (force PNG) |
| **Fallback behavior** | N/A | Automatically falls back to static WebP if animated generation fails |
| **sticker_image module** | Simple image renderer | Multi-frame animator + ffmpeg encoder |

---

## License / Лицензия

Private project. All rights reserved. / Закрытый проект. Все права защищены.
