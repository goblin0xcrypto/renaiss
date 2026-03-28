"""
generate_card.py
================
Generate a personal SBT ranking card using the Renaiss background image.
Reads data from nft_data.db. Outputs images/profile_card.png.
"""

import os
import sqlite3
import urllib.request
from PIL import Image, ImageDraw, ImageFont

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SBT_BASE  = "https://8nothtoc5ds7a0x3.public.blob.vercel-storage.com/SBT/minified/"
SBT_CACHE = os.path.join(_BASE_DIR, "images", "sbt")
os.makedirs(SBT_CACHE, exist_ok=True)

# token_id -> filename (slug from JS bundle)
TOKEN_IMAGES = {
    1: "1-the-trader.png",
    2: "2-pack-opener.png",
    3: "3-the-recruiter.png",
    4: "4-community-voice.png",
    5: "5-early-bird.png",
    6: "6-sprint-challenger.png",
    7: "7-the-survivor.png",
    8: "8-global-explorer.png",
    10: "10-beta-pioneer.png",
    11: "11-top-trader-sbt-season-1.png",
    12: "12-x-linker-new.png",
    13: "13-discord-linker.png",
    14: "14-fund-your-account.png",
    19: "19-ice-breaker.png",
    20: "20-christmas-carol.png",
    21: "22-s-plus-breaker.png",
    22: "21-hall-of-fame-new.png",
    23: "23-growth-catalyst.png",
    24: "24-referral-force.png",
    25: "25-speed-of-hands.png",
    26: "26-conviction-holder.png",
    27: "27-narrative-builder.png",
    28: "28-signal-amplifier.png",
    29: "29-core-contributor.png",
    30: "30-real-grinder.png",
    31: "31-the-unluckiest-ripper.png",
    32: "32-new-year-opener.png",
    33: "33-the-vanguard.png",
    34: "34-grand-ripper.png",
    35: "35-supreme-collector.png",
    36: "36-rng-martyr.png",
    37: "37-heat-survivor.png",
    38: "38-identity-flexer.png",
    39: "39-signal-booster.png",
    40: "40-live-participant.png",
    41: "41-signal-follower.png",
    42: "42-one-piece-ama.png",
    43: "43-discord-server-booster.png",
    44: "44-community-dev.png",
    45: "45-infinite-pioneer.png",
    46: "46-infinite-grinder.png",
    47: "47-infinite-flash-mint.png",
    48: "48-infinite-flex.png",
    49: "49-infinite-cursed.png",
    50: "50-refs.png",
    51: "51-legacy-triple-pull.png",
    52: "52-legacy-flash-mint.png",
    53: "53-lunar-spring-cleaning-day.png",
    54: "54-lunar-zodiac-x-pokemon-day.png",
    55: "55-lunar-worst-gift-day.png",
    56: "56-lunar-memory-keeper.png",
    57: "57-ceo-roast.png",
    58: "58-god-of-wealth.png",
    59: "59-bnb-lunar-genesis-50.png",
    60: "60-lunar-triple-entry.png",
    61: "61-lunar-elite-draw.png",
    62: "62-lunar-live-witness.png",
    63: "63-community-event-mvp.png",
    64: "64-community-event-survivor.png",
    65: "65-community-event-organizer.png",
    66: "66-superliquid-test-pioneer.png",
    67: "67-hong-kong-explorer-2026.png",
    68: "68-pokemon-30th-anniversary-v2.png",
    69: "69-pokemon-30th-s-card-v2.png",
    70: "70-voyaga-pack-v2.png",
    71: "71-manga-rare-v2.png",
    72: "72-voyaga-s-card-v2.png",
    73: "73-pokemon-30th-voyaga-collector-v2.png",
    74: "74-community-battle-winner.png",
    75: "75-renacrypt-pack.png",
    76: "76-omega-pack.png",
    77: "77-omega-s-card.png",
    78: "78-renacrypt-epic-card.png",
    79: "79-renacrypt-legendary-card.png",
    80: "80-tcg-double-giant.png",
    81: "81-korea-explorer.png",
    82: "82-korea-wayfinder.png",
    83: "83-korea-helper.png",
    84: "84-korea-s-card.png",
    85: "85-taipei-explorer.png",
    86: "86-malaysia-explorer.png",
    87: "87-out-of-stock.png",
    88: "88-skyline-traveler.png",
    89: "89-psa-1.png",
    90: "90-legacy-elite.png",
    91: "91-legacy-pioneer.png",
    92: "92-beta-2-0-event.png",
}


def _load_token_images_from_db() -> dict[int, str]:
    """Merge DB sbt_metadata into TOKEN_IMAGES (DB wins for new entries)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("SELECT token_id, image_filename FROM sbt_metadata").fetchall()
        conn.close()
        merged = dict(TOKEN_IMAGES)
        for tid, fname in rows:
            merged[int(tid)] = fname
        return merged
    except Exception:
        return TOKEN_IMAGES


def get_sbt_image(token_id: int, size: int) -> Image.Image | None:
    images = _load_token_images_from_db()
    filename = images.get(token_id)
    if not filename:
        return None
    cache_path = os.path.join(SBT_CACHE, filename)
    if not os.path.exists(cache_path):
        url = SBT_BASE + filename
        try:
            urllib.request.urlretrieve(url, cache_path)
        except Exception:
            pass  # could not download SBT image
            return None
    try:
        img = Image.open(cache_path).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        return img
    except Exception:
        return None

# ── Config ─────────────────────────────────────────────────────────────────────
DEFAULT_TARGET = "0x17c011298047e8ebd116749782a3d5f3c618d8b7"
CARDS_DIR   = os.path.join(_BASE_DIR, "images", "cards")
DB_FILE     = os.environ.get("DB_FILE") or os.path.join(_BASE_DIR, "nft_data.db")

os.makedirs(CARDS_DIR, exist_ok=True)

_FONTS_DIR  = os.path.join(_BASE_DIR, "fonts")
FONT_BOLD   = os.path.join(_FONTS_DIR, "DejaVuSans-Bold.ttf")
FONT_REG    = os.path.join(_FONTS_DIR, "DejaVuSans.ttf")
FONT_MONO   = os.path.join(_FONTS_DIR, "DejaVuSansMono.ttf")

# Colors — dark-on-white palette
NAVY        = (28,  48,  80)      # Renaiss brand dark text
NAVY_LIGHT  = (28,  48,  80, 180)
DARK        = (20,  20,  30)
GRAY        = (100, 110, 130)
GOLD        = (200, 145,  10)     # amber, readable on white
GOLD_BG     = (255, 240, 200)     # pale gold for badge backgrounds
DIVIDER     = (220, 225, 235)
WHITE       = (255, 255, 255)


def load_data(address: str) -> dict | None:
    try:
        conn = sqlite3.connect(DB_FILE)
        rank_row = conn.execute(
            "SELECT rank, total_sbt FROM rankings WHERE address = ?", (address,)
        ).fetchone()
        total_holders = conn.execute("SELECT COUNT(*) FROM rankings").fetchone()[0]
        meta_count = conn.execute("SELECT COUNT(*) FROM sbt_metadata").fetchone()[0]
        total_types = meta_count if meta_count > 0 else len(TOKEN_IMAGES)
        tokens = conn.execute(
            "SELECT token_id, token_name FROM holdings WHERE address = ? ORDER BY token_id",
            (address,)
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError:
        return None

    return {
        "address": address,
        "rank": rank_row[0] if rank_row else 0,
        "total_sbt": rank_row[1] if rank_row else 0,
        "total_holders": total_holders,
        "total_types": total_types,
        "tokens": tokens,
    }


def _bg_image(rank: int) -> str:
    _img = os.path.join(_BASE_DIR, "images")
    if rank <= 10:
        return os.path.join(_img, "gold.jpg")
    elif rank <= 50:
        return os.path.join(_img, "silver.jpg")
    elif rank <= 100:
        return os.path.join(_img, "copper.jpg")
    else:
        return os.path.join(_img, "black.jpg")


def make_card(data: dict) -> str:
    # ── Load background ────────────────────────────────────────────────────────
    bg = Image.open(_bg_image(data["rank"])).convert("RGBA")
    W = bg.size[0]   # 976

    PAD      = 60
    MID      = 490   # below the wreath bottom (~y 450)
    ROW_H    = 28
    COLS     = 3
    list_y   = MID + PAD + 30

    # Wreath inner-circle center (empirically measured for image.jpg)
    WREATH_CX = 600
    WREATH_CY = 245

    # Calculate canvas height to fit all tokens
    rows_needed = max(1, -(-len(data["tokens"]) // COLS))
    H = max(bg.size[1], list_y + rows_needed * ROW_H + PAD)

    # Build canvas: paste bg at top, fill remainder with white
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    canvas.paste(bg, (0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # ── Fonts ──────────────────────────────────────────────────────────────────
    rank_str      = f"{data['rank']}"
    WREATH_MAX_W  = 220   # max pixel width for rank text inside wreath inner circle
    rank_font_size = 160
    f_rank = ImageFont.truetype(FONT_BOLD, rank_font_size)
    rank_bbox = f_rank.getbbox(rank_str)
    rank_w    = rank_bbox[2] - rank_bbox[0]
    while rank_w > WREATH_MAX_W and rank_font_size > 40:
        rank_font_size -= 4
        f_rank    = ImageFont.truetype(FONT_BOLD, rank_font_size)
        rank_bbox = f_rank.getbbox(rank_str)
        rank_w    = rank_bbox[2] - rank_bbox[0]
    rank_h = rank_bbox[3] - rank_bbox[1]

    f_label  = ImageFont.truetype(FONT_BOLD,  22)
    f_small  = ImageFont.truetype(FONT_REG,   18)
    f_mono   = ImageFont.truetype(FONT_MONO,  18)
    f_token  = ImageFont.truetype(FONT_REG,   17)
    f_title  = ImageFont.truetype(FONT_BOLD,  20)
    f_id     = ImageFont.truetype(FONT_MONO,  14)

    # ── TOP LEFT: address + SBT count ─────────────────────────────────────────
    addr = data["address"]
    addr_short = addr[:8] + " ··· " + addr[-6:]

    y = 190
    draw.text((PAD, y), "ADDRESS", font=f_label, fill=GOLD)
    y += 28
    draw.text((PAD, y), addr_short, font=f_mono, fill=NAVY)

    y += 44
    draw.text((PAD, y), "TOTAL SBTs", font=f_label, fill=GOLD)
    y += 30
    draw.text((PAD, y), str(data["total_sbt"]), font=ImageFont.truetype(FONT_BOLD, 100), fill=NAVY)
    sbt_bbox = ImageFont.truetype(FONT_BOLD, 100).getbbox(str(data["total_sbt"]))
    draw.text((PAD, y + sbt_bbox[3] + 14), f"of {data['total_types']} types", font=f_small, fill=DARK)

    # ── RANK: centered inside the wreath ──────────────────────────────────────

    # Draw rank number centered at wreath center (shifted right+down)
    rx = WREATH_CX - rank_w // 2 - rank_bbox[0] + 30
    ry = WREATH_CY - rank_h // 2 - rank_bbox[1] + 60
    draw.text((rx, ry), rank_str, font=f_rank, fill=NAVY)

    # "RANK" label — moved down
    draw.text((380, 135), "RANK", font=f_label, fill=GOLD)

    # "of X,XXX holders" — shifted right+down
    draw.text((830, 440), f"of {data['total_holders']:,}\nholders", font=f_small, fill=DARK)

    # ── BOTTOM: achievements list ──────────────────────────────────────────────
    title_y = MID + PAD - 10
    draw.text((PAD, title_y), f"ACHIEVEMENTS  ({len(data['tokens'])})", font=f_title, fill=GOLD)
    draw.line([(PAD, title_y + 28), (W - PAD, title_y + 28)], fill=DIVIDER, width=1)

    tokens   = data["tokens"]
    list_y   = title_y + 40
    row_h    = ROW_H
    img_size = row_h - 4
    col_w    = (W - PAD * 2) // COLS
    max_rows = -(-len(tokens) // COLS)   # ceil div

    for i, (tid, name) in enumerate(tokens):
        col = i // max_rows
        row = i % max_rows
        if col >= COLS:
            break
        x = PAD + col * col_w
        y = list_y + row * row_h

        sbt_img = get_sbt_image(tid, img_size)
        if sbt_img:
            canvas.paste(sbt_img, (x, y + (row_h - img_size) // 2), sbt_img)
            icon_w = img_size + 6
        else:
            draw.rounded_rectangle([x, y + 4, x + 34, y + 22], radius=4, fill=GOLD_BG)
            draw.text((x + 3, y + 5), f"#{tid}", font=f_id, fill=GOLD)
            icon_w = 40

        max_px = col_w - icon_w - 4
        display = name
        while draw.textlength(display, font=f_token) > max_px and len(display) > 3:
            display = display[:-2] + "…"
        draw.text((x + icon_w, y + (row_h - 17) // 2), display, font=f_token, fill=DARK)

    # ── Save ───────────────────────────────────────────────────────────────────
    output = os.path.join(CARDS_DIR, f"{data['address'][:10]}.png")
    out = canvas.convert("RGB")
    out.save(output, quality=95)
    return output


def generate_card_for_address(address: str) -> str | None:
    """Generate card for given address. Returns output path, or None if not found in DB."""
    address = address.lower()
    data = load_data(address)
    if data is None:
        return None
    if data["rank"] == 0 and data["total_sbt"] == 0:
        return None
    return make_card(data)


def main():
    import sys
    address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    path = generate_card_for_address(address)
    if path is None:
        print("Address not found in database.")
    else:
        print(f"Card saved: {path}")


if __name__ == "__main__":
    main()
