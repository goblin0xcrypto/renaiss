"""
Renaiss 完整交易統計分析
透過 BSCScan tokentx API 分析錢包所有 USDT 流向，依合約分類統計
可作為模組被 bot.py 引用，也可直接執行
"""

import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

# ========================
# 設定（敏感資訊從 .env 讀取）
# ========================
USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955"
USDT_DECIMALS = 18

BSCSCAN_API = "https://api.etherscan.io/v2/api"
BSCSCAN_CHAIN_ID = 56
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")

# ========================
# 合約分類（全小寫）
# ========================
PACK_CONTRACTS = {addr.lower() for addr in {
    "0xaab5f5fa75437a6e9e7004c12c9c56cda4b4885a",
    "0x94e7732b0b2e7c51ffd0d56580067d9c2e2b7910",
    "0xb2891022648c5Fad3721C42C05d8d283D4d53080",
}}

MARKETPLACE_CONTRACT = "0xae3e7268ef5a062946216a44f58a8f685ffd11d0"


# ========================
# 核心函式
# ========================
def fetch_all_usdt_transfers(wallet: str) -> list:
    """抓取指定錢包所有 USDT 轉帳記錄"""
    all_transfers = []
    page = 1
    while True:
        params = {
            "chainid": BSCSCAN_CHAIN_ID,
            "module": "account",
            "action": "tokentx",
            "address": wallet,
            "contractaddress": USDT_CONTRACT,
            "page": page,
            "offset": 10000,
            "sort": "asc",
            "apikey": BSCSCAN_API_KEY,
        }
        resp = requests.get(BSCSCAN_API, params=params, timeout=30).json()
        if resp.get("message") == "No transactions found":
            break
        data = resp.get("result", [])
        if not data:
            break
        all_transfers.extend(data)
        if len(data) < 10000:
            break
        page += 1
        time.sleep(0.2)
    return all_transfers


def classify_transfer(t: dict, wallet: str) -> str:
    frm = t.get("from", "").lower()
    to = t.get("to", "").lower()
    if frm == wallet and to in PACK_CONTRACTS:
        return "open_pack"
    if frm in PACK_CONTRACTS and to == wallet:
        return "buyback"
    if frm == wallet and to == MARKETPLACE_CONTRACT:
        return "mp_buy"
    if frm == MARKETPLACE_CONTRACT and to == wallet:
        return "mp_sell"
    return "other"


def analyze_wallet(wallet: str) -> dict:
    """
    分析指定錢包的 Renaiss 交易統計
    回傳結構化結果 dict，供 bot 或 CLI 使用
    """
    wallet = wallet.lower()
    transfers = fetch_all_usdt_transfers(wallet)

    groups = {"open_pack": [], "buyback": [], "mp_buy": [], "mp_sell": [], "other": []}
    for t in transfers:
        groups[classify_transfer(t, wallet)].append(t)

    def sum_usdt(lst):
        return sum(int(t.get("value", "0")) / (10 ** USDT_DECIMALS) for t in lst)

    def count_unique_tx(lst):
        return len(set(t.get("hash") for t in lst))

    pack_txs   = count_unique_tx(groups["open_pack"])
    pack_usdt  = sum_usdt(groups["open_pack"])
    bb_txs     = count_unique_tx(groups["buyback"])
    bb_usdt    = sum_usdt(groups["buyback"])
    buy_txs    = count_unique_tx(groups["mp_buy"])
    buy_usdt   = sum_usdt(groups["mp_buy"])
    sell_txs   = count_unique_tx(groups["mp_sell"])
    sell_usdt  = sum_usdt(groups["mp_sell"])

    total_cost   = pack_usdt + buy_usdt
    total_income = bb_usdt + sell_usdt

    return {
        "wallet": wallet,
        "total_transfers": len(transfers),
        "open_pack":        {"count": pack_txs, "usdt_spent":    round(pack_usdt, 4)},
        "buyback":          {"count": bb_txs,   "usdt_received": round(bb_usdt,   4)},
        "marketplace_buy":  {"count": buy_txs,  "usdt_spent":    round(buy_usdt,  4)},
        "marketplace_sell": {"count": sell_txs, "usdt_received": round(sell_usdt, 4)},
        "summary": {
            "total_cost":   round(total_cost,   4),
            "total_income": round(total_income, 4),
            "net_spent":    round(total_cost - total_income, 4),
        },
    }


# ========================
# CLI 獨立執行
# ========================
def main():
    wallet = os.getenv("WALLET", "0x17C011298047e8EBd116749782A3d5f3C618d8B7")
    print(f"分析錢包: {wallet}\n正在抓取資料...")
    result = analyze_wallet(wallet)
    r = result

    print(f"\n共取得 {r['total_transfers']} 筆 USDT 轉帳\n")
    print("=" * 50)
    print(f"1. 開卡包：{r['open_pack']['count']} 包，花費 {r['open_pack']['usdt_spent']} USDT")
    print(f"2. Buyback：{r['buyback']['count']} 筆，收到 {r['buyback']['usdt_received']} USDT")
    print(f"3. 交易平台 買：{r['marketplace_buy']['count']} 筆，花費 {r['marketplace_buy']['usdt_spent']} USDT")
    print(f"4. 交易平台 賣：{r['marketplace_sell']['count']} 筆，收到 {r['marketplace_sell']['usdt_received']} USDT")
    print("=" * 50)
    print(f"總花費：{r['summary']['total_cost']} USDT")
    print(f"總收入：{r['summary']['total_income']} USDT")
    print(f"淨支出：{r['summary']['net_spent']} USDT")

    out_path = os.path.join(os.path.dirname(__file__), "renaiss_full_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n結果已儲存至: {out_path}")


if __name__ == "__main__":
    main()
