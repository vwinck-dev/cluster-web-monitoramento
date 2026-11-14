"""Papel client: gerador de carga sob demanda e tráfego de base contínuo."""

from .base import Role, register


@register("client")
class ClientRole(Role):
    packages = ("apache2-utils",)

    def files(self, ctx):
        settings = ctx.settings
        web_ip = settings.nodes["web"].ip
        return [
            ctx.file(
                "load.sh",
                '#!/bin/sh\nset -eu\nab -n "${1:-20000}" -c "${2:-30}" '
                f"http://{web_ip}/\n",
                "0755",
            ),
            ctx.asset(
                "client-baseline.service",
                replacements=(
                    ("${WEB_IP}", web_ip),
                    ("${GUEST_USER}", settings.guest_user),
                ),
            ),
        ]

    def commands(self, ctx):
        return [
            f"cp {ctx.guest_dir}/client-baseline.service /etc/systemd/system/client-baseline.service",
            "systemctl daemon-reload",
            "systemctl enable --now client-baseline",
        ]
