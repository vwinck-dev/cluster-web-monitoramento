"""Testes da topologia em cluster.json e dos arquivos estáticos de config/."""

import json

from support import ROOT, TempDirTestCase


class ConfigTests(TempDirTestCase):
    def test_duplicate_port_is_rejected(self):
        """Rejeita uma topologia editada inválida antes de iniciar qualquer VM."""

        def collide(data):
            data["nodes"]["client"]["ssh_port"] = data["nodes"]["web"]["ssh_port"]

        with self.assertRaisesRegex(ValueError, "Porta"):
            self.edited_settings(collide)

    def test_dashboard_queries_have_balanced_delimiters(self):
        """Detecta expressões de painel quebradas antes de o Grafana renderizá-las."""
        dashboard = json.loads((ROOT / "config/dashboard.json").read_text())
        for panel in dashboard["panels"]:
            for target in panel.get("targets", []):
                expression = target["expr"]
                for opening, closing in ("{}", "()", "[]"):
                    with self.subTest(panel=panel["title"], delimiter=opening):
                        self.assertEqual(
                            expression.count(opening), expression.count(closing)
                        )
