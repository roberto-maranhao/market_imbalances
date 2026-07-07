import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/market_imbalances.db")

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "8000"))
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me")

BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")
EODHD_API_KEY = os.environ.get("EODHD_API_KEY")

OPEN_EXCHANGE_RATES_APP_ID = os.environ.get("OPEN_EXCHANGE_RATES_APP_ID")

FRED_API_KEY = os.environ.get("FRED_API_KEY")
