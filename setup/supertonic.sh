#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .venvs vendor models cache logs data
export HF_HOME="$ROOT/cache/huggingface"
if [ ! -d vendor/supertonic/.git ]; then
  git clone https://github.com/supertone-oss-archive/supertonic.git vendor/supertonic
fi
git -C vendor/supertonic checkout 1e9799e964ea4c0dad7cde993b65c3c813a7b373
if [ ! -x .venvs/supertonic/bin/python ]; then uv venv --python 3.11 .venvs/supertonic; fi
if [ -f data/supertonic.requirements.lock.txt ]; then
  uv pip install --python .venvs/supertonic/bin/python -r data/supertonic.requirements.lock.txt
else
  uv pip install --python .venvs/supertonic/bin/python 'onnxruntime==1.23.1' 'numpy==1.26.4' 'soundfile==0.12.1' 'librosa==0.10.2.post1' 'PyYAML==6.0.3' 'huggingface_hub==0.36.0'
fi
.venvs/supertonic/bin/hf download supertone-oss-archive/supertonic-3 --revision aafc6e32416a594460b32413efc49d7fe4ce6d46 --local-dir models/supertonic
uv pip freeze --python .venvs/supertonic/bin/python > data/supertonic.requirements.lock.txt
.venvs/supertonic/bin/python -c 'import json; from pathlib import Path; Path("data/supertonic-smoke.json").write_text(json.dumps({"texts":[{"id":"smoke","text":"안녕하세요. 한국어 발음 비교를 시작합니다."}],"threads":4,"voice":"F1"},ensure_ascii=False))'
.venvs/supertonic/bin/python workers/supertonic.py --request data/supertonic-smoke.json --output-dir outputs/supertonic-smoke
.venvs/supertonic/bin/python - <<'PY'
import json
from pathlib import Path
provenance = {'model':'supertonic','ready':True,'device':'cpu',
              'source_repository':'https://github.com/supertone-oss-archive/supertonic',
              'source_revision':'1e9799e964ea4c0dad7cde993b65c3c813a7b373',
              'model_repository':'supertone-oss-archive/supertonic-3',
              'model_revision':'aafc6e32416a594460b32413efc49d7fe4ce6d46'}
Path('data/supertonic.ready.json').write_text(json.dumps(provenance, indent=2))
Path('models/supertonic/provenance.json').write_text(json.dumps(provenance, indent=2))
PY
