import json
import re
import sqlite3
import requests
from collections import defaultdict

from dotenv import dotenv_values

RENAISS_MAIN = "https://www.renaiss.xyz"
SBT_BASE     = "https://8nothtoc5ds7a0x3.public.blob.vercel-storage.com/SBT/minified/"


def fetch_sbt_metadata() -> dict[int, dict]:
    """
    Parse renaiss.xyz Next.js JS bundles to discover all SBT token IDs,
    names, and image filenames without authentication.
    Fetches both the main page and /profile/achievements to find all chunks.
    Returns {token_id: {"name": ..., "filename": ...}}
    """
    SBT_BLOB = "SBT/minified/"
    entry_re = re.compile(
        r'\{id:(\d+),name:"([^"]+)"[^}]*?imageUrl:"https://[^/]+/' + SBT_BLOB + r'([^"]+)"'
    )

    def get_chunk_names(url: str) -> set:
        try:
            html = requests.get(url, timeout=15).text
            return set(re.findall(r'([a-f0-9]{16})\.js', html))
        except Exception:
            return set()

    main_chunks = get_chunk_names(RENAISS_MAIN)
    ach_chunks  = get_chunk_names(RENAISS_MAIN + "/profile/achievements")
    all_chunks  = main_chunks | ach_chunks

    metadata: dict[int, dict] = {}
    for name in all_chunks:
        try:
            js = requests.get(
                RENAISS_MAIN + "/_next/static/chunks/" + name + ".js",
                timeout=15
            ).text
        except Exception:
            continue
        if SBT_BLOB not in js:
            continue
        for m in entry_re.finditer(js):
            tid = int(m.group(1))
            if tid not in metadata:
                metadata[tid] = {"name": m.group(2), "filename": m.group(3)}

    return metadata


def _ensure_state_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)


def save_sbt_metadata(metadata: dict[int, dict]):
    """Upsert SBT metadata (token_id, name, image_filename) into DB."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sbt_metadata (
            token_id       INTEGER PRIMARY KEY,
            name           TEXT NOT NULL,
            image_filename TEXT NOT NULL
        )
    """)
    rows = [(tid, m["name"], m["filename"]) for tid, m in metadata.items()]
    conn.executemany(
        "INSERT OR REPLACE INTO sbt_metadata VALUES (?,?,?)", rows
    )
    conn.commit()
    conn.close()


def load_achievements_from_db() -> dict[str, str]:
    """Load {token_id_str: name} from sbt_metadata table, fallback to hardcoded."""
    try:
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("SELECT token_id, name FROM sbt_metadata").fetchall()
        conn.close()
        if rows:
            return {str(tid): name for tid, name in rows}
    except Exception:
        pass
    return ACHIEVEMENTS

# Load env
import os as _os
config = dotenv_values(".env")
API_KEY = config.get("BSCSCAN_API_KEY") or _os.environ.get("BSCSCAN_API_KEY")

CONTRACT = "0x7D1B7dB704d722295fbAa284008f526634673DbF"
BSC_API = "https://api.etherscan.io/v2/api"
CHAIN_ID = 56  # BSC mainnet
ZERO = "0x0000000000000000000000000000000000000000"
TARGET = "0x17C011298047e8EBd116749782A3d5f3C618d8B7".lower()
DB_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "nft_data.db")

ACHIEVEMENTS = {
    "1": "The Trader", "2": "Pack Opener", "3": "The Recruiter",
    "4": "Community Voice", "5": "Early Bird", "6": "Sprint Challenger",
    "7": "The Survivor", "8": "Dubai Explorer", "10": "Beta Pioneer",
    "11": "Top Trader SBT - Season 1", "12": "X Linker", "13": "Discord Linker",
    "14": "Fund Your Account", "19": "Ice Breaker", "20": "Christmas Carol",
    "21": "S+ Breaker", "22": "2025 Year Award — Hall of Fame",
    "23": "2025 Year Award — Growth Catalyst", "24": "2025 Year Award — Referral Force",
    "25": "2025 Year Award — Speed of Hands", "26": "2025 Year Award — Conviction Holder",
    "27": "2025 Year Award — Narrative Builder", "28": "2025 Year Award — Signal Amplifier",
    "29": "2025 Year Award — Core Contributor", "30": "2025 Year Award — Real Grinder",
    "31": "2025 Year Award — The Unluckiest Ripper", "32": "New Year Opener",
    "33": "The Vanguard", "34": "Grand Ripper", "35": "Supreme Collector",
    "36": "RNG Martyr", "37": "Heat Survivor", "38": "Identity Flexer",
    "39": "Signal Booster", "40": "Live Participant", "41": "Signal Follower",
    "42": "One Piece AMA", "43": "Discord Server Booster", "44": "Community Developer",
    "45": "Infinite Pioneer", "46": "Infinite Grinder", "47": "Infinite Flash Mint",
    "48": "Infinite Flex", "49": "Infinite Cursed", "50": "REFS",
    "51": "Legacy Triple Pull", "52": "Legacy Flash Mint",
    "53": "Lunar Spring Cleaning Day", "54": "Lunar Zodiac X Pokémon Day",
    "55": "Lunar Worst Gift Day", "56": "Lunar Memory Keeper", "57": "CEO Roast",
    "58": "God of Wealth", "59": "BNB Lunar Genesis 50", "60": "Lunar Triple Entry",
    "61": "Lunar Elite Draw", "62": "Lunar Live Witness", "63": "Community Event MVP",
    "64": "Community Event Survivor", "65": "Community Event Organizer",
    "66": "Superliquid Test Pioneer", "67": "Hong Kong Explorer 2026",
    "68": "Pokémon 30th Anniversary", "69": "Pokémon 30th S-Card",
    "70": "Voyaga Pack", "71": "Manga Rare", "72": "Voyaga S-Card",
    "73": "Pokémon 30th & Voyaga Collector", "74": "Community Battle Winner",
    "75": "Renacrypt Pack", "76": "Omega Pack", "77": "Omega S-Card",
    "78": "Renacrypt Epic Card", "79": "Renacrypt Legendary Card", "80": "TCG Double Giant",
    "81": "Korea Explorer", "82": "Korea Wayfinder", "83": "Korea Helper",
    "84": "Korea S-Card", "85": "Taipei Explorer", "86": "Malaysia Explorer",
    "87": "Out of Stock", "88": "Skyline Traveler", "89": "PSA 1",
    "90": "Legacy Elite", "91": "Legacy Pioneer", "92": "BETA 2.0 Event",
}


# ── State persistence ──────────────────────────────────────────────────────────

def load_state() -> dict:
    conn = sqlite3.connect(DB_FILE)
    _ensure_state_table(conn)
    row = conn.execute("SELECT value FROM state WHERE key='last_block'").fetchone()
    last_block = int(row[0]) if row else 0
    row = conn.execute("SELECT value FROM state WHERE key='balances'").fetchone()
    balances = json.loads(row[0]) if row else {}
    conn.close()
    return {"last_block": last_block, "balances": balances}


def save_state(state: dict):
    conn = sqlite3.connect(DB_FILE)
    _ensure_state_table(conn)
    conn.execute("INSERT OR REPLACE INTO state VALUES ('last_block', ?)", (str(state["last_block"]),))
    conn.execute("INSERT OR REPLACE INTO state VALUES ('balances', ?)", (json.dumps(state["balances"], separators=(",", ":")),))
    conn.commit()
    conn.close()


# ── Fetching ───────────────────────────────────────────────────────────────────

def fetch_page(startblock: int, endblock: int, page: int, offset: int) -> list:
    params = {
        "chainid": CHAIN_ID,
        "module": "account",
        "action": "token1155tx",
        "contractaddress": CONTRACT,
        "startblock": startblock,
        "endblock": endblock,
        "page": page,
        "offset": offset,
        "sort": "asc",
        "apikey": API_KEY,
    }
    resp = requests.get(BSC_API, params=params, timeout=30)
    data = resp.json()
    if data["status"] == "1":
        return data["result"]
    return []


def fetch_transfers_from(startblock: int) -> tuple[list, int]:
    """
    Fetch all ERC-1155 transfers starting from startblock.
    Returns (transfers, last_block_seen).
    Uses block-range splitting to bypass the 10,000 record API cap.
    """
    transfers = []
    endblock = 99_999_999
    offset = 1000
    last_block = startblock

    print(f"\nFetching transfers from block {startblock}...")

    while startblock <= endblock:
        window = []
        page = 1

        while True:
            batch = fetch_page(startblock, endblock, page, offset)
            if not batch:
                break
            window.extend(batch)
            if len(batch) < offset:
                break
            page += 1
            if len(window) >= 10_000:
                break

        if not window:
            break

        transfers.extend(window)
        last_block = int(window[-1]["blockNumber"])
        print(f"  Blocks {startblock}–{endblock}: {len(window)} records (total: {len(transfers)})")

        if len(window) >= 10_000:
            next_start = last_block if last_block > startblock else last_block + 1
            startblock = next_start
        else:
            break

    print(f"Done fetching. New records: {len(transfers)}, last block: {last_block}")
    return transfers, last_block


# ── Balance update ─────────────────────────────────────────────────────────────

def apply_transfers(balances: dict, transfers: list) -> dict:
    """
    Incrementally apply transfer events onto the existing balances dict.
    Structure: balances[address][tokenId] = amount
    """
    # Convert to defaultdict for easy mutation
    bal: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for addr, tokens in balances.items():
        for tid, amt in tokens.items():
            bal[addr][tid] = amt

    for tx in transfers:
        token_id = tx["tokenID"]
        from_addr = tx["from"].lower()
        to_addr = tx["to"].lower()
        value = int(tx["tokenValue"])

        if from_addr != ZERO:
            bal[from_addr][token_id] -= value
            if bal[from_addr][token_id] <= 0:
                bal[from_addr].pop(token_id, None)
            if not bal[from_addr]:
                bal.pop(from_addr, None)

        if to_addr != ZERO:
            bal[to_addr][token_id] += value

    # Convert back to plain dict for JSON serialisation
    return {addr: dict(tokens) for addr, tokens in bal.items()}


# ── DB Export ──────────────────────────────────────────────────────────────────

def export_sqlite(balances: dict):
    addr_totals = {addr: sum(t.values()) for addr, t in balances.items() if sum(t.values()) > 0}

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS holdings;
        DROP TABLE IF EXISTS rankings;
        CREATE TABLE holdings (
            address TEXT NOT NULL, token_id INTEGER NOT NULL,
            token_name TEXT, amount INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (address, token_id)
        );
        CREATE TABLE rankings (
            rank INTEGER NOT NULL, address TEXT PRIMARY KEY, total_sbt INTEGER NOT NULL
        );
        CREATE INDEX idx_holdings_token ON holdings(token_id);
        CREATE INDEX idx_rankings_rank  ON rankings(rank);
    """)

    holding_rows = [
        (addr, int(tid), ACHIEVEMENTS.get(tid, f"Unknown #{tid}"), amt)
        for addr, tokens in balances.items()
        for tid, amt in tokens.items() if amt > 0
    ]
    cur.executemany("INSERT INTO holdings VALUES (?,?,?,?)", holding_rows)

    ranked = sorted(addr_totals.items(), key=lambda x: x[1], reverse=True)
    ranking_rows, prev_count, prev_rank = [], None, 0
    for i, (addr, count) in enumerate(ranked, 1):
        if count != prev_count:
            prev_rank, prev_count = i, count
        ranking_rows.append((prev_rank, addr, count))
    cur.executemany("INSERT INTO rankings VALUES (?,?,?)", ranking_rows)

    conn.commit()
    conn.close()


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_report(balances: dict):
    totals = {addr: sum(tokens.values()) for addr, tokens in balances.items()}
    total_holders = len(totals)
    total_supply = sum(totals.values())

    print(f"\nCurrent holders : {total_holders}")
    print(f"Total supply    : {total_supply}")

    target_tokens = balances.get(TARGET, {})
    target_total = sum(target_tokens.values())
    print(f"\nYour address ({TARGET}):")
    print(f"  Total NFTs held : {target_total}")
    if target_tokens:
        token_list = ", ".join(f"#{tid}×{amt}" for tid, amt in sorted(target_tokens.items(), key=lambda x: int(x[0])))
        print(f"  Token IDs       : {token_list}")

    top10 = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop 10 holders:")
    print(f"{'Rank':<6} {'Address':<44} {'NFT Count'}")
    print("-" * 60)
    for rank, (addr, count) in enumerate(top10, 1):
        marker = " <-- YOU" if addr == TARGET else ""
        print(f"{rank:<6} {addr:<44} {count}{marker}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # 1. Refresh SBT metadata from JS bundle
    metadata = fetch_sbt_metadata()
    if metadata:
        save_sbt_metadata(metadata)
        # Update in-memory ACHIEVEMENTS so export uses fresh names
        ACHIEVEMENTS.update({str(tid): m["name"] for tid, m in metadata.items()})

    # 2. Fetch on-chain transfers
    state = load_state()
    start_from = state["last_block"] + 1 if state["last_block"] else 0
    transfers, last_block = fetch_transfers_from(start_from)

    if transfers:
        state["balances"] = apply_transfers(state["balances"], transfers)
        state["last_block"] = last_block
        save_state(state)
    else:
        print("No new transfers found — data is already up to date.")

    export_sqlite(state["balances"])
    print_report(state["balances"])


if __name__ == "__main__":
    main()
