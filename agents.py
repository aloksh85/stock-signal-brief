"""
Agent Topology definition using Google Antigravity SDK.
Configures Orchestrator, Ingestion, News, and Analysis sub-agents with safety policies & tools.
Integrates with source_manager (sources.yaml) and smart_cache.
"""

import logging
from typing import Dict, Any, List
from google.antigravity import LocalAgentConfig, CapabilitiesConfig
from tools import fetch_youtube_transcripts, fetch_financial_rss, fetch_news_webpage, fetch_top_gainers, fetch_gainers_news
from hooks import metrics_hook
from analyzer import StockAnalyzer
from schemas import StockAnalysisOutput, DailyStockBriefReport
from source_manager import source_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agents")


class IngestionSubAgent:
    """Sub-agent dedicated to YouTube transcript extraction."""

    def __init__(self):
        self.tool_name = "fetch_youtube_transcripts"

    def run(self, query: str) -> Dict[str, Any]:
        metrics_hook.pre_tool_call(self.tool_name, {"query": query})
        try:
            res = fetch_youtube_transcripts(query)
            metrics_hook.post_tool_call(self.tool_name, {"query": query}, res)
            return res
        except Exception as e:
            metrics_hook.post_tool_call(self.tool_name, {"query": query}, None, error=e)
            raise e


class NewsSubAgent:
    """Sub-agent dedicated to parsing financial RSS feeds, Yahoo top gainers, and web pages."""

    def run_rss(self, rss_urls: List[str]) -> Dict[str, Any]:
        tool_name = "fetch_financial_rss"
        metrics_hook.pre_tool_call(tool_name, {"url_list": rss_urls})
        try:
            res = fetch_financial_rss(rss_urls)
            metrics_hook.post_tool_call(tool_name, {"url_list": rss_urls}, res)
            return res
        except Exception as e:
            metrics_hook.post_tool_call(tool_name, {"url_list": rss_urls}, None, error=e)
            raise e

    def run_webpage(self, webpage_url: str) -> Dict[str, Any]:
        tool_name = "fetch_news_webpage"
        metrics_hook.pre_tool_call(tool_name, {"url": webpage_url})
        try:
            res = fetch_news_webpage(webpage_url)
            metrics_hook.post_tool_call(tool_name, {"url": webpage_url}, res)
            return res
        except Exception as e:
            metrics_hook.post_tool_call(tool_name, {"url": webpage_url}, None, error=e)
            raise e

    def run_yahoo_gainers(self, limit: int = 10) -> Dict[str, Any]:
        tool_name = "fetch_yahoo_gainers_news"
        metrics_hook.pre_tool_call(tool_name, {"limit": limit})
        try:
            tickers = fetch_top_gainers(limit=limit)
            news_res = fetch_gainers_news(tickers)
            metrics_hook.post_tool_call(tool_name, {"limit": limit}, news_res)
            return news_res
        except Exception as e:
            metrics_hook.post_tool_call(tool_name, {"limit": limit}, None, error=e)
            raise e


class AnalysisSubAgent:
    """Sub-agent dedicated to local reasoning, ticker extraction, and sentiment scoring."""

    def __init__(self):
        self.analyzer = StockAnalyzer()

    def run(self, raw_text_items: List[Dict[str, Any]]) -> StockAnalysisOutput:
        tool_name = "analyze_stock_texts"
        metrics_hook.pre_tool_call(tool_name, {"items_count": len(raw_text_items)})
        try:
            output = self.analyzer.analyze_texts(raw_text_items)
            metrics_hook.post_tool_call(tool_name, {"items_count": len(raw_text_items)}, output.model_dump())
            return output
        except Exception as e:
            metrics_hook.post_tool_call(tool_name, {"items_count": len(raw_text_items)}, None, error=e)
            raise e


class StockSignalOrchestrator:
    """
    Primary Orchestrator Agent.
    Manages sources from sources.yaml, dispatches tasks to sub-agents, aggregates data, and compiles final report.
    """

    def __init__(self):
        self.agent_config = LocalAgentConfig(
            system_instructions="You are the Stock Signal Brief Orchestrator. Oversee sub-agents and generate structured reports.",
            capabilities=CapabilitiesConfig()
        )
        self.ingestion_agent = IngestionSubAgent()
        self.news_agent = NewsSubAgent()
        self.analysis_agent = AnalysisSubAgent()

    def execute_pipeline(
        self,
        rss_urls: List[str] = None,
        youtube_queries: List[str] = None,
        news_webpages: List[str] = None
    ) -> DailyStockBriefReport:
        """
        Runs the autonomous multi-agent pipeline loop using sources.yaml or custom arguments.
        """
        # Load sources from sources.yaml if not explicitly passed
        configured_sources = source_manager.load_sources()
        urls = rss_urls if rss_urls is not None else configured_sources.get("rss_feeds", [])
        yt_sources = youtube_queries if youtube_queries is not None else configured_sources.get("youtube_sources", [])
        webpages = news_webpages if news_webpages is not None else configured_sources.get("news_webpages", [])
        enable_gainers = configured_sources.get("enable_yahoo_gainers", True)
        gainers_limit = configured_sources.get("yahoo_gainers_limit", 10)

        logger.info("=== [ORCHESTRATOR] Starting Autonomous Stock Signal Loop ===")
        
        # Ollama Preflight Check (Halts execution if Ollama service is unavailable)
        logger.info("[0/5] Executing Ollama service preflight check...")
        self.analysis_agent.analyzer.require_ollama_available()

        raw_items: List[Dict[str, Any]] = []

        # 1. Advanced YouTube Search & Recent Video Filtering (within 3 days, >= 1,000 likes)
        shortlisted_tickers = set()
        if yt_sources:
            logger.info(f"[1/5] Driving advanced YouTube discovery for {len(yt_sources)} video seed sources...")
            all_yt_transcripts = []
            for q in yt_sources:
                try:
                    from tools.youtube_tool import search_related_recent_videos, extract_shortlisted_tickers_and_news
                    transcripts = search_related_recent_videos(q, days_window=3, min_likes=1000)
                    all_yt_transcripts.extend(transcripts)
                    for t in transcripts:
                        raw_items.append({
                            "title": t.get("title", ""),
                            "text": t.get("transcript", ""),
                            "source_type": "youtube",
                            "source_name": t.get("channel", "YouTube Analyst")
                        })
                except Exception as e:
                    logger.warning(f"Error in YouTube video discovery for query {q}: {e}")

            # Extract shortlisted tickers from video transcripts
            if all_yt_transcripts:
                extracted_map = extract_shortlisted_tickers_and_news(all_yt_transcripts)
                shortlisted_tickers.update(extracted_map.keys())
                logger.info(f"[1/5] Shortlisted {len(shortlisted_tickers)} tickers from YouTube transcripts: {list(shortlisted_tickers)}")

        # 2. Fetch Yahoo Finance Top Gainers News
        if enable_gainers:
            logger.info(f"[2/5] Scraping Top {gainers_limit} Yahoo Finance Gainers & fetching news...")
            try:
                gainers_data = self.news_agent.run_yahoo_gainers(limit=gainers_limit)
                for entry in gainers_data.get("entries", []):
                    raw_items.append({
                        "title": entry.get("title", ""),
                        "text": entry.get("summary", ""),
                        "ticker": entry.get("ticker"),
                        "source_type": "yahoo_gainers",
                        "source_name": entry.get("source", "Yahoo Gainers RSS")
                    })
                    if entry.get("ticker") and entry.get("ticker") != "TOP_GAINER":
                        shortlisted_tickers.add(entry.get("ticker"))
            except Exception as e:
                logger.warning(f"Error fetching Yahoo Gainers news: {e}")

        # 3. Fetch Targeted Yahoo RSS for Shortlisted Tickers + Configured RSS feeds
        if shortlisted_tickers or urls:
            combined_tickers = list(shortlisted_tickers)
            logger.info(f"[3/5] Ingesting targeted Yahoo Finance RSS news for tickers: {combined_tickers}")
            if combined_tickers:
                try:
                    targeted_rss_data = fetch_gainers_news(combined_tickers)
                    for entry in targeted_rss_data.get("entries", []):
                        raw_items.append({
                            "title": entry.get("title", ""),
                            "text": entry.get("summary", ""),
                            "ticker": entry.get("ticker"),
                            "source_type": "rss",
                            "source_name": entry.get("source", "Yahoo RSS")
                        })
                except Exception as e:
                    logger.warning(f"Error fetching targeted ticker RSS: {e}")

            if urls:
                logger.info(f"[3/5] Processing {len(urls)} standard RSS feed sources...")
                rss_data = self.news_agent.run_rss(urls)
                for entry in rss_data.get("entries", []):
                    raw_items.append({
                        "title": entry.get("title", ""),
                        "text": entry.get("summary", ""),
                        "source_type": "rss",
                        "source_name": entry.get("source", "RSS Feed")
                    })

        # 4. Fetch News Webpages
        if webpages:
            logger.info(f"[4/5] Processing {len(webpages)} custom news webpage URLs...")
            for w_url in webpages:
                page_data = self.news_agent.run_webpage(w_url)
                if page_data.get("text"):
                    raw_items.append({
                        "title": page_data.get("title", w_url),
                        "text": page_data.get("text", ""),
                        "source_type": "webpage",
                        "source_name": page_data.get("url", "Web Page")
                    })

        logger.info(f"Data Aggregated. Total raw items gathered: {len(raw_items)}")

        # 5. Dispatch Analysis Sub-Agent
        logger.info("[5/5] Dispatching Analysis Sub-Agent...")
        analysis_output = self.analysis_agent.run(raw_items)

        # Synthesize report
        bullish = [item for item in analysis_output.items if item.sentiment == "BULLISH"]
        bearish = [item for item in analysis_output.items if item.sentiment == "BEARISH"]

        all_themes = []
        for item in analysis_output.items:
            all_themes.extend(item.key_themes)
        unique_themes = list(dict.fromkeys(all_themes))

        summary_text = (
            f"Analyzed {analysis_output.processed_sources_count} financial news, RSS, and YouTube sources. "
            f"Identified {analysis_output.total_tickers} active stock tickers. "
            f"Overall macro market mood is rated {analysis_output.overall_market_mood} with "
            f"{len(bullish)} bullish and {len(bearish)} bearish signal indications."
        )

        report = DailyStockBriefReport(
            executive_summary=summary_text,
            top_bullish_signals=bullish,
            top_bearish_signals=bearish,
            macro_themes=unique_themes,
            analysis_output=analysis_output
        )

        logger.info("=== [ORCHESTRATOR] Autonomous Loop Completed Successfully ===")
        return report
