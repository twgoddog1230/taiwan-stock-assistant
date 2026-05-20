import pandas as pd
import numpy as np
from datetime import date
from typing import Optional
import logging
from modules.technical import score_technical
from modules.chip import score_chip
from modules.seasonal import score_seasonal
from modules.fundamental import score_fundamental
from modules.us_market import score_momentum

logger = logging.getLogger(__name__)

def score_stock(
    symbol: str,
    price_df: pd.DataFrame,
    chip_df: Optional[pd.DataFrame] = None,
    fundamental_info: Optional[dict] = None,
    us_data: Optional[dict] = None,
    trade_date: Optional[date] = None,
) -> dict:
    """
    綜合五大面向評分（總分100分）
    技術面 20 + 籌碼面 20 + 季節效應 20 + 基本面 20 + 資金動能 20
    """
    if trade_date is None:
        trade_date = date.today()

    result = {
        "symbol": symbol,
        "date": trade_date.isoformat(),
        "total_score": 0,
        "technical": {},
        "chip": {},
        "seasonal": {},
        "fundamental": {},
        "momentum": {},
        "signal": "hold",
        "strategy": [],
        "reasoning": [],
    }

    # 1. 技術面
    tech = score_technical(price_df)
    result["technical"] = tech

    # 2. 籌碼面
    if chip_df is not None and len(chip_df) > 0:
        chip = score_chip(chip_df, price_df)
    else:
        chip = {"score": 5, "details": ["籌碼資料不足，給予基礎分"]}
    result["chip"] = chip

    # 3. 季節效應
    seasonal = score_seasonal(trade_date)
    result["seasonal"] = seasonal

    # 4. 基本面
    fundamental = score_fundamental(fundamental_info or {})
    result["fundamental"] = fundamental

    # 5. 資金動能（美股）
    if us_data:
        momentum = score_momentum(us_data)
    else:
        momentum = {"score": 10, "details": ["美股資料不足，給予中性分"]}
    result["momentum"] = momentum

    total = (
        tech["score"] +
        chip["score"] +
        seasonal["score"] +
        fundamental["score"] +
        momentum["score"]
    )
    result["total_score"] = round(total, 1)

    # 綜合所有評分理由
    result["reasoning"] = (
        tech.get("details", []) +
        chip.get("details", []) +
        seasonal.get("details", []) +
        fundamental.get("details", []) +
        momentum.get("details", [])
    )

    # 判斷信號與策略
    result["signal"] = _determine_signal(total, tech["score"], chip["score"])
    result["strategy"] = _suggest_strategy(result)

    # 計算進場價與風險點位
    if len(price_df) > 0:
        latest_close = price_df["close"].iloc[-1]
        result["entry_price"] = round(float(latest_close), 2)
        result["stop_loss"] = round(float(latest_close * 0.95), 2)   # -5%
        result["target1"] = round(float(latest_close * 1.065), 2)    # +6.5%
        result["target2"] = round(float(latest_close * 1.12), 2)     # +12%

    return result

def _determine_signal(total: float, tech: float, chip: float) -> str:
    if total >= 78 and tech >= 12:
        return "strong_buy"
    elif total >= 65:
        return "buy"
    elif total >= 50:
        return "watch"
    elif total < 35:
        return "sell"
    else:
        return "hold"

def _suggest_strategy(result: dict) -> list[str]:
    strategies = []
    total = result["total_score"]
    tech_score = result["technical"].get("score", 0)
    chip_score = result["chip"].get("score", 0)
    seasonal = result["seasonal"]

    weekday = seasonal.get("weekday", 2)

    # 當沖：技術面強 + 今日是強勢交易日（週三/四）
    if tech_score >= 14 and weekday in [2, 3] and total >= 60:
        strategies.append("day_trade")

    # 短線（1-5天）：技術+籌碼雙強
    if tech_score >= 12 and chip_score >= 12 and total >= 65:
        strategies.append("short_term")

    # 波段（數週）：五大面向均衡高分
    if total >= 70:
        strategies.append("swing")

    if not strategies:
        strategies.append("observe")

    return strategies

def rank_stocks(scores: list[dict]) -> list[dict]:
    """排序並挑選推薦股票"""
    buy_signals = [s for s in scores if s["signal"] in ("strong_buy", "buy")]
    buy_signals.sort(key=lambda x: x["total_score"], reverse=True)
    return buy_signals[:20]
