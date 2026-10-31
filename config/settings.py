"""Project-wide configuration defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MAX_RISK_RETRY = 2
MAX_POSITION_SIZE = 0.10
USE_MOCK_LLM = True
USE_REAL_MARKET_DATA = os.getenv("USE_REAL_MARKET_DATA", "false").lower() == "true"
MARKET_DATA_CACHE_TTL = 300
MARKET_DATA_MAX_RETRIES = 3
USE_REAL_FUNDAMENTAL_DATA = os.getenv(
    "USE_REAL_FUNDAMENTAL_DATA", "false"
).lower() == "true"
FUNDAMENTAL_DATA_CACHE_TTL = 86400
USE_REAL_NEWS_DATA = os.getenv("USE_REAL_NEWS_DATA", "false").lower() == "true"
NEWS_DATA_CACHE_TTL = 900
NEWS_DATA_LIMIT = 20
USE_REAL_ANALYST_LLM = os.getenv("USE_REAL_ANALYST_LLM", "false").lower() == "true"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
ANALYST_LLM_TEMPERATURE = 0.3
ANALYST_LLM_MAX_RETRIES = 2
ANALYST_LLM_TIMEOUT = 30.0
USE_REAL_DECISION_LLM = os.getenv("USE_REAL_DECISION_LLM", "false").lower() == "true"
DECISION_LLM_TEMPERATURE = 0.2
DECISION_LLM_MAX_RETRIES = 2
DECISION_LLM_TIMEOUT = 30.0
USE_PAPER_TRADING = os.getenv("USE_PAPER_TRADING", "false").lower() == "true"
USE_REAL_PORTFOLIO_STATE = os.getenv(
    "USE_REAL_PORTFOLIO_STATE", "false"
).lower() == "true"
