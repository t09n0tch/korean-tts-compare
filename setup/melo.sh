#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p .venvs vendor models cache logs data
export HF_HOME="$ROOT/cache/huggingface"
export NLTK_DATA="$ROOT/cache/nltk"
if [ "$(uname -s)" = Linux ]; then export UV_TORCH_BACKEND=cpu; fi
if [ ! -d vendor/MeloTTS/.git ]; then
  git clone https://github.com/myshell-ai/MeloTTS.git vendor/MeloTTS
fi
git -C vendor/MeloTTS checkout 209145371cff8fc3bd60d7be902ea69cbdb7965a
if [ ! -x .venvs/melo/bin/python ]; then
  uv venv --python 3.10 .venvs/melo
fi
if [ -f data/melo.requirements.lock.txt ]; then
  uv pip install --python .venvs/melo/bin/python -r data/melo.requirements.lock.txt
else
  uv pip install --python .venvs/melo/bin/python \
    'torch==2.2.2' 'torchaudio==2.2.2' 'numpy==1.26.4' 'scipy==1.12.0' \
    'transformers==4.27.4' 'huggingface_hub==0.21.4' 'cached_path==1.6.2' \
    'librosa==0.9.1' 'numba==0.59.1' 'soundfile==0.12.1' \
    'num2words==0.5.12' 'anyascii==0.3.2' 'jamo==0.4.1' 'g2pkk==0.1.2' \
    'nltk==3.9.1' 'tqdm==4.66.5' 'setuptools==75.3.2' 'python-mecab-ko==1.3.7'
fi
.venvs/melo/bin/python setup/melo_prepare.py
uv pip freeze --python .venvs/melo/bin/python > data/melo.requirements.lock.txt
.venvs/melo/bin/python -c 'import json; from pathlib import Path; p=Path("data/melo.smoke-request.json"); p.write_text(json.dumps({"texts":[{"id":"smoke","text":"안녕하세요. 한국어 발음을 비교합니다."}],"threads":4},ensure_ascii=False))'
.venvs/melo/bin/python workers/melo.py --request data/melo.smoke-request.json --output-dir outputs/melo-smoke
.venvs/melo/bin/python -c 'import json,platform; from pathlib import Path; p=json.loads(Path("models/melo/provenance.json").read_text()); p.update(model="melo",ready=True,device="cpu",host=platform.platform()); Path("data/melo.ready.json").write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n")'
printf 'MeloTTS Korean CPU installation and smoke synthesis completed.\n'
