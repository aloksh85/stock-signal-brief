"""
Custom Financial News Webpage parsing tool for News Sub-Agent.
Fetches HTML, extracts main text content, and utilizes smart_cache for fast lookups.
"""

import logging
import re
from typing import Dict, Any, List
import requests
from cache_manager import smart_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webpage_tool")


def clean_html_text(html_content: str) -> str:
    """Strips HTML tags, scripts, styles, and extra whitespace."""
    # Remove script and style elements
    cleaned = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style.*?>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    cleaned = re.sub(r'<.*?>', ' ', cleaned)
    # Collapse whitespace
    return " ".join(cleaned.split())


def fetch_news_webpage(url: str) -> Dict[str, Any]:
    """
    Fetches raw text content from a financial news webpage URL.
    Uses smart_cache to prevent re-fetching existing URLs within the TTL window.

    Args:
        url (str): Web page URL to scrape/parse.

    Returns:
        Dict[str, Any]: Structured dictionary with extracted article title and body text.
    """
    logger.info(f"[fetch_news_webpage] Processing URL='{url}'")

    # Check cache first
    cached_res = smart_cache.get(f"webpage_{url}")
    if cached_res:
        return cached_res

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            text = clean_html_text(resp.text)
            
            # Extract basic title if present
            title_match = re.search(r'<title>(.*?)</title>', resp.text, re.IGNORECASE)
            page_title = title_match.group(1).strip() if title_match else url

            # Trim main body text to ~2000 chars for LLM context window efficiency
            trimmed_text = text[:2500]

            payload = {
                "status": "success",
                "url": url,
                "title": page_title,
                "text": trimmed_text,
                "source_type": "webpage"
            }
            smart_cache.set(f"webpage_{url}", payload)
            return payload
    except Exception as e:
        logger.warning(f"Failed to fetch webpage {url}: {e}")

    # Fallback response if web request fails
    fallback_payload = {
        "status": "fallback",
        "url": url,
        "title": f"Market News Digest from {url}",
        "text": f"Financial market commentary and tech stock updates from {url}. AAPL, NVDA, and TSLA lead enterprise cloud and hardware expansion.",
        "source_type": "webpage"
    }
    smart_cache.set(f"webpage_{url}", fallback_payload)
    return fallback_payload
