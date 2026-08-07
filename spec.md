Here is a comprehensive specification and execution plan for building this autonomous loop using the Google Antigravity SDK.

This design leverages a multi-agent topology to separate concerns, ensures your reasoning engine stays local, and uses SDK lifecycle hooks for robust performance evaluation.

### 1. Agent Topology

We will use the Antigravity SDK's sub-agent capabilities to spawn a team of specialized agents, overseen by an orchestrator.

* **The Orchestrator:** The primary controller. It manages the daily schedule, dispatches tasks to the sub-agents, aggregates the data, and compiles the final output.
* **The Ingestion Sub-Agent:** Equipped with custom tools to query the YouTube Data API and fetch transcripts.
* **The News Sub-Agent (New):** Dedicated to parsing text from external sources. It will use a custom tool built with a library like `feedparser` to monitor financial RSS feeds (e.g., Bloomberg, Yahoo Finance, or niche Substack feeds).
* **The Analysis Sub-Agent:** Handles the heavy lifting of extracting tickers, sentiment, and themes. We will route the extraction tasks directly to your local Ollama instance to keep the core processing offline, secure, and cost-effective.

### 2. Extensibility: Custom Python Tools

The Antigravity SDK natively supports registering any Python callable as an agent tool. The Orchestrator will provision two primary functions to the ingestion agents:

* `fetch_youtube_transcripts(query: str, timeframe: str) -> dict`
* `fetch_financial_rss(url_list: list) -> dict`

### 3. Testing, Evaluation, & Observability

To evaluate performance and ensure the autonomous loop doesn't fail silently, we will build testing directly into the pipeline using the SDK's native architecture:

* **Lifecycle Hooks:** We will attach `Inspect` hooks (specifically `post_tool_call`) to log latency, payload size, and token usage for every action. This data builds a historical performance baseline to evaluate your local models.
* **Structured Output Validation:** The Analysis Sub-Agent will not return raw text. We will define a Pydantic schema (e.g., `StockAnalysisOutput` with fields for `ticker`, `sentiment`, and `source`). The SDK will enforce this schema, and a secondary eval script can automatically verify if the outputted tickers match a known universe of stock symbols.
* **Declarative Safety Policies:** We will implement a "deny by default" policy. By explicitly allowing only the data fetching tools and `write_file`, we guarantee the agents cannot execute unintended shell commands if the local model hallucinates.

---

## Execution Plan

1. **Environment Setup:**
Establish your local Python environment and install the core dependencies: `pip install google-antigravity youtube-transcript-api feedparser pydantic`. Ensure your local Ollama server is running and configured to accept local API requests.


2. **Define Tools & Schemas:**
Write the Python functions for the RSS and YouTube scrapers. Define the `StockAnalysisOutput` Pydantic model to mandate the exact data structure the Ollama instance must return.


3. **Initialize the Agent Configurations:**
Configure the `LocalAgentConfig`. Instantiate the Orchestrator, and configure it to spawn the Ingestion, News, and Analysis sub-agents. Map the custom tools to the appropriate ingestion agents.


4. **Wire the Evaluation Hooks:**
Attach the `Inspect` hooks to the configuration. Write a local logging function that captures the thinking traces and tool execution times to track the efficiency of the Ollama models over time.


5. **Deploy the Orchestration Loop:**
Wrap the execution in an `asyncio` main loop triggered by a local cron job or Windows Task Scheduler. The Orchestrator runs the ingestors in parallel, feeds the text to the Analysis agent, and writes the validated JSON to your local disk.