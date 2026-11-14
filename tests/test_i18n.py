"""Testes do catálogo de mensagens em lang/."""

import json
import re
import string
import unittest

from support import ROOT

SOURCES = [ROOT / "clusterctl.py", ROOT / "scripts/smoke.py", *ROOT.glob("src/**/*.py")]
KEY_CALL = re.compile(r'\bt\(\s*"([a-z0-9_.]+)"')


def load_catalog(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fields(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class I18nTests(unittest.TestCase):
    def setUp(self):
        """Lê o catálogo padrão e todas as chaves citadas no código."""
        self.catalog = load_catalog(ROOT / "lang/pt_BR.json")
        self.used = {
            key for source in SOURCES for key in KEY_CALL.findall(source.read_text())
        }

    def test_used_keys_match_catalog(self):
        """Chave ausente quebra em execução; chave órfã só confunde quem traduz."""
        self.assertEqual(self.used - self.catalog.keys(), set(), "ausentes")
        self.assertEqual(self.catalog.keys() - self.used, set(), "órfãs")

    def test_all_catalogs_share_keys_and_placeholders(self):
        """Outros idiomas precisam das mesmas chaves e dos mesmos campos {}."""
        for path in (ROOT / "lang").glob("*.json"):
            other = load_catalog(path)
            with self.subTest(lang=path.stem):
                self.assertEqual(other.keys(), self.catalog.keys())
                for key, text in self.catalog.items():
                    self.assertEqual(fields(other[key]), fields(text), key)
