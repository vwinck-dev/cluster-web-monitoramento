"""Executor de ferramentas externas, injetado para os testes trocarem."""

import os
import subprocess
from pathlib import Path

from .i18n import t


def host_env(environ=os.environ):
    """Ambiente sem a venv ativa.

    Ferramentas do sistema com shebang "#!/usr/bin/env python3", como o
    cloud-init, achariam o Python da venv, que não enxerga os pacotes do
    sistema, e falhariam com ModuleNotFoundError.
    """
    env = dict(environ)
    venv = env.pop("VIRTUAL_ENV", None)
    if venv:
        venv_bin = Path(venv) / "bin"
        env["PATH"] = os.pathsep.join(
            entry
            for entry in env.get("PATH", "").split(os.pathsep)
            if entry and Path(entry) != venv_bin
        )
    return env


class SubprocessRunner:
    """Mostra e executa o comando, parando imediatamente se ele falhar."""

    def __call__(self, *args):
        print(t("runner.trace", command=" ".join(map(str, args))), flush=True)
        subprocess.run(args, check=True, env=host_env())
