#!/usr/bin/env python3
"""
MRKT Animated Sticker Pack — Auto-updating animated sticker packs.

EN: Creates and maintains 3 Telegram sticker packs (50 stickers each = 150 total)
    with real-time floor prices from the MRKT gift marketplace.
    Supports animated WebM video stickers (with ffmpeg) and static WebP fallback.
    Data sources: MRKT API (prices), Dune Analytics (supply), Binance (TON/USD), changes.tg (images).
    Update cycle: every 60 seconds.

RU: Создаёт и поддерживает 3 Telegram-стикерпака (по 50 = 150 всего)
    с актуальными ценами подарков с маркетплейса MRKT.
    Поддерживает анимированные WebM видео-стикеры (через ffmpeg) и статичные WebP.
    Источники: MRKT API (цены), Dune Analytics (supply), Binance (TON/USD), changes.tg (картинки).
    Цикл обновления: каждые 60 секунд.

Usage / Запуск:
    pip install -r requirements.txt
    # Ensure ffmpeg is installed for animated stickers
    # Create .env with TELEGRAM_BOT_TOKEN and OWNER_USER_ID
    python sticker_pack.py
"""

import io
import os
import sys
import json
import asyncio
import logging
from datetime import datetime

import aiohttp
from PIL import Image
from aiogram import Bot
from aiogram.types import InputSticker, BufferedInputFile

from sticker_image import generate_sticker
from mrkt_parser import fetch_mrkt_prices, get_upgraded_prices

# ─── Load .env ────────────────────────────────────────────────────
def load_dotenv():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_USER_ID", "0"))
UPDATE_INTERVAL = 60  # секунд
MAX_STICKERS = 50
ANIMATED = os.environ.get("ANIMATED_STICKERS", "1").lower() in ("1", "true", "yes")

BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
DUNE_QUERY_ID = 5133545

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sticker_state.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("mrkt-pack")

if not BOT_TOKEN:
    sys.exit("❌ TELEGRAM_BOT_TOKEN не задан! Добавьте в .env")
if not OWNER_ID:
    sys.exit("❌ OWNER_USER_ID не задан! Узнайте свой ID у @userinfobot")

EMOJI_MAP = {
    # ─── Tier 1: Premium / Collectible ───
    "plushpepe": "🐸",
    "durovscap": "🧢",
    "eternalrose": "🌹",
    "recordplayer": "🎵",
    "swisswatch": "⌚",
    "poolfloat": "🦆",
    "moodpack": "🎒",
    "santahat": "🎅",
    "heartlocket": "💝",
    "gingerman": "🍪",
    "gingercookie": "🍪",
    "signetring": "💍",
    "diamondring": "💎",
    "tophat": "🎩",
    "jesterhat": "🃏",
    "magicpotion": "🧪",
    "madpumpkin": "🎃",
    "eternalcandle": "🕯",
    "lovepotion": "💕",
    "toybear": "🧸",
    "minioscar": "🏆",
    "sakuraflower": "🌸",
    "snoopDogg": "🐶",
    "snoopdogg": "🐶",
    "ufcstrike": "🥊",
    "easteregg": "🥚",
    # ─── Tier 2: Magic / Mystic ───
    "preciouspeach": "🍑",
    "kissedfrog": "🐸",
    "hexpot": "🍯",
    "evileye": "👁",
    "sharptounge": "👅",
    "sharptongue": "👅",
    "trappedheart": "💔",
    "skullflower": "💀",
    "scaredcat": "🙀",
    "spyagaric": "🍄",
    "homemadecake": "🎂",
    "genielamp": "🪔",
    "witchhat": "🧙",
    "hangingstar": "⭐",
    "lovecandle": "❤",
    "voodoodoll": "🪆",
    "hypnolollipop": "🍭",
    "bunnymuffin": "🐰",
    "astralshard": "🔮",
    "flyingbroom": "🧹",
    "crystalball": "🔮",
    # ─── Tier 3: Gifts / Items ───
    "lootbag": "💰",
    "lolpop": "🍭",
    "iongem": "💠",
    "starnotepad": "📝",
    "deskcalendar": "📅",
    "bdaycandle": "🎂",
    "jellyBunny": "🐇",
    "jellybunny": "🐇",
    "spicedwine": "🍷",
    "perfumebottle": "🧴",
    "berrybox": "🍓",
    "vintagecigar": "🚬",
    # ─── Tier 4: Winter / Holiday ───
    "cookieheart": "🍪",
    "jinglebells": "🔔",
    "snowmittens": "🧤",
    "sleighbell": "🛷",
    "winterwreath": "🎄",
    "snowglobe": "🌐",
    "candycane": "🍬",
    "xmasstocking": "🧦",
    "holidaydrink": "🍹",
    "partysparkler": "🎇",
    # ─── Tier 5: Tech / Sci-fi ───
    "electricskull": "⚡",
    "tamagadget": "🎮",
    "nekohelmet": "😺",
    "lunarsnake": "🐍",
    "bigyear": "🎆",
    "stellarrocket": "🚀",
    "lightsword": "⚔",
    "inputkey": "🔑",
    # ─── Tier 6: Fashion / Accessories ───
    "gemsignet": "💎",
    "nailbracelet": "💅",
    "heroichelmet": "⛑",
    "bowtie": "🎀",
    "skystilettos": "👠",
    "freshsocks": "🧦",
    # ─── Tier 7: Nature / Animals ───
    "lushbouquet": "💐",
    "petsnake": "🐍",
    "snakebox": "📦",
    "rarebird": "🦜",
    "cloverpin": "🍀",
    "prettyposy": "🌺",
    "springbasket": "🧺",
    # ─── Tier 8: Food / Drinks ───
    "whipcupcake": "🧁",
    "icecream": "🍦",
    "instantramen": "🍜",
    "moussecake": "🍰",
    "happybrownie": "🍫",
    "vicecream": "🍨",
    # ─── Tier 9: Love / Valentine ───
    "joyfullbundle": "🎊",
    "joyfulbundle": "🎊",
    "cupidcharm": "💘",
    "valentinebox": "🎁",
    # ─── Tier 10: Snoop Dogg Collection ───
    "snoopcigar": "🚬",
    "swagbag": "👜",
    "lowrider": "🚗",
    "westsisesign": "🤙",
    "westsidesign": "🤙",
    # ─── Tier 11: Misc ───
    "jollychimp": "🐵",
    "moonpendant": "🌙",
    "ionicdryer": "💨",
    "mightyarm": "💪",
    "artisanbrick": "🧱",
    "faithamulet": "🛡",
    "blingbinky": "👶",
    "moneypot": "🪙",
    "bonedring": "💀",
    "bondedring": "💀",
    "jackinthebox": "🤡",
    "khabibspapakha": "🏔",
    "victorymedal": "🥇",
    "timelessbook": "📖",
    "chillflame": "🔥",
    "restlessjar": "🫙",
    "jollychimp": "🐒",
    # ─── Unupgraded gifts ───
    "trojanhorse": "🐴",
    "mask": "🎭",
    "coffin": "⚰",
    "gravestone": "🪦",
    "durovsboots": "👢",
    "durovscoat": "🧥",
    "ufcbox": "🥊",
    "durovsfigurine": "🗿",
    "airplane": "✈",
}

# ─── Unupgraded Gems config ─────────────────────────────────────
UNUPGRADED_SLUGS = [
    "trojanhorse", "mask", "coffin", "gravestone",
    "durovsboots", "durovscoat", "ufcbox",
    "khabibspapakha", "durovsfigurine", "airplane",
]
UNUPGRADED_SET = set(s.lower() for s in UNUPGRADED_SLUGS)

# CDN для картинок подарков (changes.tg)
CHANGES_TG_API = "https://api.changes.tg"

# Кэш загруженных картинок подарков: slug -> PIL.Image
gift_images_cache = {}


def get_emoji(slug):
    return EMOJI_MAP.get(slug.lower(), "🎁")


# ─── Gift image loading (via api.changes.tg) ────────────────

GIFT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gift_cache")
GIFT_OVERRIDES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gift_overrides")

SLUG_TO_GIFT_ID = {
    "plushpepe": "5936013938331222567",
    "durovscap": "5915521180483191380",
    "eternalrose": "5882125812596999035",
    "recordplayer": "5856973938650776169",
    "swisswatch": "5936043693864651359",
    "poolfloat": "5832644211639321671",
    "moodpack": "5886756255493523118",
    "santahat": "5983471780763796287",
    "heartlocket": "5868455043362980631",
    "gingerman": "5983484377902875708",
    "signetring": "5936085638515261992",
    "preciouspeach": "5933671725160989227",
    "magicpotion": "5846226946928673709",
    "kissedfrog": "5845776576658015084",
    "hexpot": "5825801628657124140",
    "evileye": "5825480571261813595",
    "sharptounge": "5841689550203650524",
    "trappedheart": "5841391256135008713",
    "skullflower": "5839038009193792264",
    "scaredcat": "5837059369300132790",
    "spyagaric": "5821261908354794038",
    "homemadecake": "5783075783622787539",
    "genielamp": "5933531623327795414",
    "jesterhat": "5933590374185435592",
    "witchhat": "5821384757304362229",
    "hangingstar": "5915733223018594841",
    "lovecandle": "5915550639663874519",
    "voodoodoll": "5836780359634649414",
    "madpumpkin": "5841632504448025405",
    "hypnolollipop": "5825895989088617224",
    "bunnymuffin": "5935936766358847989",
    "astralshard": "5933629604416717361",
    "flyingbroom": "5837063436634161765",
    "crystalball": "5841336413697606412",
    "eternalcandle": "5821205665758053411",
    "lootbag": "5868659926187901653",
    "lovepotion": "5868348541058942091",
    "toybear": "5868220813026526561",
    "diamondring": "5868503709637411929",
    "sakuraflower": "5933937398953018107",
    "tophat": "5897593557492957738",
    "minioscar": "5879737836550226478",
    "lolpop": "5170594532177215681",
    "iongem": "5843762284240831056",
    "starnotepad": "5936017773737018241",
    "deskcalendar": "5782988952268964995",
    "bdaycandle": "5782984811920491178",
    "jellyBunny": "5915502858152706668",
    "spicedwine": "5913442287462908725",
    "perfumebottle": "5913517067138499193",
    "berrybox": "5882252952218894938",
    "vintagecigar": "5857140566201991735",
    "cookieheart": "6001538689543439169",
    "jinglebells": "6001473264306619020",
    "snowmittens": "5980789805615678057",
    "sleighbell": "5981026247860290310",
    "winterwreath": "5983259145522906006",
    "snowglobe": "5981132629905245483",
    "electricskull": "5846192273657692751",
    "tamagadget": "6023752243218481939",
    "candycane": "6003373314888696650",
    "nekohelmet": "5933793770951673155",
    "lunarsnake": "6028426950047957932",
    "partysparkler": "6003643167683903930",
    "xmasstocking": "6003767644426076664",
    "bigyear": "6028283532500009446",
    "holidaydrink": "6003735372041814769",
    "gemsignet": "5859442703032386168",
    "lightsword": "5897581235231785485",
    "restlessjar": "5870784783948186838",
    "nailbracelet": "5870720080265871962",
    "heroichelmet": "5895328365971244193",
    "bowtie": "5895544372761461960",
    "lushbouquet": "5871002671934079382",
    "whipcupcake": "5933543975653737112",
    "joyfullbundle": "5870862540036113469",
    "cupidcharm": "5868561433997870501",
    "valentinebox": "5868595669182186720",
    "snoopDogg": "6014591077976114307",
    "swagbag": "6012607142387778152",
    "snoopcigar": "6012435906336654262",
    "lowrider": "6014675319464657779",
    "westsisesign": "6014697240977737490",
    "stellarrocket": "6042113507581755979",
    "jollychimp": "6005880141270483700",
    "moonpendant": "5998981470310368313",
    "ionicdryer": "5870947077877400011",
    "inputkey": "5870972044522291836",
    "mightyarm": "5895518353849582541",
    "artisanbrick": "6005797617768858105",
    "cloverpin": "5960747083030856414",
    "skystilettos": "5167939598143193218",
    "freshsocks": "5895603153683874485",
    "happybrownie": "6006064678835323371",
    "icecream": "5900177027566142759",
    "springbasket": "5773725897517433693",
    "instantramen": "6005564615793050414",
    "faithamulet": "6003456431095808759",
    "moussecake": "5935877878062253519",
    "blingbinky": "5902339509239940491",
    "moneypot": "5963238670868677492",
    "prettyposy": "5933737850477478635",
    "bonedring": "5870661333703197240",
    "petsnake": "6023917088358269866",
    "snakebox": "6023679164349940429",
    "jackinthebox": "6005659564635063386",
    "easteregg": "5773668482394620318",
    "khabibspapakha": "5839094187366024301",
    "ufcstrike": "5882260270843168924",
    "victorymedal": "5830340739074097859",
    "rarebird": "5999116401002939514",
    "timelessbook": "5886387158889005864",
    "chillflame": "5999277561060787166",
    "vicecream": "5898012527257715797",
    # Алиасы
    "bondedring": "5870661333703197240",
    "gingercookie": "5983484377902875708",
    "jellybunny": "5915502858152706668",
    "joyfulbundle": "5870862540036113469",
    "sharptongue": "5841689550203650524",
    "snoopdogg": "6014591077976114307",
    "westsidesign": "6014697240977737490",
}


async def load_gift_images(bot: Bot):
    """Скачивает PNG-картинки подарков из api.changes.tg и кэширует на диск."""
    global gift_images_cache

    os.makedirs(GIFT_CACHE_DIR, exist_ok=True)

    if os.path.isdir(GIFT_OVERRIDES_DIR):
        for fname in os.listdir(GIFT_OVERRIDES_DIR):
            if fname.lower().endswith((".png", ".webp", ".jpg", ".jpeg")):
                slug = os.path.splitext(fname)[0].lower()
                path = os.path.join(GIFT_OVERRIDES_DIR, fname)
                try:
                    gift_images_cache[slug] = Image.open(path).copy()
                    log.info(f"  Override loaded: {slug}")
                except Exception:
                    pass

    loaded = 0
    for slug, gid in SLUG_TO_GIFT_ID.items():
        if slug in gift_images_cache:
            continue
        path = os.path.join(GIFT_CACHE_DIR, f"{slug}.png")
        if os.path.exists(path):
            try:
                gift_images_cache[slug] = Image.open(path).copy()
                loaded += 1
            except Exception:
                pass

    if loaded > 0:
        log.info(f"Loaded {loaded} gift images from cache")

    missing = {s: gid for s, gid in SLUG_TO_GIFT_ID.items() if s not in gift_images_cache}
    if not missing:
        return

    log.info(f"Downloading {len(missing)} gift images from api.changes.tg...")
    async with aiohttp.ClientSession() as session:
        for slug, gift_id in missing.items():
            url = f"{CHANGES_TG_API}/original/{gift_id}.png"
            path = os.path.join(GIFT_CACHE_DIR, f"{slug}.png")
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status == 200:
                        data = await r.read()
                        with open(path, "wb") as f:
                            f.write(data)
                        gift_images_cache[slug] = Image.open(io.BytesIO(data)).copy()
                        log.info(f"  ✓ {slug} (gift #{gift_id}, {len(data)} bytes)")
                    else:
                        log.warning(f"  ✗ {slug}: HTTP {r.status}")
            except Exception as e:
                log.warning(f"  ✗ {slug}: {e}")
            await asyncio.sleep(0.2)

    total = len(SLUG_TO_GIFT_ID)
    found = len(gift_images_cache)
    failed = total - found
    log.info(f"Gift images ready: {found}/{total}")
    if failed > 0:
        missing_slugs = [s for s in SLUG_TO_GIFT_ID if s not in gift_images_cache]
        log.warning(f"⚠ {failed} gift images not found!")
        log.warning(f"  Missing: {', '.join(missing_slugs[:20])}"
                    + (f" ... and {len(missing_slugs)-20} more" if len(missing_slugs) > 20 else ""))


async def try_fetch_gift_image(slug, collections):
    """Пытается найти gift_id в данных коллекции и скачать картинку."""
    if slug in gift_images_cache:
        return gift_images_cache[slug]

    for col in collections:
        if col.get("slug", "").lower() == slug:
            gift_id = col.get("gift_id") or col.get("id") or col.get("giftId")
            if gift_id:
                SLUG_TO_GIFT_ID[slug] = gift_id
                path = os.path.join(GIFT_CACHE_DIR, f"{slug}.png")
                url = f"{CHANGES_TG_API}/original/{gift_id}.png"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                            if r.status == 200:
                                data = await r.read()
                                with open(path, "wb") as f:
                                    f.write(data)
                                gift_images_cache[slug] = Image.open(io.BytesIO(data)).copy()
                                log.info(f"  Fetched gift image for {slug} (id={gift_id})")
                                return gift_images_cache[slug]
                except Exception:
                    pass
    return None


def match_gift_image(slug):
    """Возвращает PIL.Image подарка для данного slug или None."""
    return gift_images_cache.get(slug.lower())


# ─── State ────────────────────────────────────────────────────────

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"stickers": {}, "set_name": ""}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ─── Data fetching ───────────────────────────────────────────────

async def fetch_ton_rate():
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(BINANCE_API, timeout=aiohttp.ClientTimeout(total=10)) as r:
                d = await r.json()
                return float(d.get("price", 7.2))
        except Exception as e:
            log.warning(f"TON rate error: {e}")
            return 7.2


def _name_to_slug(name):
    """Convert gift name to slug: 'Plush Pepe' -> 'plushpepe'."""
    import re
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


async def fetch_supply():
    """Fetch supply data from Dune Analytics (query 5133545)."""
    supply_map = {}
    if not DUNE_API_KEY:
        log.warning("DUNE_API_KEY not set, supply will show '--'")
        return supply_map
    async with aiohttp.ClientSession() as s:
        try:
            url = f"https://api.dune.com/api/v1/query/{DUNE_QUERY_ID}/results"
            headers = {"X-DUNE-API-KEY": DUNE_API_KEY}
            async with s.get(url, headers=headers,
                             timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status != 200:
                    log.warning(f"Dune API: {r.status}")
                    return supply_map
                data = await r.json()
            rows = data.get("result", {}).get("rows", [])
            for row in rows:
                name = row.get("collection", "")
                supply = row.get("max_supply") or row.get("initial_supply") or 0
                if name and supply:
                    slug = _name_to_slug(name)
                    if slug:
                        try:
                            supply_map[slug] = int(supply)
                        except (ValueError, TypeError):
                            pass
            log.info(f"Supply data: {len(supply_map)} collections from Dune")
        except Exception as e:
            log.warning(f"Dune supply fetch failed: {e}")
    return supply_map


async def fetch_collections():
    """Fetch all collections from MRKT API, enriched with Dune supply.

    Returns (all_collections, unupgraded_expensive, exclude_from_main).
    """
    prices = await fetch_mrkt_prices()
    if not prices:
        return [], {}, set()

    cheapest = {}
    expensive = {}
    for p in prices:
        slug = p["slug"]
        if slug not in cheapest or p["floor_price"] < cheapest[slug]["floor_price"]:
            cheapest[slug] = p
        if slug not in expensive or p["floor_price"] > expensive[slug]["floor_price"]:
            expensive[slug] = p

    dual_version_slugs = set()
    exclude_from_main = set()
    for slug in UNUPGRADED_SET:
        if slug in cheapest and slug in expensive:
            if cheapest[slug]["floor_price"] != expensive[slug]["floor_price"]:
                dual_version_slugs.add(slug)
            else:
                exclude_from_main.add(slug)
        elif slug in expensive:
            exclude_from_main.add(slug)

    result = {}
    for slug in expensive:
        if slug in dual_version_slugs:
            result[slug] = cheapest[slug]
        else:
            result[slug] = expensive[slug]

    collections = sorted(result.values(), key=lambda c: -(c["floor_price"]))

    supply_map = await fetch_supply()
    if supply_map:
        for col in collections:
            if col["slug"] in supply_map:
                col["supply"] = supply_map[col["slug"]]
        for slug in expensive:
            if slug in supply_map and slug not in dual_version_slugs:
                expensive[slug]["supply"] = supply_map[slug]

    return collections, expensive, exclude_from_main


# ─── Sticker generation helper ───────────────────────────────────

def _generate_sticker_data(col, ton_usd, gift_img):
    """Generate sticker data, trying animated first then falling back to static."""
    slug = col.get("slug", "")
    if ANIMATED:
        try:
            data = generate_sticker(col, ton_usd, fmt="WEBM", gift_img=gift_img, animated=True)
            return data, "video", f"{slug}.webm"
        except Exception as e:
            log.warning(f"    Animated failed for {slug}: {e}, falling back to static")

    data = generate_sticker(col, ton_usd, fmt="WEBP", gift_img=gift_img, animated=False)
    return data, "static", f"{slug}.webp"


# ─── Sticker pack management ─────────────────────────────────────

NUM_PACKS = 3


async def sync_unupgraded_pack(bot: Bot, set_name, collections, ton_usd, state):
    """Create or update the unupgraded gems sticker pack."""
    pack_state = state.setdefault(set_name, {})

    existing = None
    try:
        existing = await bot.get_sticker_set(name=set_name)
        log.info(f"  Unupgraded pack {set_name}: {len(existing.stickers)} stickers")
    except Exception:
        pass

    if not existing:
        if not collections:
            return

        col = collections[0]
        slug = col.get("slug", "unknown")
        gift_img = match_gift_image(slug)
        sticker_data, sticker_fmt, sticker_fname = _generate_sticker_data(col, ton_usd, gift_img)

        try:
            sticker = InputSticker(
                sticker=BufferedInputFile(sticker_data, filename=sticker_fname),
                emoji_list=[get_emoji(slug)],
                format=sticker_fmt,
            )
            await bot.create_new_sticker_set(
                user_id=OWNER_ID,
                name=set_name,
                title="MRKT Unupgraded Gems",
                stickers=[sticker],
            )
            log.info(f"  Unupgraded pack created: https://t.me/addstickers/{set_name}")

            sset = await bot.get_sticker_set(name=set_name)
            pack_state[slug.lower()] = sset.stickers[0].file_id

            for col in collections[1:MAX_STICKERS]:
                await asyncio.sleep(0.5)
                s = col.get("slug", "")
                gi = match_gift_image(s)
                sd, sf, sfn = _generate_sticker_data(col, ton_usd, gi)
                try:
                    st = InputSticker(
                        sticker=BufferedInputFile(sd, filename=sfn),
                        emoji_list=[get_emoji(s)],
                        format=sf,
                    )
                    await bot.add_sticker_to_set(
                        user_id=OWNER_ID, name=set_name, sticker=st)
                    sset = await bot.get_sticker_set(name=set_name)
                    pack_state[s.lower()] = sset.stickers[-1].file_id
                    log.info(f"    + {s} (unupgraded, {len(sd)/1024:.1f}KB)")
                except Exception as e:
                    log.warning(f"    Failed to add unupgraded {s}: {e}")

        except Exception as e:
            log.error(f"  Failed to create unupgraded pack: {e}")

    else:
        existing_file_ids = {s.file_id for s in existing.stickers}
        updated = 0

        for col in collections[:MAX_STICKERS]:
            slug = col.get("slug", "").lower()
            if not slug:
                continue

            gift_img = match_gift_image(slug)
            sticker_data, sticker_fmt, sticker_fname = _generate_sticker_data(col, ton_usd, gift_img)
            old_fid = pack_state.get(slug)

            if old_fid and old_fid in existing_file_ids:
                try:
                    new_sticker = InputSticker(
                        sticker=BufferedInputFile(sticker_data, filename=sticker_fname),
                        emoji_list=[get_emoji(slug)],
                        format=sticker_fmt,
                    )
                    await bot.replace_sticker_in_set(
                        user_id=OWNER_ID, name=set_name,
                        old_sticker=old_fid, sticker=new_sticker)
                    updated += 1
                    sset = await bot.get_sticker_set(name=set_name)
                    _refresh_file_ids(pack_state, sset)
                except Exception as e:
                    log.warning(f"    Replace failed for unupgraded {slug}: {e}")
            else:
                gi = match_gift_image(slug)
                sd, sf, sfn = _generate_sticker_data(col, ton_usd, gi)
                try:
                    st = InputSticker(
                        sticker=BufferedInputFile(sd, filename=sfn),
                        emoji_list=[get_emoji(slug)],
                        format=sf,
                    )
                    await bot.add_sticker_to_set(
                        user_id=OWNER_ID, name=set_name, sticker=st)
                    sset = await bot.get_sticker_set(name=set_name)
                    pack_state[slug] = sset.stickers[-1].file_id
                    log.info(f"    + {slug} (unupgraded, {len(sd)/1024:.1f}KB)")
                    updated += 1
                except Exception as e:
                    log.warning(f"    Failed to add unupgraded {slug}: {e}")

            await asyncio.sleep(0.35)

        log.info(f"  Unupgraded pack: updated {updated} stickers")

    state[set_name] = pack_state
    save_state(state)


async def sync_sticker_pack(bot: Bot, set_name, collections, ton_usd, state, pack_num=1):
    """Создаёт или обновляет один стикерпак (до 50 стикеров)."""
    pack_state = state.setdefault(set_name, {})

    existing = None
    try:
        existing = await bot.get_sticker_set(name=set_name)
        log.info(f"  Pack {set_name}: {len(existing.stickers)} stickers")
    except Exception:
        pass

    if not existing:
        if not collections:
            return

        col = collections[0]
        slug = col.get("slug", "unknown")
        gift_img = match_gift_image(slug)
        sticker_data, sticker_fmt, sticker_fname = _generate_sticker_data(col, ton_usd, gift_img)

        try:
            sticker = InputSticker(
                sticker=BufferedInputFile(sticker_data, filename=sticker_fname),
                emoji_list=[get_emoji(slug)],
                format=sticker_fmt,
            )
            await bot.create_new_sticker_set(
                user_id=OWNER_ID,
                name=set_name,
                title=f"{state.get('_pack_title', '@mrkt - best place to trade gifts with 0%')} #{pack_num}",
                stickers=[sticker],
            )
            log.info(f"  ✓ Pack created: https://t.me/addstickers/{set_name}")

            sset = await bot.get_sticker_set(name=set_name)
            pack_state[slug.lower()] = sset.stickers[0].file_id

            for col in collections[1:MAX_STICKERS]:
                await asyncio.sleep(0.5)
                await _add_sticker(bot, set_name, col, ton_usd, pack_state)

        except Exception as e:
            log.error(f"  Failed to create pack: {e}")

    else:
        existing_file_ids = {s.file_id for s in existing.stickers}

        updated = 0
        for col in collections[:MAX_STICKERS]:
            slug = col.get("slug", "")
            if not slug:
                continue
            slug_lower = slug.lower()

            gift_img = match_gift_image(slug)
            sticker_data, sticker_fmt, sticker_fname = _generate_sticker_data(col, ton_usd, gift_img)
            old_fid = pack_state.get(slug_lower)

            if old_fid and old_fid in existing_file_ids:
                try:
                    new_sticker = InputSticker(
                        sticker=BufferedInputFile(sticker_data, filename=sticker_fname),
                        emoji_list=[get_emoji(slug)],
                        format=sticker_fmt,
                    )
                    await bot.replace_sticker_in_set(
                        user_id=OWNER_ID,
                        name=set_name,
                        old_sticker=old_fid,
                        sticker=new_sticker,
                    )
                    updated += 1

                    sset = await bot.get_sticker_set(name=set_name)
                    _refresh_file_ids(pack_state, sset)

                except Exception as e:
                    log.warning(f"    Replace failed for {slug}: {e}")
                    try:
                        await bot.delete_sticker_from_set(sticker=old_fid)
                        del pack_state[slug_lower]
                        await asyncio.sleep(0.3)
                        await _add_sticker(bot, set_name, col, ton_usd, pack_state)
                        updated += 1
                    except Exception as e2:
                        log.error(f"    Fallback also failed for {slug}: {e2}")
            else:
                await _add_sticker(bot, set_name, col, ton_usd, pack_state)
                updated += 1

            await asyncio.sleep(0.35)

        log.info(f"  Updated {updated} stickers")

    state[set_name] = pack_state
    save_state(state)


def _refresh_file_ids(pack_state, sset):
    """Обновляет маппинг slug -> file_id из актуального стикерсета."""
    slugs = list(pack_state.keys())
    for i, sticker in enumerate(sset.stickers):
        if i < len(slugs):
            pack_state[slugs[i]] = sticker.file_id


async def _add_sticker(bot: Bot, set_name, col, ton_usd, pack_state):
    """Добавляет один стикер в пак."""
    slug = col.get("slug", "")
    gift_img = match_gift_image(slug)
    sticker_data, sticker_fmt, sticker_fname = _generate_sticker_data(col, ton_usd, gift_img)
    try:
        sticker = InputSticker(
            sticker=BufferedInputFile(sticker_data, filename=sticker_fname),
            emoji_list=[get_emoji(slug)],
            format=sticker_fmt,
        )
        await bot.add_sticker_to_set(
            user_id=OWNER_ID,
            name=set_name,
            sticker=sticker,
        )
        sset = await bot.get_sticker_set(name=set_name)
        pack_state[slug.lower()] = sset.stickers[-1].file_id
        log.info(f"    + {slug} = {col.get('floor_price', 0):.2f} TON ({sticker_fmt})")
    except Exception as e:
        log.warning(f"    ✗ Failed to add {slug}: {e}")


# ─── Main loop ───────────────────────────────────────────────────

def prompt_pack_settings(username):
    """Спрашивает у пользователя название и описание паков перед запуском."""
    suffix = f"_by_{username}"

    print("\n╔══════════════════════════════════════════════════╗")
    print("║       MRKT Animated Sticker Pack — Setup          ║")
    print("╚══════════════════════════════════════════════════╝")

    default_name = "giftprices"
    default_title = "@mrkt - best place to trade gifts with 0%"

    while True:
        print(f"\n  Pack name / Имя пака в ссылке t.me/addstickers/...")
        print(f"  (Telegram adds {suffix} automatically)")
        print(f"  For 3 packs: <name>{suffix}, <name>_2{suffix}, <name>_3{suffix}")
        print(f"  Default: {default_name}")
        user_name = input(f"\n  Enter name / Введите имя [{default_name}]: ").strip()
        if not user_name:
            user_name = default_name

        print(f"\n  Pack title / Название пака в Telegram")
        print(f"  (# number added automatically)")
        print(f"  Default: {default_title}")
        user_title = input(f"\n  Enter title / Введите название [{default_title}]: ").strip()
        if not user_title:
            user_title = default_title

        pack_names = []
        for i in range(NUM_PACKS):
            if i == 0:
                pack_names.append(f"{user_name}{suffix}")
            else:
                pack_names.append(f"{user_name}_{i+1}{suffix}")

        unupgraded_pack_name = f"unupgradedgems{suffix}"

        print(f"\n  ┌─────────────────────────────────────────────┐")
        print(f"  │  Title: {user_title}")
        for i, pn in enumerate(pack_names):
            print(f"  │  Pack {i+1}: t.me/addstickers/{pn}")
        if UNUPGRADED_SLUGS:
            print(f"  │  Unupgraded: t.me/addstickers/{unupgraded_pack_name}")
            print(f"  │  Unupgraded gifts: {len(UNUPGRADED_SLUGS)}")
        print(f"  └─────────────────────────────────────────────┘")

        confirm = input("\n  Confirm? / Подтвердить? [Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes", "д", "да"):
            break
        print("  Retrying... / Повтор...\n")

    return pack_names, user_title, unupgraded_pack_name


async def main():
    bot = Bot(token=BOT_TOKEN)
    me = await bot.get_me()
    log.info(f"Bot: @{me.username}")

    pack_names, pack_title, unupgraded_pack_name = prompt_pack_settings(me.username)

    await load_gift_images(bot)

    state = load_state()
    state["_pack_title"] = pack_title

    fmt_label = "WebM 512x512 (animated video stickers)" if ANIMATED else "WebP 512x512 (static, auto-refresh)"

    print(f"""
╔══════════════════════════════════════════════════╗
║       MRKT Animated Sticker Pack — Live Updater   ║
╠══════════════════════════════════════════════════╣
║  Bot: @{me.username:<42}║
║  Packs: {NUM_PACKS} x {MAX_STICKERS} stickers                            ║
║  Owner: {OWNER_ID:<41}║
║  Title: {pack_title:<41}║
║  Format: {fmt_label:<40}║
║  Animated: {str(ANIMATED):<38}║
║  Interval: {UPDATE_INTERVAL}s                                    ║
╠══════════════════════════════════════════════════╣""")
    for i, pn in enumerate(pack_names):
        print(f"║  #{i+1}: t.me/addstickers/{pn}")
    if UNUPGRADED_SLUGS:
        print(f"║  Unupgraded: t.me/addstickers/{unupgraded_pack_name}")
    print(f"╚══════════════════════════════════════════════════╝\n")

    cycle = 0
    while True:
        cycle += 1
        log.info(f"{'═' * 40}")
        log.info(f"Cycle #{cycle} — {datetime.now().strftime('%H:%M:%S')}")

        try:
            ton_usd = await fetch_ton_rate()
            collections, expensive_map, exclude_set = await fetch_collections()

            if not collections:
                log.warning("No collections, skipping")
            else:
                log.info(f"Fetched {len(collections)} collections from MRKT, TON=${ton_usd:.2f}")

                # Main packs: exclude only single-version unupgraded slugs
                main_cols = [c for c in collections if c["slug"] not in exclude_set]
                log.info(f"Main packs: {len(main_cols)} collections (excluded {len(exclude_set)} unupgraded)")

                for i, pack_name in enumerate(pack_names):
                    chunk = main_cols[i * MAX_STICKERS : (i + 1) * MAX_STICKERS]
                    if not chunk:
                        break
                    log.info(f"Pack #{i+1} ({pack_name}): {len(chunk)} collections")
                    await sync_sticker_pack(bot, pack_name, chunk, ton_usd, state, i + 1)

                total = sum(len(state.get(pn, {})) for pn in pack_names)
                log.info(f"Total: {total} stickers across {NUM_PACKS} packs")

                # ─── Unupgraded Gems pack (uses most expensive version per slug) ───
                if UNUPGRADED_SLUGS:
                    unupgraded_cols = []
                    for slug in UNUPGRADED_SLUGS:
                        col = expensive_map.get(slug.lower())
                        if col:
                            unupgraded_cols.append(col)
                        else:
                            log.warning(f"Unupgraded gift '{slug}' not found in MRKT")

                    if unupgraded_cols:
                        log.info(f"Unupgraded pack ({unupgraded_pack_name}): "
                                 f"{len(unupgraded_cols)} gifts")
                        await sync_unupgraded_pack(
                            bot, unupgraded_pack_name, unupgraded_cols,
                            ton_usd, state)

        except Exception as e:
            log.error(f"Error: {e}", exc_info=True)

        log.info(f"Next update in {UPDATE_INTERVAL}s...")
        await asyncio.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Остановлен.")
    finally:
        import warnings
        warnings.filterwarnings("ignore", message="Unclosed")
