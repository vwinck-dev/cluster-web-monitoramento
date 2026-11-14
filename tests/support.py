"""Fixtures compartilhados: topologia do repositório, cópias editadas e estado isolado."""

import json
import tempfile
import unittest
from pathlib import Path

from src.config import load

ROOT = Path(__file__).resolve().parents[1]
KEY = "ssh-ed25519 example"


class TempDirTestCase(unittest.TestCase):
    """Dá a cada teste um diretório temporário removido ao final."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)

    def isolated_settings(self):
        """Topologia do repositório com .state no diretório temporário."""
        return load(self.tmp, ROOT / "cluster.json")

    def edited_settings(self, edit):
        """Topologia lida de uma cópia do cluster.json alterada por edit(data)."""
        data = json.loads((ROOT / "cluster.json").read_text())
        edit(data)
        path = self.tmp / "cluster.json"
        path.write_text(json.dumps(data))
        return load(ROOT, path)
