"""Cria a imagem base, os discos overlay e as ISOs seed do cloud-init."""

import json
import os
import shutil
from pathlib import Path

from .i18n import t
from .image import BaseImage
from .provision import cloud_config, meta_data, network_config

REQUIRED_TOOLS = ("qemu-system-x86_64", "qemu-img", "xorriso", "curl", "cloud-init")
SEED_PARTS = ("user-data", "meta-data", "network-config")


def public_key():
    """Lê a chave SSH que o cloud-init vai autorizar dentro de cada VM."""
    override = os.environ.get("SSH_PUBLIC_KEY")
    candidates = (
        [Path(override).expanduser()]
        if override
        else [Path.home() / ".ssh/id_ed25519.pub", Path.home() / ".ssh/id_rsa.pub"]
    )
    for candidate in candidates:
        if candidate.is_file():
            key = candidate.read_text().strip()
            if key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
                return key
    raise SystemExit(t("prepare.error.missing_key"))


class Preparer:
    """Template Method: run() fixa a ordem dos passos de preparação."""

    def __init__(self, settings, store, runner):
        self.settings = settings
        self.store = store
        self.runner = runner
        self.image = BaseImage(settings, runner)

    def run(self):
        """Gera todos os artefatos, preservando discos overlay e senha existentes."""
        self.check_tools()
        key = public_key()
        self.check_legacy_disks()
        self.store.ensure_root()
        password = self.store.grafana_password()
        self.image.ensure()
        for name, node in self.settings.nodes.items():
            self.create_disk(name, node)
            self.write_seed(name, key, password)
            self.build_iso(name)
        print(t("prepare.done", path=self.store.root))

    def check_tools(self):
        for command in REQUIRED_TOOLS:
            if not shutil.which(command):
                raise SystemExit(t("prepare.error.missing_tool", command=command))

    def check_legacy_disks(self):
        for name in self.settings.nodes:
            disk = self.store.disk(name)
            if disk.exists() and self.store.is_legacy(name):
                raise SystemExit(t("prepare.error.legacy_disk", disk=disk))

    def create_disk(self, name, node):
        disk = self.store.disk(name)
        if disk.exists():
            return
        self.runner(
            "qemu-img",
            "create",
            "-f",
            "qcow2",
            "-F",
            "qcow2",
            "-b",
            str(self.settings.image),
            str(disk),
            f"{node.disk_gb}G",
        )

    def write_seed(self, name, key, password):
        seed = self.store.seed_dir(name)
        seed.mkdir(exist_ok=True)
        seed.chmod(0o700)
        (seed / "meta-data").write_text(meta_data(self.settings, name))
        config = cloud_config(self.settings, name, key, password)
        (seed / "user-data").write_text(
            "#cloud-config\n" + json.dumps(config, indent=2) + "\n"
        )
        (seed / "network-config").write_text(
            json.dumps(network_config(self.settings, name), indent=2) + "\n"
        )
        self.runner("cloud-init", "schema", "--config-file", str(seed / "user-data"))

    def build_iso(self, name):
        seed = self.store.seed_dir(name)
        iso = self.store.seed_iso(name)
        self.runner(
            "xorriso",
            "-as",
            "mkisofs",
            "-quiet",
            "-volid",
            "cidata",
            "-joliet",
            "-rock",
            "-output",
            str(iso),
            *(str(seed / part) for part in SEED_PARTS),
        )
        iso.chmod(0o600)
