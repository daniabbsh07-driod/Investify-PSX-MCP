# Investify-PSX-MCP

A small MCP server for Pakistan Stock Exchange data, inspired by the public PSX MCP project. It does **not** use or bypass Investify private APIs.

## Tools
- `quote(symbol)`
- `history(symbol, limit=250)`
- `intraday(symbol)`
- `rsi(symbol, period=14)`
- `macd(symbol, fast=12, slow=26, signal=9)`
- `technicals(symbol)`
- `analyze_stock(symbol)`

RSI/MACD/SMA are calculated locally from PSX end-of-day data.

## Install
Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python server.py
```

## MCP client configuration (stdio)

```json
{
  "mcpServers": {
    "investify-psx": {
      "command": "python",
      "args": ["/ABSOLUTE/PATH/Investify-PSX-MCP/server.py"]
    }
  }
}
```

For Windows, an example path is:
`C:\\Users\\YOURNAME\\Investify-PSX-MCP\\server.py`

## Important
This server currently provides PSX market/history and locally calculated technical indicators.
It intentionally does not claim to reproduce Investify's proprietary calculations or fundamentals.
Indicator values can differ between platforms because of candle source, adjustment rules, period,
rounding, and calculation conventions. Verify financial decisions against primary disclosures.
