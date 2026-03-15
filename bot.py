"""
Renaiss Discord Bot
指令：/analyze <wallet_address>
"""

import os
import re
import discord
from discord import app_commands
from dotenv import load_dotenv
from analyze_all import analyze_wallet

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ========================
# Bot 設定
# ========================
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot 已上線：{client.user}（已同步 slash commands）")


# ========================
# /analyze 指令
# ========================
@tree.command(name="analyze", description="分析 Renaiss 錢包的 USDT 交易統計")
@app_commands.describe(wallet="BSC 錢包地址（0x 開頭）")
async def analyze(interaction: discord.Interaction, wallet: str):
    # 驗證地址格式
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", wallet):
        await interaction.response.send_message(
            "❌ 錢包地址格式錯誤，請輸入正確的 BSC 地址（0x 開頭，42 個字元）",
            ephemeral=True,
        )
        return

    # 先回應「分析中」，避免 3 秒逾時（查詢可能需要數秒）
    await interaction.response.defer()

    try:
        result = await client.loop.run_in_executor(None, analyze_wallet, wallet)
    except Exception as e:
        await interaction.followup.send(f"❌ 查詢失敗：{e}")
        return

    r = result
    s = r["summary"]
    op = r["open_pack"]
    bb = r["buyback"]
    mb = r["marketplace_buy"]
    ms = r["marketplace_sell"]

    # 淨支出顏色：虧損紅、獲利綠
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
    embed.add_field(name="\u200b", value="\u200b", inline=False)  # 換行
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


# ========================
# 啟動
# ========================
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ 請在 .env 設定 DISCORD_TOKEN")
    else:
        client.run(DISCORD_TOKEN)
