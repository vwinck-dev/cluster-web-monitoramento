"""Testes de comportamento do exporter de métricas web."""

import importlib.util
import time
from unittest.mock import patch

from support import ROOT, TempDirTestCase

SPEC = importlib.util.spec_from_file_location(
    "web_metrics", ROOT / "config" / "web-metrics.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MetricsTests(TempDirTestCase):
    def test_recent_requests_errors_and_p95(self):
        """Uma amostra de 20 requisições deve reportar o p95 por nearest-rank."""
        log = self.tmp / "access.log"
        now = time.time()
        lines = [f"{now - 120} 200 100"]  # fora da janela de 60 s
        lines.extend(
            f"{now - 1} {500 if duration == 20 else 200} {duration}"
            for duration in range(1, 21)
        )
        log.write_text("\n".join(lines) + "\n")
        with patch.object(MODULE, "LOG", log):
            result = MODULE.metrics()
        self.assertIn("cluster_http_requests_last_minute 20\n", result)
        self.assertIn("cluster_http_5xx_last_minute 1\n", result)
        self.assertIn("cluster_http_latency_avg_seconds 10.500000\n", result)
        self.assertIn("cluster_http_latency_p95_seconds 19.000000\n", result)
