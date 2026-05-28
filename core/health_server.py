"""
Minimal HTTP health server for cloud platforms (Fly.io health checks).
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from core.logger import get_logger

logger = get_logger("health")


class _HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def start_health_server(port: int) -> threading.Thread:
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="health-server")
    thread.start()
    logger.info("Health server listening on 0.0.0.0:%s", port)
    return thread
