from __future__ import annotations
import math
from typing import Any
import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Investify-PSX-MCP",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
    json_response=True
)
BASE = "https://dps.psx.com.pk"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://dps.psx.com.pk/"
}

def _get_json(path: str) -> Any:
    r = requests.get(BASE + path, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def _series(symbol: str):
    symbol = symbol.upper().strip()
    data = _get_json(f"/timeseries/eod/{symbol}")
    rows = data.get("data", data) if isinstance(data, dict) else data
    out = []
    for row in rows:
        if isinstance(row, dict):
            ts = row.get("time") or row.get("timestamp") or row.get("date")
            close = row.get("close") or row.get("price")
            volume = row.get("volume")
            open_ = row.get("open")
        else:
            # PSX EOD commonly returns [timestamp, close, volume, open]
            ts = row[0] if len(row) > 0 else None
            close = row[1] if len(row) > 1 else None
            volume = row[2] if len(row) > 2 else None
            open_ = row[3] if len(row) > 3 else None
        if close is not None:
            out.append({"timestamp": ts, "close": float(close),
                        "volume": volume, "open": open_})
    out.sort(key=lambda x: x["timestamp"] if x["timestamp"] is not None else 0)
    return out

def _ema(values, period):
    if not values:
        return []
    k = 2 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1-k))
    return result

def _rsi(values, period=14):
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for a,b in zip(values[:-1], values[1:]):
        d=b-a
        gains.append(max(d,0)); losses.append(max(-d,0))
    avg_gain=sum(gains[:period])/period
    avg_loss=sum(losses[:period])/period
    for i in range(period, len(gains)):
        avg_gain=(avg_gain*(period-1)+gains[i])/period
        avg_loss=(avg_loss*(period-1)+losses[i])/period
    if avg_loss == 0:
        return 100.0
    rs=avg_gain/avg_loss
    return 100-(100/(1+rs))

@mcp.tool()
def quote(symbol: str) -> dict:
    """Latest PSX quote from market-watch."""
    symbol=symbol.upper().strip()
    r=requests.get(f"{BASE}/market-watch",headers=HEADERS,timeout=20)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    for tr in soup.select("tr"):
        cells=[c.get_text(" ",strip=True) for c in tr.select("td")]
        if cells and cells[0].upper()==symbol:
            return {"symbol":symbol,"raw_columns":cells,"source":f"{BASE}/market-watch"}
    return {"symbol":symbol,"error":"Symbol not found in current market-watch"}

@mcp.tool()
def history(symbol: str, limit: int = 250) -> dict:
    """End-of-day PSX history. Default last 250 observations."""
    rows=_series(symbol)
    return {"symbol":symbol.upper(),"count":min(limit,len(rows)),
            "data":rows[-limit:],"source":f"{BASE}/timeseries/eod/{symbol.upper()}"}

@mcp.tool()
def intraday(symbol: str) -> dict:
    """Intraday PSX time-series."""
    symbol=symbol.upper().strip()
    return {"symbol":symbol,"data":_get_json(f"/timeseries/int/{symbol}"),
            "source":f"{BASE}/timeseries/int/{symbol}"}

@mcp.tool()
def rsi(symbol: str, period: int = 14) -> dict:
    """Calculate RSI from PSX end-of-day closing prices."""
    rows=_series(symbol); vals=[x["close"] for x in rows]
    value=_rsi(vals,period)
    return {"symbol":symbol.upper(),"period":period,
            "rsi":None if value is None else round(value,2),
            "last_close": vals[-1] if vals else None,
            "observations":len(vals)}

@mcp.tool()
def macd(symbol: str, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD, signal line and histogram from PSX EOD closes."""
    rows=_series(symbol); vals=[x["close"] for x in rows]
    if len(vals) < slow + signal:
        return {"symbol":symbol.upper(),"error":"Not enough observations"}
    ef=_ema(vals,fast); es=_ema(vals,slow)
    line=[a-b for a,b in zip(ef,es)]
    sig=_ema(line,signal)
    hist=line[-1]-sig[-1]
    return {"symbol":symbol.upper(),"macd":round(line[-1],4),
            "signal":round(sig[-1],4),"histogram":round(hist,4),
            "fast":fast,"slow":slow,"signal_period":signal,
            "last_close":vals[-1]}

@mcp.tool()
def technicals(symbol: str) -> dict:
    """Compact technical snapshot: RSI(14), MACD(12,26,9), SMA20, SMA50, SMA200."""
    rows=_series(symbol); vals=[x["close"] for x in rows]
    def sma(n):
        return round(sum(vals[-n:])/n,4) if len(vals)>=n else None
    rv=_rsi(vals,14)
    ef=_ema(vals,12); es=_ema(vals,26)
    ml=[a-b for a,b in zip(ef,es)] if vals else []
    sl=_ema(ml,9) if ml else []
    return {"symbol":symbol.upper(),"last_close":vals[-1] if vals else None,
            "rsi14":round(rv,2) if rv is not None else None,
            "macd":round(ml[-1],4) if ml else None,
            "macd_signal":round(sl[-1],4) if sl else None,
            "macd_histogram":round(ml[-1]-sl[-1],4) if ml and sl else None,
            "sma20":sma(20),"sma50":sma(50),"sma200":sma(200)}

@mcp.tool()
def analyze_stock(symbol: str) -> dict:
    """One-call PSX technical dataset for AI analysis. Not investment advice."""
    return {"quote":quote(symbol),"technicals":technicals(symbol),
            "recent_history":history(symbol,60)}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
