#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .venvs models data cache logs
export UV_CACHE_DIR="$ROOT/cache/uv"
export HF_HOME="$ROOT/cache/huggingface"
if [ ! -x .venvs/ppaso/bin/python ]; then
  uv venv --python 3.11 .venvs/ppaso
fi
if [ -f data/ppaso.requirements.lock.txt ]; then
  uv pip install --python .venvs/ppaso/bin/python -r data/ppaso.requirements.lock.txt
else
  # python-mecab-ko wheels bundle the native library and dictionary on macOS
  # and Linux/WSL2; no system-wide mecab installation is required.
  uv pip install --python .venvs/ppaso/bin/python \
    'numpy==1.26.4' 'onnxruntime==1.23.1' 'soundfile==0.12.1' \
    'python-mecab-ko==1.3.7' 'python-mecab-ko-dic==2.1.1.post2'
fi
.venvs/ppaso/bin/python setup/ppaso_prepare.py
uv pip freeze --python .venvs/ppaso/bin/python > data/ppaso.requirements.lock.txt
.venvs/ppaso/bin/python workers/ppaso.py \
  --request data/ppaso-smoke.json --output-dir outputs/ppaso-smoke
.venvs/ppaso/bin/python - <<'PY'
import json
from pathlib import Path
provenance = json.loads(Path('data/ppaso.provenance.json').read_text())
smoke = json.loads(Path('outputs/ppaso-smoke/result.json').read_text())
provenance.update(ready=True, device='cpu', providers=smoke['providers'],
                  smoke_result='outputs/ppaso-smoke/result.json')
Path('data/ppaso.ready.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
PY
