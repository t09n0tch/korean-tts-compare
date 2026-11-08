#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .venvs models data cache
if [ ! -x .venvs/piper/bin/python ]; then uv venv --python 3.11 .venvs/piper; fi
if [ -f data/piper.requirements.lock.txt ]; then
  uv pip install --python .venvs/piper/bin/python -r data/piper.requirements.lock.txt
else
  uv pip install --python .venvs/piper/bin/python 'piper-tts==1.8.0' 'onnxruntime==1.31.1' 'numpy==2.4.6' 'soundfile==0.14.0'
fi
.venvs/piper/bin/python - <<'PY'
import json, pathlib, urllib.request
root = pathlib.Path.cwd()
revision = 'e7229f7d33a10e145e109b886d661984201ac3c4'
base = f'https://huggingface.co/rhasspy/piper-voices/resolve/{revision}/ko/ko_KR/kss/medium/'
for source, target in [('ko_KR-kss-medium.onnx', 'piper.onnx'), ('ko_KR-kss-medium.onnx.json', 'piper.onnx.json'), ('MODEL_CARD', 'piper.MODEL_CARD')]:
    path = root / 'models' / target
    if not path.exists():
        print('Downloading', source, flush=True)
        temporary = path.with_name(path.name + '.part')
        urllib.request.urlretrieve(base + source, temporary)
        temporary.replace(path)
(root / 'models/piper.provenance.json').write_text(json.dumps({'model': 'piper', 'model_repository': 'rhasspy/piper-voices', 'source_revision': revision}, indent=2))
(root / 'data/piper-smoke.json').write_text(json.dumps({'texts':[{'id':'smoke','text':'안녕하세요. 한국어 발음 비교를 시작합니다.'}], 'threads':4}, ensure_ascii=False))
PY
uv pip freeze --python .venvs/piper/bin/python > data/piper.requirements.lock.txt
.venvs/piper/bin/python workers/piper.py --request data/piper-smoke.json --output-dir outputs/piper-smoke
.venvs/piper/bin/python -c 'import json; from pathlib import Path; p=json.loads(Path("models/piper.provenance.json").read_text()); p.update(ready=True,device="cpu"); Path("data/piper.ready.json").write_text(json.dumps(p,indent=2))'
