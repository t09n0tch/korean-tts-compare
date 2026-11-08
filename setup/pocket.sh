#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ "$#" -eq 0 ]; then
  bash "$ROOT/setup/pocket.sh" pocket100
  exec bash "$ROOT/setup/pocket.sh" pocket300
fi
MODEL="$1"
case "$MODEL" in pocket100|pocket300) ;; *) printf 'Expected pocket100 or pocket300\n' >&2; exit 2 ;; esac
mkdir -p .venvs models cache logs data outputs
rm -f "data/$MODEL.ready.json"
export HF_HOME="$ROOT/cache/huggingface"
if [ "$(uname -s)" = Linux ]; then export UV_TORCH_BACKEND=cpu; fi
if [ ! -x .venvs/pocket/bin/python ]; then uv venv --python 3.11 .venvs/pocket; fi
if [ -f data/pocket.requirements.lock.txt ]; then
  uv pip install --python .venvs/pocket/bin/python -r data/pocket.requirements.lock.txt
else
  uv pip install --python .venvs/pocket/bin/python 'pocket-tts==4.0.1' 'torch==2.11.0' \
    'numpy==2.4.6' 'soundfile==0.14.0' 'pyyaml==6.0.3'
fi
.venvs/pocket/bin/python setup/pocket_prepare.py "$MODEL"
uv pip freeze --python .venvs/pocket/bin/python > data/pocket.requirements.lock.txt
.venvs/pocket/bin/python - "$MODEL" <<'PY'
import json, sys
from pathlib import Path
model = sys.argv[1]
Path(f'data/{model}.smoke-request.json').write_text(json.dumps({
    'model': model, 'threads': 4,
    'texts': [{'id': 'smoke', 'text': '안녕하세요. 한국어 발음을 비교합니다.'}],
}, ensure_ascii=False), encoding='utf-8')
PY
.venvs/pocket/bin/python workers/pocket.py --request "data/$MODEL.smoke-request.json" --output-dir "outputs/$MODEL-smoke"
.venvs/pocket/bin/python - "$MODEL" <<'PY'
import json, platform, sys
from pathlib import Path
model = sys.argv[1]
p = json.loads(Path(f'models/{model}/provenance.json').read_text(encoding='utf-8'))
result = json.loads(Path(f'outputs/{model}-smoke/result.json').read_text(encoding='utf-8'))
p.update(ready=True, device='cpu', host=platform.platform(),
         reference_sha256=result['reference_sha256'], smoke=result['items'][0])
Path(f'data/{model}.ready.json').write_text(json.dumps(p, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
printf '%s CPU installation and smoke synthesis completed.\n' "$MODEL"
