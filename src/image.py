"""Baixa e verifica a imagem base do Ubuntu."""

import hashlib
import urllib.request
from pathlib import Path

from .i18n import t


def digest(path: Path):
    """Calcula o SHA-256 sem carregar a imagem inteira na memória."""
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


class BaseImage:
    """Garante que a imagem local é a publicada, sem nunca trocá-la por um download ruim."""

    def __init__(self, settings, runner):
        self.settings = settings
        self.runner = runner
        self.path = settings.image

    def expected_digest(self):
        """Busca o SHA-256 oficial da imagem no SHA256SUMS publicado."""
        sums = (
            urllib.request.urlopen(self.settings.sha256s_url, timeout=60)
            .read()
            .decode()
        )
        for line in sums.splitlines():
            fields = line.split()
            if fields and fields[-1].removeprefix("*") == self.path.name:
                return fields[0]
        raise ValueError(t("image.error.missing_checksum", image=self.path.name))

    def ensure(self):
        """Reaproveita uma imagem verificada ou baixa e verifica uma nova."""
        expected = self.expected_digest()
        if not (self.path.exists() and digest(self.path) == expected):
            self._download(expected)
        print(t("image.verified", path=self.path))

    def _download(self, expected):
        part = self.path.with_name(self.path.name + ".part")
        self.runner(
            "curl",
            "--fail",
            "--location",
            "--retry",
            "3",
            "--output",
            str(part),
            self.settings.image_url,
        )
        if digest(part) != expected:
            part.unlink(missing_ok=True)
            raise ValueError(t("image.error.checksum_mismatch"))
        part.replace(self.path)
