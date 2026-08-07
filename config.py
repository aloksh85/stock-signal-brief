"""
Configuration module for Stock Signal Brief autonomous loop.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Ensure output and logs directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Performance log file path
METRICS_LOG_PATH = LOGS_DIR / "performance_metrics.jsonl"

# Ollama local endpoint configuration
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")


# Default Financial RSS Feeds
DEFAULT_RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META&region=US&lang=en-US",
    "https://www.marketwatch.com/rss/topstories",
    "https://search.cnbc.com/rs/search/combinedradios/search.xml?partnerId=2000&keywords=stock%20market",
]

# Default YouTube Search Queries
DEFAULT_YOUTUBE_QUERIES = [
    "stock market news today analysis",
    "top tech stocks outlook NVDA AAPL TSLA",
]

# Known Ticker Universe for evaluation
KNOWN_TICKER_UNIVERSE = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "GOOG",
    "UNH", "JNJ", "JPM", "V", "XOM", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
    "LLY", "PEP", "KO", "BAC", "COST", "TMO", "AVGO", "WMT", "CSCO", "MCD",
    "AMD", "INTC", "NFLX", "CRM", "ORCL", "QCOM", "PLTR", "SMCI", "DIS", "NKE"
}
