import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/market_imbalances.db")

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "8000"))
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me")

BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")

FRED_API_KEY = os.environ.get("FRED_API_KEY")
