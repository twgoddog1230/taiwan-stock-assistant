import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional
import logging
from modules.technical import calculate_indicators, score_technical
from modules.seasonal import score_seasonal, MONTHLY_BIAS, WEEKDAY_BIAS

logger = logging.getLogger(__name__)

def run_backtest(
    price_df: pd.DataFrame,
    strategy: str = "technical",
    years: int = 5,
    stop_loss_pct: float = 0.05,
    take_profit_pct: float = 0.12,
) -> dict:
    """
    執行回測

    Args:
        price_df: 歷史股價 DataFrame
        strategy: 策略類型
        years: 回測年數
        stop_loss_pct: 停損比例
        take_profit_pct: 停利比例
    """
    if price_df is None or len(price_df) < 60:
        return {"error": "歷史數據不足，無法回測"}

    # 限制回測年限
    cutoff = date.today() - timedelta(days=years * 365)
    df = price_df[price_df["date"] >= cutoff].copy()

    if len(df) < 60:
        return {"error": "該股票歷史數據不足指定年限"}

    # 計算技術指標
    df = calculate_indicators(df)

    trades = []
    position = None  # 目前持倉

    for i in range(60, len(df)):
        row = df.iloc[i]
        hist_slice = df.iloc[max(0, i-120):i+1]
        today = row["date"]

        if position is not None:
            # 持倉中：檢查停損停利
            entry_price = position["entry_price"]
            current_price = row["close"]
            days_held = (today - position["entry_date"]).days

            hit_stop = current_price <= entry_price * (1 - stop_loss_pct)
            hit_target = current_price >= entry_price * (1 + take_profit_pct)
            max_hold = days_held >= 20  # 最長持有20天

            if hit_stop or hit_target or max_hold:
                pnl_pct = (current_price - entry_price) / entry_price * 100
                reason = "停損" if hit_stop else ("停利" if hit_target else "到期出場")
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": today,
                    "entry_price": entry_price,
                    "exit_price": float(current_price),
                    "pnl_pct": round(pnl_pct, 2),
                    "days_held": days_held,
                    "win": pnl_pct > 0,
                    "exit_reason": reason,
                })
                position = None
        else:
            # 空倉：尋找進場機會
            tech = score_technical(hist_slice)
            seasonal = score_seasonal(today)
            combined_score = tech["score"] + seasonal["score"]

            if combined_score >= 28:  # 技術+季節超過28分才進場
                position = {
                    "entry_date": today,
                    "entry_price": float(row["close"]),
                }

    # 計算回測統計
    return _calc_stats(trades, years)

def _calc_stats(trades: list, years: int) -> dict:
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_return": 0,
            "max_loss": 0,
            "max_gain": 0,
            "profit_factor": 0,
            "avg_hold_days": 0,
            "years": years,
            "monthly_stats": {},
        }

    wins = [t for t in trades if t["win"]]
    losses = [t for t in trades if not t["win"]]

    win_rate = len(wins) / len(trades) * 100
    avg_return = np.mean([t["pnl_pct"] for t in trades])
    max_loss = min([t["pnl_pct"] for t in trades])
    max_gain = max([t["pnl_pct"] for t in trades])
    avg_hold = np.mean([t["days_held"] for t in trades])

    total_gain = sum(t["pnl_pct"] for t in wins) if wins else 0
    total_loss = abs(sum(t["pnl_pct"] for t in losses)) if losses else 1
    profit_factor = total_gain / total_loss if total_loss > 0 else 0

    # 月份勝率統計
    monthly = {}
    for t in trades:
        m = t["entry_date"].month
        if m not in monthly:
            monthly[m] = {"trades": 0, "wins": 0}
        monthly[m]["trades"] += 1
        if t["win"]:
            monthly[m]["wins"] += 1

    monthly_stats = {}
    for m, v in monthly.items():
        monthly_stats[m] = {
            "trades": v["trades"],
            "win_rate": round(v["wins"] / v["trades"] * 100, 1)
        }

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_return": round(float(avg_return), 2),
        "max_loss": round(float(max_loss), 2),
        "max_gain": round(float(max_gain), 2),
        "profit_factor": round(float(profit_factor), 2),
        "avg_hold_days": round(float(avg_hold), 1),
        "years": years,
        "monthly_stats": monthly_stats,
        "trades": trades[-20:],  # 最近20筆交易
    }
