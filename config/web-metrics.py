#!/usr/bin/env python3
"""Métricas do Prometheus a partir do access log do nginx; só biblioteca padrão."""

import math
import statistics
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path("/var/log/nginx/cluster_access.log")


def metrics():
    """Resume as requisições recentes do nginx no formato de texto do Prometheus."""
    now = time.time()
    try:
        with LOG.open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 2_000_000))
            data = stream.read().decode("utf-8", errors="replace")
    except FileNotFoundError:
        data = ""
    if len(data) >= 2_000_000:
        data = data.split("\n", 1)[-1]
    durations = []
    errors = 0
    for line in data.splitlines():
        try:
            timestamp, status, duration = line.split()
            if now - float(timestamp) <= 60:
                durations.append(float(duration))
                errors += int(status) >= 500
        except (ValueError, TypeError):
            continue
    durations.sort()
    count = len(durations)
    p95 = durations[math.ceil(count * 0.95) - 1] if count else 0
    avg = statistics.mean(durations) if count else 0
    return (
        f"cluster_http_requests_last_minute {count}\n"
        f"cluster_http_5xx_last_minute {errors}\n"
        f"cluster_http_latency_avg_seconds {avg:.6f}\n"
        f"cluster_http_latency_p95_seconds {p95:.6f}\n"
    )


class Handler(BaseHTTPRequestHandler):
    """Expõe as métricas calculadas via HTTP."""

    def do_GET(self):
        """Serve as métricas e rejeita caminhos não relacionados."""
        if self.path != "/metrics":
            self.send_error(404)
            return
        payload = metrics().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9113), Handler).serve_forever()
