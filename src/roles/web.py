"""Papel web: nginx, aplicação de carga e exporter de métricas HTTP."""

from .base import Role, register


@register("web")
class WebRole(Role):
    packages = ("nginx",)

    def files(self, ctx):
        return [
            ctx.asset("nginx-site.conf"),
            ctx.asset("cluster-log-format.conf"),
            ctx.asset("web-metrics.py", "0755"),
            ctx.asset("web-metrics.service"),
            ctx.asset("web-app.py", "0755"),
            ctx.asset("web-app.service"),
        ]

    def commands(self, ctx):
        directory = ctx.guest_dir
        return [
            f"cp {directory}/cluster-log-format.conf /etc/nginx/conf.d/cluster-log-format.conf",
            f"cp {directory}/nginx-site.conf /etc/nginx/sites-available/cluster",
            "rm -f /etc/nginx/sites-enabled/default",
            "ln -sf /etc/nginx/sites-available/cluster /etc/nginx/sites-enabled/cluster",
            f"cp {directory}/web-metrics.service /etc/systemd/system/web-metrics.service",
            f"cp {directory}/web-app.service /etc/systemd/system/web-app.service",
            "nginx -t",
            "systemctl daemon-reload",
            "systemctl enable --now nginx web-metrics web-app",
            "systemctl restart nginx",
        ]
