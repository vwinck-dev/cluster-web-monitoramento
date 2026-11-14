"""Papéis de VM; importar os módulos registra cada estratégia em ROLES."""

from . import client, monitor, web  # noqa: F401
from .base import ROLES, ProvisionContext
from .monitor import prometheus_config

__all__ = ["ROLES", "ProvisionContext", "prometheus_config"]
