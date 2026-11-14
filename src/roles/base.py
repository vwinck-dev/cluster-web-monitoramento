"""Contrato dos papéis de VM e registro que os associa ao nome do nó."""

from dataclasses import dataclass

DEFAULT_GUEST_DIR = "/opt/cluster-web-monitoramento"

ROLES = {}


def register(name):
    """Registra uma estratégia de papel sob o nome do nó que ela provisiona."""

    def decorator(cls):
        ROLES[name] = cls()
        return cls

    return decorator


def file_entry(path, content, permissions="0644"):
    """Monta uma entrada write_files do cloud-init com permissões explícitas."""
    return {"path": path, "content": content, "permissions": permissions}


@dataclass(frozen=True)
class ProvisionContext:
    """O que um papel precisa saber para gerar seus arquivos e comandos."""

    settings: object
    password: str

    @property
    def guest_dir(self):
        return self.settings.guest_dir

    def file(self, filename, content, permissions="0644"):
        """Cria um arquivo gerado no diretório de instalação da VM."""
        return file_entry(f"{self.guest_dir}/{filename}", content, permissions)

    def asset(self, filename, permissions="0644", replacements=()):
        """Carrega um arquivo da VM a partir de config/ e define seu caminho de instalação."""
        content = (self.settings.root / "config" / filename).read_text()
        content = content.replace(DEFAULT_GUEST_DIR, self.guest_dir)
        for old, new in replacements:
            content = content.replace(old, new)
        return self.file(filename, content, permissions)


class Role:
    """Estratégia de provisionamento de um tipo de VM."""

    packages: tuple[str, ...] = ()

    def files(self, ctx):
        return []

    def commands(self, ctx):
        return []
