import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def score_fundamental(info: dict) -> dict:
    """基本面評分（滿分20分）"""
    if not info:
        return {"score": 5, "details": ["無基本面資料，給予基礎分數"]}

    score = 0.0
    details = []

    # 本益比 P/E (0-6分)
    pe = info.get("pe_ratio")
    if pe and pe > 0:
        if 8 <= pe <= 15:
            score += 6
            details.append(f"P/E {pe:.1f}（低估值）+6")
        elif 15 < pe <= 25:
            score += 4
            details.append(f"P/E {pe:.1f}（合理）+4")
        elif 25 < pe <= 40:
            score += 2
            details.append(f"P/E {pe:.1f}（偏高）+2")
        else:
            details.append(f"P/E {pe:.1f}（高估）+0")
    else:
        score += 3  # 無資料給予中性分
        details.append("P/E 無資料，中性 +3")

    # 股東權益報酬率 ROE (0-6分)
    roe = info.get("roe")
    if roe:
        roe_pct = roe * 100 if roe < 1 else roe
        if roe_pct >= 20:
            score += 6
            details.append(f"ROE {roe_pct:.1f}%（優質）+6")
        elif roe_pct >= 15:
            score += 4
            details.append(f"ROE {roe_pct:.1f}%（良好）+4")
        elif roe_pct >= 10:
            score += 2
            details.append(f"ROE {roe_pct:.1f}%（普通）+2")
        else:
            details.append(f"ROE {roe_pct:.1f}%（偏低）+0")
    else:
        score += 3
        details.append("ROE 無資料，中性 +3")

    # 營收成長率 (0-5分)
    rev_growth = info.get("revenue_growth")
    if rev_growth:
        rev_pct = rev_growth * 100 if rev_growth < 1 else rev_growth
        if rev_pct >= 20:
            score += 5
            details.append(f"營收年增率 +{rev_pct:.1f}%（高成長）+5")
        elif rev_pct >= 10:
            score += 3
            details.append(f"營收年增率 +{rev_pct:.1f}%（穩健成長）+3")
        elif rev_pct >= 0:
            score += 1
            details.append(f"營收年增率 +{rev_pct:.1f}%（微幅成長）+1")
        else:
            details.append(f"營收年增率 {rev_pct:.1f}%（衰退）+0")
    else:
        score += 2
        details.append("營收成長率無資料 +2")

    # 股價淨值比 P/B (0-3分)
    pb = info.get("pb_ratio")
    if pb and pb > 0:
        if pb <= 1.5:
            score += 3
            details.append(f"P/B {pb:.1f}（低）+3")
        elif pb <= 3:
            score += 2
            details.append(f"P/B {pb:.1f}（合理）+2")
        elif pb <= 5:
            score += 1
            details.append(f"P/B {pb:.1f}（偏高）+1")
    else:
        score += 1
        details.append("P/B 無資料 +1")

    score = max(0, min(20, score))
    return {"score": round(score, 1), "details": details}
