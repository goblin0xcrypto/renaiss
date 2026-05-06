"""
bot.py
======
Discord bot for Renaiss.

Commands:
  /analyze <wallet>          — analyze USDT transaction stats for a BSC wallet
  /sbt_rank <address>        — generate SBT ranking card for a BSC address
  /sbt_stats                 — view holder count for each SBT
  /pack_leaderboard          — top 200 pack openers since 2026-05-01 (UTC+8)

Background task:
  Every 10 minutes: runs nft_top_holders.py to refresh on-chain SBT data
"""

import asyncio
import re
import sqlite3
import subprocess
import sys
import os
import time
import requests
import discord
from discord import app_commands
from dotenv import dotenv_values

config = dotenv_values(".env")
TOKEN = config.get("DISCORD_TOKEN") or os.environ.get("DISCORD_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE  = os.environ.get("DB_FILE") or os.path.join(BASE_DIR, "nft_data.db")
sys.path.insert(0, BASE_DIR)


# ── User wallet helpers ─────────────────────────────────────────────────────────

def _get_user_wallet(discord_id: int) -> str | None:
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS user_wallets (discord_id INTEGER PRIMARY KEY, address TEXT NOT NULL)")
        row = conn.execute("SELECT address FROM user_wallets WHERE discord_id = ?", (discord_id,)).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _save_user_wallet(discord_id: int, address: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS user_wallets (discord_id INTEGER PRIMARY KEY, address TEXT NOT NULL)")
        conn.execute("INSERT OR REPLACE INTO user_wallets VALUES (?, ?)", (discord_id, address.lower()))
        conn.commit()
        conn.close()
    except Exception:
        pass


class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(periodic_update())


client = Bot()


@client.event
async def on_ready():
    pass


# ── /analyze ───────────────────────────────────────────────────────────────────

async def _wallet_autocomplete(interaction: discord.Interaction, current: str):
    saved = _get_user_wallet(interaction.user.id)
    if saved and (not current or saved.startswith(current.lower())):
        return [app_commands.Choice(name=saved, value=saved)]
    return []


@client.tree.command(name="analyze", description="分析 Renaiss 錢包的 USDT 交易統計")
@app_commands.describe(wallet="BSC 錢包地址（0x 開頭）— 不填則使用上次的地址")
@app_commands.autocomplete(wallet=_wallet_autocomplete)
async def analyze(interaction: discord.Interaction, wallet: str = None):
    uid = interaction.user.id

    if wallet:
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", wallet):
            await interaction.response.send_message(
                "❌ 錢包地址格式錯誤，請輸入正確的 BSC 地址（0x 開頭，42 個字元）",
                ephemeral=True,
            )
            return
        _save_user_wallet(uid, wallet)
    else:
        wallet = _get_user_wallet(uid)
        if not wallet:
            await interaction.response.send_message(
                "❌ 尚無儲存的地址，請輸入你的 BSC 錢包地址。",
                ephemeral=True,
            )
            return

    await interaction.response.defer()

    try:
        from analyze_all import analyze_wallet
        result = await asyncio.get_event_loop().run_in_executor(None, analyze_wallet, wallet)
    except Exception as e:
        await interaction.followup.send(f"❌ 查詢失敗：{e}")
        return

    r = result
    s = r["summary"]
    op = r["open_pack"]
    bb = r["buyback"]
    mb = r["marketplace_buy"]
    ms = r["marketplace_sell"]

    color = discord.Color.red() if s["net_spent"] > 0 else discord.Color.green()
    masked = f"{wallet[:6]}...{wallet[-4:]}"

    embed = discord.Embed(
        title="📊 Renaiss 交易統計",
        description=f"`{masked}`",
        color=color,
    )
    embed.add_field(
        name="📦 開卡包",
        value=f"共 **{op['count']}** 包\n花費 **{op['usdt_spent']:,.2f}** USDT",
        inline=True,
    )
    embed.add_field(
        name="💰 Buyback（賣回項目方）",
        value=f"共 **{bb['count']}** 筆\n收到 **{bb['usdt_received']:,.2f}** USDT",
        inline=True,
    )
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.add_field(
        name="🛒 交易平台 買入",
        value=f"共 **{mb['count']}** 筆\n花費 **{mb['usdt_spent']:,.2f}** USDT",
        inline=True,
    )
    embed.add_field(
        name="💵 交易平台 賣出",
        value=f"共 **{ms['count']}** 筆\n收到 **{ms['usdt_received']:,.2f}** USDT",
        inline=True,
    )
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.add_field(
        name="📈 總覽",
        value=(
            f"總花費：**{s['total_cost']:,.2f}** USDT\n"
            f"總收入：**{s['total_income']:,.2f}** USDT\n"
            f"淨{'支出' if s['net_spent'] > 0 else '獲利'}：**{abs(s['net_spent']):,.2f}** USDT"
        ),
        inline=False,
    )
    embed.set_footer(text=f"資料來源：BSCScan｜共掃描 {r['total_transfers']} 筆 USDT 轉帳")

    await interaction.followup.send(embed=embed)


# ── /sbt_stats ─────────────────────────────────────────────────────────────────

def _sbt_stats_query() -> list[tuple[str, int]]:
    try:
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("""
            SELECT m.name, COUNT(DISTINCT h.address) AS holders
            FROM sbt_metadata m
            LEFT JOIN holdings h ON h.token_id = m.token_id
            GROUP BY m.token_id
            ORDER BY holders DESC
        """).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


_EMBED_DESC_LIMIT = 4096


def _sbt_stats_embeds(rows: list) -> list[discord.Embed]:
    """Split rows into multiple embeds, each within the description character limit."""
    header = "**SBT Name** — Number of unique holders\n\n"
    lines = [f"**{name}** — {holders:,}" for name, holders in rows]

    embeds, current_lines, total = [], [], len(header)
    for line in lines:
        cost = len(line) + 1  # +1 for newline
        if total + cost > _EMBED_DESC_LIMIT:
            embeds.append("\n".join(current_lines))
            current_lines, total = [], 0
        current_lines.append(line)
        total += cost
    if current_lines:
        embeds.append("\n".join(current_lines))

    result = []
    for i, desc in enumerate(embeds):
        embed = discord.Embed(
            title="📊 SBT Holder Statistics",
            description=(header + desc) if i == 0 else desc,
            color=discord.Color.gold(),
        )
        if i == len(embeds) - 1:
            embed.set_footer(text=f"{len(rows)} SBT types · Updated every 10 minutes")
        result.append(embed)
    return result


@client.tree.command(name="sbt_stats", description="View holder count for each SBT")
async def sbt_stats(interaction: discord.Interaction):
    rows = _sbt_stats_query()
    if not rows:
        await interaction.response.send_message("❌ No data available.", ephemeral=True)
        return
    embeds = _sbt_stats_embeds(rows)
    await interaction.response.send_message(embed=embeds[0])
    for embed in embeds[1:]:
        await interaction.followup.send(embed=embed)


# ── /sbt_rank ──────────────────────────────────────────────────────────────────

async def _address_autocomplete(interaction: discord.Interaction, current: str):
    saved = _get_user_wallet(interaction.user.id)
    if saved and (not current or saved.startswith(current.lower())):
        return [app_commands.Choice(name=saved, value=saved)]
    return []


@client.tree.command(name="sbt_rank", description="Generate your Renaiss SBT ranking card")
@app_commands.describe(address="Your BSC wallet address (0x...) — omit to use your saved address")
@app_commands.autocomplete(address=_address_autocomplete)
async def sbt_rank(interaction: discord.Interaction, address: str = None):
    uid = interaction.user.id

    if address:
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
            await interaction.response.send_message(
                "Invalid address. Please provide a valid BSC address (0x + 40 hex chars).",
                ephemeral=True,
            )
            return
        _save_user_wallet(uid, address)
    else:
        address = _get_user_wallet(uid)
        if not address:
            await interaction.response.send_message(
                "No saved address found. Please provide your BSC wallet address.",
                ephemeral=True,
            )
            return

    await interaction.response.defer()

    try:
        path = await asyncio.get_event_loop().run_in_executor(None, _generate, address)
    except Exception as e:
        await interaction.followup.send(f"Error generating card: {e}")
        return

    if path is None:
        await interaction.followup.send(
            f"Address `{address}` not found in the database. "
            "Data updates every 10 minutes. Please try again shortly."
        )
        return

    await interaction.followup.send(file=discord.File(path))


def _generate(address: str):
    from generate_card import generate_card_for_address
    return generate_card_for_address(address)



# ── /pack_leaderboard ──────────────────────────────────────────────────────────

# 2026-05-01 00:00:00 UTC+8 = 2026-04-30 16:00:00 UTC
_PACK_LB_START_TS = 1777564800
_PACK_LB_START_LABEL = "2026-05-01 00:00 UTC+8"

_PACK_CONTRACT_LIST = [
    "0xaab5f5fa75437a6e9e7004c12c9c56cda4b4885a",
    "0x94e7732b0b2e7c51ffd0d56580067d9c2e2b7910",
    "0xb2891022648c5fad3721c42c05d8d283d4d53080",
]

_BSCSCAN_API   = "https://api.etherscan.io/v2/api"
_USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955"


def _pack_db_init(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pack_opens (
            tx_hash      TEXT PRIMARY KEY,
            contract     TEXT NOT NULL,
            buyer        TEXT NOT NULL,
            block_number INTEGER NOT NULL,
            timestamp    INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pack_sync_state (
            contract     TEXT PRIMARY KEY,
            last_block   INTEGER NOT NULL
        );
    """)
    conn.commit()


def _get_start_block(api_key: str) -> int:
    """Convert _PACK_LB_START_TS to BSC block number."""
    resp = requests.get(_BSCSCAN_API, params={
        "chainid": 56,
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": _PACK_LB_START_TS,
        "closest": "before",
        "apikey": api_key,
    }, timeout=30).json()
    try:
        return int(resp["result"])
    except Exception:
        return 0


def _sync_pack_opens():
    """Fetch only new on-chain pack opens and persist them to DB."""
    api_key = (
        dotenv_values(".env").get("BSCSCAN_API_KEY")
        or os.environ.get("BSCSCAN_API_KEY", "")
    )
    genesis_block = _get_start_block(api_key)

    conn = sqlite3.connect(DB_FILE)
    _pack_db_init(conn)

    for contract in _PACK_CONTRACT_LIST:
        row = conn.execute(
            "SELECT last_block FROM pack_sync_state WHERE contract = ?", (contract,)
        ).fetchone()
        cursor_block = row[0] if row else genesis_block

        while True:
            params = {
                "chainid": 56,
                "module": "account",
                "action": "tokentx",
                "address": contract,
                "contractaddress": _USDT_CONTRACT,
                "startblock": cursor_block,
                "page": 1,
                "offset": 10000,
                "sort": "asc",
                "apikey": api_key,
            }
            resp = requests.get(_BSCSCAN_API, params=params, timeout=30).json()
            if resp.get("message") == "No transactions found":
                break
            data = resp.get("result")
            if not isinstance(data, list) or not data:
                break

            new_txs = 0
            rows = []
            for tx in data:
                ts = int(tx.get("timeStamp", 0))
                if ts < _PACK_LB_START_TS:
                    continue
                if tx.get("to", "").lower() != contract:
                    continue
                rows.append((
                    tx["hash"],
                    contract,
                    tx.get("from", "").lower(),
                    int(tx["blockNumber"]),
                    ts,
                ))
                new_txs += 1

            if rows:
                conn.executemany(
                    "INSERT OR IGNORE INTO pack_opens VALUES (?,?,?,?,?)", rows
                )
                conn.commit()

            if len(data) < 10000 or new_txs == 0:
                last_block = int(data[-1]["blockNumber"])
                conn.execute(
                    "INSERT OR REPLACE INTO pack_sync_state VALUES (?,?)",
                    (contract, last_block),
                )
                conn.commit()
                break

            cursor_block = int(data[-1]["blockNumber"])
            time.sleep(0.25)

    conn.close()


def _query_pack_counts() -> dict[str, int]:
    """Return {buyer: pack_count} from the local DB cache."""
    conn = sqlite3.connect(DB_FILE)
    _pack_db_init(conn)
    rows = conn.execute(
        "SELECT buyer, COUNT(*) FROM pack_opens GROUP BY buyer"
    ).fetchall()
    conn.close()
    return {addr: cnt for addr, cnt in rows}


_PACK_LB_PAGE_SIZE = 50


def _pack_lb_embeds(counts: dict[str, int]) -> list[discord.Embed]:
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:50]

    lines = [
        f"`#{i+1:<3}` `{addr[:6]}...{addr[-4:]}` — **{cnt}** pack{'s' if cnt != 1 else ''}"
        for i, (addr, cnt) in enumerate(ranked)
    ]

    header = (
        f"**Top 50 Pack Openers**\n"
        f"Since {_PACK_LB_START_LABEL}\n\n"
    )

    # Split into pages: max _PACK_LB_PAGE_SIZE entries OR _EMBED_DESC_LIMIT chars
    pages = []
    chunk, total = [], len(header)
    for line in lines:
        cost = len(line) + 1
        if len(chunk) >= _PACK_LB_PAGE_SIZE or total + cost > _EMBED_DESC_LIMIT:
            pages.append(chunk)
            chunk, total = [], 0
        chunk.append(line)
        total += cost
    if chunk:
        pages.append(chunk)

    result = []
    for i, group in enumerate(pages):
        desc = (header + "\n".join(group)) if i == 0 else "\n".join(group)
        embed = discord.Embed(
            title="📦 Pack Opening Leaderboard",
            description=desc,
            color=discord.Color.blurple(),
        )
        if i == len(pages) - 1:
            total_opens = sum(counts.values())
            embed.set_footer(
                text=f"{len(counts)} unique addresses · {total_opens} total packs opened"
            )
        result.append(embed)
    return result


@client.tree.command(name="pack_leaderboard", description="Top 50 pack openers since 2026-05-01 (UTC+8)")
async def pack_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        await asyncio.get_event_loop().run_in_executor(None, _sync_pack_opens)
        counts = await asyncio.get_event_loop().run_in_executor(None, _query_pack_counts)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to fetch data: {e}")
        return

    if not counts:
        await interaction.followup.send("No pack opens found since the start date.")
        return

    embeds = _pack_lb_embeds(counts)
    await interaction.followup.send(embed=embeds[0])
    for embed in embeds[1:]:
        await interaction.followup.send(embed=embed)


# ── Background update ──────────────────────────────────────────────────────────

def _run_update():
    try:
        subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "nft_top_holders.py")],
            cwd=BASE_DIR, check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        pass
    try:
        _sync_pack_opens()
    except Exception:
        pass


async def periodic_update():
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.get_event_loop().run_in_executor(None, _run_update)
        await asyncio.sleep(600)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client.run(TOKEN)
