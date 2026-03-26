"""
bot.py
======
Discord bot for Renaiss SBT ranking cards.

Commands:
  /card <address>  — generate and send a profile card for the given BSC address

Background task:
  Every hour: runs nft_top_holders.py then nft_analyze.py to refresh data
"""

import asyncio
import subprocess
import sys
import os
import discord
from discord import app_commands
from dotenv import dotenv_values

config = dotenv_values(".env")
TOKEN = config.get("DISCORD_TOKEN") or os.environ.get("DISCORD_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(hourly_update())


client = Bot()


@client.event
async def on_ready():
    pass


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

    loop = asyncio.get_event_loop()
    try:
        path = await loop.run_in_executor(None, _generate, address)
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
    """Blocking call — runs in thread pool."""
    sys.path.insert(0, BASE_DIR)
    from generate_card import generate_card_for_address
    return generate_card_for_address(address)


def _run_update():
    try:
        subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "nft_top_holders.py")],
            cwd=BASE_DIR, check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        pass


async def hourly_update():
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.get_event_loop().run_in_executor(None, _run_update)
        await asyncio.sleep(600)


if __name__ == "__main__":
    client.run(TOKEN)
