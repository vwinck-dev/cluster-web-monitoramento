"""Testes da coleta de evidências com navegador e runner falsos."""

import shutil
from unittest.mock import patch

from support import ROOT, TempDirTestCase

from src.evidence import (
    BASELINE,
    LOAD_REQUESTS,
    TARGETS,
    UNDER_LOAD,
    Endpoints,
    EvidenceCollector,
)
from src.lab import Lab


class FakeBrowser:
    """Registra as chamadas e grava um arquivo vazio no lugar de cada captura."""

    def __init__(self, log):
        self.log = log

    def login(self, base_url, user, password):
        self.log.append(("login", base_url, user, password))

    def open(self, url):
        self.log.append(("open", url))

    def wait_for_charts(self, count):
        self.log.append(("wait", count))

    def screenshot(self, path):
        path.write_bytes(b"")
        self.log.append(("shot", path.name))

    def close(self):
        self.log.append(("close",))


class EvidenceTests(TempDirTestCase):
    def setUp(self):
        """Cada teste roda numa cópia do projeto, para evidence/ não sujar o repositório."""
        super().setUp()
        shutil.copytree(ROOT / "config", self.tmp / "config")
        self.settings = self.isolated_settings()
        self.log = []

    def collector(self, readings, timeout_clock=None):
        values = iter(readings)
        return EvidenceCollector(
            self.settings,
            FakeBrowser(self.log),
            lambda *argv: self.log.append(("load", argv)),
            ["ssh", "client", "load"],
            "secret",
            query=lambda url, expr: next(values),
            sleep=lambda _: self.log.append(("sleep",)),
            clock=timeout_clock or (lambda: 0),
        )

    def test_endpoints_follow_monitor_forwards(self):
        """As URLs saem dos encaminhamentos do cluster.json, não de portas fixas."""
        self.assertEqual(
            Endpoints.from_settings(self.settings),
            Endpoints("http://127.0.0.1:3000", "http://127.0.0.1:9090"),
        )

    def test_captures_baseline_then_load_then_targets(self):
        """A linha de base vem antes da carga; a captura sob carga só depois de ela aparecer."""
        saved = self.collector([5, 5, LOAD_REQUESTS]).run()
        dashboard = f"http://127.0.0.1:3000/d/{self.settings.name}?kiosk"
        self.assertEqual(
            self.log,
            [
                ("login", "http://127.0.0.1:3000", "admin", "secret"),
                ("open", dashboard),
                ("wait", 6),
                ("shot", BASELINE),
                ("load", ("ssh", "client", "load")),
                ("sleep",),
                ("open", dashboard),
                ("wait", 6),
                ("shot", UNDER_LOAD),
                ("open", "http://127.0.0.1:9090/classic/targets"),
                ("shot", TARGETS),
                ("close",),
            ],
        )
        self.assertEqual([path.name for path in saved], [BASELINE, UNDER_LOAD, TARGETS])

    def test_previous_captures_are_removed(self):
        """Capturas de uma execução anterior não sobram ao lado das novas."""
        output = self.settings.root / "evidence"
        output.mkdir()
        (output / "antiga.png").write_bytes(b"")
        self.collector([0, LOAD_REQUESTS]).run()
        self.assertEqual(
            sorted(path.name for path in output.glob("*.png")),
            sorted([BASELINE, UNDER_LOAD, TARGETS]),
        )

    def test_load_never_seen_fails_and_closes_browser(self):
        """Sem a carga no Prometheus, não há captura sob carga falsa; o navegador fecha."""
        ticks = iter(range(0, 1000, 30))
        with self.assertRaisesRegex(RuntimeError, "não registrou a carga"):
            self.collector([0] * 10, timeout_clock=lambda: next(ticks)).run()
        self.assertNotIn(("shot", UNDER_LOAD), self.log)
        self.assertEqual(self.log[-1], ("close",))

    def test_lab_runs_load_script_on_client(self):
        """A Facade roda o load.sh no cliente por SSH não interativo e usa a senha do lab."""
        calls = []
        lab = Lab(self.settings, runner=lambda *argv: calls.append(argv))
        lab.store.ensure_root()
        values = iter([0, LOAD_REQUESTS])
        with patch("src.evidence.prometheus_value", lambda url, expr: next(values)):
            lab.evidence(browser=FakeBrowser(self.log))
        (argv,) = calls
        self.assertEqual(argv[:3], ("ssh", "-o", "BatchMode=yes"))
        self.assertEqual(
            argv[-4:],
            ("sudo", f"{self.settings.guest_dir}/load.sh", str(LOAD_REQUESTS), "30"),
        )
        self.assertEqual(self.log[0][3], lab.store.grafana_password())
        self.assertNotIn(
            "BatchMode=yes", lab.ssh_argv("client")
        )  # ssh da CLI segue interativo
