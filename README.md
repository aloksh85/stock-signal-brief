# 📈 Stock Signal Brief: Autonomous Multi-Agent Loop & Web Dashboard

An autonomous, local-first multi-agent development pipeline built with the **Google Antigravity SDK (`google-antigravity`)**, Pydantic schema validation, `youtube-transcript-api`, `feedparser`, smart local caching, and a modern Web Dashboard UI.

---

## 🏛️ System Architecture & Workflow

The system combines persistent YAML configuration (`sources.yaml`), smart local caching (`cache/`), and an interactive Web Dashboard UI:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Web Dashboard UI (Port 8080)                    │
│    Manage YouTube Links, Financial RSS Feeds, & News Webpage URLs      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Reads/Writes)
                                    ▼
                          ┌──────────────────┐
                          │   sources.yaml   │
                          └─────────┬────────┘
                                    │
                  ┌─────────────────┴────────────────────────────┐
                  │          StockSignalOrchestrator             │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │    Ingestion Sub-Agent    │                   │      News Sub-Agent       │
   │  (tools/youtube_tool.py)  │                   │ (RSS & webpage_tool.py)   │
   └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │ (Uses smart_cache TTL: 12 hrs)
                                         ▼
                           ┌───────────────────────────┐
                           │    Analysis Sub-Agent     │
                           │   (analyzer.py Engine)    │
                           └─────────────┬─────────────┘
                                         │ (Ollama / NLP Fallback)
                                         ▼
                           ┌───────────────────────────┐
                           │ Pydantic Schema Validator │
                           │       (schemas.py)        │
                           └─────────────┬─────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │  Daily Brief Markdown/JSON│                   │  SDK Telemetry JSONL Log  │
   │         (output/)         │                   │          (logs/)          │
   └───────────────────────────┘                   └───────────────────────────┘
```

---

## 🌐 1. Web Dashboard UI (`http://localhost:8080`)

Launch the web dashboard to manage sources and trigger runs visually:

```bash
/home/sharma76/miniconda3/bin/python web_server.py
```
Open **`http://localhost:8080`** in your browser to:
- **Paste & Save Sources**: Instantly add YouTube video links, channel handles, RSS feeds, or news webpage URLs to `sources.yaml`.
- **Run Autonomous Loop**: Trigger the multi-agent pipeline with a single click.
- **View Live Signals**: Visual Bullish / Bearish ticker cards with confidence indicators, key themes, and source summaries.
- **Monitor Telemetry & Cache**: Inspect real-time cache hit rates and execution latency.

---

## 📄 2. Persistent Source Config (`sources.yaml`)

Sources are saved to `sources.yaml` for version control and daily background cron runs:

```yaml
rss_feeds:
  - "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META"
  - "https://www.marketwatch.com/rss/topstories"

youtube_sources:
  - "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  - "stock market news today analysis"

news_webpages:
  - "https://www.reuters.com/business/finance"
```

---

## ⚡ 3. Smart Source Caching (`cache_manager.py`)

- Hashes URLs and text payloads using SHA256.
- Prevents re-downloading or re-processing identical news pages or video transcripts fetched within the **12-Hour TTL window**.
- Dramatically reduces latency on recurring daily runs.

---

## ⏰ 4. Daily Automatic Execution (Cron)

Schedule the pipeline to run automatically every morning at 8:00 AM using `sources.yaml`:

```cron
0 8 * * * /home/sharma76/miniconda3/bin/python /home/sharma76/sandbox/stock-signal-brief/main.py >> /home/sharma76/sandbox/stock-signal-brief/logs/cron.log 2>&1
```

---

## 📊 5. Automated Evaluation & Telemetry (`eval_pipeline.py`)

```bash
/home/sharma76/miniconda3/bin/python eval_pipeline.py
```
Outputs schema validation status, ticker universe alignment, and tool latency metrics.
