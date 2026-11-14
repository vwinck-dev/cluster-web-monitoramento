# Cluster Web Monitoramento

Este projeto cria **três máquinas virtuais (VMs)** no seu computador para mostrar, no Grafana, como uma carga de requisições afeta um servidor web. Você controla as VMs pela CLI `clusterctl.py`; não precisa configurar cada uma manualmente.

| VM | O que faz | IP entre as VMs | Acesso pelo seu computador |
| --- | --- | --- | --- |
| `web` | Servidor HTTP com nginx e exportador de métricas | `10.20.30.10` | Site: `http://127.0.0.1:18080`; SSH: porta `2221` |
| `client` | Envia requisições ao servidor para gerar carga | `10.20.30.20` | SSH: porta `2222` |
| `monitor` | Coleta as métricas com Prometheus e mostra gráficos no Grafana | `10.20.30.30` | Grafana: `http://127.0.0.1:3000`; Prometheus: `http://127.0.0.1:9090` |

**Como funciona:** as VMs se comunicam por uma rede virtual interna. O `client` chama o `web`; o Prometheus, no `monitor`, coleta as métricas; o Grafana apresenta os gráficos. Os serviços acessíveis pelo computador anfitrião escutam apenas em `127.0.0.1`.

## 1. Confira os pré-requisitos

Use um computador **Linux x86-64** com KVM habilitado. Instale os programas abaixo pelo gerenciador de pacotes da sua distribuição:

- Python **3.12 ou superior**;
- `qemu-system-x86_64` e `qemu-img`;
- `xorriso`, `curl` e `cloud-init`;
- cliente `ssh` e uma chave SSH pública.

Para conferir se os programas estão disponíveis:

```bash
python3 --version
qemu-system-x86_64 --version
qemu-img --version
xorriso -version
curl --version
cloud-init --version
```

Se ainda não tiver uma chave SSH pública, crie uma:

```bash
ssh-keygen -t ed25519
```

Aceite o caminho padrão (`~/.ssh/id_ed25519`). Se sua chave pública estiver em outro lugar, informe o caminho ao executar o preparo:

```bash
SSH_PUBLIC_KEY=/caminho/para/chave.pub python3 clusterctl.py prepare
```

A primeira preparação baixa a imagem oficial do Ubuntu Cloud e verifica seu SHA-256. Separe espaço em disco para a imagem e os discos diferenciais das VMs. Para ligar as três VMs ao mesmo tempo, deixe pelo menos **4,5 GiB de RAM disponíveis**. Os comandos de operação do lab não exigem `sudo`.

## 2. Prepare e ligue as VMs

Execute os comandos **na pasta do projeto**:

```bash
python3 clusterctl.py prepare
python3 clusterctl.py start
python3 clusterctl.py status
```

`prepare` cria a imagem base, os discos diferenciais e as ISOs de configuração. `start` liga as VMs. `status` mostra quais estão rodando e as portas SSH. No primeiro boot, as VMs ainda instalam pacotes: aguarde alguns minutos antes de abrir o dashboard. O cliente passa a enviar uma requisição leve a cada cinco segundos, para manter uma linha de base nos gráficos HTTP. Para acompanhar a instalação de uma VM, entre nela e execute `cloud-init status --wait`:

```bash
python3 clusterctl.py ssh web
cloud-init status --wait
exit
```

Repita com `client` ou `monitor` se necessário. Para ligar apenas uma VM, use, por exemplo, `python3 clusterctl.py start web`.

## 3. Abra o dashboard e gere carga

1. Abra o Grafana em **http://127.0.0.1:3000**.
2. Entre com usuário `admin`. A senha está no arquivo local `.state/grafana-password`; você pode lê-la com `cat .state/grafana-password`.
3. Abra o dashboard **Cluster Web Monitoramento**. Antes da carga, observe CPU, memória, rede, requisições, latência e disponibilidade.
4. Entre na VM cliente com `python3 clusterctl.py ssh client` e execute:

   ```bash
   sudo /opt/cluster-web-monitoramento/load.sh 20000 30
   ```

   `20000` é o total de requisições e `30` é o número de requisições simultâneas. Digite `exit` para voltar ao seu terminal.
5. Compare os gráficos durante e depois da carga. Em **http://127.0.0.1:9090/classic/targets**, confira se os quatro alvos do Prometheus aparecem como `UP`.

O exportador calcula as métricas HTTP usando os últimos **60 segundos** do log do nginx. O tráfego leve do cliente mantém os gráficos de requisições e latência preenchidos; o comando de carga produz um pico visível. Se uma carga muito curta quase não aparecer, repita o comando. O site do `web` também pode ser testado diretamente em **http://127.0.0.1:18080**.

Para verificar automaticamente o lab **com as três VMs ligadas e o primeiro boot concluído**, execute na pasta do projeto:

```bash
python3 -m scripts.smoke
```

Esse teste confere o cloud-init das três VMs, a comunicação HTTP pelo host e pelo cliente, os quatro alvos do Prometheus e as consultas dos seis painéis do Grafana, e no fim gera as evidências descritas abaixo, o que inclui uma carga de 10.000 requisições.

### Evidências

No fim do smoke test, o lab gera as evidências em `evidence/`. Também é possível gerá-las sozinhas com `python3 clusterctl.py evidence`. A pasta é recriada a cada execução e ignorada pelo Git. São três capturas:

| Arquivo | Conteúdo |
| --- | --- |
| `dashboard-linha-de-base.png` | Dashboard antes da carga, só com o tráfego leve do cliente. |
| `dashboard-sob-carga.png` | Dashboard depois de 10.000 requisições (30 simultâneas) enviadas pelo `client`, capturado quando o Prometheus já registrou a carga. |
| `prometheus-quatro-alvos.png` | Página de alvos do Prometheus com os quatro alvos. |

A captura usa Selenium com Firefox headless, uma dependência opcional:

```bash
python3 -m pip install -r requirements-evidence.txt
```

Sem Selenium ou Firefox, o smoke avisa e pula as evidências; o comando `evidence` falha com a mesma mensagem.

## 4. Desligue as VMs

```bash
python3 clusterctl.py stop
python3 clusterctl.py status
```

Você também pode desligar um nó específico com `python3 clusterctl.py stop web`.

## Configuração e arquivos

- [`cluster.json`](cluster.json): nome do cluster, usuário SSH, imagem, IPs, MACs, portas, RAM, disco e rede. Edite **antes** de `prepare`.
- [`clusterctl.py`](clusterctl.py): comandos `prepare`, `start`, `stop`, `status`, `ssh` e `evidence`.
- [`src/`](src/): leitura da configuração, download da imagem, geração do cloud-init e controle do QEMU (veja **Arquitetura** abaixo).
- [`config/`](config/): nginx, aplicação web, exportador, Prometheus, Grafana e dashboard que serão instalados nas VMs.
- `.state/`: arquivos gerados localmente, incluindo discos, logs e senha. Essa pasta é ignorada pelo Git.

Para usar outro arquivo de topologia sem alterar `cluster.json`, acrescente `--config caminho.json` **antes** da ação, por exemplo: `python3 clusterctl.py --config outro-cluster.json prepare`. Os papéis `web`, `client` e `monitor` são obrigatórios. Se mudar IPs ou portas, use os novos valores ao acessar os serviços.

### VMs preparadas antes da renomeação

Os discos antigos usam outra identidade e outros MACs. O projeto bloqueia o boot desses discos com a nova configuração para evitar uma VM sem rede. Para recriá-los:

1. Pare as VMs com `python3 clusterctl.py stop`.
2. Faça uma cópia de `.state/` **se quiser guardar dados antigos**.
3. Remova apenas os discos diferenciais `.state/*.qcow2`.
4. Execute `python3 clusterctl.py prepare` e depois `python3 clusterctl.py start`.

A preparação não apaga discos automaticamente. Mudanças feitas em `config/` depois do primeiro boot também exigem aplicar a configuração dentro da VM ou recriar seu disco diferencial.

## Arquitetura

O `clusterctl.py` só interpreta a linha de comando. O trabalho fica em `src/`, organizado em design patterns usados apenas onde eliminam ramificações ou facilitam testes:

| Módulo | Padrão | Responsabilidade |
| --- | --- | --- |
| `commands.py` | **Command** + registro | Cada ação da CLI (`prepare`, `start`, `stop`, `status`, `ssh`, `evidence`) é uma classe que valida seus argumentos e executa. |
| `lab.py` | **Facade** | `Lab` monta e conecta configuração, estado, preparo e VMs; a CLI só conversa com ele. |
| `roles/` | **Strategy** + registro | `WebRole`, `ClientRole` e `MonitorRole` definem pacotes, arquivos e comandos de cada VM. |
| `provision.py` | Esqueleto comum | Monta o cloud-init comum e delega a parte específica ao papel do nó. |
| `prepare.py` | **Template Method** | `Preparer.run()` fixa a ordem do preparo: ferramentas, chave, imagem, discos, seeds e ISOs. |
| `qemu.py` | **Builder** | `QemuCommandBuilder` monta o comando QEMU passo a passo. |
| `shutdown.py` | **Chain of Responsibility** | O desligamento tenta SSH e, se falhar, ACPI pelo monitor do QEMU. |
| `evidence.py` | **Template Method** + porta | `EvidenceCollector.run()` fixa a ordem das capturas: linha de base, carga, sob carga e alvos. O navegador entra pela porta `Browser`. |
| `browser.py` | **Adapter** | `SeleniumBrowser` implementa `Browser` com Selenium; é o único módulo que importa o Selenium. |
| `state.py` | **Repository** | `StateStore` concentra os caminhos e a leitura dos artefatos em `.state/`. |
| `config.py` | Regras de validação | `SettingsLoader` aplica regras independentes: IPs, MACs, capacidade e portas. |
| `runner.py` | Injeção de dependência | `CommandRunner` executa ferramentas externas; os testes trocam por funções falsas. |
| `domain.py` | Objetos de valor | `Node` e `Settings` imutáveis. |

**Mensagens:** todo texto que a CLI e o smoke test mostram ao usuário (prints, erros e textos do `--help`) fica em [`lang/pt_BR.json`](lang/pt_BR.json) e é lido por `src/i18n.py` com `t("chave", campo=valor)`. Para outro idioma, crie `lang/<idioma>.json` com as mesmas chaves e campos `{}` e rode com `CLUSTER_LANG=<idioma>`. Chaves ausentes voltam para pt_BR. `tests/test_i18n.py` falha se o código usar uma chave inexistente, se sobrar chave sem uso ou se outro idioma divergir nos campos. Os arquivos que rodam dentro das VMs (`config/*`) não usam o catálogo, porque são instalados sozinhos.

**Para adicionar um papel novo**, crie `src/roles/NOME.py` com uma classe `@register("NOME")` derivada de `Role`, importe o módulo em `roles/__init__.py` e acrescente o nó em `cluster.json`. **Para adicionar um comando**, crie em `commands.py` uma classe `@command("nome")` derivada de `Command`.

## Verificações antes de enviar código

O repositório usa **Ruff** para formato e análise de Python, **ShellCheck** para scripts shell, validação dos JSONs e testes automatizados. Instale Ruff e ShellCheck; se tiver `uv`, o script pode executar a versão fixada do Ruff por `uvx`. No Ubuntu, por exemplo:

```bash
sudo apt-get install shellcheck python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install ruff==0.17.5
```

Ative os Git hooks versionados **uma vez por clone**:

```bash
git config core.hooksPath .githooks
```

O hook `pre-commit` executa os linters e verifica espaços dos arquivos preparados para commit. O hook `pre-push` executa os testes. Para rodar tudo manualmente:

```bash
./scripts/lint.sh
python3 -m unittest discover -s tests -v
```

O [CI](.github/workflows/ci.yml) repete essas verificações em pushes e pull requests para `main` e `develop`.

## Se algo não funcionar

| Sintoma | O que verificar |
| --- | --- |
| `Comando ausente` | Instale o programa indicado na mensagem e rode `prepare` novamente. |
| `Chave SSH pública ausente` | Crie `~/.ssh/id_ed25519.pub` ou use `SSH_PUBLIC_KEY=/caminho/chave.pub`. |
| `RAM insuficiente` | Feche outros programas ou inicie menos VMs com `start web`, por exemplo. |
| `disco e seed legados detectados` | Siga os quatro passos de **VMs preparadas antes da renomeação**. |
| Grafana ainda não abre | Espere o primeiro boot; entre em `monitor` e rode `cloud-init status --wait`. |
| Algum serviço não iniciou | Consulte `.state/NOME.log` no host e `/var/log/cloud-init-output.log` dentro da VM. |
| Um alvo está `DOWN` no Prometheus | Confira se a VM correspondente está ligada com `python3 clusterctl.py status` e se terminou o cloud-init. |

## Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE).
