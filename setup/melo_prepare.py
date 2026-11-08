"""Pin downloads and apply narrow CPU/Korean loading compatibility patches."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ['HF_HOME'] = str(ROOT / 'cache/huggingface')
os.environ['NLTK_DATA'] = str(ROOT / 'cache/nltk')

repo = ROOT / 'vendor/MeloTTS'
cleaner = repo / 'melo/text/cleaner.py'
text = cleaner.read_text()
text = text.replace(
    'from . import chinese, japanese, english, chinese_mix, korean, french, spanish',
    'from importlib import import_module',
)
text = text.replace(
    'language_module_map = {"ZH": chinese, "JP": japanese, "EN": english, \'ZH_MIX_EN\': chinese_mix, \'KR\': korean,\n                    \'FR\': french, \'SP\': spanish, \'ES\': spanish}',
    'language_module_map = {"ZH": "chinese", "JP": "japanese", "EN": "english", "ZH_MIX_EN": "chinese_mix", "KR": "korean", "FR": "french", "SP": "spanish", "ES": "spanish"}',
)
text = text.replace('language_module = language_module_map[language]',
                    'language_module = import_module("melo.text." + language_module_map[language])')
cleaner.write_text(text)

bert = repo / 'melo/text/japanese_bert.py'
text = bert.read_text()
text = text.replace('''    if (
        sys.platform == "darwin"
        and torch.backends.mps.is_available()
        and device == "cpu"
    ):
        device = "mps"
''', '    # Local comparison: honor the caller\'s explicit CPU device.\n')
bert.write_text(text)

init = repo / 'melo/text/__init__.py'
text = init.read_text()
start = text.index('def get_bert(')
text = text[:start] + '''def get_bert(norm_text, word2ph, language, device):
    from importlib import import_module
    modules = {"ZH": "chinese_bert", "EN": "english_bert", "JP": "japanese_bert",
               "ZH_MIX_EN": "chinese_mix", "FR": "french_bert", "SP": "spanish_bert",
               "ES": "spanish_bert", "KR": "korean"}
    module = import_module("melo.text." + modules[language])
    return module.get_bert_feature(norm_text, word2ph, device)
'''
init.write_text(text)

from huggingface_hub import snapshot_download
model_revision = '0207e5adfc90129a51b6b03d89be6d84360ed323'
bert_revision = '1779cc0982ada0216dd6de0dd4e86fb78201926d'
snapshot_download('myshell-ai/MeloTTS-Korean', revision=model_revision,
                  local_dir=ROOT / 'models/melo', local_dir_use_symlinks=False,
                  allow_patterns=['config.json', 'checkpoint.pth', 'README.md'])
snapshot_download('kykim/bert-kor-base', revision=bert_revision,
                  local_dir=ROOT / 'models/melo-bert', local_dir_use_symlinks=False,
                  allow_patterns=['config.json', 'pytorch_model.bin', 'tokenizer_config.json',
                                  'tokenizer.json', 'vocab.txt', 'special_tokens_map.json'])

# Resolve the tokenizer and optional BERT features from pinned local files.
korean = repo / 'melo/text/korean.py'
text = korean.read_text()
text = text.replace("model_id = 'kykim/bert-kor-base'",
                    "import os\nmodel_id = os.environ.get('MELO_KOREAN_BERT_DIR', 'kykim/bert-kor-base')")
korean.write_text(text)

import nltk
Path(os.environ['NLTK_DATA']).mkdir(parents=True, exist_ok=True)
nltk.download('cmudict', download_dir=os.environ['NLTK_DATA'], raise_on_error=True)
(ROOT / 'models/melo/provenance.json').write_text(json.dumps({
    'source_repository': 'https://github.com/myshell-ai/MeloTTS',
    'source_revision': '209145371cff8fc3bd60d7be902ea69cbdb7965a',
    'model_repository': 'myshell-ai/MeloTTS-Korean', 'model_revision': model_revision,
    'bert_repository': 'kykim/bert-kor-base', 'bert_revision': bert_revision,
    'patches': ['lazy language imports', 'honor explicit CPU instead of auto MPS',
                'pinned local Korean BERT path'],
}, ensure_ascii=False, indent=2) + '\n')
