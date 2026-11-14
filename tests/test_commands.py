"""Testes da validação de argumentos de cada comando da CLI."""

import unittest

from src.commands import COMMANDS


class CommandTests(unittest.TestCase):
    def test_invalid_node_arguments_are_reported(self):
        """Cada comando recusa os próprios argumentos inválidos via parser.error."""
        cases = {
            ("ssh", ()): 1,
            ("ssh", ("web",)): 0,
            ("prepare", ("web",)): 1,
            ("evidence", ("web",)): 1,
            ("start", ("web", "client")): 0,
        }
        for (name, nodes), expected in cases.items():
            errors = []
            COMMANDS[name].validate(list(nodes), errors.append)
            with self.subTest(command=name, nodes=nodes):
                self.assertEqual(len(errors), expected)
