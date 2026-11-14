"""Adapter: implementa a porta Browser de evidence.py com Selenium e Firefox headless.

Módulo separado para que só a coleta de evidências exija o Selenium
(requirements-evidence.txt); o resto do lab e os testes não dependem dele.
"""

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from .evidence import EvidenceUnavailable
from .i18n import t

WINDOW = (1600, 1000)
TIMEOUT = 60
# Cada painel de série temporal do Grafana desenha um gráfico uPlot (.uplot).
CHART = ".uplot"


class SeleniumBrowser:
    """Firefox headless controlado pelo Selenium."""

    def __init__(self):
        options = Options()
        options.add_argument("-headless")
        try:
            self.driver = webdriver.Firefox(options=options)
        except WebDriverException as exc:  # Firefox ou geckodriver ausente
            raise EvidenceUnavailable(t("evidence.error.unavailable")) from exc
        self.driver.set_window_size(*WINDOW)

    def _wait(self, condition):
        WebDriverWait(self.driver, TIMEOUT).until(condition)

    def login(self, base_url, user, password):
        """Entra pelo formulário: o Firefox não envia credenciais embutidas na URL."""
        self.driver.get(f"{base_url}/login")
        self._wait(lambda d: d.find_elements(By.NAME, "user"))
        self.driver.find_element(By.NAME, "user").send_keys(user)
        self.driver.find_element(By.NAME, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        self._wait(lambda d: "/login" not in d.current_url)

    def open(self, url):
        self.driver.get(url)

    def wait_for_charts(self, count):
        """Espera os painéis desenharem: o load da página vem antes dos dados."""
        self._wait(lambda d: len(d.find_elements(By.CSS_SELECTOR, CHART)) >= count)

    def screenshot(self, path):
        self.driver.save_screenshot(str(path))

    def close(self):
        self.driver.quit()
