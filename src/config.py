"""Leitura do cluster.json e validação da topologia por regras independentes."""

import ipaddress
import json
import re
from pathlib import Path

from .domain import Node, Settings
from .i18n import t
from .roles import ROLES


class NodeRule:
    """Regra aplicada a cada nó; guarda o que já viu para detectar conflitos."""

    def check(self, name, node, network):
        raise NotImplementedError


class AddressInNetwork(NodeRule):
    def check(self, name, node, network):
        ipaddress.ip_interface(f"{node.ip}/{network['cidr_prefix']}")


class UniqueAddresses(NodeRule):
    def __init__(self):
        self.addresses = set()
        self.macs = set()

    def check(self, name, node, network):
        if (
            node.ip in self.addresses
            or node.cluster_mac in self.macs
            or node.uplink_mac in self.macs
        ):
            raise ValueError(t("config.error.duplicate_address", name=name))
        self.addresses.add(node.ip)
        self.macs.update((node.cluster_mac, node.uplink_mac))


class PositiveCapacity(NodeRule):
    def check(self, name, node, network):
        if node.ram_mb <= 0 or node.disk_gb <= 0:
            raise ValueError(t("config.error.capacity", name=name))


class UniqueHostPorts(NodeRule):
    def __init__(self):
        self.ports = set()

    def check(self, name, node, network):
        for port in node.host_ports:
            if not 1 <= port <= 65535 or port in self.ports:
                raise ValueError(t("config.error.port", port=port))
            self.ports.add(port)


def default_rules():
    """Cria regras novas a cada leitura, já que algumas acumulam estado."""
    return [
        AddressInNetwork(),
        UniqueAddresses(),
        PositiveCapacity(),
        UniqueHostPorts(),
    ]


class SettingsLoader:
    """Converte o JSON em Settings, aplicando as regras na ordem configurada."""

    def __init__(self, rules_factory=default_rules):
        self.rules_factory = rules_factory

    def load(self, root: Path, config_path: Path | None = None) -> Settings:
        data = json.loads((config_path or root / "cluster.json").read_text())
        self._check_identity(data)
        network = data["network"]
        rules = self.rules_factory()
        nodes = {}
        for name, raw in data["nodes"].items():
            node = self._node(raw)
            for rule in rules:
                rule.check(name, node, network)
            nodes[name] = node
        if not ROLES.keys() <= nodes.keys():
            raise ValueError(t("config.error.required_roles"))
        return Settings(
            root,
            data["name"],
            data["guest_user"],
            network["bus"],
            network["cidr_prefix"],
            network["memory_reserve_mb"],
            data["image"]["url"],
            data["image"]["sha256s_url"],
            nodes,
        )

    @staticmethod
    def _check_identity(data):
        if not re.fullmatch(r"[a-z][a-z0-9-]*", data["name"]):
            raise ValueError(t("config.error.cluster_name"))
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", data["guest_user"]):
            raise ValueError(t("config.error.guest_user"))

    @staticmethod
    def _node(raw):
        return Node(
            raw["ip"],
            raw["cluster_mac"],
            raw["uplink_mac"],
            raw["ram_mb"],
            raw["ssh_port"],
            tuple(map(tuple, raw["forwards"])),
            raw["disk_gb"],
        )


def load(root: Path, config_path: Path | None = None) -> Settings:
    """Atalho para o carregador padrão."""
    return SettingsLoader().load(root, config_path)
