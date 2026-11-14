"""Verifica pelo host um laboratório em execução e, no fim, gera as evidências."""

import base64
import json
import subprocess
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from src.config import load
from src.evidence import EvidenceUnavailable
from src.i18n import t
from src.lab import Lab

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = load(ROOT)


def request(url, username=None, password=None):
    """Busca um endpoint HTTP local, opcionalmente com basic auth do Grafana."""
    headers = {}
    if username is not None:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    response = urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=10
    )
    return response.read().decode()


def ssh(name, command):
    """Roda uma checagem somente leitura na VM sem alterar o known_hosts do usuário."""
    port = SETTINGS.nodes[name].ssh_port
    return subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={SETTINGS.state / 'smoke-known-hosts'}",
            "-o",
            "ConnectTimeout=5",
            "-p",
            str(port),
            f"{SETTINGS.guest_user}@127.0.0.1",
            command,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    ).stdout


def main():
    """Verifica a inicialização das VMs, HTTP, quatro alvos de scrape e dashboard."""
    for name in SETTINGS.nodes:
        assert "status: done" in ssh(name, "cloud-init status"), t(
            "smoke.error.cloud_init", name=name
        )
        print(t("smoke.cloud_init_done", name=name))
    assert ssh("client", "systemctl is-active client-baseline").strip() == "active", t(
        "smoke.error.baseline"
    )
    assert "servidor web ativo" in request("http://127.0.0.1:18080/"), t(
        "smoke.error.web_down"
    )
    assert "servidor web ativo" in ssh(
        "client", f"curl -fsS http://{SETTINGS.nodes['web'].ip}/"
    ), t("smoke.error.client_unreachable")
    print(t("smoke.http_ok"))
    targets = json.loads(request("http://127.0.0.1:9090/api/v1/targets"))["data"][
        "activeTargets"
    ]
    expected = {(f"{node.ip}:9100", "nodes") for node in SETTINGS.nodes.values()}
    expected.add((f"{SETTINGS.nodes['web'].ip}:9113", "web"))
    observed = {
        (target["discoveredLabels"]["__address__"], target["labels"]["job"])
        for target in targets
        if target["health"] == "up"
    }
    assert expected <= observed, t("smoke.error.targets", missing=expected - observed)
    print(t("smoke.prometheus_ok"))
    health = json.loads(request("http://127.0.0.1:3000/api/health"))
    assert health["database"] == "ok", t("smoke.error.grafana", health=health)
    password = (SETTINGS.state / "grafana-password").read_text().strip()
    dashboard = json.loads(
        request(
            f"http://127.0.0.1:3000/api/dashboards/uid/{SETTINGS.name}",
            "admin",
            password,
        )
    )["dashboard"]
    assert len(dashboard["panels"]) >= 6, t("smoke.error.dashboard_incomplete")
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            query = urlencode({"query": target["expr"]})
            result = json.loads(request(f"http://127.0.0.1:9090/api/v1/query?{query}"))
            assert result["status"] == "success" and result["data"]["result"], t(
                "smoke.error.panel_empty", title=panel["title"]
            )
    print(t("smoke.grafana_ok"))
    try:
        Lab(SETTINGS).evidence()
    except EvidenceUnavailable as exc:
        print(t("evidence.skipped", reason=exc))


if __name__ == "__main__":
    main()
