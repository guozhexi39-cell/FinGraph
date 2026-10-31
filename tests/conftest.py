"""Keep automated tests offline even when a developer has a real .env file."""

import os


for _setting in (
    "USE_REAL_MARKET_DATA",
    "USE_REAL_FUNDAMENTAL_DATA",
    "USE_REAL_NEWS_DATA",
    "USE_REAL_ANALYST_LLM",
    "USE_REAL_DECISION_LLM",
    "USE_REAL_PORTFOLIO_STATE",
    "USE_PAPER_TRADING",
):
    os.environ[_setting] = "false"
