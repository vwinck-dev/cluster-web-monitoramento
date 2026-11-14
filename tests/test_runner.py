"""Testes do ambiente usado para rodar as ferramentas do sistema."""

import unittest

from src.runner import host_env


class RunnerTests(unittest.TestCase):
    def test_active_venv_is_hidden_from_system_tools(self):
        """Com a venv ativa, o cloud-init acharia o python3 dela e não o do sistema."""
        env = host_env(
            {
                "VIRTUAL_ENV": "/proj/.venv",
                "PATH": "/proj/.venv/bin:/usr/bin",
                "HOME": "/h",
            }
        )
        self.assertEqual(env, {"PATH": "/usr/bin", "HOME": "/h"})

    def test_environment_without_venv_is_unchanged(self):
        environ = {"PATH": "/usr/local/bin:/usr/bin"}
        self.assertEqual(host_env(environ), environ)
