#!/bin/sh
# Executa as mesmas checagens estáticas localmente e na CI.
set -eu

cd "$(dirname "$0")/.."

run_ruff() {
    if command -v ruff >/dev/null 2>&1; then
        ruff "$@"
    elif [ -x .venv/bin/ruff ]; then
        .venv/bin/ruff "$@"
    elif command -v uvx >/dev/null 2>&1; then
        uvx --from ruff==0.17.5 ruff "$@"
    else
        echo 'Ruff ausente: instale ruff ou uv e tente novamente.' >&2
        exit 1
    fi
}

if ! command -v shellcheck >/dev/null 2>&1; then
    echo 'ShellCheck ausente: instale shellcheck e tente novamente.' >&2
    exit 1
fi

run_ruff format --check clusterctl.py src config/web-app.py config/web-metrics.py scripts/smoke.py tests
run_ruff check clusterctl.py src config/web-app.py config/web-metrics.py scripts/smoke.py tests
shellcheck -s sh config/install-monitor.sh scripts/lint.sh .githooks/pre-commit .githooks/pre-push
sh -n config/install-monitor.sh
python3 -m json.tool cluster.json >/dev/null
python3 -m json.tool config/dashboard.json >/dev/null
for catalog in lang/*.json; do
    python3 -m json.tool "$catalog" >/dev/null
done
