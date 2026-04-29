#!/usr/bin/env bash
# Lethe coordinator startup — venv, deps, preflight, uvicorn.
# Run from repo root:  ./tools/start.sh
#
# Skips pip install if requirements.txt hasn't changed since the last run
# (uses .venv/.requirements.stamp). Pass --force-install to override.

set -euo pipefail

FORCE_INSTALL=false
SKIP_PREFLIGHT=false
STRICT=false
PORT=8000

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force-install) FORCE_INSTALL=true; shift ;;
        --skip-preflight) SKIP_PREFLIGHT=true; shift ;;
        --strict) STRICT=true; shift ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COORDINATOR="$REPO_ROOT/src/coordinator"
VENV="$COORDINATOR/.venv"
REQUIREMENTS="$COORDINATOR/requirements.txt"
STAMP="$VENV/.requirements.stamp"
PREFLIGHT="$REPO_ROOT/tools/preflight.py"

# Detect venv layout (Scripts/ on Windows-Python, bin/ on Unix)
if [[ -f "$VENV/Scripts/activate" ]]; then
    ACTIVATE="$VENV/Scripts/activate"
elif [[ -f "$VENV/bin/activate" ]]; then
    ACTIVATE="$VENV/bin/activate"
else
    ACTIVATE=""
fi

step() { printf "\033[36m==> %s\033[0m\n" "$1"; }
done_msg() { printf "    \033[2m%s\033[0m\n" "$1"; }

# 1. venv
step "Virtual environment"
if [[ -z "$ACTIVATE" ]]; then
    done_msg "creating $VENV"
    python -m venv "$VENV"
    if [[ -f "$VENV/Scripts/activate" ]]; then ACTIVATE="$VENV/Scripts/activate"
    else ACTIVATE="$VENV/bin/activate"; fi
else
    done_msg "exists"
fi
# shellcheck disable=SC1090
source "$ACTIVATE"

# 2. requirements
step "Dependencies"
needs_install=false
if [[ "$FORCE_INSTALL" == "true" ]] || [[ ! -f "$STAMP" ]] || [[ "$REQUIREMENTS" -nt "$STAMP" ]]; then
    needs_install=true
fi
if [[ "$needs_install" == "true" ]]; then
    done_msg "installing from $REQUIREMENTS"
    python -m pip install --disable-pip-version-check -q -r "$REQUIREMENTS"
    date -Iseconds > "$STAMP"
else
    done_msg "up to date (use --force-install to override)"
fi

# 3. preflight
if [[ "$SKIP_PREFLIGHT" != "true" ]]; then
    step "Preflight checks"
    args=("$PREFLIGHT")
    if [[ "$STRICT" == "true" ]]; then args+=("--strict"); fi
    if ! python "${args[@]}"; then
        if [[ "$STRICT" == "true" ]]; then
            echo "preflight failed (strict mode)" >&2
            exit 1
        fi
    fi
fi

# 4. uvicorn
step "Starting coordinator on :$PORT"
cd "$COORDINATOR"
exec python -m uvicorn main:app --reload --port "$PORT"