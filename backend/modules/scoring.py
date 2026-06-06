import pandas as pd
from datetime import date
from typing import Optional
import logging
from modules.technical import score_technical
from modules.chip import score_chip
from modules.seasonal import score_seasonal
from modules.fundamental import score_fundamental
from modules.us_market import score_momentum, get_position_size_pct

logger = logging.getLogger(__name__)


def detect_sell_signals(price_df: pd.DataFrame) -> list[dict]:
    """
    偵測三種賣出警告訊號（P1）
    1. 技術面破位：收盤跌破 MA20
    2. 爆量出貨：量 > 5 倍均量 + 長上影線 + 收黑
    3. 追蹤停損：從近 20 日高點回落超過 8%
    """
    if price_df is None or len(price_df) < 2:
        return []

    signals = []
    latest = price_df.iloc[-1]

    close    = float(latest.get("close", 0) or 0)
    high     = float(latest.get("high", 0) or 0)
    open_p   = float(latest.get("open", 0) or 0)
    ma20     = latest.get("ma20")
    vol_ratio = float(latest.get("vol_ratio", 0) or 0)

    # ── 訊號 1：技術面破位（收盤跌破月線 MA20）─────────────────────────────
    if ma20 is not None and pd.notna(ma20) and close > 0:
        if close < float(ma20):
            signals.append({
                "type": "tech_breakdown",
                "severity": "high",
                "reason": (
                    f"⚠️ 收盤({close:.2f})跌破月線MA20({float(ma20):.2f})，"
                    "趨勢轉弱，建議停損出場"
                ),
            })

    # ── 訊號 2：爆量出貨（量 > 5 倍均量 + 上影線 > 實體 2 倍 + 收黑）────────
    if close > 0 and open_p > 0 and vol_ratio > 5:
        body         = abs(close - open_p)
        upper_shadow = high - max(close, open_p)
        if close < open_p and body > 0 and upper_shadow > body * 2:
            signals.append({
                "type": "blow_off_top",
                "severity": "high",
                "reason": (
                    f"🚨 爆量（{vol_ratio:.1f}倍均量）+長上影線+收黑，"
                    "疑似主力出貨，強烈建議賣出"
                ),
            })

    # ── 訊號 3：追蹤停損（從近 20 日收盤高點回落 > 8%）───────────────────
    if len(price_df) >= 20 and close > 0:
        recent_high = float(price_df["close"].tail(20).max())
        drawdown = (recent_high - close) / recent_high * 100
        if drawdown > 8:
            signals.append({
                "type": "trailing_stop",
                "severity": "medium",
                "reason": (
                    f"📉 從近20日高點({recent_high:.2f})回落 {drawdown:.1f}%，"
                    "超過8%追蹤停損線，建議考慮減碼"
                ),
            })

    return signals


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

    買進邏輯（P1 三 Gate AND 交集）：
      Gate B：費半 SOX 昨夜跌幅 < -2% → 降級，不發 strong_buy
      Gate C：技術面必須出現「帶量突破20日高點」或「5MA黃金交叉20MA」
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
        "sell_signals": [],
        "position_size_pct": 100,
    }

    # 1. 技術面（含突破旗標）
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

    # 5. 資金動能（美股 + TSM ADR）
    if us_data:
        momentum = score_momentum(us_data)
    else:
        momentum = {"score": 10, "details": ["美股資料不足，給予中性分"], "sox_chg": 0, "vix_val": 20}
    result["momentum"] = momentum

    total = (
        tech["score"] +
        chip["score"] +
        seasonal["score"] +
        fundamental["score"] +
        momentum["score"]
    )
    result["total_score"] = round(total, 1)

    # 綜合評分理由
    result["reasoning"] = (
        tech.get("details", []) +
        chip.get("details", []) +
        seasonal.get("details", []) +
        fundamental.get("details", []) +
        momentum.get("details", [])
    )

    # VIX 倉位建議（P2）
    vix_val = momentum.get("vix_val", 20)
    result["position_size_pct"] = get_position_size_pct(float(vix_val))

    # 賣出訊號偵測（P1）
    sell_sigs = detect_sell_signals(price_df)
    result["sell_signals"] = sell_sigs
    for sig in sell_sigs:
        result["reasoning"].append(sig["reason"])

    # 判斷信號與策略
    sox_chg = momentum.get("sox_chg", 0)
    result["signal"] = _determine_signal(total, tech, sox_chg)
    result["strategy"] = _suggest_strategy(result)

    # 計算進場價與風險點位（停損改為 -8% 追蹤停損基準）
    if len(price_df) > 0:
        latest_close = float(price_df["close"].iloc[-1])
        result["entry_price"] = round(latest_close, 2)
        result["stop_loss"]   = round(latest_close * 0.92, 2)   # -8% 追蹤停損
        result["target1"]     = round(latest_close * 1.065, 2)  # +6.5%
        result["target2"]     = round(latest_close * 1.12, 2)   # +12%

    return result


def _determine_signal(
    total: float,
    tech_result: dict,
    sox_chg: float,
) -> str:
    """
    三 Gate 買進邏輯（P1）：
      Gate B：SOX 跌幅 ≥ -2% 才允許 strong_buy（系統性風險過濾）
      Gate C：必須出現帶量突破 OR 5MA 金叉（技術觸發點）

    信號等級：
      strong_buy ： total ≥ 78 AND tech ≥ 12 AND Gate B AND Gate C
      buy         ： total ≥ 65 AND Gate B
      watch       ： total ≥ 50
      hold        ： total ≥ 35
      sell        ： total < 35
    """
    tech_score      = tech_result.get("score", 0) if isinstance(tech_result, dict) else float(tech_result)
    breakout        = tech_result.get("breakout", False) if isinstance(tech_result, dict) else False
    ma5_cross       = tech_result.get("ma5_golden_cross", False) if isinstance(tech_result, dict) else False

    gate_b = sox_chg > -2.0          # 費半跌幅不超過 -2%
    gate_c = breakout or ma5_cross   # 帶量突破 或 5MA金叉

    if total >= 78 and tech_score >= 12 and gate_b and gate_c:
        return "strong_buy"
    elif total >= 65 and gate_b:
        return "buy"
    elif total >= 50:
        return "watch"
    elif total < 35:
        return "sell"
    else:
        return "hold"


def _suggest_strategy(result: dict) -> list[str]:
    strategies = []
    total       = result["total_score"]
    tech_score  = result["technical"].get("score", 0)
    chip_score  = result["chip"].get("score", 0)
    seasonal    = result["seasonal"]
    weekday     = seasonal.get("weekday", 2)
    breakout    = result["technical"].get("breakout", False)

    # 當沖：技術強 + 週三/四 + 出現突破
    if tech_score >= 14 and weekday in [2, 3] and total >= 60 and breakout:
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
    """排序並挑選推薦股票（strong_buy 優先，次按總分）"""
    buy_signals = [s for s in scores if s["signal"] in ("strong_buy", "buy")]

    def sort_key(x):
        signal_weight = 1 if x["signal"] == "strong_buy" else 0
        return (signal_weight, x["total_score"])

    buy_signals.sort(key=sort_key, reverse=True)
    return buy_signals[:20]
