"""Testes de comportamento da verificação da imagem de VM baixada."""

import hashlib
from pathlib import Path
from unittest.mock import patch

from support import TempDirTestCase

from src.image import BaseImage


class ImageTests(TempDirTestCase):
    def setUp(self):
        """Usa um diretório de estado isolado para nunca tocar discos reais de VM."""
        super().setUp()
        self.settings = self.isolated_settings()
        self.settings.state.mkdir()
        self.good_data = b"verified Ubuntu image"
        checksum = hashlib.sha256(self.good_data).hexdigest()
        self.sums = f"{checksum} *{self.settings.image.name}\n".encode()

    def test_verified_cache_is_reused(self):
        """Uma imagem local que confere não deve ser baixada de novo."""
        self.settings.image.write_bytes(self.good_data)
        with patch("src.image.urllib.request.urlopen") as urlopen:
            urlopen.return_value.read.return_value = self.sums
            BaseImage(
                self.settings, lambda *args: self.fail("download não deveria rodar")
            ).ensure()
        self.assertEqual(self.settings.image.read_bytes(), self.good_data)

    def test_bad_download_cannot_replace_existing_image(self):
        """Um checksum divergente deve deixar o arquivo anterior intacto."""
        self.settings.image.write_bytes(b"previous image")

        def fake_download(*args):
            Path(args[args.index("--output") + 1]).write_bytes(b"corrupt download")

        with patch("src.image.urllib.request.urlopen") as urlopen:
            urlopen.return_value.read.return_value = self.sums
            with self.assertRaisesRegex(ValueError, "SHA256"):
                BaseImage(self.settings, fake_download).ensure()
        self.assertEqual(self.settings.image.read_bytes(), b"previous image")
        self.assertFalse(
            (self.settings.state / (self.settings.image.name + ".part")).exists()
        )
