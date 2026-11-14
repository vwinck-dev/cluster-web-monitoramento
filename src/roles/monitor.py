"""Papel monitor: Prometheus, Grafana e o dashboard provisionado."""

from .base import Role, register


def prometheus_config(settings):
    """Preenche o template do Prometheus com os endereços dos nós configurados."""
    config = (settings.root / "config/prometheus.yml").read_text()
    targets = "\n".join(
        f"          - {node.ip}:9100" for node in settings.nodes.values()
    )
    return (
        config.replace("          - ${NODE_TARGETS}", targets)
        .replace("${WEB_IP}", settings.nodes["web"].ip)
        .replace("cluster: cluster-web-monitoramento", f"cluster: {settings.name}")
    )


@register("monitor")
class MonitorRole(Role):
    packages = ("prometheus", "gnupg", "wget")

    def files(self, ctx):
        settings = ctx.settings
        return [
            ctx.file("prometheus.yml", prometheus_config(settings)),
            ctx.asset("grafana-datasource.yml"),
            ctx.asset("grafana-dashboard-provider.yml"),
            ctx.asset(
                "dashboard.json",
                replacements=(("cluster-web-monitoramento", settings.name),),
            ),
            ctx.file(
                "grafana.env", f"GF_SECURITY_ADMIN_PASSWORD={ctx.password}\n", "0600"
            ),
            ctx.asset("install-monitor.sh", "0755"),
        ]

    def commands(self, ctx):
        return [f"{ctx.guest_dir}/install-monitor.sh"]
