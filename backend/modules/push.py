import json
import logging
from typing import Optional
from pywebpush import webpush, WebPushException
from config import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_CLAIMS_EMAIL

logger = logging.getLogger(__name__)

def send_push(subscription: dict, title: str, body: str, url: str = "/", icon: str = "/icons/icon-192.png") -> bool:
    """發送 Web Push 通知"""
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        logger.warning("VAPID 金鑰未設定，跳過推播")
        return False

    try:
        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url,
            "icon": icon,
        })
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"},
        )
        return True
    except WebPushException as e:
        logger.error(f"推播失敗: {e}")
        return False
    except Exception as e:
        logger.error(f"推播異常: {e}")
        return False

def send_daily_pre_market(db, report: str, top_picks: list) -> int:
    """發送每日盤前通知給所有用戶"""
    from models import PushSubscription, User
    count = 0
    subscriptions = db.query(PushSubscription).all()
    title = "📊 今日盤前分析已出爐"
    body = report[:100] + "..." if len(report) > 100 else report

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        if send_push(subscription_info, title, body, "/"):
            count += 1
    return count

def send_daily_post_market(db, top_picks: list) -> int:
    """發送每日收盤後推薦通知"""
    from models import PushSubscription
    count = 0
    subscriptions = db.query(PushSubscription).all()

    if top_picks:
        names = "、".join([p.get("name", p.get("symbol", "")) for p in top_picks[:3]])
        title = "🎯 今日收盤分析完成"
        body = f"明日重點觀察：{names}，共 {len(top_picks)} 檔入選"
    else:
        title = "📉 今日收盤分析完成"
        body = "今日無強力推薦標的，建議觀望"

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        if send_push(subscription_info, title, body, "/"):
            count += 1
    return count

def send_price_alert(db, user_id: int, symbol: str, name: str, alert_type: str, price: float) -> bool:
    """發送個股價格警示"""
    from models import PushSubscription
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()

    type_text = {
        "stop_loss": "⚠️ 停損提醒",
        "target1": "✅ 第一目標達到",
        "target2": "🎉 第二目標達到",
        "add_on_breakout": "📈 加碼時機",
        "add_on_dip": "💡 補買時機",
    }

    title = type_text.get(alert_type, "📢 價格提醒")
    body = f"{name}（{symbol}）目前價格 {price:.2f} 元"

    for sub in subs:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        send_push(subscription_info, title, body, f"/stock/{symbol}")

    return len(subs) > 0
