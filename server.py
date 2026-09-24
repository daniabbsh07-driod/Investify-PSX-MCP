from __future__ import annotations

import time
import os
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP
from pypsx import TradingClient

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
PYPSX_API_KEY = os.getenv("PYPSX_API_KEY")
PYPSX_SECRET_KEY = os.getenv("PYPSX_SECRET_KEY")

pypsx_client = TradingClient(
    api_key=PYPSX_API_KEY,
    secret_key=PYPSX_SECRET_KEY,
    paper=True,
)

@mcp.tool()
def test_pypsx_connection() -> dict:
    """Test pyPSX authentication without exposing credentials."""
    try:
        account = pypsx_client.get_account()
        return {
            "success": True,
            "message": "pyPSX connection successful",
            "account": str(account),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
@mcp.tool()
def test_pypsx_quote(symbol: str = "LUCK") -> dict:
    """Test pyPSX market quote without changing the existing Yahoo quote tool."""
    try:
        symbol = symbol.upper().strip()
        result = pypsx_client.get_quote(symbol)

        return {
            "success": True,
            "symbol": symbol,
            "data": result,
            "source": "pyPSX",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "source": "pyPSX",
        }
        @mcp.tool()
def pypsx_quote(symbol: str) -> dict:
    """Current pyPSX market snapshot. Updates every few seconds during market hours."""
    symbol = symbol.upper().strip()
    try:
        data = pypsx_client.get_quote(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "data": data,
            "is_realtime": True,
            "source": "pyPSX",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "source": "pyPSX",
        }


@mcp.tool()
def pypsx_history(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    limit: int = 250,
) -> dict:
    """Daily PSX OHLCV history from pyPSX."""
    symbol = symbol.upper().strip()
    try:
        bars = pypsx_client.get_historical(
            symbol,
            start=start,
            end=end,
        )

        if limit < 1:
            limit = 1

        bars = bars[-limit:]

        return {
            "success": True,
            "symbol": symbol,
            "interval": "1d",
            "count": len(bars),
            "data": bars,
            "source": "pyPSX",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "source": "pyPSX",
        }


@mcp.tool()
def pypsx_intraday(
    symbol: str,
    days: int = 2,
) -> dict:
    """Latest 1-minute PSX OHLCV candles from pyPSX."""
    symbol = symbol.upper().strip()

    if days < 1:
        days = 1
    if days > 2:
        days = 2

    try:
        candles = pypsx_client.get_intraday(
            symbol,
            days=days,
        )

        return {
            "success": True,
            "symbol": symbol,
            "days": days,
            "interval": "1m",
            "count": len(candles),
            "data": candles,
            "source": "pyPSX",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "source": "pyPSX",
        }


@mcp.tool()
def pypsx_historical_intraday(
    symbol: str,
    start: str,
    end: str,
    interval: str = "5m",
) -> dict:
    """Historical intraday PSX candles: 1m, 5m, 15m or 1h."""
    symbol = symbol.upper().strip()
    interval = interval.lower().strip()

    if interval not in {"1m", "5m", "15m", "1h"}:
        return {
            "success": False,
            "symbol": symbol,
            "error": "interval must be 1m, 5m, 15m or 1h",
            "source": "pyPSX",
        }

    try:
        data = pypsx_client.get_historical_intraday(
            [symbol],
            start=start,
            end=end,
            interval=interval,
        )

        return {
            "success": True,
            "symbol": symbol,
            "interval": interval,
            "data": data,
            "source": "pyPSX",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "source": "pyPSX",
        }


@mcp.tool()
def pypsx_recent_trades(
    symbol: str,
    limit: int = 20,
) -> dict:
    """Recent PSX trade ticks."""
    symbol = symbol.upper().strip()

    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    try:
        trades = pypsx_client.get_recent_trades(
            symbol,
            limit=limit,
        )

        return {
            "success": True,
            "symbol": symbol,
            "count": len(trades),
            "data": trades,
            "source": "pyPSX",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "source": "pyPSX",
        }


@mcp.tool()
def pypsx_fundamentals(symbol: str) -> dict:
    """PSX fundamentals available from pyPSX."""
    symbol = symbol.upper().strip()

    try:
        data = pypsx_client.get_fundamentals(symbol)

        return {
            "success": True,
            "symbol": symbol,
            "data": data,
            "source": "pyPSX",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "source": "pyPSX",
        }


@mcp.tool()
def pypsx_full_snapshot(symbol: str) -> dict:
    """Combined current quote, recent 1m candles, trades and fundamentals."""
    symbol = symbol.upper().strip()

    result = {
        "symbol": symbol,
        "source": "pyPSX",
    }

    try:
        result["quote"] = pypsx_client.get_quote(symbol)
    except Exception as e:
        result["quote_error"] = str(e)

    try:
        result["intraday_1m"] = pypsx_client.get_intraday(
            symbol,
            days=2,
        )
    except Exception as e:
        result["intraday_error"] = str(e)

    try:
        result["recent_trades"] = pypsx_client.get_recent_trades(
            symbol,
            limit=20,
        )
    except Exception as e:
        result["recent_trades_error"] = str(e)

    try:
        result["fundamentals"] = pypsx_client.get_fundamentals(symbol)
    except Exception as e:
        result["fundamentals_error"] = str(e)

    return result
# ============================================================
# YAHOO FINANCE DATA SOURCE
# PSX symbols generally use .KA
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

    symbol = _clean_symbol(symbol)
    yahoo_symbol = _yahoo_symbol(symbol)

    url = f"{YAHOO_CHART_URL}/{yahoo_symbol}"

    params = {
        "range": range_,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }

    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=25,
    )

    response.raise_for_status()

    payload = response.json()

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

    quote_list = (
        result
        .get("indicators", {})
        .get("quote", [])
    )

    if not quote_list:
        return []

    quote_data = quote_list[0]

    opens = quote_data.get("open", [])
    highs = quote_data.get("high", [])
    lows = quote_data.get("low", [])
    closes = quote_data.get("close", [])
    volumes = quote_data.get("volume", [])

    rows = []

    for i, timestamp in enumerate(timestamps):

        close = (
            closes[i]
            if i < len(closes)
            else None
        )

        if close is None:
            continue

        rows.append({
            "timestamp": timestamp,
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
        })

    return rows


# ============================================================
# INDICATOR FUNCTIONS
# ============================================================

def _sma(values: list[float], period: int):

    if period <= 0 or len(values) < period:
        return None

    return sum(values[-period:]) / period


def _ema_series(
    values: list[float],
    period: int,
):

    if not values or period <= 0:
        return []

    multiplier = 2 / (period + 1)

    ema_values = [values[0]]

    for value in values[1:]:

        previous = ema_values[-1]

        ema = (
            value * multiplier
            + previous * (1 - multiplier)
        )

        ema_values.append(ema)

    return ema_values


def _rsi(
    values: list[float],
    period: int = 14,
):

    if period <= 0:
        return None

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
            (avg_gain * (period - 1))
            + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1))
            + losses[i]
        ) / period

    if avg_loss == 0:

        if avg_gain == 0:
            return 50.0

        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def _macd_values(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
):

    if (
        fast <= 0
        or slow <= 0
        or signal <= 0
        or fast >= slow
    ):
        return None

    if len(values) < slow:
        return None

    fast_ema = _ema_series(
        values,
        fast,
    )

    slow_ema = _ema_series(
        values,
        slow,
    )

    macd_line = [
        fast_ema[i] - slow_ema[i]
        for i in range(len(values))
    ]

    signal_line = _ema_series(
        macd_line,
        signal,
    )

    if not signal_line:
        return None

    macd_value = macd_line[-1]
    signal_value = signal_line[-1]

    return {
        "macd": macd_value,
        "signal": signal_value,
        "histogram": (
            macd_value - signal_value
        ),
    }


# ============================================================
# MCP TOOL: QUOTE
# ============================================================

@mcp.tool()
def quote(symbol: str) -> dict:
    """
    Return the latest available verified daily OHLCV bar.

    Important:
    This is NOT advertised as a live real-time PSX quote.
    Yahoo Finance meta regularMarketPrice is intentionally
    not used because it may be stale/inconsistent for PSX.
    """

    symbol = _clean_symbol(symbol)

    rows = _series(symbol)

    if not rows:

        return {
            "symbol": symbol,
            "yahoo_symbol": _yahoo_symbol(symbol),
            "error": "No daily market data available",
            "source": "Yahoo Finance",
        }

    latest = rows[-1]

    previous = (
        rows[-2]
        if len(rows) >= 2
        else None
    )

    latest_close = latest.get("close")

    previous_close = (
        previous.get("close")
        if previous
        else None
    )

    change = None
    change_percent = None

    if (
        latest_close is not None
        and previous_close is not None
    ):

        change = latest_close - previous_close

        if previous_close != 0:
            change_percent = (
                change / previous_close
            ) * 100

    return {
        "symbol": symbol,
        "yahoo_symbol": _yahoo_symbol(symbol),

        "latest_close": latest_close,

        "previous_close": previous_close,

        "change": change,

        "change_percent": change_percent,

        "timestamp": latest.get("timestamp"),

        "open": latest.get("open"),
        "high": latest.get("high"),
        "low": latest.get("low"),
        "close": latest_close,
        "volume": latest.get("volume"),

        "quote_type": "latest_available_daily_bar",

        "is_realtime": False,

        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL: HISTORY
# ============================================================

@mcp.tool()
def history(
    symbol: str,
    limit: int = 250,
) -> dict:
    """
    Return daily historical OHLCV data.
    """

    symbol = _clean_symbol(symbol)

    rows = _series(symbol)

    if limit < 1:
        limit = 1

    selected = rows[-limit:]

    return {
        "symbol": symbol,
        "yahoo_symbol": _yahoo_symbol(symbol),
        "interval": "1d",
        "count": len(selected),
        "data": selected,
        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL: INTRADAY
# ============================================================

@mcp.tool()
def intraday(symbol: str) -> dict:
    """
    Intraday is deliberately disabled.

    Yahoo Finance was observed returning daily PSX bars even
    when a 5-minute interval was requested. Returning those
    bars as intraday would be misleading.
    """

    symbol = _clean_symbol(symbol)

    return {
        "symbol": symbol,
        "yahoo_symbol": _yahoo_symbol(symbol),

        "available": False,

        "data": [],

        "message": (
            "Reliable PSX intraday data is currently unavailable "
            "from the configured source. Daily bars are not being "
            "misrepresented as intraday data."
        ),

        "source": None,
    }


# ============================================================
# MCP TOOL: RSI
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

        "observations": len(closes),

        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL: MACD
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

    values = _macd_values(
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

        "values": values,

        "last_close": (
            closes[-1]
            if closes
            else None
        ),

        "observations": len(closes),

        "source": "Yahoo Finance",
    }


# ============================================================
# MCP TOOL: TECHNICALS
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
# MCP TOOL: ANALYZE STOCK
# ============================================================

@mcp.tool()
def analyze_stock(symbol: str) -> dict:
    """
    Return factual technical measurements.

    This tool does not claim guaranteed profit
    or guaranteed future price movement.
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

    return {
        "symbol": symbol,

        "last_available_close": current,

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

        "data_type": "daily",

        "is_realtime": False,

        "source": "Yahoo Finance",

        "generated_at_unix": int(
            time.time()
        ),
    }


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http"
    )
