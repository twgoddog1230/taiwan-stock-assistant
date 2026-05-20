import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """計算所有技術指標"""
    if df is None or len(df) < 30:
        return df

    df = df.copy().sort_values("date").reset_index(drop=True)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # 均線系統
    for period in [5, 10, 20, 60, 120, 240]:
        df[f"ma{period}"] = close.rolling(period).mean()

    # 均線多頭排列分數
    df["ma_alignment"] = 0.0
    ma_periods = [5, 10, 20, 60]
    for i in range(len(df)):
        row = df.iloc[i]
        count = 0
        total = len(ma_periods) - 1
        for j in range(len(ma_periods) - 1):
            v1 = row.get(f"ma{ma_periods[j]}")
            v2 = row.get(f"ma{ma_periods[j+1]}")
            if pd.notna(v1) and pd.notna(v2) and v1 > v2:
                count += 1
        df.at[i, "ma_alignment"] = count / total if total > 0 else 0

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # RSI
    df["rsi"] = _calc_rsi(close, 14)

    # KD (Stochastic)
    low_min = low.rolling(9).min()
    high_max = high.rolling(9).max()
    rsv = (close - low_min) / (high_max - low_min + 1e-9) * 100
    k = pd.Series(index=df.index, dtype=float)
    d = pd.Series(index=df.index, dtype=float)
    k.iloc[0] = 50.0
    d.iloc[0] = 50.0
    for i in range(1, len(df)):
        k.iloc[i] = k.iloc[i-1] * 2/3 + rsv.iloc[i] * 1/3
        d.iloc[i] = d.iloc[i-1] * 2/3 + k.iloc[i] * 1/3
    df["k"] = k
    df["d"] = d

    # 布林通道
    df["bb_mid"] = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std
    df["bb_pct"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)

    # 量能分析
    df["vol_ma5"] = volume.rolling(5).mean()
    df["vol_ma20"] = volume.rolling(20).mean()
    df["vol_ratio"] = volume / (df["vol_ma20"] + 1e-9)

    # 價格位置（在近60日高低之間的位置）
    df["price_position"] = (close - low.rolling(60).min()) / (high.rolling(60).max() - low.rolling(60).min() + 1e-9)

    # 漲跌幅
    df["change_pct"] = close.pct_change() * 100

    return df

def _calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - 100 / (1 + rs)

def score_technical(df: pd.DataFrame) -> dict:
    """技術面評分（滿分20分）"""
    if df is None or len(df) < 2:
        return {"score": 0, "details": []}

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    score = 0.0
    details = []

    # 均線多頭排列 (0-6分)
    alignment = float(latest.get("ma_alignment", 0))
    ma_score = alignment * 6
    score += ma_score
    if ma_score >= 4:
        details.append(f"均線多頭排列 +{ma_score:.1f}")

    # MACD 訊號 (0-5分)
    macd = latest.get("macd", 0)
    macd_hist = latest.get("macd_hist", 0)
    prev_hist = prev.get("macd_hist", 0)
    if pd.notna(macd) and pd.notna(macd_hist):
        if macd > 0 and macd_hist > 0:
            score += 3
            details.append("MACD 多頭區間 +3")
        elif macd_hist > 0 and (pd.isna(prev_hist) or prev_hist <= 0):
            score += 5
            details.append("MACD 金叉訊號 +5")
        elif macd_hist > prev_hist:
            score += 2
            details.append("MACD 動能增強 +2")

    # RSI 狀態 (0-5分)
    rsi = latest.get("rsi")
    if pd.notna(rsi):
        if 40 <= rsi <= 70:
            score += 3
            details.append(f"RSI 健康區間({rsi:.0f}) +3")
        elif 30 <= rsi < 40:
            score += 5
            details.append(f"RSI 超賣反彈({rsi:.0f}) +5")
        elif rsi > 80:
            score -= 2
            details.append(f"RSI 超買({rsi:.0f}) -2")

    # KD 訊號 (0-4分)
    k = latest.get("k")
    d = latest.get("d")
    prev_k = prev.get("k")
    prev_d = prev.get("d")
    if all(pd.notna(v) for v in [k, d, prev_k, prev_d]):
        if k > d and prev_k <= prev_d:
            score += 4
            details.append("KD 金叉 +4")
        elif k > d and k < 80:
            score += 2
            details.append("KD 多頭 +2")

    score = max(0, min(20, score))
    return {"score": round(score, 1), "details": details}

def get_technical_signal(df: pd.DataFrame) -> str:
    """判斷技術面買賣訊號"""
    result = score_technical(df)
    score = result["score"]
    if score >= 14:
        return "strong_buy"
    elif score >= 10:
        return "buy"
    elif score >= 6:
        return "hold"
    else:
        return "sell"
