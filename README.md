# Renaiss Transaction Analyzer

分析指定 BSC 錢包在 Renaiss 項目的所有 USDT 交易統計，支援 CLI 執行與 Discord Bot。

## 功能

- 開卡包次數與花費 USDT
- Buyback 賣回項目方收到的 USDT
- 交易平台買入 / 賣出的 USDT

## 環境需求

- Python 3.10+
- BSCScan API Key（免費申請：https://bscscan.com/myapikey）
- Discord Bot Token（若使用 Bot 功能）

## 安裝

```bash
pip install -r requirements.txt
```

## 設定

複製 `.env.example` 並改名為 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

```env
BSCSCAN_API_KEY=your_bscscan_api_key_here
DISCORD_TOKEN=your_discord_bot_token_here  # 只有使用 Bot 才需要
```

## 使用方式

### CLI 直接執行

在 `.env` 加入要查詢的錢包地址：

```env
WALLET=0xYourWalletAddressHere
```

```bash
python analyze_all.py
```

### Discord Bot

**步驟一：建立 Bot**

1. 前往 https://discord.com/developers/applications → New Application
2. 左側 Bot → Reset Token → 複製 token 填入 `.env`
3. 左側 OAuth2 → URL Generator
   - Scopes：`bot` + `applications.commands`
   - Bot Permissions：`Send Messages` + `Embed Links`
4. 複製產生的 URL，在瀏覽器開啟，將 Bot 加入你的伺服器

**步驟二：啟動 Bot**

```bash
python bot.py
```

看到 `Bot 已上線` 後，在 Discord 頻道使用指令：

**步驟一：輸入 `/` 叫出指令提示，選擇 `/analyze`**

![輸入指令](images/usage_slash.png)

**步驟二：輸入你的 BSC 錢包地址後送出，Bot 會公開回覆統計結果**

![查詢結果](images/usage_result.png)

## 新增卡包合約

若項目方推出新版卡包合約，在 `analyze_all.py` 的 `PACK_CONTRACTS` 加入新地址：

```python
PACK_CONTRACTS = {addr.lower() for addr in {
    "0xaab5f5fa75437a6e9e7004c12c9c56cda4b4885a",
    "0x94e7732b0b2e7c51ffd0d56580067d9c2e2b7910",
    "0xb2891022648c5fad3721c42c05d8d283d4d53080",
    "0x新合約地址",  # 新增這裡
}}
```
