import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def score_chip(chip_df: pd.DataFrame, price_df: pd.DataFrame) -> dict:
    """籌碼面評分（滿分20分）"""
    if chip_df is None or len(chip_df) == 0:
        return {"score": 0, "details": []}

    chip_df = chip_df.sort_values("date").tail(20)
    score = 0.0
    details = []

    # 外資分析 (0-8分)
    if "foreign_net" in chip_df.columns:
        foreign_net = chip_df["foreign_net"]
        recent_5 = foreign_net.tail(5)
        consecutive_buy = 0
        for v in reversed(recent_5.values):
            if v > 0:
                consecutive_buy += 1
            else:
                break

        if consecutive_buy >= 5:
            score += 8
            details.append(f"外資連續買超 {consecutive_buy} 天 +8")
        elif consecutive_buy >= 3:
            score += 6
            details.append(f"外資連續買超 {consecutive_buy} 天 +6")
        elif consecutive_buy >= 1:
            score += 3
            details.append(f"外資近期買超 +3")
        elif recent_5.sum() < 0:
            score -= 2
            details.append("外資近期賣超 -2")

    # 投信分析 (0-5分)
    if "trust_net" in chip_df.columns:
        trust_net = chip_df["trust_net"]
        trust_recent = trust_net.tail(5)
        trust_consecutive = 0
        for v in reversed(trust_recent.values):
            if v > 0:
                trust_consecutive += 1
            else:
                break

        if trust_consecutive >= 3:
            score += 5
            details.append(f"投信連續買超 {trust_consecutive} 天 +5")
        elif trust_consecutive >= 1:
            score += 2
            details.append("投信近期買超 +2")

    # 融資分析（逆向指標，融資減少是好事） (0-4分)
    if "margin_balance" in chip_df.columns:
        margin = chip_df["margin_balance"]
        if len(margin) >= 5:
            margin_change = (margin.iloc[-1] - margin.iloc[-5]) / (margin.iloc[-5] + 1e-9)
            if margin_change < -0.05:
                score += 4
                details.append("融資餘額下降（法人接手） +4")
            elif margin_change > 0.10:
                score -= 3
                details.append("融資大增（散戶追高）-3")

    # 三大法人合計 (0-3分)
    if "foreign_net" in chip_df.columns and "trust_net" in chip_df.columns:
        combined = chip_df["foreign_net"] + chip_df["trust_net"]
        if "dealer_net" in chip_df.columns:
            combined += chip_df["dealer_net"]
        if combined.tail(3).mean() > 0:
            score += 3
            details.append("三大法人合計近期淨買超 +3")

    score = max(0, min(20, score))
    return {"score": round(score, 1), "details": details}
