from __future__ import annotations

import time
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP


# ============================================================
# MCP SERVER
# ============================================================

mcp = FastMCP(
    "Investify-PSX-MCP",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
    json_response=True,
)


# ============================================================
# DATA SOURCE
# Yahoo Finance uses .KA for Karachi Stock Exchange / PSX
# Example: LUCK -> LUCK.KA
# ============================================================

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}


def _clean_symbol(symbol: str) -> str:
    symbol = symbol.upper().strip()

    if symbol.endswith(".KA"):
        symbol = symbol[:-3]

    return symbol


def _yahoo_symbol(symbol: str) -> str:
    return f"{_clean_symbol(symbol)}.KA"


def _yahoo_chart(
    symbol: str,
    range_: str = "2y",
    interval: str = "1d",
) -> dict[str, Any]:

    psx_symbol = _clean_symbol(symbol)
    yahoo_symbol = _yahoo_symbol(psx_symbol)

    url = f"{YAHOO_CHART_URL}/{yahoo_symbol}"

    params = {
        "range": range_,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }

    r = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=25,
    )

    r.raise_for_status()

    payload = r.json()

    chart = payload.get("chart", {})

    if chart.get("error"):
        raise ValueError(
            f"Yahoo Finance error for {yahoo_symbol}: "
            f"{chart['error']}"
        )

    results = chart.get("result")

    if not results:
        raise ValueError(
            f"No Yahoo Finance data found for {yahoo_symbol}"
        )

    return results[0]


# ============================================================
# DAILY HISTORICAL SERIES
# ============================================================

def _series(symbol: str) -> list[dict[str, Any]]:

    result = _yahoo_chart(
        symbol,
        range_="2y",
        interval="1d",
    )

    timestamps = result.get("timestamp", [])

    indicators = result.get("indicators", {})
    quote_list = indicators.get("quote", [])

    if not quote_list:
        return []

    quote = quote_list[0]

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    rows = []

    for i, ts in enumerate(timestamps):

        close = closes[i] if i < len(closes) else None

        if close is None:
            continue

        row = {
            "timestamp": ts,
            "open": (
                opens[i]
                if i < len(opens)
                else None
            ),
            "high": (
                highs[i]
                if i < len(highs)
                else None
            ),
            "low": (
                lows[i]
                if i < len(lows)
                else None
            ),
            "close": float(close),
            "volume": (
                volumes[i]
                if i < len(volumes)
                else None
            ),
        }

        rows.append(row)

    return rows


# ============================================================
# INDICATORS
# ============================================================

def _sma(values: list[float], period: int):

    if len(values) < period:
        return None

    return sum(values[-period:]) / period


def _ema_series(values: list[float], period: int):

    if not values:
        return []

    k = 2 / (period + 1)

    result = [values[0]]

    for value in values[1:]:

        result.append(
            value * k
            + result[-1] * (1 - k)
        )

    return result


def _rsi(values: list[float], period: int = 14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = values[i] - values[i - 1]

        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):

        avg_gain = (
            avg_gain * (period - 1)
            + gains[i]
        ) / period

        avg_loss = (
            avg_loss * (period - 1)
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def _macd_values(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
):

    if len(values) < slow:
        return None

    fast_ema = _ema_series(values, fast)
    slow_ema = _ema_series(values, slow)

    macd_line = [
        fast_ema[i] - slow_ema[i]
        for i in range(len(values))
    ]

    signal_line = _ema_series(
        macd_line,
        signal,
    )

    macd = macd_line[-1]
    signal_value = signal_line[-1]
    histogram = macd - signal_value

    return {
        "macd": macd,
        "signal": signal_value,
        "histogram": histogram,
    }


# ============================================================
# MCP TOOL — QUOTE
# ============================================================

@mcp.tool()
def quote(symbol: str) -> dict:
    """
    Latest available PSX quote using Yahoo Finance .KA data.
    """

    symbol = _clean_symbol(symbol)

    result = _yahoo_chart(
        symbol,
        range_="5d",
        interval="1d",
    )

    meta = result.get("meta", {})

    rows = []

    timestamps = result.get("timestamp", [])
    quote_list = (
        result
        .get("indicators", {})
        .get("quote", [])
    )

    if quote_list:

        q = quote_list[0]

        closes = q.get("close", [])
        opens = q.get("open", [])
        highs = q.get("high", [])
        lows = q.get("low", [])
        volumes = q.get("volume", [])

        for i, ts in enumerate(timestamps):

            close = (
                closes[i]
                if i < len(closes)
                else None
            )

            if close is None:
                continue

            rows.append({
                "timestamp": ts,
                "open": (
                    opens[i]
                    if i < len(opens)
                    else None
                ),
                "high": (
                    highs[i]
                    if i < len(highs)
                    else None
                ),
                "low": (
                    lows[i]
                    if i < len(lows)
                    else None
                ),
                "close": close,
                "volume": (
                    volumes[i]
                    if i < len(volumes)
                    else None
                ),
            })

    latest_bar = rows[-1] if rows else None

    return {
        "symbol": symbol,
        "yahoo_symbol": _yahoo_symbol(symbol),
        "name": meta.get("longName")
        or meta.get("shortName"),
        "exchange": meta.get("fullExchangeName")
        or meta.get("exchangeName"),
        "currency": meta.get("currency"),
        "market_price": meta.get(
            "regularMarketPrice"
        ),
        "previous_close": meta.get(
            "chartPreviousClose"
        )
        or meta.get("previousClose"),
        "market_time": meta.get(
            "regularMarketTime"
        ),
        "latest_bar": latest_bar,
        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL — HISTORY
# ============================================================

@mcp.tool()
def history(
    symbol: str,
    limit: int = 250,
) -> dict:
    """
    PSX daily historical OHLCV.
    """

    symbol = _clean_symbol(symbol)

    rows = _series(symbol)

    if limit < 1:
        limit = 1

    selected = rows[-limit:]

    return {
        "symbol": symbol,
        "yahoo_symbol": _yahoo_symbol(symbol),
        "count": len(selected),
        "data": selected,
        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL — INTRADAY
# ============================================================

@mcp.tool()
def intraday(symbol: str) -> dict:
    """
    Recent PSX intraday data.
    Yahoo 5-minute bars are used.
    """

    symbol = _clean_symbol(symbol)

    result = _yahoo_chart(
        symbol,
        range_="5d",
        interval="5m",
    )

    timestamps = result.get("timestamp", [])

    quote_list = (
        result
        .get("indicators", {})
        .get("quote", [])
    )

    if not quote_list:

        return {
            "symbol": symbol,
            "count": 0,
            "data": [],
            "source": "Yahoo Finance",
        }

    q = quote_list[0]

    opens = q.get("open", [])
    highs = q.get("high", [])
    lows = q.get("low", [])
    closes = q.get("close", [])
    volumes = q.get("volume", [])

    rows = []

    for i, ts in enumerate(timestamps):

        close = (
            closes[i]
            if i < len(closes)
            else None
        )

        if close is None:
            continue

        rows.append({
            "timestamp": ts,
            "open": (
                opens[i]
                if i < len(opens)
                else None
            ),
            "high": (
                highs[i]
                if i < len(highs)
                else None
            ),
            "low": (
                lows[i]
                if i < len(lows)
                else None
            ),
            "close": close,
            "volume": (
                volumes[i]
                if i < len(volumes)
                else None
            ),
        })

    return {
        "symbol": symbol,
        "yahoo_symbol": _yahoo_symbol(symbol),
        "interval": "5m",
        "count": len(rows),
        "data": rows,
        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL — RSI
# ============================================================

@mcp.tool()
def rsi(
    symbol: str,
    period: int = 14,
) -> dict:

    symbol = _clean_symbol(symbol)

    rows = _series(symbol)

    closes = [
        row["close"]
        for row in rows
        if row.get("close") is not None
    ]

    value = _rsi(
        closes,
        period,
    )

    return {
        "symbol": symbol,
        "period": period,
        "rsi": value,
        "last_close": (
            closes[-1]
            if closes
            else None
        ),
        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL — MACD
# ============================================================

@mcp.tool()
def macd(
    symbol: str,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict:

    symbol = _clean_symbol(symbol)

    rows = _series(symbol)

    closes = [
        row["close"]
        for row in rows
        if row.get("close") is not None
    ]

    result = _macd_values(
        closes,
        fast,
        slow,
        signal,
    )

    return {
        "symbol": symbol,
        "fast": fast,
        "slow": slow,
        "signal_period": signal,
        "values": result,
        "last_close": (
            closes[-1]
            if closes
            else None
        ),
        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL — TECHNICALS
# ============================================================

@mcp.tool()
def technicals(symbol: str) -> dict:

    symbol = _clean_symbol(symbol)

    rows = _series(symbol)

    closes = [
        row["close"]
        for row in rows
        if row.get("close") is not None
    ]

    if not closes:

        return {
            "symbol": symbol,
            "error": "No historical data available",
        }

    return {
        "symbol": symbol,
        "last_close": closes[-1],

        "rsi14": _rsi(
            closes,
            14,
        ),

        "macd": _macd_values(
            closes,
            12,
            26,
            9,
        ),

        "sma20": _sma(
            closes,
            20,
        ),

        "sma50": _sma(
            closes,
            50,
        ),

        "sma200": _sma(
            closes,
            200,
        ),

        "observations": len(closes),

        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL — ANALYZE STOCK
# ============================================================

@mcp.tool()
def analyze_stock(symbol: str) -> dict:
    """
    Returns factual technical measurements.
    It does not provide guaranteed buy/sell advice.
    """

    symbol = _clean_symbol(symbol)

    rows = _series(symbol)

    closes = [
        row["close"]
        for row in rows
        if row.get("close") is not None
    ]

    if not closes:

        return {
            "symbol": symbol,
            "error": "No historical data available",
        }

    current = closes[-1]

    rsi14 = _rsi(
        closes,
        14,
    )

    macd_data = _macd_values(
        closes,
        12,
        26,
        9,
    )

    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)

    return {
        "symbol": symbol,
        "current_price": current,
        "rsi14": rsi14,
        "macd": macd_data,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "source": "Yahoo Finance",
        "generated_at_unix": int(time.time()),
    }


# ============================================================
# START MCP SERVER
# ============================================================

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http"
    )
