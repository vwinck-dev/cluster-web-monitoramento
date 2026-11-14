"""Command: cada ação da CLI valida seus argumentos e delega à Facade."""

from .i18n import t

COMMANDS = {}


def command(name):
    """Registra o comando sob o nome usado na linha de comando."""

    def decorator(cls):
        COMMANDS[name] = cls()
        return cls

    return decorator


class Command:
    """Contrato de uma ação: validar os nós pedidos e então executar."""

    def validate(self, nodes, error):
        """Recebe os nós digitados e a função de erro do argparse."""

    def execute(self, lab, names):
        raise NotImplementedError

    def run(self, lab, nodes, error):
        self.validate(nodes, error)
        self.execute(lab, nodes or lab.node_names)


@command("prepare")
class PrepareCommand(Command):
    def validate(self, nodes, error):
        if nodes:
            error(t("cli.error.prepare_takes_no_nodes"))

    def execute(self, lab, names):
        lab.prepare()


@command("start")
class StartCommand(Command):
    def execute(self, lab, names):
        lab.start(names)


@command("stop")
class StopCommand(Command):
    def execute(self, lab, names):
        lab.stop(names)


@command("status")
class StatusCommand(Command):
    def execute(self, lab, names):
        lab.status()


@command("ssh")
class SshCommand(Command):
    def validate(self, nodes, error):
        if len(nodes) != 1:
            error(t("cli.error.ssh_needs_one_node"))

    def execute(self, lab, names):
        lab.ssh(names[0])


@command("evidence")
class EvidenceCommand(Command):
    def validate(self, nodes, error):
        if nodes:
            error(t("cli.error.evidence_takes_no_nodes"))

    def execute(self, lab, names):
        lab.evidence()
