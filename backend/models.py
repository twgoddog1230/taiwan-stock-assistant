from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Date, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, default="")
    total_capital = Column(Float, default=100000)
    risk_level = Column(String, default="moderate")  # conservative / moderate / aggressive
    fugle_api_key = Column(String, default="")
    fugle_api_secret = Column(String, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    push_subscriptions = relationship("PushSubscription", back_populates="user")
    watchlist = relationship("Watchlist", back_populates="user")
    trades = relationship("TradeRecord", back_populates="user")

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="push_subscriptions")

class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    market = Column(String, default="TWSE")  # TWSE / TPEX
    industry = Column(String, default="")
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class DailyPrice(Base):
    __tablename__ = "daily_prices"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    change_pct = Column(Float)

class ChipData(Base):
    __tablename__ = "chip_data"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    foreign_buy = Column(Float, default=0)
    foreign_sell = Column(Float, default=0)
    foreign_net = Column(Float, default=0)
    trust_buy = Column(Float, default=0)
    trust_sell = Column(Float, default=0)
    trust_net = Column(Float, default=0)
    dealer_net = Column(Float, default=0)
    margin_balance = Column(Float, default=0)
    short_balance = Column(Float, default=0)

class DailyAnalysis(Base):
    __tablename__ = "daily_analyses"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    total_score = Column(Float, default=0)
    chip_score = Column(Float, default=0)
    technical_score = Column(Float, default=0)
    seasonal_score = Column(Float, default=0)
    fundamental_score = Column(Float, default=0)
    momentum_score = Column(Float, default=0)
    strategy = Column(String, default="")  # day_trade / short / swing
    signal = Column(String, default="")    # buy / sell / hold / watch
    reasoning = Column(Text, default="")
    entry_price = Column(Float)
    stop_loss = Column(Float)
    target1 = Column(Float)
    target2 = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    note = Column(String, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="watchlist")

class TradeRecord(Base):
    __tablename__ = "trade_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    stock_name = Column(String, default="")
    action = Column(String, nullable=False)  # buy / sell
    shares = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    strategy = Column(String, default="")
    note = Column(String, default="")
    trade_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="trades")

class MarketSummary(Base):
    __tablename__ = "market_summaries"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    taiex_close = Column(Float)
    taiex_change_pct = Column(Float)
    sp500_change_pct = Column(Float)
    nasdaq_change_pct = Column(Float)
    sox_change_pct = Column(Float)
    vix = Column(Float)
    usd_twd = Column(Float)
    foreign_net_buy = Column(Float)
    market_sentiment = Column(String, default="neutral")  # bullish / bearish / neutral
    pre_market_report = Column(Text, default="")
    post_market_report = Column(Text, default="")
    top_picks = Column(Text, default="")  # JSON string of top picks
    created_at = Column(DateTime(timezone=True), server_default=func.now())
