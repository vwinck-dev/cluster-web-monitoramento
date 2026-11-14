"""Mensagens para o usuário, lidas de lang/<idioma>.json."""

import json
import os
from functools import cache
from pathlib import Path

LANG_DIR = Path(__file__).resolve().parents[1] / "lang"
DEFAULT_LANG = "pt_BR"


@cache
def catalog(lang=DEFAULT_LANG):
    """Carrega o catálogo do idioma, caindo para pt_BR se ele não existir."""
    path = LANG_DIR / f"{lang}.json"
    if not path.is_file():
        path = LANG_DIR / f"{DEFAULT_LANG}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def current_lang():
    """Idioma escolhido por CLUSTER_LANG; pt_BR quando não definido."""
    return os.environ.get("CLUSTER_LANG", DEFAULT_LANG)


def t(key, **values):
    """Retorna a mensagem da chave com os valores substituídos."""
    messages = catalog(current_lang())
    template = messages.get(key) or catalog(DEFAULT_LANG)[key]
    return template.format(**values)
