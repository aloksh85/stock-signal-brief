"""
Reasoning Engine: Local Ollama API client with heuristic NLP fallback strategy.
Extracts tickers, sentiment, and key themes into validated Pydantic models.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
import requests
from config import OLLAMA_ENDPOINT, OLLAMA_MODEL, KNOWN_TICKER_UNIVERSE
from schemas import StockAnalysisItem, StockAnalysisOutput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyzer")

COMPANY_NAME_MAP = {
    "NVDA": "NVIDIA Corporation",
    "AAPL": "Apple Inc.",
    "TSLA": "Tesla, Inc.",
    "MSFT": "Microsoft Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "GOOG": "Alphabet Inc.",
    "META": "Meta Platforms, Inc.",
    "AMD": "Advanced Micro Devices, Inc.",
    "INTC": "Intel Corporation",
    "PLTR": "Palantir Technologies Inc.",
    "SMCI": "Super Micro Computer, Inc."
}

BULLISH_KEYWORDS = ["surge", "surged", "outperform", "upgraded", "highs", "demand", "strong", "growth", "bullish", "jumped", "expand", "record"]
BEARISH_KEYWORDS = ["cuts", "cut", "down", "pressure", "bearish", "loss", "decline", "fall", "warns", "drop", "dropped", "slump"]


class StockAnalyzer:
    """Handles LLM analysis via local Ollama or heuristic rule fallback."""

    def __init__(self, ollama_endpoint: str = OLLAMA_ENDPOINT, model: str = OLLAMA_MODEL):
        self.endpoint = ollama_endpoint
        self.model = model

    def check_ollama_available(self, timeout: float = 2.0) -> bool:
        """
        Preflight health check for Ollama API endpoint.
        Returns True if Ollama service is reachable, False otherwise.
        """
        tags_url = self.endpoint.rsplit("/", 1)[0] + "/tags"
        try:
            resp = requests.get(tags_url, timeout=timeout)
            if resp.status_code == 200:
                logger.info(f"[StockAnalyzer] Ollama preflight check PASSED: Reachable at {tags_url}")
                return True
        except Exception as e:
            logger.warning(f"[StockAnalyzer] Ollama preflight check FAILED at {tags_url}: {e}")

        return False

    def require_ollama_available(self, timeout: float = 2.0):
        """
        Enforces Ollama preflight check. Raises RuntimeError and halts execution if Ollama is not available.
        """
        if not self.check_ollama_available(timeout=timeout):
            err_msg = (
                f"Ollama Preflight Check Failed! Service is not reachable at '{self.endpoint}'. "
                "Execution halted. Please start Ollama server (`ollama serve`) before running."
            )
            logger.error(f"[StockAnalyzer] {err_msg}")
            raise RuntimeError(err_msg)

    def analyze_texts(self, text_items: List[Dict[str, Any]]) -> StockAnalysisOutput:
        """
        Analyzes a list of ingested text items (from YouTube and RSS) and extracts structured stock insights.

        Args:
            text_items (List[Dict[str, Any]]): Ingested items containing 'text', 'title', 'source_type', 'source_name'.

        Returns:
            StockAnalysisOutput: Validated Pydantic schema containing analysis items.
        """
        logger.info(f"[StockAnalyzer] Analyzing {len(text_items)} text items...")
        
        # Try Ollama endpoint first
        ollama_result = self._try_ollama_analysis(text_items)
        if ollama_result:
            return ollama_result

        # Fallback to heuristic NLP extraction
        logger.info("[StockAnalyzer] Ollama endpoint unavailable or failed. Executing Fallback NLP Extraction.")
        return self._heuristic_analysis(text_items)

    def _try_ollama_analysis(self, text_items: List[Dict[str, Any]]) -> Optional[StockAnalysisOutput]:
        """Attempts structured prompt extraction via local Ollama API."""
        prompt = (
            "You are a senior financial stock analyst. Analyze ALL of the following ingested news and transcript texts. "
            "Identify ALL unique stock ticker symbols mentioned or referenced across the texts (especially top gainers like PLTR, OKLO, WWR, NVDA, QS, RKLB, YJ, SOAR, ABCL, USAR, etc.). "
            "For EVERY ticker found, extract company_name, sentiment (BULLISH, BEARISH, or NEUTRAL), confidence_score (0.0 to 1.0), key_themes, recommendation ('BUY' if BULLISH with high confidence >= 0.75 else 'WAIT'), source_type, concise 1-sentence source_summary, and relevant_news (an array of all news headlines or transcript snippets relevant to this ticker).\n"
            "You MUST return a JSON object containing entries for EVERY distinct ticker identified across the texts. Do not truncate the items list.\n\n"
            "Respond ONLY with a JSON object matching this schema:\n"
            "{\n"
            '  "items": [\n'
            '    {"ticker": "PLTR", "company_name": "Palantir Technologies", "sentiment": "BULLISH", "confidence_score": 0.95, "key_themes": ["Defense AI"], "recommendation": "BUY", "relevant_news": ["Palantir stock rallied on strategic AI contract", "[Bullish Investor] PLTR breakout surge"], "source_type": "yahoo_gainers", "source_summary": "Palantir stock rallied on strategic AI contract"},\n'
            '    {"ticker": "OKLO", "company_name": "Oklo Inc.", "sentiment": "BULLISH", "confidence_score": 0.92, "key_themes": ["Nuclear Energy"], "recommendation": "BUY", "relevant_news": ["Oklo reported Q2 criticality milestone and earnings progress"], "source_type": "yahoo_gainers", "source_summary": "Oklo reported Q2 criticality milestone and earnings progress"}\n'
            "  ],\n"
            '  "total_tickers": 2,\n'
            '  "overall_market_mood": "BULLISH",\n'
            f'  "processed_sources_count": {len(text_items)}\n'
            "}\n\n"
            f"Texts to analyze:\n{json.dumps(text_items, indent=2)}"
        )

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            logger.info(f"[StockAnalyzer] Sending request to Ollama endpoint '{self.endpoint}' with model '{self.model}' ({len(text_items)} text items)...")
            resp = requests.post(self.endpoint, json=payload, timeout=60)
            if resp.status_code == 200:
                raw_json = resp.json().get("response", "")
                parsed_data = json.loads(raw_json)
                parsed_data["analysis_engine"] = f"Ollama LLM ({self.model})"
                output = StockAnalysisOutput.model_validate(parsed_data)
                logger.info(f"[StockAnalyzer] Ollama analysis succeeded: Extracted {output.total_tickers} tickers!")
                return output
            else:
                logger.warning(f"[StockAnalyzer] Ollama API returned non-200 status code: {resp.status_code}")
        except Exception as e:
            logger.warning(f"[StockAnalyzer] Ollama generation request failed or timed out: {e}")

        return None

    def _heuristic_analysis(self, text_items: List[Dict[str, Any]]) -> StockAnalysisOutput:
        """Fallback NLP rule engine that extracts tickers, calculates sentiment, and outputs Pydantic model."""
        analyzed_items: List[StockAnalysisItem] = []
        seen_tickers = set()

        for item in text_items:
            content = f"{item.get('title', '')} {item.get('text', '')} {item.get('summary', '')}"
            source_type = item.get("source_type", "rss")
            
            # Identify matched tickers
            matched_tickers = set()
            item_ticker = item.get("ticker")
            if item_ticker and item_ticker != "TOP_GAINER":
                matched_tickers.add(item_ticker)

            words = set(re.findall(r'\b[A-Z]{2,5}\b', content))
            matched_tickers.update(words.intersection(KNOWN_TICKER_UNIVERSE))

            for ticker in matched_tickers:
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)

                # Determine sentiment score based on keyword counts
                content_lower = content.lower()
                bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw in content_lower)
                bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw in content_lower)

                if bullish_count > bearish_count:
                    sentiment = "BULLISH"
                    conf = min(0.70 + (bullish_count * 0.08), 0.98)
                elif bearish_count > bullish_count:
                    sentiment = "BEARISH"
                    conf = min(0.70 + (bearish_count * 0.08), 0.95)
                else:
                    sentiment = "NEUTRAL"
                    conf = 0.65

                # Recommendation calculation
                recommendation = "BUY" if (sentiment == "BULLISH" and conf >= 0.75) else "WAIT"

                # Collect all relevant news snippets for this ticker
                relevant_snippets = []
                for news_item in text_items:
                    news_text = f"{news_item.get('title', '')} {news_item.get('summary', '')} {news_item.get('text', '')}"
                    if ticker in news_text or news_item.get("ticker") == ticker:
                        headline = news_item.get("title") or news_item.get("summary") or news_text[:120]
                        if headline and headline not in relevant_snippets:
                            relevant_snippets.append(headline)

                if not relevant_snippets:
                    relevant_snippets.append(item.get("title") or item.get("text", "")[:120])

                # Extract key themes
                themes = []
                if any(k in content_lower for k in ["ai", "chip", "datacenter", "cloud"]):
                    themes.append("Artificial Intelligence & Tech Infrastructure")
                if any(k in content_lower for k in ["fed", "rate", "inflation", "cut"]):
                    themes.append("Monetary Policy & Interest Rates")
                if any(k in content_lower for k in ["earnings", "revenue", "quarter"]):
                    themes.append("Quarterly Earnings Performance")
                if any(k in content_lower for k in ["ev", "car", "margin", "competition"]):
                    themes.append("EV Market Dynamics")
                if not themes:
                    themes.append("Market Sentiment & Trading Volume")

                comp_name = COMPANY_NAME_MAP.get(ticker, f"{ticker} Inc.")
                summary_snippet = item.get("title") or item.get("text", "")[:120]

                analyzed_items.append(StockAnalysisItem(
                    ticker=ticker,
                    company_name=comp_name,
                    sentiment=sentiment,
                    confidence_score=round(conf, 2),
                    key_themes=themes,
                    recommendation=recommendation,
                    relevant_news=relevant_snippets[:5],
                    source_type=source_type if source_type in ["youtube", "rss", "hybrid", "yahoo_gainers"] else "rss",
                    source_summary=summary_snippet
                ))

        # Overall market mood calculation
        bullish_total = sum(1 for i in analyzed_items if i.sentiment == "BULLISH")
        bearish_total = sum(1 for i in analyzed_items if i.sentiment == "BEARISH")
        
        if bullish_total > bearish_total:
            mood = "BULLISH"
        elif bearish_total > bullish_total:
            mood = "BEARISH"
        elif analyzed_items:
            mood = "MIXED"
        else:
            mood = "NEUTRAL"

        return StockAnalysisOutput(
            items=analyzed_items,
            total_tickers=len(analyzed_items),
            overall_market_mood=mood,
            processed_sources_count=len(text_items),
            analysis_engine="Fallback Heuristic NLP (Ollama Timed Out / Unavailable)"
        )
