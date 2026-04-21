#!/usr/bin/env python3
"""
Generate 8 different MRKT-style sticker designs for Plush Pepe.
Run: python generate_designs.py
Output: design_1.png ... design_8.png in current directory.
"""
import io
import math
import os
import random
import urllib.request
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 512, 512
GOLD = (255, 208, 0)
WHITE = (255, 255, 255)
GREEN = (0, 220, 110)
BLUE_TON = (50, 140, 255)
ORANGE = (255, 180, 0)
GRAY = (160, 160, 175)
BLACK = (0, 0, 0)
CORNER = 48

# Sample data
COL = {
    "slug": "plushpepe",
    "floor_price": 6120.50,
    "change_24h": 3.2,
    "supply": 5000,
}
TON_USD = 1.26
STAR_USD = 0.015


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


def _fit_font(draw, text, max_w, start, min_s=20):
    for sz in range(start, min_s - 1, -2):
        f = get_font(sz)
        bb = draw.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= max_w:
            return f
    return get_font(min_s)


def _make_ring(color, thickness, radius=CORNER):
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, W-1, H-1], radius=radius, fill=255)
    inner_r = max(radius - thickness, 0)
    md.rounded_rectangle([thickness, thickness, W-1-thickness, H-1-thickness], radius=inner_r, fill=0)
    if len(color) == 4:
        r, g, b, a = color
        solid = Image.new("RGBA", (W, H), (r, g, b, 255))
        mask = mask.point(lambda p: int(p * a / 255))
    else:
        solid = Image.new("RGBA", (W, H), (*color, 255))
    solid.putalpha(mask)
    return solid


def _card_mask():
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, W-1, H-1], radius=CORNER, fill=255)
    return m


def _clip(layer, card_mask):
    r, g, b, a = layer.split()
    return Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, card_mask)))


def border_glow(img, accent=GOLD, intensity=1.0):
    cm = _card_mask()
    for thick, blur, alpha in [(22, 24, 100), (14, 12, 150), (8, 5, 220), (5, 1, 240)]:
        a = int(alpha * intensity)
        ring = _make_ring((*accent, a), thick)
        ring = ring.filter(ImageFilter.GaussianBlur(radius=blur))
        img = Image.alpha_composite(img, _clip(ring, cm))
    return img


def mrkt_watermark(img, text="MRKT", alpha=255):
    f = get_font(270)
    tmp = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    txt = Image.new("RGBA", (tw+80, th+80), (0,0,0,0))
    ImageDraw.Draw(txt).text((40,40), text, font=f, fill=(42,42,42,alpha))
    rot = txt.rotate(55, expand=True, resample=Image.BICUBIC)
    wm = Image.new("RGBA", (W, H), (0,0,0,0))
    rx, ry = rot.size
    wm.paste(rot, ((W-rx)//2-5, (H-ry)//2+10), rot)
    m = Image.new("L", (W,H), 0)
    ImageDraw.Draw(m).rounded_rectangle([4,4,W-5,H-5], radius=CORNER-2, fill=255)
    wr,wg,wb,wa = wm.split()
    wm = Image.merge("RGBA", (wr,wg,wb, ImageChops.multiply(wa, m)))
    return Image.alpha_composite(img, wm)


def load_gift_img():
    """Load plushpepe image — from cache or download from CDN."""
    cache_dir = "gift_cache"
    path = os.path.join(cache_dir, "plushpepe.png")
    if os.path.exists(path):
        return Image.open(path).copy()
    # Download from changes.tg CDN
    url = "https://api.changes.tg/original/5936013938331222567.png"
    print(f"Downloading plushpepe image from CDN...")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        data = urllib.request.urlopen(url, timeout=15).read()
        with open(path, "wb") as f:
            f.write(data)
        print(f"  Saved to {path} ({len(data)} bytes)")
        return Image.open(io.BytesIO(data)).copy()
    except Exception as e:
        print(f"  Failed to download: {e}")
        return None


def paste_gift(img, gift_img, y=86, size=140):
    if gift_img:
        g = gift_img.copy().resize((size, size), Image.LANCZOS)
        if g.mode != "RGBA":
            g = g.convert("RGBA")
        img.paste(g, ((W-size)//2, y), g)
    return img


def common_data():
    floor = COL["floor_price"]
    usd = floor * TON_USD
    change = COL["change_24h"]
    stars = int(usd / STAR_USD)
    supply = COL["supply"]
    return floor, usd, change, stars, supply


# ════════════════════════════════════════════════════════════════
# Design 1: Original MRKT style (current production design)
# ════════════════════════════════════════════════════════════════
def design_1(gift_img):
    floor, usd, change, stars, supply = common_data()
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, fill=BLACK)
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, outline=GOLD, width=4)
    img = mrkt_watermark(img)
    img = border_glow(img)
    draw = ImageDraw.Draw(img)

    _center(draw, "PLUSH PEPE", get_font(40), 44, GOLD)
    img = paste_gift(img, gift_img, 86, 140)
    _center(draw, f"${usd:,.2f}", _fit_font(draw, f"${usd:,.2f}", W-50, 70, 36), 242, GREEN)

    # Change pill
    f_chg = get_font(30)
    chg_text = f"\u2197 +{change:.1f}%"
    cbb = draw.textbbox((0,0), chg_text, font=f_chg)
    cw = cbb[2]-cbb[0]+32
    cx = (W-cw)//2
    draw.rounded_rectangle([cx,320,cx+cw,362], radius=21, fill=(0,28,0), outline=(*GREEN,140), width=2)
    _center(draw, chg_text, f_chg, 325, GREEN)

    f_info = get_font(26)
    ton_s = f"{floor:,.2f} ton"
    stars_s = f"{stars:,} \u2605"
    tbb = draw.textbbox((0,0), ton_s, font=f_info)
    sbb = draw.textbbox((0,0), stars_s, font=f_info)
    tw = tbb[2]-tbb[0]; sw = sbb[2]-sbb[0]
    sx = (W-(tw+20+sw))//2
    draw.text((sx, 378), ton_s, fill=BLUE_TON, font=f_info)
    draw.text((sx+tw+20, 378), stars_s, fill=ORANGE, font=f_info)
    _center(draw, f"Supply: {supply:,} pcs", get_font(24), 414, GRAY)
    _center(draw, datetime.now().strftime("%d %b %Y  %H:%M UTC"), get_font(22), H-42, GOLD)
    return img


# ════════════════════════════════════════════════════════════════
# Design 2: Centered big price, gift on the left side
# ════════════════════════════════════════════════════════════════
def design_2(gift_img):
    floor, usd, change, stars, supply = common_data()
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, fill=(10,10,15))
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, outline=GOLD, width=3)
    img = mrkt_watermark(img)
    img = border_glow(img, intensity=0.7)
    draw = ImageDraw.Draw(img)

    # Top bar with name
    draw.rounded_rectangle([20, 16, W-20, 60], radius=20, fill=(30,30,10), outline=(*GOLD,100), width=2)
    _center(draw, "PLUSH PEPE", get_font(28), 22, GOLD)

    # Gift image left + big price right
    if gift_img:
        g = gift_img.copy().resize((160, 160), Image.LANCZOS).convert("RGBA")
        img.paste(g, (30, 80), g)
    draw = ImageDraw.Draw(img)

    # Big price on the right
    price_text = f"${usd:,.2f}"
    pf = _fit_font(draw, price_text, 280, 52, 30)
    pbb = draw.textbbox((0,0), price_text, font=pf)
    pw = pbb[2]-pbb[0]
    draw.text((W-pw-40, 110), price_text, fill=WHITE, font=pf)

    # Change below price
    chg_text = f"+{change:.1f}%"
    draw.text((W-140, 170), chg_text, fill=GREEN, font=get_font(30))

    # Divider line
    draw.line([(30, 260), (W-30, 260)], fill=(*GOLD, 80), width=2)

    # Stats grid
    f_label = get_font(20)
    f_val = get_font(26)
    col1x, col2x = 60, W//2 + 30

    draw.text((col1x, 280), "FLOOR", fill=GRAY, font=f_label)
    draw.text((col1x, 305), f"{floor:,.2f} TON", fill=BLUE_TON, font=f_val)

    draw.text((col2x, 280), "STARS", fill=GRAY, font=f_label)
    draw.text((col2x, 305), f"{stars:,} \u2605", fill=ORANGE, font=f_val)

    draw.text((col1x, 355), "SUPPLY", fill=GRAY, font=f_label)
    draw.text((col1x, 380), f"{supply:,}", fill=WHITE, font=f_val)

    draw.text((col2x, 355), "24H", fill=GRAY, font=f_label)
    draw.text((col2x, 380), f"+{change:.1f}%", fill=GREEN, font=f_val)

    # Bottom
    _center(draw, datetime.now().strftime("%d %b %Y  %H:%M UTC"), get_font(20), H-38, (*GOLD, 180))
    return img


# ════════════════════════════════════════════════════════════════
# Design 3: Ticket/receipt style with dashed line
# ════════════════════════════════════════════════════════════════
def design_3(gift_img):
    floor, usd, change, stars, supply = common_data()
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, fill=(15,12,8))
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, outline=GOLD, width=3)
    img = mrkt_watermark(img)
    draw = ImageDraw.Draw(img)

    # Title strip
    draw.rectangle([0, 14, W, 62], fill=(*GOLD, 255))
    _center(draw, "MRKT PRICE TICKET", get_font(30), 22, BLACK)

    # Gift centered
    img = paste_gift(img, gift_img, 76, 120)
    draw = ImageDraw.Draw(img)
    _center(draw, "PLUSH PEPE", get_font(32), 204, GOLD)

    # Dashed divider
    for x in range(30, W-30, 16):
        draw.line([(x, 248), (x+8, 248)], fill=(*GOLD, 120), width=2)

    # Price section
    _center(draw, f"${usd:,.2f}", get_font(58), 262, WHITE)

    # Another dashed divider
    for x in range(30, W-30, 16):
        draw.line([(x, 336), (x+8, 336)], fill=(*GOLD, 120), width=2)

    # Details
    f = get_font(24)
    items = [
        ("Floor:", f"{floor:,.2f} TON", BLUE_TON),
        ("Stars:", f"{stars:,} \u2605", ORANGE),
        ("Supply:", f"{supply:,} pcs", GRAY),
        ("24h:", f"+{change:.1f}%", GREEN),
    ]
    y = 350
    for label, val, color in items:
        draw.text((60, y), label, fill=GRAY, font=f)
        draw.text((W-60-draw.textbbox((0,0), val, font=f)[2], y), val, fill=color, font=f)
        y += 32

    _center(draw, datetime.now().strftime("%d %b %Y  %H:%M UTC"), get_font(20), H-36, (*GOLD, 160))
    return img


# ════════════════════════════════════════════════════════════════
# Design 4: Diamond/premium card with double border
# ════════════════════════════════════════════════════════════════
def design_4(gift_img):
    floor, usd, change, stars, supply = common_data()
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, fill=(5,5,12))
    # Double border
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, outline=GOLD, width=4)
    draw.rounded_rectangle([8,8,W-9,H-9], radius=CORNER-6, outline=(*GOLD,100), width=2)
    img = mrkt_watermark(img)
    img = border_glow(img, intensity=1.2)
    draw = ImageDraw.Draw(img)

    # Crown/diamond icon
    _center(draw, "\u2666 PLUSH PEPE \u2666", get_font(34), 28, GOLD)

    # Big gift image
    img = paste_gift(img, gift_img, 72, 160)
    draw = ImageDraw.Draw(img)

    # Huge price
    price_text = f"${usd:,.2f}"
    _center(draw, price_text, _fit_font(draw, price_text, W-40, 72, 40), 245, WHITE)

    # Accent line under price
    lw = 200
    draw.line([(W//2-lw//2, 322), (W//2+lw//2, 322)], fill=GOLD, width=3)

    # Change + TON on one line
    f = get_font(28)
    line = f"{floor:,.2f} TON  |  +{change:.1f}%  |  {stars:,}\u2605"
    lf = _fit_font(draw, line, W-60, 28, 18)
    bb = draw.textbbox((0,0), line, font=lf)
    lx = (W-(bb[2]-bb[0]))//2
    # Draw parts in different colors
    parts = [
        (f"{floor:,.2f} TON", BLUE_TON),
        ("  |  ", GRAY),
        (f"+{change:.1f}%", GREEN),
        ("  |  ", GRAY),
        (f"{stars:,}\u2605", ORANGE),
    ]
    x = lx
    for text, color in parts:
        draw.text((x, 340), text, fill=color, font=lf)
        x += draw.textbbox((0,0), text, font=lf)[2] - draw.textbbox((0,0), text, font=lf)[0]

    _center(draw, f"Supply: {supply:,} pcs", get_font(22), 380, GRAY)

    # Bottom gold bar
    draw.rounded_rectangle([30, H-52, W-30, H-22], radius=15, fill=(*GOLD, 40), outline=(*GOLD, 80), width=1)
    _center(draw, datetime.now().strftime("%d %b %Y  %H:%M UTC"), get_font(20), H-48, GOLD)
    return img


# ════════════════════════════════════════════════════════════════
# Design 5: Compact HUD / dashboard style
# ════════════════════════════════════════════════════════════════
def design_5(gift_img):
    floor, usd, change, stars, supply = common_data()
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, fill=(8,8,8))
    draw.rounded_rectangle([0,0,W-1,H-1], radius=CORNER, outline=GOLD, width=3)
    img = mrkt_watermark(img)
    draw = ImageDraw.Draw(img)

    # Top: gift small + name + price in a row
    if gift_img:
        g = gift_img.copy().resize((80, 80), Image.LANCZOS).convert("RGBA")
        img.paste(g, (24, 24), g)
    draw = ImageDraw.Draw(img)
    draw.text((116, 28), "PLUSH PEPE", fill=GOLD, font=get_font(28))
    draw.text((116, 62), f"#{1} by floor price", fill=GRAY, font=get_font(18))

    # Separator
    draw.line([(24, 116), (W-24, 116)], fill=(*GOLD, 60), width=1)

    # Huge centered price
    price_text = f"${usd:,.2f}"
    _center(draw, price_text, _fit_font(draw, price_text, W-40, 80, 40), 130, WHITE)

    # Change pill
    chg_text = f" +{change:.1f}% "
    cf = get_font(32)
    cbb = draw.textbbox((0,0), chg_text, font=cf)
    cw = cbb[2]-cbb[0]+20
    cx = (W-cw)//2
    draw.rounded_rectangle([cx, 220, cx+cw, 260], radius=20, fill=(0,30,0), outline=GREEN, width=2)
    _center(draw, chg_text, cf, 224, GREEN)

    # Info boxes
    box_w = 210
    box_h = 70
    gap = 20
    left_x = (W - 2*box_w - gap) // 2
    right_x = left_x + box_w + gap
    by = 285

    # TON box
    draw.rounded_rectangle([left_x, by, left_x+box_w, by+box_h], radius=16,
                           fill=(15,15,25), outline=(*BLUE_TON, 100), width=2)
    draw.text((left_x+14, by+8), "FLOOR", fill=GRAY, font=get_font(16))
    draw.text((left_x+14, by+30), f"{floor:,.2f} TON", fill=BLUE_TON, font=get_font(26))

    # Stars box
    draw.rounded_rectangle([right_x, by, right_x+box_w, by+box_h], radius=16,
                           fill=(20,15,5), outline=(*ORANGE, 100), width=2)
    draw.text((right_x+14, by+8), "STARS", fill=GRAY, font=get_font(16))
    draw.text((right_x+14, by+30), f"{stars:,} \u2605", fill=ORANGE, font=get_font(26))

    # Supply box (full width)
    sy = by + box_h + 15
    draw.rounded_rectangle([left_x, sy, right_x+box_w, sy+55], radius=16,
                           fill=(12,12,12), outline=(*GOLD, 60), width=1)
    draw.text((left_x+14, sy+10), "SUPPLY", fill=GRAY, font=get_font(16))
    sup_text = f"{supply:,} pcs"
    sbb = draw.textbbox((0,0), sup_text, font=get_font(26))
    draw.text((right_x+box_w-14-(sbb[2]-sbb[0]), sy+16), sup_text, fill=WHITE, font=get_font(26))

    # Bottom
    _center(draw, datetime.now().strftime("%d %b %Y  %H:%M UTC"), get_font(20), H-38, (*GOLD, 160))
    return img


# ════════════════════════════════════════════════════════════════
# Design 6: TGS-style (yellow header bar, stats rows, clean layout)
# ════════════════════════════════════════════════════════════════
def design_6(gift_img):
    floor, usd, change, stars, supply = common_data()
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    # Pure black background, no rounded corners for this style
    draw.rounded_rectangle([0,0,W-1,H-1], radius=12, fill=(20,20,20))

    # ── Yellow top bar ──
    draw.rectangle([0, 0, W, 58], fill=GOLD)
    # "MRKT" left
    draw.text((20, 12), "MRKT", fill=BLACK, font=get_font(30))
    # TON price badge right
    ton_text = f"+{floor:,.1f} TON"
    tf = get_font(18)
    tbb = draw.textbbox((0,0), ton_text, font=tf)
    tw = tbb[2]-tbb[0]
    badge_x = W - tw - 30
    draw.rounded_rectangle([badge_x-10, 14, W-14, 46], radius=14, fill=(30,30,30))
    draw.text((badge_x, 18), ton_text, fill=GOLD, font=tf)

    # ── Gift name (big, bold, yellow on black) ──
    name_font = _fit_font(draw, "PLUSH PEPE", W-40, 48, 30)
    _center(draw, "PLUSH PEPE", name_font, 72, GOLD)

    # ── Gift image ──
    img = paste_gift(img, gift_img, 126, 130)
    draw = ImageDraw.Draw(img)

    # ── Big USD price (yellow) ──
    price_text = f"${usd:,.2f}"
    pf = _fit_font(draw, price_text, W-60, 62, 36)
    _center(draw, price_text, pf, 268, GOLD)

    # ── Change line (green) ──
    chg_text = f"\u25b2 {change:.1f}% TODAY"
    _center(draw, chg_text, get_font(24), 338, GREEN)

    # ── Divider ──
    draw.line([(30, 376), (W-30, 376)], fill=(60,60,60), width=1)

    # ── Stats rows ──
    f_label = get_font(24)
    f_val = get_font(24)
    rows = [
        ("TON", f"{floor:,.2f}", WHITE),
        ("STARS", f"{stars:,}", WHITE),
        ("SUPPLY", f"{supply:,}", WHITE),
    ]
    y = 388
    for label, val, color in rows:
        draw.text((36, y), label, fill=GRAY, font=f_label)
        vbb = draw.textbbox((0,0), val, font=f_val)
        draw.text((W-36-(vbb[2]-vbb[0]), y), val, fill=color, font=f_val)
        if y < 388 + 30 * 2:
            draw.line([(30, y+32), (W-30, y+32)], fill=(45,45,45), width=1)
        y += 36

    # ── Bottom date (small, muted) ──
    date_text = datetime.now().strftime("%Y-%m-%d  %H:%M UTC")
    df = get_font(18)
    dbb = draw.textbbox((0,0), date_text, font=df)
    dw = dbb[2]-dbb[0]
    dx = (W-dw)//2
    draw.rounded_rectangle([dx-12, H-38, dx+dw+12, H-12], radius=10, fill=(40,40,40))
    _center(draw, date_text, df, H-36, GRAY)

    return img


# ════════════════════════════════════════════════════════════════
# Design 7: Yellow dotted card with black ribbon banner
# ════════════════════════════════════════════════════════════════
def design_7(gift_img):
    floor, usd, change, stars, supply = common_data()
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Black base
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=16, fill=(15, 15, 15))

    # ── Top black header bar ──
    draw.rectangle([0, 0, W, 52], fill=(15, 15, 15))
    draw.text((24, 12), "MRKT", fill=GOLD, font=get_font(28))
    chg_color = GREEN if change >= 0 else (255, 80, 80)
    chg_sign = "\u25b2" if change >= 0 else "\u25bc"
    chg_text = f"{chg_sign}{abs(change):.1f}%"
    cf = get_font(24)
    cbb = draw.textbbox((0, 0), chg_text, font=cf)
    draw.text((W - 24 - (cbb[2] - cbb[0]), 16), chg_text, fill=chg_color, font=cf)

    # ── Yellow section with dotted pattern ──
    yellow_top = 52
    yellow_bot = 340
    draw.rectangle([0, yellow_top, W, yellow_bot], fill=GOLD)

    # Polka dot pattern on yellow
    dot_r = 3
    dot_spacing = 16
    for dy in range(yellow_top + 8, yellow_bot - 4, dot_spacing):
        offset = dot_spacing // 2 if ((dy - yellow_top) // dot_spacing) % 2 else 0
        for dx in range(8 + offset, W - 4, dot_spacing):
            draw.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r],
                         fill=(235, 193, 0))

    # ── Gift image ──
    gift_y = yellow_top + 16
    gift_size = 110
    img = paste_gift(img, gift_img, gift_y, gift_size)
    draw = ImageDraw.Draw(img)

    # ── Black ribbon/banner for name ──
    name = "PLUSH PEPE"
    ribbon_y = gift_y + gift_size + 10
    ribbon_h = 50
    ribbon_cx = W // 2
    ribbon_hw = 170  # half width of main body
    notch = 18  # triangle notch depth

    # Banner polygon: rectangle with arrow notches on sides
    banner = [
        (ribbon_cx - ribbon_hw - notch, ribbon_y),
        (ribbon_cx - ribbon_hw, ribbon_y + ribbon_h // 2),
        (ribbon_cx - ribbon_hw - notch, ribbon_y + ribbon_h),
        (ribbon_cx + ribbon_hw + notch, ribbon_y + ribbon_h),
        (ribbon_cx + ribbon_hw, ribbon_y + ribbon_h // 2),
        (ribbon_cx + ribbon_hw + notch, ribbon_y),
    ]
    draw.polygon(banner, fill=BLACK)

    nf = _fit_font(draw, name, ribbon_hw * 2 - 20, 32, 20)
    _center(draw, name, nf, ribbon_y + (ribbon_h - nf.size) // 2 + 2, WHITE)

    # ── Big USD price on yellow ──
    price_text = f"${usd:,.2f}"
    price_y = ribbon_y + ribbon_h + 10
    pf = _fit_font(draw, price_text, W - 60, 56, 32)
    _center(draw, price_text, pf, price_y, BLACK)

    # ── Small change indicator ──
    small_chg = f"{chg_sign} {abs(change):.1f}%"
    scf = get_font(22)
    scbb = draw.textbbox((0, 0), small_chg, font=scf)
    scw = scbb[2] - scbb[0]
    price_bb = draw.textbbox((0, 0), price_text, font=pf)
    price_w = price_bb[2] - price_bb[0]
    price_x = (W - price_w) // 2
    draw.text((price_x + price_w + 10, price_y + (pf.size - scf.size)), small_chg,
              fill=chg_color, font=scf)

    # ── Dark stats section ──
    stats_top = yellow_bot
    f_label = get_font(22)
    f_val = get_font(22)
    rows = [
        ("TON", f"{floor:,.2f}"),
        ("STARS", f"{stars:,}"),
        ("SUPPLY", f"{supply:,}"),
    ]
    row_h = 38
    y = stats_top + 14
    for i, (label, val) in enumerate(rows):
        draw.text((36, y), label, fill=GRAY, font=f_label)
        vbb = draw.textbbox((0, 0), val, font=f_val)
        draw.text((W - 36 - (vbb[2] - vbb[0]), y), val, fill=WHITE, font=f_val)
        y += row_h
        if i < len(rows) - 1:
            draw.line([(30, y - 6), (W - 30, y - 6)], fill=(50, 50, 50), width=1)

    # ── Bottom info line ──
    ton_change = floor * (change / 100)
    bot_text = f"+{ton_change:,.1f} TON \u00b7 {datetime.now().strftime('%H:%M')} UTC"
    _center(draw, bot_text, get_font(18), H - 34, GRAY)

    return img


# ════════════════════════════════════════════════════════════════
# Design 8: MRKT promo — "Our love to users is PRICELESS" + infinity
# ════════════════════════════════════════════════════════════════
def design_8(gift_img):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Outer dark area ──
    draw.rectangle([0, 0, W, H], fill=(18, 18, 22))

    # ── Inner card with rounded rect ──
    pad = 28
    draw.rounded_rectangle([pad, pad, W - pad, H - pad - 40],
                           radius=36, fill=(12, 12, 16))

    # ── Neon yellow glow border ──
    for i, (thick, blur_r, alpha) in enumerate([
        (18, 18, 80), (12, 10, 120), (7, 5, 180), (4, 2, 230)
    ]):
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.rounded_rectangle([pad, pad, W - pad, H - pad - 40],
                             radius=36, outline=(*GOLD, alpha), width=thick)
        glow = glow.filter(ImageFilter.GaussianBlur(radius=blur_r))
        img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # ── Sharp yellow border on top ──
    draw.rounded_rectangle([pad, pad, W - pad, H - pad - 40],
                           radius=36, outline=GOLD, width=3)

    # ── Faint watermark "K" in background ──
    wm_font = get_font(320)
    wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wm)
    bb = wd.textbbox((0, 0), "K", font=wm_font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    wd.text(((W - tw) // 2 + 60, (H - th) // 2 - 50), "K",
            fill=(40, 40, 45, 80), font=wm_font)
    # Clip to card area
    card_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle(
        [pad + 3, pad + 3, W - pad - 3, H - pad - 43], radius=34, fill=255)
    wr, wg, wb, wa = wm.split()
    wm = Image.merge("RGBA", (wr, wg, wb, ImageChops.multiply(wa, card_mask)))
    img = Image.alpha_composite(img, wm)
    draw = ImageDraw.Draw(img)

    # ── Subtle pulse line at top ──
    pulse_y = pad + 18
    pulse_points = []
    for x in range(pad + 40, W - pad - 40):
        # Flat line with a small heartbeat bump in the middle
        mid = W // 2
        dx = x - mid
        if abs(dx) < 20:
            y_off = -int(12 * math.exp(-(dx ** 2) / 50))
        elif abs(dx - 30) < 10:
            y_off = int(6 * math.exp(-((dx - 30) ** 2) / 30))
        else:
            y_off = 0
        pulse_points.append((x, pulse_y + y_off))
    if len(pulse_points) > 1:
        draw.line(pulse_points, fill=(*GOLD, 60), width=2)

    # ── "MRKT" title ──
    _center(draw, "MRKT", get_font(48), pad + 36, GOLD)

    # ── Gift image (heart) ──
    img = paste_gift(img, gift_img, pad + 92, 120)
    draw = ImageDraw.Draw(img)

    # ── "Our love to users is" ──
    _center(draw, "Our love to users is", get_font(32), 250, WHITE)

    # ── "PRICELESS" in gold/orange ──
    _center(draw, "PRICELESS", get_font(52), 292, (255, 180, 0))

    # ── Large infinity symbol ──
    inf_font = get_font(120)
    _center(draw, "\u221e", inf_font, 345, WHITE)

    # ── Small infinity at bottom (outside card) ──
    small_inf = get_font(32)
    _center(draw, "\u221e", small_inf, H - 36, (180, 180, 190))

    return img


# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    gift_img = load_gift_img()
    if not gift_img:
        print("No plushpepe image found, generating without gift image")

    designs = [design_1, design_2, design_3, design_4, design_5, design_6, design_7, design_8]
    for i, fn in enumerate(designs, 1):
        img = fn(gift_img)
        path = f"design_{i}.png"
        img.save(path, "PNG")
        print(f"Saved {path}")

    print(f"\nDone! {len(designs)} designs saved.")
