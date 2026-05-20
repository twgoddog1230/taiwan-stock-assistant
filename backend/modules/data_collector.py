import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)

TWSE_BASE = "https://www.twse.com.tw/rwd/zh"
TPEX_BASE = "https://www.tpex.org.tw/web/stock"

def get_stock_list_twse() -> list[dict]:
    """取得上市股票清單"""
    try:
        url = f"{TWSE_BASE}/api/codes/listingStocks"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        stocks = []
        for item in data.get("data", []):
            if len(item) >= 2 and item[0].isdigit():
                stocks.append({"symbol": item[0], "name": item[1], "market": "TWSE"})
        return stocks
    except Exception as e:
        logger.error(f"取得上市股票清單失敗: {e}")
        return []

def get_stock_list_tpex() -> list[dict]:
    """取得上櫃股票清單"""
    try:
        url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        stocks = []
        for item in data:
            code = item.get("SecuritiesCompanyCode", "")
            name = item.get("CompanyName", "")
            if code and name:
                stocks.append({"symbol": code, "name": name, "market": "TPEX"})
        return stocks
    except Exception as e:
        logger.error(f"取得上櫃股票清單失敗: {e}")
        return []

def get_historical_prices(symbol: str, years: int = 25) -> pd.DataFrame:
    """使用 yfinance 取得歷史股價（最長25年）"""
    try:
        ticker_symbol = f"{symbol}.TW"
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(start=start_date, auto_adjust=True)
        if df.empty:
            ticker_symbol = f"{symbol}.TWO"
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_date, auto_adjust=True)
        if not df.empty:
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["symbol"] = symbol
            df = df[["symbol", "date", "open", "high", "low", "close", "volume"]].dropna()
        return df
    except Exception as e:
        logger.error(f"取得 {symbol} 歷史股價失敗: {e}")
        return pd.DataFrame()

def get_twse_daily(trade_date: Optional[str] = None) -> pd.DataFrame:
    """取得TWSE每日行情（預設今日）"""
    if not trade_date:
        trade_date = datetime.now().strftime("%Y%m%d")
    try:
        url = f"{TWSE_BASE}/api/exchangeReport/STOCK_DAY_ALL"
        params = {"date": trade_date, "response": "json"}
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        fields = data.get("fields", [])
        rows = data.get("data", [])
        df = pd.DataFrame(rows, columns=fields)
        return df
    except Exception as e:
        logger.error(f"取得TWSE每日行情失敗: {e}")
        return pd.DataFrame()

def get_three_major_investors(trade_date: Optional[str] = None) -> pd.DataFrame:
    """取得三大法人買賣超資料"""
    if not trade_date:
        trade_date = datetime.now().strftime("%Y%m%d")
    try:
        url = f"{TWSE_BASE}/api/fund/T86"
        params = {"date": trade_date, "selectType": "ALLBUT0999", "response": "json"}
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        fields = data.get("fields", [])
        rows = data.get("data", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=fields)
        return df
    except Exception as e:
        logger.error(f"取得三大法人資料失敗: {e}")
        return pd.DataFrame()

def get_margin_trading(trade_date: Optional[str] = None) -> pd.DataFrame:
    """取得融資融券資料"""
    if not trade_date:
        trade_date = datetime.now().strftime("%Y%m%d")
    try:
        url = f"{TWSE_BASE}/api/marginTrading/MI_MARGN"
        params = {"date": trade_date, "selectType": "ALL", "response": "json"}
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        fields = data.get("fields4", data.get("fields", []))
        rows = data.get("data", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=fields)
        return df
    except Exception as e:
        logger.error(f"取得融資融券資料失敗: {e}")
        return pd.DataFrame()

def get_us_market_data() -> dict:
    """取得美股主要指數收盤數據"""
    symbols = {
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dow": "^DJI",
        "sox": "^SOX",
        "vix": "^VIX",
        "usd_twd": "TWD=X",
    }
    result = {}
    try:
        for key, sym in symbols.items():
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                last_close = hist["Close"].iloc[-1]
                change_pct = ((last_close - prev_close) / prev_close) * 100
                result[key] = {
                    "close": round(float(last_close), 2),
                    "change_pct": round(float(change_pct), 2),
                }
            elif len(hist) == 1:
                result[key] = {
                    "close": round(float(hist["Close"].iloc[-1]), 2),
                    "change_pct": 0.0,
                }
    except Exception as e:
        logger.error(f"取得美股數據失敗: {e}")
    return result

def get_financial_news() -> list[dict]:
    """取得台灣財經新聞（RSS）"""
    import feedparser
    feeds = [
        "https://www.cnyes.com/rss/cat/tw_stock",
        "https://tw.stock.yahoo.com/rss",
    ]
    news = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                news.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200],
                    "published": entry.get("published", ""),
                    "link": entry.get("link", ""),
                })
        except Exception as e:
            logger.warning(f"取得新聞失敗 {feed_url}: {e}")
    return news[:10]

def get_stock_info(symbol: str) -> dict:
    """取得個股基本資訊"""
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        info = ticker.info
        if not info.get("regularMarketPrice"):
            ticker = yf.Ticker(f"{symbol}.TWO")
            info = ticker.info
        return {
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "market_cap": info.get("marketCap"),
            "dividend_yield": info.get("dividendYield"),
            "roe": info.get("returnOnEquity"),
            "eps": info.get("trailingEps"),
            "revenue_growth": info.get("revenueGrowth"),
        }
    except Exception as e:
        logger.error(f"取得 {symbol} 基本資訊失敗: {e}")
        return {}
