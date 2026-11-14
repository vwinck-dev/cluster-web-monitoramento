"""Facade: um único ponto de entrada que monta e liga os componentes do laboratório."""

import os
from pathlib import Path

from .config import load
from .evidence import LOAD_CONCURRENCY, LOAD_REQUESTS, EvidenceCollector, open_browser
from .prepare import Preparer
from .runner import SubprocessRunner
from .shutdown import default_chain
from .state import StateStore
from .vm import VmController


class Lab:
    """Esconde da CLI como configuração, estado, QEMU e cloud-init se conectam."""

    def __init__(self, settings, runner=None):
        self.settings = settings
        self.runner = runner or SubprocessRunner()
        self.store = StateStore(settings)
        self.vms = VmController(
            settings, self.store, self.runner, default_chain(settings, self.store)
        )

    @classmethod
    def from_config(cls, root: Path, config_path: Path | None = None):
        return cls(load(root, config_path))

    @property
    def node_names(self):
        return list(self.settings.nodes)

    def prepare(self):
        Preparer(self.settings, self.store, self.runner).run()

    def start(self, names):
        self.vms.start(names)

    def stop(self, names):
        self.vms.stop(names)

    def status(self):
        self.vms.status()

    def ssh_argv(self, name, batch=False):
        """Monta o comando ssh para um nó; batch recusa prompts, para uso não interativo."""
        return [
            "ssh",
            *(["-o", "BatchMode=yes"] if batch else []),
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-p",
            str(self.settings.nodes[name].ssh_port),
            f"{self.settings.guest_user}@127.0.0.1",
        ]

    def ssh(self, name):
        """Substitui o processo atual pela sessão SSH no nó."""
        argv = self.ssh_argv(name)
        os.execvp(argv[0], argv)

    def evidence(self, browser=None):
        """Gera em evidence/ as capturas antes e durante a carga e dos alvos."""
        load_argv = [
            *self.ssh_argv("client", batch=True),
            "sudo",
            f"{self.settings.guest_dir}/load.sh",
            str(LOAD_REQUESTS),
            str(LOAD_CONCURRENCY),
        ]
        return EvidenceCollector(
            self.settings,
            browser or open_browser(),
            self.runner,
            load_argv,
            self.store.grafana_password(),
        ).run()
