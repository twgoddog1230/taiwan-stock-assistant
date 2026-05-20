from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional, List
import json
import os
import logging

from database import get_db, init_db
from models import User, Stock, DailyAnalysis, MarketSummary, Watchlist, TradeRecord, PushSubscription
from auth import verify_password, get_password_hash, create_access_token, get_current_user
from modules.scheduler import create_scheduler
from modules.data_collector import get_historical_prices, get_us_market_data
from modules.technical import calculate_indicators
from modules.scoring import score_stock
from modules.backtest import run_backtest
from modules.money_mgmt import calculate_position, calculate_portfolio_summary
from modules.push import send_push

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="台股交易小幫手", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_state = {}

@app.on_event("startup")
async def startup():
    init_db()
    _seed_stocks()
    scheduler = create_scheduler(app_state)
    scheduler.start()
    app_state["scheduler"] = scheduler
    logger.info("台股交易小幫手啟動完成")

@app.on_event("shutdown")
async def shutdown():
    if "scheduler" in app_state:
        app_state["scheduler"].shutdown()

def _seed_stocks():
    """初始化股票清單（主要台股）"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(Stock).count() > 0:
            return
        major_stocks = [
            ("2330", "台積電", "TWSE"), ("2317", "鴻海", "TWSE"), ("2454", "聯發科", "TWSE"),
            ("2308", "台達電", "TWSE"), ("2382", "廣達", "TWSE"), ("2303", "聯電", "TWSE"),
            ("2412", "中華電", "TWSE"), ("2886", "兆豐金", "TWSE"), ("2891", "中信金", "TWSE"),
            ("2882", "國泰金", "TWSE"), ("2881", "富邦金", "TWSE"), ("1301", "台塑", "TWSE"),
            ("1303", "南亞", "TWSE"), ("2002", "中鋼", "TWSE"), ("3008", "大立光", "TWSE"),
            ("2395", "研華", "TWSE"), ("2357", "華碩", "TWSE"), ("2379", "瑞昱", "TWSE"),
            ("3034", "聯詠", "TWSE"), ("2327", "國巨", "TWSE"), ("2615", "萬海", "TWSE"),
            ("2603", "長榮", "TWSE"), ("2609", "陽明", "TWSE"), ("2376", "技嘉", "TWSE"),
            ("4938", "和碩", "TWSE"), ("3711", "日月光投控", "TWSE"), ("2408", "南亞科", "TWSE"),
            ("2337", "旺宏", "TWSE"), ("5347", "聯名電", "TWSE"), ("6505", "台塑化", "TWSE"),
        ]
        for sym, name, market in major_stocks:
            db.add(Stock(symbol=sym, name=name, market=market))
        db.commit()
        logger.info(f"初始化 {len(major_stocks)} 支主要股票")
    finally:
        db.close()

# ─── 認證 API ────────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
def register(email: str = Body(...), password: str = Body(...), display_name: str = Body(""), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="此 Email 已被使用")
    user = User(email=email, hashed_password=get_password_hash(password), display_name=display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "display_name": user.display_name}}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email 或密碼錯誤")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "total_capital": user.total_capital}}

@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "display_name": current_user.display_name, "total_capital": current_user.total_capital, "risk_level": current_user.risk_level}

@app.put("/api/auth/settings")
def update_settings(
    total_capital: Optional[float] = Body(None),
    risk_level: Optional[str] = Body(None),
    display_name: Optional[str] = Body(None),
    fugle_api_key: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if total_capital is not None:
        current_user.total_capital = total_capital
    if risk_level in ("conservative", "moderate", "aggressive"):
        current_user.risk_level = risk_level
    if display_name is not None:
        current_user.display_name = display_name
    if fugle_api_key is not None:
        current_user.fugle_api_key = fugle_api_key
    db.commit()
    return {"status": "ok"}

# ─── 市場摘要 API ────────────────────────────────────────────────────────────

@app.get("/api/market/today")
def get_today_market(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date.today()
    summary = db.query(MarketSummary).filter(MarketSummary.date == today).first()
    if not summary:
        # 即時取得
        us_data = get_us_market_data()
        return {
            "date": today.isoformat(),
            "us_market": us_data,
            "pre_market_report": "今日盤前報告尚未產生",
            "top_picks": [],
        }
    picks = json.loads(summary.top_picks) if summary.top_picks else []
    return {
        "date": today.isoformat(),
        "taiex_change_pct": summary.taiex_change_pct,
        "sp500_change_pct": summary.sp500_change_pct,
        "nasdaq_change_pct": summary.nasdaq_change_pct,
        "sox_change_pct": summary.sox_change_pct,
        "vix": summary.vix,
        "usd_twd": summary.usd_twd,
        "pre_market_report": summary.pre_market_report,
        "post_market_report": summary.post_market_report,
        "top_picks": picks[:10],
    }

@app.get("/api/market/picks")
def get_top_picks(trade_date: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_date = date.fromisoformat(trade_date) if trade_date else date.today()
    analyses = (
        db.query(DailyAnalysis)
        .filter(DailyAnalysis.date == target_date, DailyAnalysis.signal.in_(["strong_buy", "buy"]))
        .order_by(DailyAnalysis.total_score.desc())
        .limit(20)
        .all()
    )
    results = []
    for a in analyses:
        stock = db.query(Stock).filter(Stock.symbol == a.symbol).first()
        position = calculate_position(current_user.total_capital, a.entry_price or 100, a.total_score, current_user.risk_level)
        results.append({
            "symbol": a.symbol,
            "name": stock.name if stock else a.symbol,
            "score": a.total_score,
            "signal": a.signal,
            "strategy": a.strategy.split(",") if a.strategy else [],
            "entry_price": a.entry_price,
            "stop_loss": a.stop_loss,
            "target1": a.target1,
            "target2": a.target2,
            "reasoning": a.reasoning.split("\n")[:5] if a.reasoning else [],
            "position": position,
        })
    return results

# ─── 股票分析 API ────────────────────────────────────────────────────────────

@app.get("/api/stock/{symbol}/analysis")
def get_stock_analysis(symbol: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date.today()
    analysis = db.query(DailyAnalysis).filter(DailyAnalysis.symbol == symbol, DailyAnalysis.date == today).first()

    if not analysis:
        # 即時分析
        price_df = get_historical_prices(symbol, years=2)
        if price_df is None or price_df.empty:
            raise HTTPException(status_code=404, detail="找不到該股票資料")
        price_df = calculate_indicators(price_df)
        us_data = get_us_market_data()
        result = score_stock(symbol=symbol, price_df=price_df, us_data=us_data, trade_date=today)
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        result["name"] = stock.name if stock else symbol
        position = calculate_position(current_user.total_capital, result.get("entry_price", 100), result["total_score"], current_user.risk_level)
        result["position"] = position
        return result

    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    position = calculate_position(current_user.total_capital, analysis.entry_price or 100, analysis.total_score, current_user.risk_level)
    return {
        "symbol": symbol,
        "name": stock.name if stock else symbol,
        "score": analysis.total_score,
        "signal": analysis.signal,
        "strategy": analysis.strategy.split(",") if analysis.strategy else [],
        "entry_price": analysis.entry_price,
        "stop_loss": analysis.stop_loss,
        "target1": analysis.target1,
        "target2": analysis.target2,
        "reasoning": analysis.reasoning.split("\n") if analysis.reasoning else [],
        "position": position,
    }

@app.get("/api/stock/{symbol}/backtest")
def get_backtest(symbol: str, years: int = 5, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    price_df = get_historical_prices(symbol, years=max(years, 5))
    if price_df is None or price_df.empty:
        raise HTTPException(status_code=404, detail="找不到歷史數據")
    result = run_backtest(price_df, years=years)
    return result

@app.get("/api/stock/{symbol}/prices")
def get_prices(symbol: str, days: int = 180, current_user: User = Depends(get_current_user)):
    price_df = get_historical_prices(symbol, years=1)
    if price_df is None or price_df.empty:
        raise HTTPException(status_code=404, detail="找不到股價資料")
    price_df = price_df.tail(days)
    price_df = calculate_indicators(price_df)
    return price_df[["date", "open", "high", "low", "close", "volume", "ma5", "ma20", "ma60", "rsi", "macd"]].fillna(0).to_dict(orient="records")

# ─── 自選股 API ──────────────────────────────────────────────────────────────

@app.get("/api/watchlist")
def get_watchlist(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    result = []
    for w in items:
        stock = db.query(Stock).filter(Stock.symbol == w.symbol).first()
        analysis = db.query(DailyAnalysis).filter(DailyAnalysis.symbol == w.symbol, DailyAnalysis.date == date.today()).first()
        result.append({
            "id": w.id,
            "symbol": w.symbol,
            "name": stock.name if stock else w.symbol,
            "note": w.note,
            "score": analysis.total_score if analysis else None,
            "signal": analysis.signal if analysis else None,
        })
    return result

@app.post("/api/watchlist")
def add_watchlist(symbol: str = Body(...), note: str = Body(""), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Watchlist).filter(Watchlist.user_id == current_user.id, Watchlist.symbol == symbol).first()
    if existing:
        return {"status": "already_exists"}
    db.add(Watchlist(user_id=current_user.id, symbol=symbol, note=note))
    db.commit()
    return {"status": "added"}

@app.delete("/api/watchlist/{symbol}")
def remove_watchlist(symbol: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Watchlist).filter(Watchlist.user_id == current_user.id, Watchlist.symbol == symbol).delete()
    db.commit()
    return {"status": "removed"}

# ─── 交易紀錄 API ────────────────────────────────────────────────────────────

@app.get("/api/trades")
def get_trades(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trades = db.query(TradeRecord).filter(TradeRecord.user_id == current_user.id).order_by(TradeRecord.trade_date.desc()).limit(100).all()
    return [{"id": t.id, "symbol": t.symbol, "name": t.stock_name, "action": t.action, "shares": t.shares,
             "price": t.price, "total_amount": t.total_amount, "strategy": t.strategy,
             "note": t.note, "trade_date": t.trade_date.isoformat()} for t in trades]

@app.post("/api/trades")
def add_trade(
    symbol: str = Body(...),
    action: str = Body(...),
    shares: int = Body(...),
    price: float = Body(...),
    strategy: str = Body(""),
    note: str = Body(""),
    trade_date: str = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    td = date.fromisoformat(trade_date) if trade_date else date.today()
    record = TradeRecord(
        user_id=current_user.id,
        symbol=symbol,
        stock_name=stock.name if stock else symbol,
        action=action,
        shares=shares,
        price=price,
        total_amount=shares * price,
        strategy=strategy,
        note=note,
        trade_date=td,
    )
    db.add(record)
    db.commit()
    return {"status": "ok", "id": record.id}

@app.get("/api/trades/stats")
def get_trade_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trades = db.query(TradeRecord).filter(TradeRecord.user_id == current_user.id).all()
    trade_dicts = [{"symbol": t.symbol, "action": t.action, "total_amount": t.total_amount, "price": t.price, "shares": t.shares} for t in trades]
    summary = calculate_portfolio_summary(trade_dicts, current_user.total_capital)
    return summary

# ─── 推播訂閱 API ────────────────────────────────────────────────────────────

@app.post("/api/push/subscribe")
def subscribe_push(
    endpoint: str = Body(...),
    p256dh: str = Body(...),
    auth: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if not existing:
        db.add(PushSubscription(user_id=current_user.id, endpoint=endpoint, p256dh=p256dh, auth=auth))
        db.commit()
    return {"status": "subscribed"}

@app.get("/api/push/vapid-public-key")
def get_vapid_public_key():
    from config import VAPID_PUBLIC_KEY
    return {"public_key": VAPID_PUBLIC_KEY}

# ─── 手動觸發分析（測試用）──────────────────────────────────────────────────

@app.post("/api/admin/run-analysis")
def trigger_analysis(current_user: User = Depends(get_current_user)):
    from modules.scheduler import run_post_market_analysis
    import threading
    thread = threading.Thread(target=run_post_market_analysis, args=(app_state,))
    thread.daemon = True
    thread.start()
    return {"status": "started", "message": "分析已在背景執行，約需10-30分鐘"}

@app.post("/api/admin/run-pre-market")
def trigger_pre_market(current_user: User = Depends(get_current_user)):
    from modules.scheduler import run_pre_market_analysis
    import threading
    thread = threading.Thread(target=run_pre_market_analysis, args=(app_state,))
    thread.daemon = True
    thread.start()
    return {"status": "started", "message": "盤前分析已在背景執行"}

# ─── 搜尋股票 ─────────────────────────────────────────────────────────────────

@app.get("/api/stocks/search")
def search_stocks(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stocks = db.query(Stock).filter(
        (Stock.symbol.contains(q)) | (Stock.name.contains(q))
    ).limit(10).all()
    return [{"symbol": s.symbol, "name": s.name, "market": s.market} for s in stocks]

# ─── 前端靜態檔案服務 ────────────────────────────────────────────────────────

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        index_file = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend not built"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
