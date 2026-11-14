#!/usr/bin/env python3
"""Prepara e opera as VMs do monitoramento de cluster web sem privilégios de root."""

import argparse
from pathlib import Path

from src.commands import COMMANDS
from src.i18n import t
from src.lab import Lab


def main():
    """Interpreta a CLI e delega a ação ao comando registrado."""
    parser = argparse.ArgumentParser(description=t("cli.description"))
    parser.add_argument("--config", type=Path, help=t("cli.help.config"))
    parser.add_argument("action", choices=tuple(COMMANDS))
    parser.add_argument("nodes", nargs="*", help=t("cli.help.nodes"))
    args = parser.parse_args()
    lab = Lab.from_config(Path(__file__).resolve().parent, args.config)
    invalid = set(args.nodes) - set(lab.node_names)
    if invalid:
        parser.error(t("cli.error.unknown_nodes", nodes=", ".join(sorted(invalid))))
    COMMANDS[args.action].run(lab, args.nodes, parser.error)


if __name__ == "__main__":
    main()
