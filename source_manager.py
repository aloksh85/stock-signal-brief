"""
YAML Source Configuration Manager for Stock Signal Brief.
Handles loading, adding, and removing sources from sources.yaml.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("source_manager")

SOURCES_YAML_PATH = Path(__file__).parent / "sources.yaml"


class SourceManager:
    """Manages reading and updating sources.yaml."""

    def __init__(self, yaml_path: Path = SOURCES_YAML_PATH):
        self.yaml_path = yaml_path
        self._ensure_yaml_exists()

    def _ensure_yaml_exists(self):
        if not self.yaml_path.exists():
            default_data = {
                "enable_yahoo_gainers": True,
                "yahoo_gainers_limit": 10,
                "rss_feeds": [
                    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META",
                    "https://www.marketwatch.com/rss/topstories"
                ],
                "youtube_sources": [
                    "stock market news today analysis",
                    "top tech stocks outlook NVDA AAPL TSLA"
                ],
                "news_webpages": [
                    "https://www.reuters.com/business/finance"
                ]
            }
            self.save_sources(default_data)

    def load_sources(self) -> Dict[str, Any]:
        """Loads and returns sources from sources.yaml."""
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return {
                    "enable_yahoo_gainers": data.get("enable_yahoo_gainers", True),
                    "yahoo_gainers_limit": data.get("yahoo_gainers_limit", 10),
                    "rss_feeds": data.get("rss_feeds", []),
                    "youtube_sources": data.get("youtube_sources", []),
                    "news_webpages": data.get("news_webpages", [])
                }
        except Exception as e:
            logger.error(f"Error loading sources.yaml: {e}")
            return {
                "enable_yahoo_gainers": True,
                "yahoo_gainers_limit": 10,
                "rss_feeds": [],
                "youtube_sources": [],
                "news_webpages": []
            }

    def save_sources(self, data: Dict[str, List[str]]) -> bool:
        """Saves current source data dictionary to sources.yaml."""
        try:
            with open(self.yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.info("Successfully updated sources.yaml")
            return True
        except Exception as e:
            logger.error(f"Error saving sources.yaml: {e}")
            return False

    def add_source(self, category: str, url_or_query: str) -> bool:
        """Adds a source string to category ('rss_feeds', 'youtube_sources', 'news_webpages')."""
        sources = self.load_sources()
        if category not in sources:
            sources[category] = []

        item = url_or_query.strip()
        if item and item not in sources[category]:
            sources[category].append(item)
            return self.save_sources(sources)
        return False

    def remove_source(self, category: str, url_or_query: str) -> bool:
        """Removes a source string from category."""
        sources = self.load_sources()
        if category in sources and url_or_query in sources[category]:
            sources[category].remove(url_or_query)
            return self.save_sources(sources)
        return False

    def toggle_yahoo_gainers(self, enabled: bool) -> bool:
        """Toggles enable_yahoo_gainers setting in sources.yaml."""
        sources = self.load_sources()
        sources["enable_yahoo_gainers"] = enabled
        return self.save_sources(sources)



# Global instance
source_manager = SourceManager()
