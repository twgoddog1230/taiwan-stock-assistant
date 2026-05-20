import math
from typing import Optional

def calculate_position(
    total_capital: float,
    stock_price: float,
    score: float,
    risk_level: str = "moderate",
    max_positions: int = 4,
) -> dict:
    """
    計算建議倉位大小與分批投入計畫

    Args:
        total_capital: 總可用資金（新台幣）
        stock_price: 當前股價
        score: 總評分（0-100）
        risk_level: 風險偏好 conservative/moderate/aggressive
        max_positions: 最多同時持有標的數
    """
    risk_pct = {"conservative": 0.15, "moderate": 0.20, "aggressive": 0.25}.get(risk_level, 0.20)

    # 依評分調整倉位比例
    if score >= 80:
        position_pct = risk_pct
    elif score >= 70:
        position_pct = risk_pct * 0.8
    else:
        position_pct = risk_pct * 0.6

    max_amount = total_capital * position_pct

    # 第一批：50% 現在進場
    first_batch_amount = max_amount * 0.5
    lot_size = 1000  # 1張 = 1000股
    lot_cost = stock_price * lot_size

    # 計算建議整張數
    lots = max(0, math.floor(first_batch_amount / lot_cost))
    # 若買不起整張，改用零股
    if lots == 0 and stock_price <= first_batch_amount:
        shares_odd = math.floor(first_batch_amount / stock_price)
        actual_amount = shares_odd * stock_price
        entry_type = "odd_lot"
    else:
        shares_odd = 0
        actual_amount = lots * lot_cost
        entry_type = "lot"

    stop_loss_price = round(stock_price * 0.95, 2)
    target1_price = round(stock_price * 1.065, 2)
    target2_price = round(stock_price * 1.12, 2)

    max_loss = actual_amount * 0.05  # 最大虧損（停損5%）

    second_batch_add_price = round(stock_price * 1.05, 2)  # 突破+5%加碼
    second_batch_dip_price = round(stock_price * 0.97, 2)  # 回測-3%補買

    second_batch_amount = max_amount * 0.35
    third_batch_amount = max_amount * 0.15

    return {
        "total_capital": total_capital,
        "max_position_amount": round(max_amount),
        "position_pct": round(position_pct * 100, 1),
        "first_batch": {
            "amount": round(actual_amount),
            "lots": lots if entry_type == "lot" else 0,
            "shares": shares_odd if entry_type == "odd_lot" else lots * 1000,
            "type": entry_type,
            "entry_price": stock_price,
        },
        "second_batch_add": {
            "trigger_price": second_batch_add_price,
            "condition": f"股價突破 {second_batch_add_price} 元且量能放大",
            "amount": round(second_batch_amount),
        },
        "second_batch_dip": {
            "trigger_price": second_batch_dip_price,
            "condition": f"回測 {second_batch_dip_price} 元且止跌回穩",
            "amount": round(second_batch_amount),
        },
        "stop_loss": {
            "price": stop_loss_price,
            "condition": f"跌破 {stop_loss_price} 元",
            "max_loss": round(max_loss),
        },
        "targets": {
            "target1": {"price": target1_price, "action": "建議出售50%（+6.5%）"},
            "target2": {"price": target2_price, "action": "建議全出（+12%）"},
        },
        "risk_reward_ratio": round(0.065 / 0.05, 1),
    }

def calculate_portfolio_summary(trades: list, total_capital: float) -> dict:
    """計算持倉組合摘要"""
    if not trades:
        return {"total_invested": 0, "unrealized_pnl": 0, "cash_available": total_capital}

    buy_trades = [t for t in trades if t.get("action") == "buy"]
    sell_trades = [t for t in trades if t.get("action") == "sell"]

    total_invested = sum(t.get("total_amount", 0) for t in buy_trades)
    total_sold = sum(t.get("total_amount", 0) for t in sell_trades)

    return {
        "total_invested": round(total_invested - total_sold),
        "cash_available": round(total_capital - total_invested + total_sold),
        "active_positions": len(set(t["symbol"] for t in buy_trades if t.get("symbol") not in
                                    [st["symbol"] for st in sell_trades])),
    }
