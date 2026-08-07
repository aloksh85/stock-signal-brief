"""
Main entry point for running the Stock Signal Brief autonomous pipeline.
Executes multi-agent orchestrator loop and outputs JSON and Markdown reports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from config import OUTPUT_DIR, METRICS_LOG_PATH
from agents import StockSignalOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")


def generate_markdown_report(report) -> str:
    """Generates a clean markdown brief report from DailyStockBriefReport object."""
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    md_lines = [
        f"# 📈 Autonomous Stock Signal Brief ({date_str})",
        "",
        f"**Generated At:** {report.generated_at}",
        f"**Macro Market Mood:** `{report.analysis_output.overall_market_mood}`",
        f"**Sources Analyzed:** {report.analysis_output.processed_sources_count}",
        f"**Unique Tickers Identified:** {report.analysis_output.total_tickers}",
        "",
        "## 📝 Executive Summary",
        f"{report.executive_summary}",
        "",
        "## 🚀 Top Bullish Signals",
    ]

    if report.top_bullish_signals:
        for item in report.top_bullish_signals:
            rec_badge = "🟢 BUY" if getattr(item, "recommendation", "WAIT") == "BUY" else "🟡 WAIT"
            news_bullets = "\n".join([f"  * {news}" for news in getattr(item, "relevant_news", [])]) if getattr(item, "relevant_news", []) else f"  * {item.source_summary}"
            md_lines.extend([
                f"### 🟢 {item.ticker} - {item.company_name} | Signal: `{rec_badge}`",
                f"- **Sentiment:** `BULLISH` (Confidence: {item.confidence_score * 100:.0f}%)",
                f"- **Action Recommendation:** `{getattr(item, 'recommendation', 'BUY')}`",
                f"- **Key Themes:** {', '.join(item.key_themes)}",
                f"- **Relevant News & Video Insights:**\n{news_bullets}",
                ""
            ])
    else:
        md_lines.append("*No distinct bullish signals detected today.*\n")

    md_lines.append("## 🔻 Top Bearish / Caution Signals")
    if report.top_bearish_signals:
        for item in report.top_bearish_signals:
            rec_badge = "🔴 WAIT / AVOID"
            news_bullets = "\n".join([f"  * {news}" for news in getattr(item, "relevant_news", [])]) if getattr(item, "relevant_news", []) else f"  * {item.source_summary}"
            md_lines.extend([
                f"### 🔴 {item.ticker} - {item.company_name} | Signal: `{rec_badge}`",
                f"- **Sentiment:** `BEARISH` (Confidence: {item.confidence_score * 100:.0f}%)",
                f"- **Action Recommendation:** `WAIT`",
                f"- **Key Themes:** {', '.join(item.key_themes)}",
                f"- **Relevant News & Video Insights:**\n{news_bullets}",
                ""
            ])
    else:
        md_lines.append("*No distinct bearish signals detected today.*\n")

    md_lines.extend([
        "## 🌐 Dominant Market Themes",
        "\n".join([f"- {theme}" for theme in report.macro_themes]),
        "",
        "---",
        "*Powered by Google Antigravity SDK & Local Reasoning Engine*"
    ])

    return "\n".join(md_lines)


def save_report_artifacts(report) -> tuple:
    """Saves both JSON and Markdown reports to OUTPUT_DIR."""
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    json_path = OUTPUT_DIR / f"daily_stock_brief_{date_str}.json"
    md_path = OUTPUT_DIR / f"daily_stock_brief_{date_str}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)
    logger.info(f"Saved JSON brief artifact to: {json_path}")

    md_content = generate_markdown_report(report)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Saved Markdown brief report to: {md_path}")
    return json_path, md_path


def main():
    logger.info("Initializing Stock Signal Brief Autonomous System...")
    orchestrator = StockSignalOrchestrator()
    
    # Run pipeline loop
    report = orchestrator.execute_pipeline()
    save_report_artifacts(report)
    logger.info(f"Performance metrics logged to: {METRICS_LOG_PATH}")


if __name__ == "__main__":
    main()
