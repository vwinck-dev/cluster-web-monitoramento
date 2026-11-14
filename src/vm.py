"""Ciclo de vida das VMs: partida, desligamento e estado."""

import time
from pathlib import Path

from .i18n import t
from .qemu import qemu_command


def available_mb():
    """Lê o MemAvailable do Linux em MiB para a checagem de segurança na partida."""
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return 0


class VmController:
    """Opera os processos QEMU; dependências externas entram pelo construtor."""

    def __init__(
        self,
        settings,
        store,
        runner,
        shutdown,
        memory_probe=available_mb,
        sleep=time.sleep,
    ):
        self.settings = settings
        self.store = store
        self.runner = runner
        self.shutdown = shutdown
        self.memory_probe = memory_probe
        self.sleep = sleep

    def start(self, names):
        """Inicia as VMs paradas após confirmar os artefatos e a memória disponível."""
        self._check_artifacts(names)
        pending = [name for name in names if not self.store.pid(name)]
        self._check_memory(pending)
        for name in pending:
            self.runner(*qemu_command(self.settings, self.store, name))
            print(
                t(
                    "vm.started",
                    name=name,
                    pid=self.store.pid(name),
                    port=self.settings.nodes[name].ssh_port,
                )
            )

    def _check_artifacts(self, names):
        if not self.settings.image.exists() or any(
            not self.store.seed_iso(name).exists() for name in names
        ):
            raise SystemExit(t("vm.error.not_prepared"))
        for name in names:
            if not self.store.has_identity(name):
                raise SystemExit(t("vm.error.legacy_seed", name=name))

    def _check_memory(self, pending):
        required = (
            sum(self.settings.nodes[name].ram_mb for name in pending)
            + self.settings.memory_reserve_mb
        )
        available = self.memory_probe()
        if pending and available < required:
            raise SystemExit(
                t("vm.error.memory", available=available, required=required)
            )

    def stop(self, names, attempts=30):
        """Pede desligamento limpo via SSH e, se falhar, recorre ao ACPI do QEMU."""
        for name in names:
            if not self.store.pid(name):
                print(t("vm.already_stopped", name=name))
                continue
            print(
                t("vm.shutdown_requested", name=name, method=self.shutdown.handle(name))
            )
            for _ in range(attempts):
                if not self.store.pid(name):
                    print(t("vm.stopped", name=name))
                    break
                self.sleep(1)
            else:
                print(t("vm.still_stopping", name=name))

    def status(self):
        """Mostra o estado do processo e os endereços de acesso de todos os nós."""
        for name, node in self.settings.nodes.items():
            current = self.store.pid(name)
            state = (
                t("vm.status.running", pid=current)
                if current
                else t("vm.status.stopped")
            )
            print(
                t(
                    "vm.status.line",
                    name=name,
                    state=state,
                    ip=node.ip,
                    port=node.ssh_port,
                )
            )
