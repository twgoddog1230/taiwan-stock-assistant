import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/taiwan_stock")
SECRET_KEY = os.getenv("SECRET_KEY", "changeme-in-production-use-random-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "admin@example.com")

MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 13
MARKET_CLOSE_MINUTE = 30
PRE_MARKET_NOTIFY_HOUR = 8
PRE_MARKET_NOTIFY_MINUTE = 0
POST_MARKET_ANALYSIS_HOUR = 15
POST_MARKET_ANALYSIS_MINUTE = 30
