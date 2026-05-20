import logging
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)
TAIPEI_TZ = pytz.timezone("Asia/Taipei")

def run_pre_market_analysis(app_state: dict):
    """每日 08:00 盤前分析（美股 + 新聞）"""
    logger.info("開始執行盤前分析...")
    try:
        from database import SessionLocal
        from models import MarketSummary
        from modules.us_market import get_us_market_summary, get_news_summary, generate_pre_market_report, score_momentum
        import json

        db = SessionLocal()
        today = date.today()

        us_data = get_us_market_summary()
        news = get_news_summary()
        report = generate_pre_market_report(us_data, news)
        momentum = score_momentum(us_data)

        existing = db.query(MarketSummary).filter(MarketSummary.date == today).first()
        if existing:
            existing.pre_market_report = report
            existing.sp500_change_pct = us_data.get("sp500", {}).get("change_pct", 0)
            existing.nasdaq_change_pct = us_data.get("nasdaq", {}).get("change_pct", 0)
            existing.sox_change_pct = us_data.get("sox", {}).get("change_pct", 0)
            existing.vix = us_data.get("vix", {}).get("close", 0)
            existing.usd_twd = us_data.get("usd_twd", {}).get("close", 0)
        else:
            summary = MarketSummary(
                date=today,
                sp500_change_pct=us_data.get("sp500", {}).get("change_pct", 0),
                nasdaq_change_pct=us_data.get("nasdaq", {}).get("change_pct", 0),
                sox_change_pct=us_data.get("sox", {}).get("change_pct", 0),
                vix=us_data.get("vix", {}).get("close", 0),
                usd_twd=us_data.get("usd_twd", {}).get("close", 0),
                pre_market_report=report,
            )
            db.add(summary)
        db.commit()

        # 發送推播
        from modules.push import send_daily_pre_market
        sent = send_daily_pre_market(db, report, [])
        logger.info(f"盤前分析完成，推播 {sent} 位用戶")
        db.close()
    except Exception as e:
        logger.error(f"盤前分析失敗: {e}")

def run_post_market_analysis(app_state: dict):
    """每日 15:30 盤後分析（全市場評分）"""
    logger.info("開始執行盤後分析...")
    try:
        from database import SessionLocal
        from models import Stock, DailyAnalysis, MarketSummary
        from modules.data_collector import get_historical_prices, get_three_major_investors, get_us_market_summary
        from modules.technical import calculate_indicators
        from modules.scoring import score_stock, rank_stocks
        import json

        db = SessionLocal()
        today = date.today()
        us_data = get_us_market_summary()

        stocks = db.query(Stock).filter(Stock.is_active == True).limit(200).all()
        all_scores = []

        for stock in stocks:
            try:
                price_df = get_historical_prices(stock.symbol, years=1)
                if price_df is None or len(price_df) < 30:
                    continue
                price_df = calculate_indicators(price_df)
                result = score_stock(
                    symbol=stock.symbol,
                    price_df=price_df,
                    us_data=us_data,
                    trade_date=today,
                )
                all_scores.append({**result, "name": stock.name})

                analysis = DailyAnalysis(
                    symbol=stock.symbol,
                    date=today,
                    total_score=result["total_score"],
                    chip_score=result["chip"]["score"],
                    technical_score=result["technical"]["score"],
                    seasonal_score=result["seasonal"]["score"],
                    fundamental_score=result["fundamental"]["score"],
                    momentum_score=result["momentum"]["score"],
                    signal=result["signal"],
                    strategy=",".join(result["strategy"]),
                    reasoning="\n".join(result["reasoning"]),
                    entry_price=result.get("entry_price"),
                    stop_loss=result.get("stop_loss"),
                    target1=result.get("target1"),
                    target2=result.get("target2"),
                )
                db.merge(analysis)
            except Exception as e:
                logger.warning(f"{stock.symbol} 分析失敗: {e}")
                continue

        top_picks = rank_stocks(all_scores)[:10]

        summary = db.query(MarketSummary).filter(MarketSummary.date == today).first()
        if summary:
            summary.top_picks = json.dumps(top_picks, ensure_ascii=False, default=str)
            summary.post_market_report = f"今日完成 {len(all_scores)} 支股票分析，{len(top_picks)} 支入選推薦清單"
        db.commit()

        from modules.push import send_daily_post_market
        sent = send_daily_post_market(db, top_picks)
        logger.info(f"盤後分析完成，分析 {len(all_scores)} 支，推薦 {len(top_picks)} 支，推播 {sent} 位用戶")
        db.close()
    except Exception as e:
        logger.error(f"盤後分析失敗: {e}")

def create_scheduler(app_state: dict) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TAIPEI_TZ)

    # 每日 08:00 盤前分析
    scheduler.add_job(
        lambda: run_pre_market_analysis(app_state),
        CronTrigger(hour=8, minute=0, timezone=TAIPEI_TZ),
        id="pre_market",
        replace_existing=True,
    )

    # 每日 15:30 盤後分析
    scheduler.add_job(
        lambda: run_post_market_analysis(app_state),
        CronTrigger(hour=15, minute=30, timezone=TAIPEI_TZ),
        id="post_market",
        replace_existing=True,
    )

    return scheduler
