"""Chain of Responsibility do desligamento: SSH primeiro, ACPI do QEMU depois."""

import socket
import subprocess

from .i18n import t


class ShutdownHandler:
    """Tenta desligar a VM; se não conseguir, passa o pedido adiante."""

    def __init__(self, successor=None):
        self.successor = successor

    def handle(self, name):
        """Retorna a mensagem do elo que aceitou o pedido."""
        message = self.attempt(name)
        if message is not None:
            return message
        if self.successor is None:
            raise RuntimeError(t("shutdown.error.exhausted", name=name))
        return self.successor.handle(name)

    def attempt(self, name):
        raise NotImplementedError


class SshShutdown(ShutdownHandler):
    """Pede um desligamento limpo ao sistema da VM."""

    def __init__(self, settings, successor=None):
        super().__init__(successor)
        self.settings = settings

    def attempt(self, name):
        node = self.settings.nodes[name]
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "StrictHostKeyChecking=accept-new",
                    "-o",
                    "ConnectTimeout=3",
                    "-p",
                    str(node.ssh_port),
                    f"{self.settings.guest_user}@127.0.0.1",
                    "sudo shutdown -h now",
                ],
                capture_output=True,
                check=False,
                timeout=8,
            )
        except subprocess.TimeoutExpired:
            return None
        return t("shutdown.ssh") if result.returncode == 0 else None


class AcpiShutdown(ShutdownHandler):
    """Envia system_powerdown pelo socket de monitor do QEMU."""

    def __init__(self, store, successor=None):
        super().__init__(successor)
        self.store = store

    def attempt(self, name):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as monitor:
            monitor.settimeout(5)
            monitor.connect(str(self.store.monitor_socket(name)))
            monitor.sendall(b"system_powerdown\n")
        return t("shutdown.acpi")


def default_chain(settings, store):
    """Monta a cadeia padrão usada por clusterctl.py stop."""
    return SshShutdown(settings, AcpiShutdown(store))
