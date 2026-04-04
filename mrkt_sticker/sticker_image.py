#!/usr/bin/env python3
"""
MRKT Animated Sticker Image Generator / Генератор анимированных стикеров MRKT.

EN: Generates 512x512 sticker cards with live gift price data.
    Supports both static (WebP/PNG) and animated (WebM video) output.
    Animated mode renders frames with Pillow and encodes to WebM via ffmpeg.
    Includes: neon pulse line, collection name, gift thumbnail, USD price
    (colored by trend), change badge, TON/Stars info, supply, watermark,
    and animated visual effects (glow, particles) for growth/drop states.

RU: Создаёт карточки 512x512 с данными о цене подарка.
    Поддерживает статический (WebP/PNG) и анимированный (WebM видео) режимы.
    Анимация: рендер кадров через Pillow + кодирование в WebM через ffmpeg.
    Неоновый пульс, название, миниатюра, цена USD (цвет по тренду),
    плашка изменения, TON/Stars, supply, watermark, анимированные эффекты.
"""

import io
import os
import math
import re
import random
import shutil
import subprocess
import tempfile
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

log = logging.getLogger("mrkt-image")

W, H = 512, 512
WHITE = (255, 255, 255)
GREEN = (0, 220, 110)
RED = (255, 70, 70)
GRAY = (160, 160, 175)
GOLD = (255, 208, 0)
BLUE_TON = (50, 140, 255)
ORANGE = (255, 180, 0)
STAR_USD = 0.015
CORNER = 48

# Animation settings
ANIM_FPS = 30
ANIM_DURATION = 3  # seconds — smoother, longer loop
ANIM_FRAMES = ANIM_FPS * ANIM_DURATION

# Slugs that should show "unboxed" label
UNBOXED_SLUGS = {"ufcstrike"}

# Check ffmpeg availability
HAS_FFMPEG = shutil.which("ffmpeg") is not None
if not HAS_FFMPEG:
    log.warning("ffmpeg not found — animated stickers will fall back to static")


# Ручные override'ы для имён, которые regex не может правильно разбить
SLUG_DISPLAY_NAMES = {
    "durovscap": "DUROV'S CAP",
    "khabibspapakha": "KHABIB'S PAPAKHA",
    "ufcstrike": "UFC STRIKE",
    "snoopdogg": "SNOOP DOGG",
    "plushpepe": "PLUSH PEPE",
    "eternalrose": "ETERNAL ROSE",
    "recordplayer": "RECORD PLAYER",
    "swisswatch": "SWISS WATCH",
    "poolfloat": "POOL FLOAT",
    "moodpack": "MOOD PACK",
    "santahat": "SANTA HAT",
    "heartlocket": "HEART LOCKET",
    "signetring": "SIGNET RING",
    "diamondring": "DIAMOND RING",
    "magicpotion": "MAGIC POTION",
    "lovepotion": "LOVE POTION",
    "sakuraflower": "SAKURA FLOWER",
    "preciouspeach": "PRECIOUS PEACH",
    "kissedfrog": "KISSED FROG",
    "madpumpkin": "MAD PUMPKIN",
    "eternalcandle": "ETERNAL CANDLE",
    "toybear": "TOY BEAR",
    "minioscar": "MINI OSCAR",
    "tophat": "TOP HAT",
    "jesterhat": "JESTER HAT",
    "evileye": "EVIL EYE",
    "hexpot": "HEX POT",
    "scaredcat": "SCARED CAT",
    "skullflower": "SKULL FLOWER",
    "trappedheart": "TRAPPED HEART",
    "homemadecake": "HOMEMADE CAKE",
    "sharptongue": "SHARP TONGUE",
    "spyagaric": "SPY AGARIC",
    "hangingstar": "HANGING STAR",
    "bonedring": "BONED RING",
    "bondedring": "BONDED RING",
    "gingerman": "GINGER MAN",
    "gingercookie": "GINGER COOKIE",
    "jellybunny": "JELLY BUNNY",
    "victorymedal": "VICTORY MEDAL",
    "rarebird": "RARE BIRD",
    "timelessbook": "TIMELESS BOOK",
    "chillflame": "CHILL FLAME",
    "vicecream": "VICE CREAM",
    "jackinthebox": "JACK IN THE BOX",
    "petsnake": "PET SNAKE",
    "snakebox": "SNAKE BOX",
    "easteregg": "EASTER EGG",
}


def format_slug(slug):
    """Превращает camelCase/PascalCase slug в читаемое название."""
    override = SLUG_DISPLAY_NAMES.get(slug.lower())
    if override:
        return override
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', slug)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s)
    return s.upper()


def get_font(size):
    for name in ["DejaVuSans-Bold.ttf", "Inter-Bold.ttf", "arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _center(draw, text, font, y, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, y), text, fill=fill, font=font)


def _fit_font(draw, text, max_width, start_size, min_size=20):
    for size in range(start_size, min_size - 1, -2):
        f = get_font(size)
        bb = draw.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= max_width:
            return f
    return get_font(min_size)


def draw_heartbeat(draw, y_center, accent, alpha=35):
    points = []
    mid = W // 2
    for x in range(20, mid - 70):
        points.append((x, y_center))
    pulse = [
        (mid - 70, y_center),
        (mid - 50, y_center + 15),
        (mid - 35, y_center - 50),
        (mid - 10, y_center + 30),
        (mid + 15, y_center - 22),
        (mid + 35, y_center + 8),
        (mid + 55, y_center),
    ]
    points.extend(pulse)
    for x in range(mid + 55, W - 20):
        points.append((x, y_center))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(*accent, alpha), width=3)
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(*accent, alpha // 4), width=8)


def draw_heartbeat_animated(draw, y_center, accent, alpha=35, progress=1.0):
    """Animated heartbeat — draws only up to `progress` fraction of the line."""
    points = []
    mid = W // 2
    for x in range(20, mid - 70):
        points.append((x, y_center))
    pulse = [
        (mid - 70, y_center),
        (mid - 50, y_center + 15),
        (mid - 35, y_center - 50),
        (mid - 10, y_center + 30),
        (mid + 15, y_center - 22),
        (mid + 35, y_center + 8),
        (mid + 55, y_center),
    ]
    points.extend(pulse)
    for x in range(mid + 55, W - 20):
        points.append((x, y_center))

    n = max(1, int(len(points) * progress))
    for i in range(min(n - 1, len(points) - 1)):
        draw.line([points[i], points[i + 1]], fill=(*accent, alpha), width=3)
    for i in range(min(n - 1, len(points) - 1)):
        draw.line([points[i], points[i + 1]], fill=(*accent, alpha // 4), width=8)


def draw_top_pulse(img, yc, accent):
    """Неоновая линия пульса вверху карточки с ярким свечением."""
    mid = W // 2
    left = CORNER + 20
    right = W - CORNER - 20
    pts = []
    for x in range(left, mid - 25):
        pts.append((x, yc))
    pts += [
        (mid - 25, yc), (mid - 15, yc + 5), (mid - 8, yc - 14),
        (mid, yc + 9), (mid + 8, yc - 7), (mid + 15, yc + 3),
        (mid + 25, yc),
    ]
    for x in range(mid + 25, right + 1):
        pts.append((x, yc))

    glow3 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(glow3)
    for i in range(len(pts) - 1):
        d3.line([pts[i], pts[i + 1]], fill=(*accent, 80), width=20)
    glow3 = glow3.filter(ImageFilter.GaussianBlur(radius=10))
    img = Image.alpha_composite(img, glow3)

    glow2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(glow2)
    for i in range(len(pts) - 1):
        d2.line([pts[i], pts[i + 1]], fill=(*accent, 140), width=10)
    glow2 = glow2.filter(ImageFilter.GaussianBlur(radius=5))
    img = Image.alpha_composite(img, glow2)

    glow1 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(glow1)
    for i in range(len(pts) - 1):
        d1.line([pts[i], pts[i + 1]], fill=(*accent, 200), width=6)
    glow1 = glow1.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.alpha_composite(img, glow1)

    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(core)
    bright = (min(accent[0] + 180, 255), min(accent[1] + 180, 255), min(accent[2] + 180, 255))
    for i in range(len(pts) - 1):
        dc.line([pts[i], pts[i + 1]], fill=(*bright, 255), width=2)
    img = Image.alpha_composite(img, core)

    return img


def draw_top_pulse_animated(img, yc, accent, spot_pos=0.0):
    """Animated neon pulse with a bright spot traveling along the line."""
    mid = W // 2
    left = CORNER + 20
    right = W - CORNER - 20
    pts = []
    for x in range(left, mid - 25):
        pts.append((x, yc))
    pts += [
        (mid - 25, yc), (mid - 15, yc + 5), (mid - 8, yc - 14),
        (mid, yc + 9), (mid + 8, yc - 7), (mid + 15, yc + 3),
        (mid + 25, yc),
    ]
    for x in range(mid + 25, right + 1):
        pts.append((x, yc))

    total = len(pts)
    spot_idx = int(spot_pos * total) % total

    # Base glow (dimmer)
    glow3 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(glow3)
    for i in range(total - 1):
        d3.line([pts[i], pts[i + 1]], fill=(*accent, 40), width=14)
    glow3 = glow3.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img, glow3)

    # Core line (dimmer)
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(core)
    bright = (min(accent[0] + 180, 255), min(accent[1] + 180, 255), min(accent[2] + 180, 255))
    for i in range(total - 1):
        dc.line([pts[i], pts[i + 1]], fill=(*bright, 120), width=2)
    img = Image.alpha_composite(img, core)

    # Bright traveling spot
    spot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(spot)
    spot_range = 30
    for i in range(max(0, spot_idx - spot_range), min(total - 1, spot_idx + spot_range)):
        dist = abs(i - spot_idx)
        intensity = max(0, 1.0 - dist / spot_range)
        intensity = intensity * intensity
        a = int(intensity * 255)
        w = int(2 + intensity * 12)
        ds.line([pts[i], pts[min(i + 1, total - 1)]], fill=(*accent, a), width=w)
    spot = spot.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.alpha_composite(img, spot)

    # White-hot center of spot
    if 0 <= spot_idx < total:
        hot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dh = ImageDraw.Draw(hot)
        for i in range(max(0, spot_idx - 5), min(total - 1, spot_idx + 5)):
            dist = abs(i - spot_idx)
            a = int((1.0 - dist / 5) * 255)
            dh.line([pts[i], pts[min(i + 1, total - 1)]], fill=(255, 255, 255, a), width=3)
        img = Image.alpha_composite(img, hot)

    return img


def _make_border_ring(color, thickness, radius=CORNER):
    """Create a uniform-thickness ring using a grayscale mask.

    Draws outer filled rounded rect on a mask, then draws inner filled
    rounded rect with black to punch a hole. The mask becomes the alpha
    channel of a solid-color layer. Result: perfectly uniform ring.
    """
    # Build ring mask (white = visible, black = transparent)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    # Outer shape — white
    md.rounded_rectangle([0, 0, W - 1, H - 1], radius=radius, fill=255)
    # Inner cutout — black (this DOES work on grayscale "L" mode)
    inner_r = max(radius - thickness, 0)
    md.rounded_rectangle(
        [thickness, thickness, W - 1 - thickness, H - 1 - thickness],
        radius=inner_r, fill=0,
    )
    # Create colored layer and apply mask as alpha
    # color can be (r, g, b, a) — we scale mask by the alpha component
    if len(color) == 4:
        r, g, b, a = color
        solid = Image.new("RGBA", (W, H), (r, g, b, 255))
        # Scale mask by target alpha
        from PIL import ImageEnhance
        mask = mask.point(lambda p: int(p * a / 255))
    else:
        solid = Image.new("RGBA", (W, H), (*color, 255))
    solid.putalpha(mask)
    return solid


def draw_border_glow(img, intensity=1.0, accent=None):
    """Uniform perimeter glow — equal thickness including rounded corners.

    Uses filled-rect subtraction instead of outline to avoid Pillow's
    corner thinning artifact. Color adapts to trend.
    """
    if accent is None:
        accent = GOLD

    bright = (min(accent[0] + 60, 255), min(accent[1] + 60, 255), min(accent[2] + 60, 255))

    # ── Card-shape mask for clipping ──
    card_mask = Image.new("L", (W, H), 0)
    mask_draw = ImageDraw.Draw(card_mask)
    mask_draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=CORNER, fill=255)

    def _clip(layer):
        r, g, b, a = layer.split()
        return Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, card_mask)))

    # ── Layer 1: Wide bloom (thick ring, heavy blur) ──
    a1 = int(100 * intensity)
    ring1 = _make_border_ring((accent[0], accent[1], accent[2], a1), 22)
    ring1 = ring1.filter(ImageFilter.GaussianBlur(radius=24))
    img = Image.alpha_composite(img, _clip(ring1))

    # ── Layer 2: Mid glow ──
    a2 = int(150 * intensity)
    ring2 = _make_border_ring((accent[0], accent[1], accent[2], a2), 14)
    ring2 = ring2.filter(ImageFilter.GaussianBlur(radius=12))
    img = Image.alpha_composite(img, _clip(ring2))

    # ── Layer 3: Inner glow (bright, tight) ──
    a3 = int(220 * intensity)
    ring3 = _make_border_ring((accent[0], accent[1], accent[2], a3), 8)
    ring3 = ring3.filter(ImageFilter.GaussianBlur(radius=5))
    img = Image.alpha_composite(img, _clip(ring3))

    # ── Layer 4: Hot edge ──
    a4 = int(240 * intensity)
    ring4 = _make_border_ring((*bright, a4), 5)
    ring4 = ring4.filter(ImageFilter.GaussianBlur(radius=1))
    img = Image.alpha_composite(img, _clip(ring4))

    return img


def _draw_shimmer_text(draw, text, font, y, base_color, shimmer_pos):
    """Draw text with a golden shimmer wave traveling letter by letter.

    shimmer_pos: 0.0-1.0, position of the shimmer highlight in the text.
    """
    # Measure total width to center
    bb = draw.textbbox((0, 0), text, font=font)
    total_w = bb[2] - bb[0]
    x = (W - total_w) // 2

    num_chars = len(text)
    if num_chars == 0:
        return

    # Draw each character with individual color based on shimmer wave
    for i, ch in enumerate(text):
        char_pos = i / max(num_chars - 1, 1)  # 0.0 to 1.0
        # Distance from shimmer center (wrapping)
        dist = abs(char_pos - shimmer_pos)
        dist = min(dist, 1.0 - dist)  # wrap around
        # Shimmer falloff — wider and softer
        shimmer = max(0, 1.0 - dist * 5.0)
        shimmer = shimmer * shimmer  # ease-in

        # Interpolate from base_color toward bright white-gold
        r = int(base_color[0] + (255 - base_color[0]) * shimmer)
        g = int(base_color[1] + (255 - base_color[1]) * shimmer)
        b = int(base_color[2] + (min(200, base_color[2] + 100) - base_color[2]) * shimmer)
        color = (r, g, b)

        draw.text((x, y), ch, fill=color, font=font)
        ch_bb = draw.textbbox((0, 0), ch, font=font)
        x += ch_bb[2] - ch_bb[0]


def draw_gold_glow(img, alpha_mult=1.0):
    """Золотистое свечение в верхней части карточки (зона картинки подарка)."""
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W // 2, 130
    for y in range(H):
        for x in range(W):
            dist = math.sqrt((x - cx) ** 2 + ((y - cy) * 1.2) ** 2)
            if dist < 160:
                t = 1.0 - (dist / 160)
                t = t * t * t
                a = int(t * 50 * alpha_mult)
                glow.putpixel((x, y), (GOLD[0], GOLD[1], GOLD[2], a))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    return Image.alpha_composite(img, glow)


def draw_mrkt_watermark(img):
    """Диагональный MRKT watermark на заднем фоне."""
    f = get_font(270)
    text = "MRKT"
    tmp = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]

    txt_layer = Image.new("RGBA", (tw + 80, th + 80), (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_layer)
    txt_draw.text((40, 40), text, font=f, fill=(42, 42, 42, 255))

    rotated = txt_layer.rotate(55, expand=True, resample=Image.BICUBIC)

    wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rx, ry = rotated.size
    wm.paste(rotated, ((W - rx) // 2 - 5, (H - ry) // 2 + 10), rotated)

    mask = Image.new("L", (W, H), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([4, 4, W - 5, H - 5], radius=CORNER - 2, fill=255)
    wm_r, wm_g, wm_b, wm_a = wm.split()
    clipped_a = ImageChops.multiply(wm_a, mask)
    wm = Image.merge("RGBA", (wm_r, wm_g, wm_b, clipped_a))

    return Image.alpha_composite(img, wm)


def draw_growth_effects(img, accent, y_offset=0):
    """Эффекты роста: свечение за ценой + искры/частицы вверх."""
    fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fx)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W // 2, 270
    for y in range(H):
        for x in range(W):
            dist = math.sqrt((x - cx) ** 2 + ((y - cy) * 1.5) ** 2)
            if dist < 140:
                t = 1.0 - (dist / 140)
                t = t * t
                a = int(t * 40)
                glow.putpixel((x, y), (accent[0], accent[1], accent[2], a))
    fx = Image.alpha_composite(fx, glow)
    draw = ImageDraw.Draw(fx)

    random.seed(42)
    for _ in range(18):
        x = random.randint(80, W - 80)
        y = random.randint(180, 310) + y_offset
        y = max(0, min(H - 1, y))
        size = random.randint(2, 5)
        alpha = random.randint(60, 160)
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(accent[0], accent[1], accent[2], alpha))

    for _ in range(8):
        x = random.randint(100, W - 100)
        y = random.randint(200, 300) + y_offset
        y = max(0, min(H - 10, y))
        length = random.randint(8, 20)
        alpha = random.randint(50, 120)
        draw.line([(x, y), (x, y - length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x - 3, y - length + 4), (x, y - length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x + 3, y - length + 4), (x, y - length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)

    return Image.alpha_composite(img, fx)


def draw_drop_effects(img, accent, y_offset=0):
    """Эффекты падения: красное свечение + частицы вниз."""
    fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fx)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W // 2, 270
    for y in range(H):
        for x in range(W):
            dist = math.sqrt((x - cx) ** 2 + ((y - cy) * 1.5) ** 2)
            if dist < 140:
                t = 1.0 - (dist / 140)
                t = t * t
                a = int(t * 40)
                glow.putpixel((x, y), (accent[0], accent[1], accent[2], a))
    fx = Image.alpha_composite(fx, glow)
    draw = ImageDraw.Draw(fx)

    random.seed(42)
    for _ in range(18):
        x = random.randint(80, W - 80)
        y = random.randint(200, 320) + y_offset
        y = max(0, min(H - 1, y))
        size = random.randint(2, 5)
        alpha = random.randint(60, 160)
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(accent[0], accent[1], accent[2], alpha))

    for _ in range(8):
        x = random.randint(100, W - 100)
        y = random.randint(210, 300) + y_offset
        y = max(0, min(H - 10, y))
        length = random.randint(8, 20)
        alpha = random.randint(50, 120)
        draw.line([(x, y), (x, y + length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x - 3, y + length - 4), (x, y + length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x + 3, y + length - 4), (x, y + length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)

    return Image.alpha_composite(img, fx)


# ─── Static base layer (reusable across frames) ─────────────────

def _build_base_layer(col, ton_usd, accent, change):
    """Build the static parts of the card that don't change per frame."""
    slug = col.get("slug", "???")
    floor = col.get("floor_price", 0)
    supply = col.get("supply") or col.get("total_supply") or col.get("total_count")
    usd = floor * ton_usd
    stars = int(usd / STAR_USD) if STAR_USD > 0 else 0

    # Background with rounded corners
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=CORNER, fill=(0, 0, 0, 255))
    # Border — same coords/radius as fill, drawn ON TOP so it's perfectly aligned
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=CORNER, outline=GOLD, width=4)

    # MRKT watermark
    img = draw_mrkt_watermark(img)

    draw = ImageDraw.Draw(img)

    # NOTE: Collection name is drawn per-frame with shimmer animation
    # (not here in the base layer)

    # USD Price
    price_text = f"${usd:,.2f}"
    f_price = _fit_font(draw, price_text, W - 50, 70, 36)
    if change is not None and change > 0.01:
        price_color = GREEN
    elif change is not None and change < -0.01:
        price_color = RED
    else:
        price_color = WHITE
    _center(draw, price_text, f_price, 242, price_color)

    # Change pill
    f_chg = get_font(30)
    cy = 320
    ch = 42
    if change is not None and change > 0.01:
        chg_text = f"\u2197 +{change:.1f}%"
    elif change is not None and change < -0.01:
        chg_text = f"\u2198 {change:.1f}%"
    else:
        chg_text = "\u2014 0.0%"
    cbb = draw.textbbox((0, 0), chg_text, font=f_chg)
    cw = cbb[2] - cbb[0] + 32
    cx = (W - cw) // 2
    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=ch // 2,
                            fill=(accent[0] // 8, accent[1] // 8, accent[2] // 8, 255),
                            outline=(*accent, 140), width=2)
    _center(draw, chg_text, f_chg, cy + 5, accent)

    # Info line: ton (blue) + stars (orange)
    f_info = get_font(26)
    info_y = 378
    ton_s = f"{floor:,.2f}" if floor < 10000 else f"{floor:,.0f}"
    ton_part = f"{ton_s} ton"
    stars_part = f"{stars:,} \u2605"
    ton_bb = draw.textbbox((0, 0), ton_part, font=f_info)
    gap_bb = draw.textbbox((0, 0), "   ", font=f_info)
    stars_bb = draw.textbbox((0, 0), stars_part, font=f_info)
    ton_w = ton_bb[2] - ton_bb[0]
    gap_w = gap_bb[2] - gap_bb[0]
    stars_w = stars_bb[2] - stars_bb[0]
    sx = (W - (ton_w + gap_w + stars_w)) // 2
    draw.text((sx, info_y), ton_part, fill=BLUE_TON, font=f_info)
    draw.text((sx + ton_w + gap_w, info_y), stars_part, fill=ORANGE, font=f_info)

    # Supply
    try:
        supply_i = int(supply) if supply else 0
        supply_s = f"{supply_i:,} pcs" if supply_i > 0 else None
    except (ValueError, TypeError):
        supply_s = None
    if supply_s:
        _center(draw, f"Supply: {supply_s}", get_font(24), info_y + 36, GRAY)

    # Unboxed label
    if slug.lower() in UNBOXED_SLUGS:
        _center(draw, "unboxed", get_font(20), info_y + 62, GRAY)

    # Date
    now_str = datetime.now().strftime("%d %b %Y  %H:%M UTC")
    _center(draw, now_str, get_font(22), H - 42, GOLD)

    return img


def _render_frame(base_img, frame_num, total_frames, accent, change, gift_img, col):
    """Render a single animation frame with animated effects on top of base."""
    t = frame_num / total_frames  # 0.0 to 1.0
    img = base_img.copy()

    # 1. Animated border glow — very slow breathing (one half-cycle per 3s loop)
    border_intensity = 0.5 + 0.5 * math.sin(t * math.pi)
    img = draw_border_glow(img, intensity=border_intensity, accent=accent)

    # 2. Animated gold glow (same slow pace, slight phase offset)
    breath = 0.5 + 0.5 * math.sin(t * math.pi + 0.3)
    img = draw_gold_glow(img, alpha_mult=breath)

    # 3. Animated growth/drop particles (slow smooth drift)
    if change is not None and change > 0.01:
        drift = int(-20 * math.sin(t * math.pi))  # smooth up and reset
        img = draw_growth_effects(img, accent, y_offset=drift)
    elif change is not None and change < -0.01:
        drift = int(20 * math.sin(t * math.pi))  # smooth down and reset
        img = draw_drop_effects(img, accent, y_offset=drift)

    draw = ImageDraw.Draw(img)

    # 4. Collection name with letter-by-letter golden shimmer
    slug = col.get("slug", "???")
    display_name = format_slug(slug)
    name_font = _fit_font(draw, display_name, W - 50, 44, 24)
    shimmer_pos = t % 1.0  # one full pass per loop (slow)
    _draw_shimmer_text(draw, display_name, name_font, 44, GOLD, shimmer_pos)

    # 5. Animated heartbeat (one slow draw per full loop)
    hb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hb_progress = t  # one complete draw over the full 3s loop
    hb_progress = min(1.0, hb_progress * 1.15)  # slight acceleration, pause at end
    draw_heartbeat_animated(ImageDraw.Draw(hb), 235, accent, 30, progress=hb_progress)
    img = Image.alpha_composite(img, hb)

    # 6. Animated neon pulse line (slow traveling spot)
    img = draw_top_pulse_animated(img, 28, accent, spot_pos=t)
    draw = ImageDraw.Draw(img)

    # 7. Gift image with gentle slow bob
    if gift_img:
        thumb_size = 140
        try:
            gift_resized = gift_img.copy().resize((thumb_size, thumb_size), Image.LANCZOS)
            if gift_resized.mode != "RGBA":
                gift_resized = gift_resized.convert("RGBA")
            bob_y = int(3 * math.sin(t * 2 * math.pi))
            img.paste(gift_resized, ((W - thumb_size) // 2, 86 + bob_y), gift_resized)
        except Exception:
            pass

    return img


def _encode_webm(frame_dir, num_frames):
    """Encode PNG frames to WebM video using ffmpeg."""
    output = os.path.join(frame_dir, "output.webm")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(ANIM_FPS),
        "-i", os.path.join(frame_dir, "%04d.png"),
        "-c:v", "libvpx-vp9",
        "-b:v", "0",
        "-crf", "50",
        "-pix_fmt", "yuva420p",
        "-auto-alt-ref", "0",
        "-deadline", "good",
        "-cpu-used", "5",
        "-row-mt", "1",
        "-an",
        "-t", str(ANIM_DURATION),
        output
    ]
    subprocess.run(cmd, check=True, timeout=60)

    with open(output, "rb") as f:
        data = f.read()

    # If too large (>256KB), retry with lower quality
    if len(data) > 256 * 1024:
        cmd2 = cmd.copy()
        for i, arg in enumerate(cmd2):
            if arg == "50":
                cmd2[i] = "58"
        subprocess.run(cmd2, check=True, timeout=60)
        with open(output, "rb") as f:
            data = f.read()

    return data


# ─── Main entry point ────────────────────────────────────────────

def generate_sticker(col, ton_usd=7.2, fmt="WEBP", gift_img=None, animated=False):
    """Generate a sticker card.

    Args:
        col: Collection data dict with slug, floor_price, supply, change_24h etc.
        ton_usd: Current TON/USD exchange rate.
        fmt: Output format — "WEBP", "PNG", or "WEBM" (for animated).
        gift_img: Optional PIL.Image of the gift thumbnail.
        animated: If True, generate animated WebM video sticker.

    Returns:
        bytes: Image/video data.
    """
    slug = col.get("slug", "???")
    floor = col.get("floor_price", 0)

    change = col.get("change_24h")
    if change is None:
        prev1d = col.get("floor_price_prev1day")
        if prev1d and prev1d > 0 and floor > 0:
            change = round(((floor - prev1d) / prev1d) * 100, 1)
        elif col.get("price_change_24h") is not None:
            change = col.get("price_change_24h")

    if change is not None and change > 0.01:
        accent = GREEN
    elif change is not None and change < -0.01:
        accent = RED
    else:
        accent = GOLD

    # ── Animated mode ──
    if animated and HAS_FFMPEG:
        return _generate_animated(col, ton_usd, accent, change, gift_img)

    # ── Static mode (original behavior) ──
    return _generate_static(col, ton_usd, fmt, gift_img, accent, change)


def _generate_static(col, ton_usd, fmt, gift_img, accent, change):
    """Generate static sticker — original behavior."""
    slug = col.get("slug", "???")
    floor = col.get("floor_price", 0)
    supply = col.get("supply") or col.get("total_supply") or col.get("total_count")
    usd = floor * ton_usd
    stars = int(usd / STAR_USD) if STAR_USD > 0 else 0

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=CORNER, fill=(0, 0, 0, 255))
    draw.rounded_rectangle([2, 2, W - 3, H - 3], radius=CORNER - 2, outline=GOLD, width=5)

    img = draw_mrkt_watermark(img)
    img = draw_gold_glow(img)

    if change is not None and change > 0.01:
        img = draw_growth_effects(img, accent)
    elif change is not None and change < -0.01:
        img = draw_drop_effects(img, accent)

    draw = ImageDraw.Draw(img)

    hb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_heartbeat(ImageDraw.Draw(hb), 235, accent, 30)
    img = Image.alpha_composite(img, hb)

    img = draw_top_pulse(img, 28, accent)
    draw = ImageDraw.Draw(img)

    display_name = format_slug(slug)
    _center(draw, display_name, _fit_font(draw, display_name, W - 50, 44, 24), 44, GOLD)

    if gift_img:
        thumb_size = 140
        try:
            gift_resized = gift_img.copy().resize((thumb_size, thumb_size), Image.LANCZOS)
            if gift_resized.mode != "RGBA":
                gift_resized = gift_resized.convert("RGBA")
            img.paste(gift_resized, ((W - thumb_size) // 2, 86), gift_resized)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    price_text = f"${usd:,.2f}"
    f_price = _fit_font(draw, price_text, W - 50, 70, 36)
    if change is not None and change > 0.01:
        price_color = GREEN
    elif change is not None and change < -0.01:
        price_color = RED
    else:
        price_color = WHITE
    _center(draw, price_text, f_price, 242, price_color)

    f_chg = get_font(30)
    cy = 320
    ch = 42
    if change is not None and change > 0.01:
        chg_text = f"\u2197 +{change:.1f}%"
    elif change is not None and change < -0.01:
        chg_text = f"\u2198 {change:.1f}%"
    else:
        chg_text = "\u2014 0.0%"
    cbb = draw.textbbox((0, 0), chg_text, font=f_chg)
    cw = cbb[2] - cbb[0] + 32
    cx = (W - cw) // 2
    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=ch // 2,
                            fill=(accent[0] // 8, accent[1] // 8, accent[2] // 8, 255),
                            outline=(*accent, 140), width=2)
    _center(draw, chg_text, f_chg, cy + 5, accent)

    f_info = get_font(26)
    info_y = 378
    ton_s = f"{floor:,.2f}" if floor < 10000 else f"{floor:,.0f}"
    ton_part = f"{ton_s} ton"
    stars_part = f"{stars:,} \u2605"
    ton_bb = draw.textbbox((0, 0), ton_part, font=f_info)
    gap_bb = draw.textbbox((0, 0), "   ", font=f_info)
    stars_bb = draw.textbbox((0, 0), stars_part, font=f_info)
    ton_w = ton_bb[2] - ton_bb[0]
    gap_w = gap_bb[2] - gap_bb[0]
    stars_w = stars_bb[2] - stars_bb[0]
    sx = (W - (ton_w + gap_w + stars_w)) // 2
    draw.text((sx, info_y), ton_part, fill=BLUE_TON, font=f_info)
    draw.text((sx + ton_w + gap_w, info_y), stars_part, fill=ORANGE, font=f_info)

    try:
        supply_i = int(supply) if supply else 0
        supply_s = f"{supply_i:,} pcs" if supply_i > 0 else None
    except (ValueError, TypeError):
        supply_s = None
    if supply_s:
        _center(draw, f"Supply: {supply_s}", get_font(24), info_y + 36, GRAY)

    if slug.lower() in UNBOXED_SLUGS:
        _center(draw, "unboxed", get_font(20), info_y + 62, GRAY)

    now_str = datetime.now().strftime("%d %b %Y  %H:%M UTC")
    _center(draw, now_str, get_font(22), H - 42, GOLD)

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


def _generate_animated(col, ton_usd, accent, change, gift_img):
    """Generate animated WebM video sticker."""
    # Build static base layer (text, border, watermark, prices — don't change per frame)
    base = _build_base_layer(col, ton_usd, accent, change)

    tmp_dir = tempfile.mkdtemp(prefix="mrkt_anim_")
    try:
        # Render frames
        for i in range(ANIM_FRAMES):
            frame = _render_frame(base, i, ANIM_FRAMES, accent, change, gift_img, col)
            frame_path = os.path.join(tmp_dir, f"{i:04d}.png")
            frame.save(frame_path, format="PNG")

        # Encode to WebM
        webm_data = _encode_webm(tmp_dir, ANIM_FRAMES)
        log.info(f"Animated sticker: {len(webm_data) / 1024:.1f} KB")
        return webm_data

    finally:
        # Cleanup
        shutil.rmtree(tmp_dir, ignore_errors=True)
