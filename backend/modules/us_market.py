import yfinance as yf
import feedparser
import requests
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

def get_us_market_summary() -> dict:
    """取得美股市場摘要，用於盤前分析"""
    data = {}
    try:
        symbols = {"sp500": "^GSPC", "nasdaq": "^IXIC", "sox": "^SOX", "vix": "^VIX", "usd_twd": "TWD=X"}
        for key, sym in symbols.items():
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="3d")
                if len(hist) >= 2:
                    prev = float(hist["Close"].iloc[-2])
                    last = float(hist["Close"].iloc[-1])
                    pct = ((last - prev) / prev) * 100
                    data[key] = {"close": round(last, 2), "change_pct": round(pct, 2)}
                elif len(hist) == 1:
                    data[key] = {"close": round(float(hist["Close"].iloc[-1]), 2), "change_pct": 0.0}
            except Exception:
                data[key] = {"close": 0, "change_pct": 0}
    except Exception as e:
        logger.error(f"取得美股資料失敗: {e}")

    return data

def score_momentum(us_data: dict) -> dict:
    """資金動能面評分（滿分20分）—基於美股與大盤"""
    score = 0.0
    details = []

    # S&P 500 方向 (0-5分)
    sp500 = us_data.get("sp500", {})
    sp_chg = sp500.get("change_pct", 0)
    if sp_chg > 1.5:
        score += 5
        details.append(f"S&P500 大漲 {sp_chg:+.1f}% +5")
    elif sp_chg > 0.3:
        score += 3
        details.append(f"S&P500 上漲 {sp_chg:+.1f}% +3")
    elif sp_chg < -1.5:
        score -= 3
        details.append(f"S&P500 大跌 {sp_chg:+.1f}% -3")
    elif sp_chg < -0.3:
        score -= 1
        details.append(f"S&P500 下跌 {sp_chg:+.1f}% -1")
    else:
        score += 1
        details.append(f"S&P500 持平 {sp_chg:+.1f}% +1")

    # 費城半導體指數 SOX（台股科技股最重要指標）(0-7分)
    sox = us_data.get("sox", {})
    sox_chg = sox.get("change_pct", 0)
    if sox_chg > 2.0:
        score += 7
        details.append(f"費半大漲 {sox_chg:+.1f}%（利多台灣半導體）+7")
    elif sox_chg > 0.5:
        score += 4
        details.append(f"費半上漲 {sox_chg:+.1f}% +4")
    elif sox_chg < -2.0:
        score -= 4
        details.append(f"費半大跌 {sox_chg:+.1f}%（利空半導體）-4")
    elif sox_chg < -0.5:
        score -= 2
        details.append(f"費半下跌 {sox_chg:+.1f}% -2")
    else:
        score += 2
        details.append(f"費半持平 {sox_chg:+.1f}% +2")

    # VIX 恐慌指數 (0-5分)
    vix = us_data.get("vix", {})
    vix_val = vix.get("close", 20)
    if vix_val < 15:
        score += 5
        details.append(f"VIX {vix_val:.1f}（市場平靜，適合操作）+5")
    elif vix_val < 20:
        score += 3
        details.append(f"VIX {vix_val:.1f}（正常偏低）+3")
    elif vix_val < 25:
        score += 1
        details.append(f"VIX {vix_val:.1f}（微恐慌）+1")
    elif vix_val < 35:
        score -= 2
        details.append(f"VIX {vix_val:.1f}（市場恐慌）-2")
    else:
        score -= 4
        details.append(f"VIX {vix_val:.1f}（極度恐慌，謹慎操作）-4")

    # 美元/台幣匯率 (0-3分)
    usd_twd = us_data.get("usd_twd", {})
    twd_chg = usd_twd.get("change_pct", 0)
    if twd_chg < -0.3:
        score += 3
        details.append(f"台幣升值 {abs(twd_chg):.1f}%（外資匯入）+3")
    elif twd_chg > 0.5:
        score -= 1
        details.append(f"台幣貶值（外資匯出壓力）-1")
    else:
        score += 1
        details.append("匯率穩定 +1")

    score = max(0, min(20, score))
    return {"score": round(score, 1), "details": details}

def get_news_summary() -> list[dict]:
    """取得財經新聞摘要"""
    news = []
    feeds = [
        "https://www.cnyes.com/rss/cat/tw_stock",
        "https://tw.stock.yahoo.com/rss",
    ]
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                news.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:150],
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            logger.warning(f"取得新聞失敗: {e}")
    return news[:8]

def generate_pre_market_report(us_data: dict, news: list[dict]) -> str:
    """生成盤前摘要報告"""
    sp500 = us_data.get("sp500", {})
    nasdaq = us_data.get("nasdaq", {})
    sox = us_data.get("sox", {})
    vix = us_data.get("vix", {})
    usd_twd = us_data.get("usd_twd", {})

    sp_chg = sp500.get("change_pct", 0)
    sox_chg = sox.get("change_pct", 0)
    vix_val = vix.get("close", 20)

    # 研判市場方向
    if sp_chg > 1 and sox_chg > 1 and vix_val < 20:
        sentiment = "偏多，今日台股有望跟漲"
        strategy = "可積極布局，尤其半導體相關股"
    elif sp_chg > 0 and vix_val < 25:
        sentiment = "溫和偏多，台股應有支撐"
        strategy = "可正常布局，注意個股籌碼"
    elif sp_chg < -1.5 or vix_val > 28:
        sentiment = "偏空，台股面臨賣壓"
        strategy = "建議降低倉位，避免追高"
    else:
        sentiment = "中性偏觀望"
        strategy = "選擇性操作，以強勢個股為主"

    report = f"""【今日盤前摘要】
🇺🇸 美股收盤：S&P500 {sp_chg:+.1f}%｜NASDAQ {nasdaq.get('change_pct',0):+.1f}%｜費半 {sox_chg:+.1f}%
😰 恐慌指數：VIX {vix_val:.1f}
💵 美元/台幣：{usd_twd.get('close',32):.2f}（{usd_twd.get('change_pct',0):+.2f}%）

📊 市場研判：{sentiment}
🎯 今日策略：{strategy}"""

    if news:
        report += "\n\n📰 重要財經新聞："
        for n in news[:3]:
            report += f"\n• {n['title']}"

    return report
