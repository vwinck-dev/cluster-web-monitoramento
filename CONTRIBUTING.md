# Como contribuir

1. Crie um branch a partir de `main` com um nome curto (`fix/porta-grafana`, `feat/papel-db`).
2. Ative os hooks uma vez por clone: `git config core.hooksPath .githooks`.
3. Antes de abrir o pull request, rode:

   ```bash
   ./scripts/lint.sh
   python3 -m unittest discover -s tests -v
   ```

4. Abra o pull request para `main` e descreva o que mudou e como você testou. A CI precisa passar.

Mensagens exibidas ao usuário vão em `lang/pt_BR.json`, nunca direto no código (veja a seção **Mensagens** do README). Para mudanças nas VMs, teste com `python3 -m scripts.smoke` se puder ligar o lab.

Vulnerabilidades não entram como issue: siga o [`SECURITY.md`](SECURITY.md).
