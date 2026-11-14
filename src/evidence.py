"""Coleta de evidências: o dashboard antes e durante a carga e os alvos do Prometheus.

As capturas são geradas a cada execução em evidence/, ignorada pelo Git. O
navegador fica atrás da porta Browser (o adaptador real está em browser.py) e a
carga roda pelo runner injetado, então os testes trocam os dois.
"""

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

from .i18n import t

GRAFANA_USER = "admin"
GRAFANA_PORT = 3000
PROMETHEUS_PORT = 9090
LOAD_REQUESTS = 10000
LOAD_CONCURRENCY = 30
# Requisições contadas pelo exportador na janela dos últimos 60 s do nginx.
REQUESTS_METRIC = "cluster_http_requests_last_minute"
LOAD_TIMEOUT_S = 60
POLL_S = 2

BASELINE = "dashboard-linha-de-base.png"
UNDER_LOAD = "dashboard-sob-carga.png"
TARGETS = "prometheus-quatro-alvos.png"


class EvidenceUnavailable(RuntimeError):
    """Selenium ou Firefox ausente: não há como capturar as páginas."""


class Browser(Protocol):
    def login(self, base_url: str, user: str, password: str) -> None: ...
    def open(self, url: str) -> None: ...
    def wait_for_charts(self, count: int) -> None: ...
    def screenshot(self, path) -> None: ...
    def close(self) -> None: ...


def open_browser():
    """Abre o navegador real; o import tardio mantém o Selenium opcional."""
    try:
        from .browser import SeleniumBrowser
    except ImportError as exc:
        raise EvidenceUnavailable(t("evidence.error.unavailable")) from exc
    return SeleniumBrowser()


@dataclass(frozen=True)
class Endpoints:
    """URLs do Grafana e do Prometheus no host, tiradas dos encaminhamentos do monitor."""

    grafana: str
    prometheus: str

    @classmethod
    def from_settings(cls, settings):
        monitor = settings.nodes["monitor"]
        return cls(
            grafana=f"http://127.0.0.1:{monitor.host_port(GRAFANA_PORT)}",
            prometheus=f"http://127.0.0.1:{monitor.host_port(PROMETHEUS_PORT)}",
        )


def prometheus_value(base_url, expr):
    """Retorna a soma do resultado instantâneo de uma consulta PromQL."""
    url = f"{base_url}/api/v1/query?{urlencode({'query': expr})}"
    with urllib.request.urlopen(url, timeout=10) as response:
        result = json.load(response)["data"]["result"]
    return sum(float(sample["value"][1]) for sample in result)


class EvidenceCollector:
    """Template Method: linha de base, carga, captura sob carga e alvos, nessa ordem."""

    def __init__(
        self,
        settings,
        browser,
        runner,
        load_argv,
        password,
        query=None,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.settings = settings
        self.browser = browser
        self.runner = runner
        self.load_argv = load_argv
        self.password = password
        self.query = query or prometheus_value
        self.sleep = sleep
        self.clock = clock
        self.endpoints = Endpoints.from_settings(settings)
        self.output = settings.root / "evidence"
        dashboard = json.loads((settings.root / "config/dashboard.json").read_text())
        self.panels = len(dashboard["panels"])

    @property
    def dashboard_url(self):
        return f"{self.endpoints.grafana}/d/{self.settings.name}?kiosk"

    def run(self):
        """Gera as três capturas e devolve seus caminhos."""
        self.reset_output()
        try:
            self.browser.login(self.endpoints.grafana, GRAFANA_USER, self.password)
            saved = [self.capture_dashboard(BASELINE)]
            baseline = self.requests_last_minute()
            self.runner(*self.load_argv)
            self.wait_for_load(baseline)
            saved.append(self.capture_dashboard(UNDER_LOAD))
            saved.append(
                self.capture(f"{self.endpoints.prometheus}/classic/targets", TARGETS)
            )
        finally:
            self.browser.close()
        return saved

    def reset_output(self):
        """Remove capturas de execuções anteriores para não misturar resultados."""
        self.output.mkdir(exist_ok=True)
        for old in self.output.glob("*.png"):
            old.unlink()

    def capture_dashboard(self, filename):
        self.browser.open(self.dashboard_url)
        self.browser.wait_for_charts(self.panels)
        return self.save(filename)

    def capture(self, url, filename):
        self.browser.open(url)
        return self.save(filename)

    def save(self, filename):
        path = self.output / filename
        self.browser.screenshot(path)
        print(t("evidence.saved", path=path))
        return path

    def requests_last_minute(self):
        return self.query(self.endpoints.prometheus, REQUESTS_METRIC)

    def wait_for_load(self, baseline):
        """Espera o Prometheus registrar ao menos metade da carga enviada."""
        expected = baseline + LOAD_REQUESTS / 2
        deadline = self.clock() + LOAD_TIMEOUT_S
        while self.requests_last_minute() < expected:
            if self.clock() >= deadline:
                raise RuntimeError(
                    t("evidence.error.load_not_seen", expected=int(expected))
                )
            self.sleep(POLL_S)
