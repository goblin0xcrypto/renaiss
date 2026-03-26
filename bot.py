"""
bot.py
======
Discord bot for Renaiss.

Commands:
  /analyze <wallet>  — analyze USDT transaction stats for a BSC wallet
  /sbt_rank <address> — generate SBT ranking card for a BSC address

Background task:
  Every 10 minutes: runs nft_top_holders.py to refresh on-chain SBT data
"""

import asyncio
import re
import subprocess
import sys
import os
import discord
from discord import app_commands
from dotenv import dotenv_values

config = dotenv_values(".env")
TOKEN = config.get("DISCORD_TOKEN") or os.environ.get("DISCORD_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


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

@client.tree.command(name="analyze", description="分析 Renaiss 錢包的 USDT 交易統計")
@app_commands.describe(wallet="BSC 錢包地址（0x 開頭）")
async def analyze(interaction: discord.Interaction, wallet: str):
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", wallet):
        await interaction.response.send_message(
            "❌ 錢包地址格式錯誤，請輸入正確的 BSC 地址（0x 開頭，42 個字元）",
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


# ── /sbt_rank ──────────────────────────────────────────────────────────────────

@client.tree.command(name="sbt_rank", description="Generate your Renaiss SBT ranking card")
@app_commands.describe(address="Your BSC wallet address (0x...)")
async def sbt_rank(interaction: discord.Interaction, address: str):
    if not address.startswith("0x") or len(address) != 42:
        await interaction.response.send_message(
            "Invalid address. Please provide a valid BSC address (0x + 40 hex chars).",
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


# ── Background update ──────────────────────────────────────────────────────────

def _run_update():
    try:
        subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "nft_top_holders.py")],
            cwd=BASE_DIR, check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        pass


async def periodic_update():
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.get_event_loop().run_in_executor(None, _run_update)
        await asyncio.sleep(600)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client.run(TOKEN)
