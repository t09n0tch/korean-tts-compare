#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
command -v uv >/dev/null || { echo 'uv가 필요합니다: https://docs.astral.sh/uv/getting-started/installation/'; exit 1; }
command -v git >/dev/null || { echo 'Git이 필요합니다.'; exit 1; }
for model in supertonic melo piper ppaso; do
    bash "setup/$model.sh"
done
bash setup/pocket.sh
echo '설치 완료. .venvs/piper/bin/python serve.py 로 시작하세요.'
