#!/usr/bin/env bash
# run.sh - venv 환경에서 MyCoder 에이전트를 실행합니다.
#
# 사용법:
#   ./run.sh          # 실제 Ollama 에이전트 실행 (agent.py)
#   ./run.sh demo     # Ollama 없이 동작 원리 데모 (demo.py)
#   ./run.sh setup    # venv 설치만 수행

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── venv 생성 및 의존성 설치 ───────────────────────────

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "[setup] venv 생성 중..."
        python3 -m venv "$VENV_DIR"
    else
        echo "[setup] 기존 venv 사용: $VENV_DIR"
    fi

    echo "[setup] 의존성 설치 중..."
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
    echo "[setup] 완료"
}

# ── 실행 ──────────────────────────────────────────────

setup_venv

MODE="${1:-agent}"

case "$MODE" in
    demo)
        echo "[실행] demo.py (Ollama 없이 동작 원리 시뮬레이션)"
        exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/demo.py"
        ;;
    setup)
        echo "[완료] venv 설정이 끝났습니다."
        ;;
    agent|*)
        echo "[실행] agent.py (Ollama 에이전트)"
        exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/agent.py"
        ;;
esac
