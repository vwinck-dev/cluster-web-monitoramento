"""Repository dos artefatos gerados em .state: discos, seeds, PIDs e segredos."""

import os
import secrets


class StateStore:
    """Centraliza onde cada artefato de cada nó mora e como é lido."""

    def __init__(self, settings):
        self.settings = settings
        self.root = settings.state

    def disk(self, name):
        return self.root / f"{name}.qcow2"

    def seed_dir(self, name):
        return self.root / f"seed-{name}"

    def metadata(self, name):
        return self.seed_dir(name) / "meta-data"

    def seed_iso(self, name):
        return self.root / f"{name}-seed.iso"

    def pid_file(self, name):
        return self.root / f"{name}.pid"

    def serial_log(self, name):
        return self.root / f"{name}.log"

    def monitor_socket(self, name):
        return self.root / f"{name}.monitor.sock"

    @property
    def password_file(self):
        return self.root / "grafana-password"

    def ensure_root(self):
        """Cria .state com permissão restrita ao usuário."""
        self.root.mkdir(exist_ok=True)
        self.root.chmod(0o700)

    def grafana_password(self):
        """Lê a senha do Grafana, gerando-a só na primeira vez."""
        if not self.password_file.exists():
            self.password_file.write_text(secrets.token_urlsafe(18) + "\n")
        self.password_file.chmod(0o600)
        return self.password_file.read_text().strip()

    def pid(self, name):
        """Retorna o PID da VM ativa, ou None se o arquivo de PID faltar ou estiver obsoleto."""
        try:
            number = int(self.pid_file(name).read_text())
            os.kill(number, 0)
            return number
        except (FileNotFoundError, ValueError, ProcessLookupError):
            return None

    def has_identity(self, name):
        """Indica se o seed existente foi gerado para a identidade atual do nó."""
        metadata = self.metadata(name)
        return (
            metadata.exists()
            and f"instance-id: {self.settings.instance_id(name)}"
            in metadata.read_text()
        )

    def is_legacy(self, name):
        """Detecta um seed existente de outra identidade (antes da renomeação)."""
        return self.metadata(name).exists() and not self.has_identity(name)
