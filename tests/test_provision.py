"""Testes dos payloads do cloud-init e do Prometheus gerados a partir da topologia."""

from support import KEY, ROOT, TempDirTestCase

from src.config import load
from src.provision import cloud_config, network_config
from src.roles import ROLES, prometheus_config


class ProvisionTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.settings = load(ROOT)

    def test_common_skeleton_precedes_role(self):
        """Identidade e pacotes/comandos comuns vêm antes dos específicos do papel."""
        config = cloud_config(self.settings, "web", KEY, "secret")
        self.assertEqual(config["hostname"], "cluster-web-monitoramento-web")
        self.assertEqual(config["users"][0]["name"], "cluster")
        self.assertEqual(
            config["packages"],
            [
                "openssh-server",
                "prometheus-node-exporter",
                "curl",
                *ROLES["web"].packages,
            ],
        )
        self.assertEqual(
            config["runcmd"][0], "systemctl enable --now ssh prometheus-node-exporter"
        )

    def test_unknown_role_is_rejected(self):
        """Um nó sem estratégia registrada não gera cloud-init pela metade."""
        with self.assertRaisesRegex(ValueError, "Nó desconhecido"):
            cloud_config(self.settings, "database", KEY, "secret")

    def test_network_pins_cluster_ip(self):
        network = network_config(self.settings, "web")
        self.assertEqual(
            network["ethernets"]["cluster"]["addresses"], ["10.20.30.10/24"]
        )

    def test_client_provisions_continuous_baseline_requests(self):
        """Mantém os gráficos HTTP com dados entre as execuções manuais de carga."""
        client = cloud_config(self.settings, "client", KEY, "secret")
        files = {entry["path"]: entry["content"] for entry in client["write_files"]}
        service = files["/opt/cluster-web-monitoramento/client-baseline.service"]
        self.assertIn("systemctl enable --now client-baseline", client["runcmd"])
        self.assertIn(self.settings.nodes["web"].ip, service)

    def test_changed_web_ip_reaches_guest_and_prometheus(self):
        """Gerador de carga e alvos de scrape acompanham o IP editado."""

        def move_web(data):
            data["nodes"]["web"]["ip"] = "10.20.30.44"

        settings = self.edited_settings(move_web)
        client = cloud_config(settings, "client", KEY, "secret")
        self.assertIn("http://10.20.30.44/", client["write_files"][0]["content"])
        prometheus = prometheus_config(settings)
        self.assertIn("10.20.30.44:9113", prometheus)
        self.assertIn("10.20.30.44:9100", prometheus)
