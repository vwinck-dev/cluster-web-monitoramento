# Política de segurança

## Como relatar uma vulnerabilidade

Não abra uma issue pública. Use o relato privado do GitHub: aba **Security** → **Report a vulnerability** neste repositório. A resposta inicial vem em até 7 dias.

## Escopo

Este é um laboratório acadêmico para rodar localmente. As VMs expõem serviços apenas em `127.0.0.1`, o SSH aceita somente chave pública e a senha do Grafana é gerada por máquina em `.state/`, que nunca é versionada. Relatos sobre esses limites, sobre o provisionamento (`src/`, `config/`) ou sobre a CI são bem-vindos.
