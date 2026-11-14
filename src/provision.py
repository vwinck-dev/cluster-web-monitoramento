"""Payloads do cloud-init: esqueleto comum mais a estratégia do papel do nó."""

from .i18n import t
from .roles import ROLES, ProvisionContext

BASE_PACKAGES = ("openssh-server", "prometheus-node-exporter", "curl")
BASE_COMMANDS = ("systemctl enable --now ssh prometheus-node-exporter",)


def role_for(name):
    """Resolve a estratégia registrada para o nó, rejeitando nomes sem papel."""
    try:
        return ROLES[name]
    except KeyError:
        raise ValueError(t("provision.error.unknown_node", name=name)) from None


def meta_data(settings, name):
    """Gera o meta-data que fixa a identidade da instância."""
    instance = settings.instance_id(name)
    return f"instance-id: {instance}\nlocal-hostname: {instance}\n"


def network_config(settings, name):
    """Mapeia cada NIC pelo MAC para a ordem das interfaces não alterar o IP."""
    node = settings.nodes[name]
    return {
        "version": 2,
        "ethernets": {
            "uplink": {
                "match": {"macaddress": node.uplink_mac},
                "dhcp4": True,
                "dhcp6": False,
            },
            "cluster": {
                "match": {"macaddress": node.cluster_mac},
                "addresses": [f"{node.ip}/{settings.cidr_prefix}"],
                "dhcp4": False,
                "dhcp6": False,
            },
        },
    }


def cloud_config(settings, name, key, password):
    """Monta as configurações comuns do cloud-init mais o papel da VM escolhida."""
    role = role_for(name)
    ctx = ProvisionContext(settings, password)
    return {
        "hostname": settings.instance_id(name),
        "manage_etc_hosts": True,
        "users": [
            {
                "name": settings.guest_user,
                "groups": "sudo",
                "sudo": "ALL=(ALL) NOPASSWD:ALL",
                "shell": "/bin/bash",
                "ssh_authorized_keys": [key],
            }
        ],
        "ssh_pwauth": False,
        "disable_root": True,
        "package_update": True,
        "packages": [*BASE_PACKAGES, *role.packages],
        "write_files": role.files(ctx),
        "runcmd": [*BASE_COMMANDS, *role.commands(ctx)],
        "final_message": t("provision.final_message", cluster=settings.name, name=name),
    }
