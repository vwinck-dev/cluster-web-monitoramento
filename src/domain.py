"""Objetos de valor imutáveis que descrevem a topologia do laboratório."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Node:
    ip: str
    cluster_mac: str
    uplink_mac: str
    ram_mb: int
    ssh_port: int
    forwards: tuple[tuple[int, int], ...]
    disk_gb: int

    @property
    def host_ports(self):
        """Retorna todas as portas que este nó ocupa no host."""
        return [self.ssh_port, *(host for host, _ in self.forwards)]

    def host_port(self, guest_port):
        """Retorna a porta do host encaminhada para a porta da VM."""
        for host, guest in self.forwards:
            if guest == guest_port:
                return host
        raise KeyError(guest_port)


@dataclass(frozen=True)
class Settings:
    root: Path
    name: str
    guest_user: str
    bus: str
    cidr_prefix: int
    memory_reserve_mb: int
    image_url: str
    sha256s_url: str
    nodes: dict[str, Node]

    @property
    def state(self):
        """Retorna o diretório com os discos, seeds e segredos gerados."""
        return self.root / ".state"

    @property
    def image(self):
        """Retorna o nome do arquivo local da imagem base configurada."""
        return self.state / Path(self.image_url).name

    @property
    def guest_dir(self):
        """Retorna o diretório de instalação dentro das VMs."""
        return f"/opt/{self.name}"

    def instance_id(self, name):
        """Retorna a identidade cloud-init que amarra disco, seed e NICs."""
        return f"{self.name}-{name}"
