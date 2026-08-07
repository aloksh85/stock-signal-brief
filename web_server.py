"""
Lightweight REST API & Web Dashboard Server for Stock Signal Brief.
Serves the web dashboard UI and manages sources.yaml, smart cache, and manual pipeline execution.
"""

import json
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from source_manager import source_manager
from cache_manager import smart_cache
from agents import StockSignalOrchestrator
from config import OUTPUT_DIR, METRICS_LOG_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("web_server")

BASE_DIR = Path(__file__).parent.resolve()
HOST = "0.0.0.0"
PORT = 8080


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler providing REST API endpoints and static file serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/sources":
            self._set_headers(200)
            sources = source_manager.load_sources()
            self.wfile.write(json.dumps(sources).encode("utf-8"))

        elif path == "/api/cache-stats":
            self._set_headers(200)
            stats = smart_cache.get_stats()
            self.wfile.write(json.dumps(stats).encode("utf-8"))

        elif path == "/api/latest-report":
            json_files = sorted(OUTPUT_DIR.glob("daily_stock_brief_*.json"))
            if json_files:
                latest_file = json_files[-1]
                with open(latest_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                self._set_headers(200)
                self.wfile.write(json.dumps(content).encode("utf-8"))
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "No reports generated yet."}).encode("utf-8"))

        elif path == "/" or path == "/index.html":
            index_path = BASE_DIR / "index.html"
            if index_path.exists():
                self._set_headers(200, content_type="text/html")
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404)
                self.wfile.write(b"index.html not found")
        else:
            super().do_GET()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            body_json = json.loads(post_body.decode("utf-8")) if post_body else {}
        except Exception:
            body_json = {}

        if path == "/api/sources/add":
            category = body_json.get("category")
            url_or_query = body_json.get("url_or_query")
            if category and url_or_query:
                success = source_manager.add_source(category, url_or_query)
                self._set_headers(200 if success else 400)
                self.wfile.write(json.dumps({"success": success, "sources": source_manager.load_sources()}).encode("utf-8"))
            else:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing category or url_or_query"}).encode("utf-8"))

        elif path == "/api/sources/remove":
            category = body_json.get("category")
            url_or_query = body_json.get("url_or_query")
            if category and url_or_query:
                success = source_manager.remove_source(category, url_or_query)
                self._set_headers(200 if success else 400)
                self.wfile.write(json.dumps({"success": success, "sources": source_manager.load_sources()}).encode("utf-8"))
            else:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing category or url_or_query"}).encode("utf-8"))

        elif path == "/api/sources/toggle-gainers":
            enabled = body_json.get("enabled", True)
            success = source_manager.toggle_yahoo_gainers(bool(enabled))
            self._set_headers(200 if success else 400)
            self.wfile.write(json.dumps({"success": success, "sources": source_manager.load_sources()}).encode("utf-8"))


        elif path == "/api/run":
            logger.info("Manual pipeline run triggered via Web Dashboard.")
            try:
                from main import save_report_artifacts
                orchestrator = StockSignalOrchestrator()
                report = orchestrator.execute_pipeline()
                save_report_artifacts(report)
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "success", "report": report.model_dump()}).encode("utf-8"))
            except Exception as e:
                logger.error(f"Error running pipeline: {e}")
                self._set_headers(500)
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))


def run_server(port=PORT):
    server_address = (HOST, port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    logger.info(f"🚀 Stock Signal Web Dashboard running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
