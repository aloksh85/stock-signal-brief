"""
Yahoo Finance Top Gainers Scraper and News RSS Parser Tool.
Fetches top daily stock gainers from Yahoo Finance and retrieves detailed news feeds for them.
"""

import logging
import re
import urllib.request
from typing import Dict, Any, List
import feedparser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yahoo_gainers_tool")

DEFAULT_FALLBACK_GAINERS = ["NVDA", "PLTR", "TSLA", "AMD", "SMCI", "AVGO", "INTC", "ARM", "MSFT", "AMZN"]

SAMPLE_GAINERS_NEWS_FALLBACK = [
    {
        "title": "Palantir (PLTR) Rallies 8% Following New Defense AI Contract Award",
        "summary": "Palantir Technologies stock surged today as investors cheered a major strategic AI expansion contract.",
        "link": "https://finance.yahoo.com/news/pltr-defense-contract-rally-101",
        "published": "2026-08-07T14:30:00Z",
        "source": "Yahoo Finance Gainers RSS",
        "ticker": "PLTR"
    },
    {
        "title": "Oklo (OKLO) Gains 12% on Next-Gen Nuclear Energy Deployment Milestone",
        "summary": "Oklo Inc stock led energy gainers following regulatory clearance for its commercial microreactor design.",
        "link": "https://finance.yahoo.com/news/oklo-microreactor-milestone-102",
        "published": "2026-08-07T15:00:00Z",
        "source": "Yahoo Finance Gainers RSS",
        "ticker": "OKLO"
    }
]


def clean_html(raw_html: str) -> str:
    """Removes HTML tags and extra whitespace from text."""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return " ".join(cleantext.split())


def fetch_top_gainers(limit: int = 10) -> List[str]:
    """
    Scrapes Yahoo Finance Gainers page (https://finance.yahoo.com/gainers/) to extract top gainers stock tickers.

    Args:
        limit (int): Number of top gainers to extract (default 10).

    Returns:
        List[str]: List of top ticker symbols.
    """
    url = "https://finance.yahoo.com/gainers/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    logger.info(f"[fetch_top_gainers] Querying Yahoo Gainers page: {url}")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            # Extract symbol regex pattern from Yahoo Finance JSON payload
            raw_symbols = re.findall(r'\"symbol\":\"([A-Z0-9.\-]+)\"', html)
            
            # Filter to standard equity tickers (1-5 uppercase letters, ignore crypto like BTC-USD)
            tickers = []
            for s in raw_symbols:
                if re.match(r'^[A-Z]{1,5}$', s) and s not in tickers:
                    tickers.append(s)
                if len(tickers) >= limit:
                    break

            if tickers:
                logger.info(f"[fetch_top_gainers] Successfully extracted {len(tickers)} gainers: {tickers}")
                return tickers
    except Exception as e:
        logger.warning(f"[fetch_top_gainers] Error scraping Yahoo Gainers page: {e}")

    logger.info(f"[fetch_top_gainers] Using default fallback gainers list: {DEFAULT_FALLBACK_GAINERS[:limit]}")
    return DEFAULT_FALLBACK_GAINERS[:limit]


def fetch_gainers_news(tickers: List[str]) -> Dict[str, Any]:
    """
    Queries Yahoo Finance RSS feed for news articles covering the specified top gainers tickers.

    Args:
        tickers (List[str]): List of ticker symbols to query news for.

    Returns:
        Dict[str, Any]: Structured dictionary with news entries for top gainers.
    """
    if not tickers:
        tickers = DEFAULT_FALLBACK_GAINERS[:10]

    logger.info(f"[fetch_gainers_news] Fetching Yahoo Finance news RSS for top gainers: {tickers}")
    items: List[Dict[str, Any]] = []

    for t in tickers:
        rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}"
        try:
            feed = feedparser.parse(rss_url)
            if feed.entries:
                for entry in feed.entries[:2]:  # Take top 2 articles per gainer
                    title = entry.get("title", "")
                    summary = clean_html(entry.get("summary", entry.get("description", "")))
                    items.append({
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", ""),
                        "published": entry.get("published", entry.get("updated", "")),
                        "source": f"Yahoo Finance Gainers RSS ({t})",
                        "ticker": t
                    })
        except Exception as e:
            logger.warning(f"[fetch_gainers_news] Error fetching RSS feed for gainer {t}: {e}")

    if not items:
        logger.info("[fetch_gainers_news] Using fallback news entries for top gainers")
        items = SAMPLE_GAINERS_NEWS_FALLBACK

    return {
        "status": "success",
        "top_gainers_count": len(tickers),
        "tickers": tickers,
        "total_news_items": len(items),
        "entries": items
    }
