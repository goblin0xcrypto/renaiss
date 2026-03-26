"""
nft_analyze.py
==============
Analyze Renaiss SBT holdings using local nft_state.json (from nft_top_holders.py).
No API calls needed — all data is already on disk.

Outputs:
  - Per-achievement: how many holders, top holders
  - Per-address: which achievements held and count
  - Overall top 10 holders
"""

import json
from collections import defaultdict

STATE_FILE = "nft_state.json"
TARGET = "0x17C011298047e8EBd116749782A3d5f3C618d8B7".lower()

# Achievement metadata extracted from renaiss.xyz JS bundle
ACHIEVEMENTS = {
    "1": "The Trader",
    "2": "Pack Opener",
    "3": "The Recruiter",
    "4": "Community Voice",
    "5": "Early Bird",
    "6": "Sprint Challenger",
    "7": "The Survivor",
    "8": "Dubai Explorer",
    "10": "Beta Pioneer",
    "11": "Top Trader SBT - Season 1",
    "12": "X Linker",
    "13": "Discord Linker",
    "14": "Fund Your Account",
    "19": "Ice Breaker",
    "20": "Christmas Carol",
    "21": "S+ Breaker",
    "22": "2025 Year Award — Hall of Fame",
    "23": "2025 Year Award — Growth Catalyst",
    "24": "2025 Year Award — Referral Force",
    "25": "2025 Year Award — Speed of Hands",
    "26": "2025 Year Award — Conviction Holder",
    "27": "2025 Year Award — Narrative Builder",
    "28": "2025 Year Award — Signal Amplifier",
    "29": "2025 Year Award — Core Contributor",
    "30": "2025 Year Award — Real Grinder",
    "31": "2025 Year Award — The Unluckiest Ripper",
    "32": "New Year Opener",
    "33": "The Vanguard",
    "34": "Grand Ripper",
    "35": "Supreme Collector",
    "36": "RNG Martyr",
    "37": "Heat Survivor",
    "38": "Identity Flexer",
    "39": "Signal Booster",
    "40": "Live Participant",
    "41": "Signal Follower",
    "42": "One Piece AMA",
    "43": "Discord Server Booster",
    "44": "Community Developer",
    "45": "Infinite Pioneer",
    "46": "Infinite Grinder",
    "47": "Infinite Flash Mint",
    "48": "Infinite Flex",
    "49": "Infinite Cursed",
    "50": "REFS",
    "51": "Legacy Triple Pull",
    "52": "Legacy Flash Mint",
    "53": "Lunar Spring Cleaning Day",
    "54": "Lunar Zodiac X Pokémon Day",
    "55": "Lunar Worst Gift Day",
    "56": "Lunar Memory Keeper",
    "57": "CEO Roast",
    "58": "God of Wealth",
    "59": "BNB Lunar Genesis 50",
    "60": "Lunar Triple Entry",
    "61": "Lunar Elite Draw",
    "62": "Lunar Live Witness",
    "63": "Community Event MVP",
    "64": "Community Event Survivor",
    "65": "Community Event Organizer",
    "66": "Superliquid Test Pioneer",
    "67": "Hong Kong Explorer 2026",
    "68": "Pokémon 30th Anniversary",
    "69": "Pokémon 30th S-Card",
    "70": "Voyaga Pack",
    "71": "Manga Rare",
    "72": "Voyaga S-Card",
    "73": "Pokémon 30th & Voyaga Collector",
    "74": "Community Battle Winner",
    "75": "Renacrypt Pack",
    "76": "Omega Pack",
    "77": "Omega S-Card",
    "78": "Renacrypt Epic Card",
    "79": "Renacrypt Legendary Card",
    "80": "TCG Double Giant",
}


def load_state() -> dict:
    with open(STATE_FILE) as f:
        return json.load(f)


def build_indexes(balances: dict):
    """
    Build two indexes from balances:
      token_holders[tokenId] -> {address: amount, ...}
      addr_totals[address]   -> total SBT count
    """
    token_holders: dict[str, dict[str, int]] = defaultdict(dict)
    addr_totals: dict[str, int] = {}

    for addr, tokens in balances.items():
        total = 0
        for tid, amt in tokens.items():
            if amt > 0:
                token_holders[tid][addr] = amt
                total += amt
        if total > 0:
            addr_totals[addr] = total

    return token_holders, addr_totals


def print_your_profile(balances: dict):
    tokens = balances.get(TARGET, {})
    total = sum(tokens.values())
    print(f"\n{'='*60}")
    print(f"YOUR ADDRESS: {TARGET}")
    print(f"Total SBTs held: {total}")
    print(f"{'='*60}")
    if not tokens:
        print("  (no tokens found)")
        return
    for tid in sorted(tokens.keys(), key=lambda x: int(x)):
        amt = tokens[tid]
        name = ACHIEVEMENTS.get(tid, f"Unknown #{tid}")
        qty = f" x{amt}" if amt > 1 else ""
        print(f"  #{tid:<4} {name}{qty}")


def print_top_holders(addr_totals: dict, n: int = 10):
    top = sorted(addr_totals.items(), key=lambda x: x[1], reverse=True)[:n]
    print(f"\n{'='*60}")
    print(f"TOP {n} SBT HOLDERS (total count)")
    print(f"{'='*60}")
    print(f"{'Rank':<6} {'Address':<44} {'Total'}")
    print("-" * 58)
    for rank, (addr, count) in enumerate(top, 1):
        marker = " ← YOU" if addr == TARGET else ""
        print(f"{rank:<6} {addr:<44} {count}{marker}")


def print_achievement_stats(token_holders: dict):
    print(f"\n{'='*60}")
    print("ACHIEVEMENT STATS (sorted by holder count)")
    print(f"{'='*60}")
    print(f"{'ID':<6} {'Holders':<10} {'Name'}")
    print("-" * 58)

    rows = []
    for tid, holders in token_holders.items():
        holder_count = len(holders)
        name = ACHIEVEMENTS.get(tid, f"Unknown #{tid}")
        rows.append((holder_count, int(tid), name, tid))

    for holder_count, _, name, tid in sorted(rows, reverse=True):
        print(f"#{tid:<5} {holder_count:<10} {name}")


def print_achievement_top_holders(token_holders: dict, top_n: int = 5):
    print(f"\n{'='*60}")
    print(f"TOP {top_n} HOLDERS PER ACHIEVEMENT")
    print(f"{'='*60}")

    for tid in sorted(token_holders.keys(), key=lambda x: int(x)):
        holders = token_holders[tid]
        name = ACHIEVEMENTS.get(tid, f"Unknown #{tid}")
        top = sorted(holders.items(), key=lambda x: x[1], reverse=True)[:top_n]
        total_holders = len(holders)
        print(f"\n#{tid} {name}  ({total_holders} holders)")
        for addr, amt in top:
            marker = " ← YOU" if addr == TARGET else ""
            qty = f" x{amt}" if amt > 1 else ""
            print(f"    {addr}{qty}{marker}")


def export_csv(balances: dict, filename: str = "nft_holdings.csv"):
    """Export full holdings table as CSV: address, tokenId, tokenName, amount"""
    rows = []
    for addr, tokens in balances.items():
        for tid, amt in tokens.items():
            if amt > 0:
                name = ACHIEVEMENTS.get(tid, f"Unknown #{tid}")
                rows.append((addr, tid, name, amt))

    rows.sort(key=lambda x: (x[0], int(x[1])))

    with open(filename, "w") as f:
        f.write("address,token_id,token_name,amount\n")
        for addr, tid, name, amt in rows:
            safe_name = name.replace(",", ";")
            f.write(f"{addr},{tid},{safe_name},{amt}\n")

    print(f"Exported {len(rows)} rows to {filename}")


def export_rankings_csv(addr_totals: dict, filename: str = "nft_rankings.csv"):
    """Export per-address ranking CSV: rank, address, total_sbt_count"""
    ranked = sorted(addr_totals.items(), key=lambda x: x[1], reverse=True)

    with open(filename, "w") as f:
        f.write("rank,address,total_sbt\n")
        prev_count = None
        prev_rank = 0
        for i, (addr, count) in enumerate(ranked, 1):
            # Same count = same rank (dense ranking)
            if count != prev_count:
                prev_rank = i
                prev_count = count
            f.write(f"{prev_rank},{addr},{count}\n")

    print(f"Exported {len(ranked)} addresses to {filename}")


def export_sqlite(balances: dict, addr_totals: dict, filename: str = "nft_data.db"):
    """
    Export to SQLite with two tables:
      holdings(address, token_id, token_name, amount)
      rankings(rank, address, total_sbt)

    Example queries:
      -- Top 10 holders
      SELECT rank, address, total_sbt FROM rankings ORDER BY rank LIMIT 10;
      -- All tokens for one address
      SELECT token_id, token_name, amount FROM holdings WHERE address = '0x...';
      -- All holders of a specific token
      SELECT h.address, r.rank, h.amount FROM holdings h JOIN rankings r USING(address)
        WHERE h.token_id = '5' ORDER BY r.rank;
    """
    import sqlite3

    conn = sqlite3.connect(filename)
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS holdings;
        DROP TABLE IF EXISTS rankings;
        CREATE TABLE holdings (
            address    TEXT NOT NULL,
            token_id   INTEGER NOT NULL,
            token_name TEXT,
            amount     INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (address, token_id)
        );
        CREATE TABLE rankings (
            rank       INTEGER NOT NULL,
            address    TEXT PRIMARY KEY,
            total_sbt  INTEGER NOT NULL
        );
        CREATE INDEX idx_holdings_token ON holdings(token_id);
        CREATE INDEX idx_rankings_rank  ON rankings(rank);
    """)

    holding_rows = []
    for addr, tokens in balances.items():
        for tid, amt in tokens.items():
            if amt > 0:
                name = ACHIEVEMENTS.get(tid, f"Unknown #{tid}")
                holding_rows.append((addr, int(tid), name, amt))
    cur.executemany("INSERT INTO holdings VALUES (?,?,?,?)", holding_rows)

    ranked = sorted(addr_totals.items(), key=lambda x: x[1], reverse=True)
    ranking_rows = []
    prev_count = None
    prev_rank = 0
    for i, (addr, count) in enumerate(ranked, 1):
        if count != prev_count:
            prev_rank = i
            prev_count = count
        ranking_rows.append((prev_rank, addr, count))
    cur.executemany("INSERT INTO rankings VALUES (?,?,?)", ranking_rows)

    conn.commit()
    conn.close()
    print(f"Exported to SQLite: {filename}")


def main():
    state = load_state()
    balances = state["balances"]

    print(f"State loaded: {len(balances)} holders, last block {state['last_block']}")
    print(f"Updated at: {state['updated_at']}")

    token_holders, addr_totals = build_indexes(balances)

    # 1. Your profile
    print_your_profile(balances)

    # 2. Overall top holders
    print_top_holders(addr_totals, n=10)

    # 3. Per-achievement stats
    print_achievement_stats(token_holders)

    # 4. Top holders per achievement
    print_achievement_top_holders(token_holders, top_n=3)

    # 5. Export files
    #print()
    #export_csv(balances)
    #export_rankings_csv(addr_totals)
    export_sqlite(balances, addr_totals)


if __name__ == "__main__":
    main()
