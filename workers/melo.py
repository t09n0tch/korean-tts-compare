#!/usr/bin/env python3
"""MeloTTS Korean CPU worker; see setup/melo.sh for reproducible installation."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding='utf-8'))
    threads = max(1, min(int(request.get('threads', 4)), 16))
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = str(threads)
    os.environ['HF_HOME'] = str(ROOT / 'cache/huggingface')
    os.environ['NLTK_DATA'] = str(ROOT / 'cache/nltk')
    os.environ['MELO_KOREAN_BERT_DIR'] = str(ROOT / 'models/melo-bert')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    sys.path.insert(0, str(ROOT / 'vendor/MeloTTS'))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    load_start = time.perf_counter()
    import numpy as np
    import soundfile as sf
    import torch
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(42)
    np.random.seed(42)
    from melo.api import TTS
    model = TTS(language='KR', device='cpu',
                config_path=str(ROOT / 'models/melo/config.json'),
                ckpt_path=str(ROOT / 'models/melo/checkpoint.pth'))
    # Include the lazily loaded Korean frontend/BERT in model load timing.
    from melo.text import korean
    korean.korean_text_to_phonemes('안녕하세요')
    if not getattr(model.hps.data, 'disable_bert', False):
        from melo.text import japanese_bert
        from transformers import AutoModelForMaskedLM
        japanese_bert.models[korean.model_id] = AutoModelForMaskedLM.from_pretrained(
            korean.model_id, local_files_only=True).to('cpu').eval()
        japanese_bert.tokenizers[korean.model_id] = korean.tokenizer
    assert all(p.device.type == 'cpu' for p in model.parameters())
    speaker = model.hps.data.spk2id['KR']
    rate = model.hps.data.sampling_rate
    result = {'model': 'melo', 'device': 'cpu', 'voice': 'KR', 'sample_rate': rate,
              'threads': threads, 'seed': 42,
              'load_seconds': round(time.perf_counter() - load_start, 6), 'items': []}
    for index, item in enumerate(request['texts']):
        item_id = str(item.get('id', index + 1))
        if not re.fullmatch(r'[A-Za-z0-9_-]+', item_id):
            raise ValueError('Sentence id must contain letters, numbers, underscores or hyphens')
        text = str(item['text']).strip()
        if not text:
            raise ValueError('Sentence must not be empty')
        torch.manual_seed(42)
        started = time.perf_counter()
        audio = model.tts_to_file(text, speaker, output_path=None, speed=1.0, quiet=True)
        elapsed = time.perf_counter() - started
        if not np.isfinite(audio).all() or len(audio) == 0:
            raise RuntimeError('MeloTTS returned invalid audio')
        filename = f'{item_id}.wav'
        sf.write(args.output_dir / filename, audio, rate, subtype='PCM_16')
        seconds = len(audio) / rate
        result['items'].append({'id': item_id, 'text': text, 'path': filename,
                                'seconds': round(seconds, 6),
                                'generation_seconds': round(elapsed, 6),
                                'rtf': round(elapsed / seconds, 6)})
        (args.output_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(f'MeloTTS {item_id}: {seconds:.2f}s audio, {elapsed:.2f}s generation', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
