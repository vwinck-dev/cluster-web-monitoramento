#!/usr/bin/env python3
"""Pequena carga HTTP para tornar visíveis a CPU e a latência no laboratório."""

import time
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    """Serve a pequena carga usada para tornar observável o custo das requisições."""

    def do_GET(self):
        """Executa um trabalho fixo de CPU e responde o endpoint raiz."""
        if self.path != "/":
            self.send_error(404)
            return
        value = b"cluster-web-monitoramento"
        for _ in range(300):
            value = sha256(value).digest()
        time.sleep(0.004)
        payload = b"Cluster Web Monitoramento - servidor web ativo\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
