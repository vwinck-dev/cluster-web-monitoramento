"""Testes do ciclo de vida das VMs: comando QEMU, checagens de partida e desligamento."""

from unittest.mock import patch

from support import ROOT, TempDirTestCase

from src.config import load
from src.lab import Lab
from src.qemu import qemu_command
from src.shutdown import ShutdownHandler
from src.state import StateStore
from src.vm import VmController


class Fixed(ShutdownHandler):
    """Elo de teste que aceita (texto) ou recusa (None) e registra as chamadas."""

    def __init__(self, answer, successor=None):
        super().__init__(successor)
        self.answer = answer
        self.calls = []

    def attempt(self, name):
        self.calls.append(name)
        return self.answer


def no_qemu(*args):
    raise AssertionError("QEMU não deveria rodar")


class VmTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.settings = self.isolated_settings()
        self.store = StateStore(self.settings)
        self.store.ensure_root()
        self.settings.image.touch()

    def prepare_seeds(self, instance_id):
        for name in self.settings.nodes:
            self.store.seed_dir(name).mkdir()
            self.store.metadata(name).write_text(f"instance-id: {instance_id(name)}\n")
            self.store.seed_iso(name).touch()

    def test_qemu_command_uses_node_configuration(self):
        """O QEMU recebe identidade, NICs e forwards configurados."""
        settings = load(ROOT)
        command = qemu_command(settings, StateStore(settings), "web")
        self.assertEqual(
            command[:3],
            ["qemu-system-x86_64", "-name", "cluster-web-monitoramento-web"],
        )
        self.assertIn(
            "user,id=uplink,restrict=off,hostfwd=tcp:127.0.0.1:2221-:22,hostfwd=tcp:127.0.0.1:18080-:80",
            command,
        )
        self.assertIn("virtio-net-pci,netdev=cluster,mac=52:54:00:4c:06:10", command)

    def test_start_rejects_legacy_seed(self):
        """Uma nova identidade de NIC não sobe com o seed de outra instância."""
        self.prepare_seeds(lambda name: f"old-name-{name}")
        with self.assertRaisesRegex(SystemExit, "legados"):
            Lab(self.settings, no_qemu).start(["web"])

    def test_start_refuses_without_memory(self):
        """A checagem de RAM usa a sonda injetada e não chama o QEMU."""
        self.prepare_seeds(self.settings.instance_id)
        vms = VmController(
            self.settings, self.store, no_qemu, Fixed("ok"), memory_probe=lambda: 100
        )
        with self.assertRaisesRegex(SystemExit, "RAM insuficiente"):
            vms.start(list(self.settings.nodes))

    def test_stop_uses_injected_chain(self):
        """O controlador delega o desligamento à cadeia e espera o PID sumir."""
        chain = Fixed("ok")
        vms = VmController(self.settings, self.store, None, chain, sleep=lambda _: None)
        pids = iter([123, None])
        with patch.object(self.store, "pid", side_effect=lambda name: next(pids)):
            vms.stop(["web"])
        self.assertEqual(chain.calls, ["web"])

    def test_shutdown_chain_falls_back_and_stops_at_first_success(self):
        """Recusa passa ao próximo elo; aceite encerra a cadeia."""
        acpi = Fixed("acpi")
        self.assertEqual(Fixed(None, acpi).handle("web"), "acpi")
        self.assertEqual(acpi.calls, ["web"])
        unused = Fixed("acpi")
        self.assertEqual(Fixed("ssh", unused).handle("web"), "ssh")
        self.assertEqual(unused.calls, [])

    def test_shutdown_chain_exhausted_raises(self):
        with self.assertRaises(RuntimeError):
            Fixed(None).handle("web")
