"""Builder do comando QEMU, para cada parte da VM ser montada em um passo nomeado."""


class QemuCommandBuilder:
    """Acumula os argumentos do qemu-system-x86_64 em uma interface fluente."""

    def __init__(self, binary="qemu-system-x86_64"):
        self.args = [binary]

    def _add(self, *args):
        self.args.extend(args)
        return self

    def name(self, value):
        return self._add("-name", value)

    def kvm(self, machine="q35", cpu="host", smp=2):
        return self._add(
            "-enable-kvm", "-machine", machine, "-cpu", cpu, "-smp", str(smp)
        )

    def memory(self, mb):
        return self._add("-m", str(mb))

    def headless(self, pid_file):
        return self._add("-display", "none", "-daemonize", "-pidfile", str(pid_file))

    def serial_log(self, path):
        return self._add("-serial", f"file:{path}")

    def monitor_socket(self, path):
        return self._add("-monitor", f"unix:{path},server,nowait")

    def disk(self, path):
        return self._add("-drive", f"file={path},if=virtio,format=qcow2")

    def cdrom(self, path):
        return self._add("-drive", f"file={path},media=cdrom,readonly=on")

    def user_network(self, netdev_id, mac, forwards):
        netdev = f"user,id={netdev_id},restrict=off" + "".join(
            f",hostfwd=tcp:127.0.0.1:{host}-:{guest}" for host, guest in forwards
        )
        return self._add("-netdev", netdev)._nic(netdev_id, mac)

    def multicast_network(self, netdev_id, mac, bus):
        return self._add(
            "-netdev", f"socket,id={netdev_id},mcast={bus},localaddr=127.0.0.1"
        )._nic(netdev_id, mac)

    def _nic(self, netdev_id, mac):
        return self._add("-device", f"virtio-net-pci,netdev={netdev_id},mac={mac}")

    def build(self):
        return list(self.args)


def qemu_command(settings, store, name):
    """Monta o comando de uma VM inteiramente a partir da topologia configurada."""
    node = settings.nodes[name]
    return (
        QemuCommandBuilder()
        .name(settings.instance_id(name))
        .kvm()
        .memory(node.ram_mb)
        .headless(store.pid_file(name))
        .serial_log(store.serial_log(name))
        .monitor_socket(store.monitor_socket(name))
        .disk(store.disk(name))
        .cdrom(store.seed_iso(name))
        .user_network("uplink", node.uplink_mac, [(node.ssh_port, 22), *node.forwards])
        .multicast_network("cluster", node.cluster_mac, settings.bus)
        .build()
    )
