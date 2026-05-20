import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 台股月份歷史統計勝率（基於歷史研究，正值代表通常偏多）
MONTHLY_BIAS = {
    1: 0.6,   # 元月效應，偏多
    2: 0.55,  # 農曆年後回補
    3: 0.5,   # 中性
    4: 0.55,  # 第一季財報公布前後
    5: 0.45,  # Sell in May，偏弱
    6: 0.45,  # 偏弱
    7: 0.5,   # 中性
    8: 0.45,  # 暑期淡季
    9: 0.45,  # 全球市場季節性弱勢
    10: 0.6,  # 第三季財報行情
    11: 0.6,  # 電子旺季尾聲 + 法說會
    12: 0.55, # 年底作帳行情
}

# 星期效應（週間效應）- 各交易日歷史勝率
WEEKDAY_BIAS = {
    0: 0.44,  # 週一：週末壞消息效應，偏弱
    1: 0.50,  # 週二：中性
    2: 0.54,  # 週三：月中偏強
    3: 0.55,  # 週四：本週最強
    4: 0.47,  # 週五：收盤避險賣壓
}

WEEKDAY_NAMES = {0: "週一", 1: "週二", 2: "週三", 3: "週四", 4: "週五"}

def score_seasonal(trade_date: Optional[date] = None) -> dict:
    """週期與季節效應評分（滿分20分）"""
    if trade_date is None:
        trade_date = date.today()

    score = 0.0
    details = []

    # 月份效應 (0-10分)
    month = trade_date.month
    monthly_win_rate = MONTHLY_BIAS.get(month, 0.5)
    monthly_score = (monthly_win_rate - 0.5) * 20  # -10 ~ +10
    monthly_score_normalized = max(0, min(10, 5 + monthly_score))
    score += monthly_score_normalized

    month_names = {1:"1月", 2:"2月", 3:"3月", 4:"4月", 5:"5月", 6:"6月",
                   7:"7月", 8:"8月", 9:"9月", 10:"10月", 11:"11月", 12:"12月"}
    month_notes = {
        1: "元月效應偏多",
        5: "五月賣出效應偏弱",
        9: "九月傳統弱勢月",
        10: "Q3財報行情",
        11: "電子旺季+法說會",
        12: "年底作帳行情",
    }
    note = month_notes.get(month, "")
    details.append(f"{month_names[month]}月勝率{monthly_win_rate:.0%} {note} +{monthly_score_normalized:.1f}")

    # 週間效應 (0-6分)
    weekday = trade_date.weekday()
    weekday_win_rate = WEEKDAY_BIAS.get(weekday, 0.5)
    weekday_score = (weekday_win_rate - 0.5) * 12
    weekday_score_normalized = max(0, min(6, 3 + weekday_score))
    score += weekday_score_normalized

    day_name = WEEKDAY_NAMES.get(weekday, "")
    details.append(f"{day_name}週間效應勝率{weekday_win_rate:.0%} +{weekday_score_normalized:.1f}")

    # 季報效應 (0-4分)
    quarter_effect = _get_quarter_effect(trade_date)
    score += quarter_effect["score"]
    if quarter_effect["detail"]:
        details.append(quarter_effect["detail"])

    score = max(0, min(20, score))
    return {"score": round(score, 1), "details": details, "month": month, "weekday": weekday}

def _get_quarter_effect(trade_date: date) -> dict:
    """季報前後效應"""
    month = trade_date.month
    day = trade_date.day

    # 季報公布月份（3月/5月/8月/11月）前後有效應
    report_months = {3: "Q4財報", 5: "Q1財報", 8: "Q2財報", 11: "Q3財報"}

    if month in report_months:
        if 10 <= day <= 20:
            return {"score": 4, "detail": f"{report_months[month]}公布期間+強勢效應 +4"}
        elif day > 20:
            return {"score": 2, "detail": f"{report_months[month]}公布後延伸 +2"}

    # 月底/月初資金調度效應
    if day <= 3 or day >= 28:
        return {"score": 1, "detail": "月底月初資金效應 +1"}

    return {"score": 0, "detail": ""}

def get_market_calendar_info(trade_date: Optional[date] = None) -> dict:
    """取得市場日曆資訊"""
    if trade_date is None:
        trade_date = date.today()

    month = trade_date.month
    weekday = trade_date.weekday()

    return {
        "month": month,
        "weekday": weekday,
        "weekday_name": WEEKDAY_NAMES.get(weekday, ""),
        "monthly_bias": MONTHLY_BIAS.get(month, 0.5),
        "weekday_bias": WEEKDAY_BIAS.get(weekday, 0.5),
        "is_strong_period": MONTHLY_BIAS.get(month, 0.5) >= 0.55 and WEEKDAY_BIAS.get(weekday, 0.5) >= 0.52,
    }
