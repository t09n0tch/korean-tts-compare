"""Offline CPU-only adapter for the Korean Pocket-TTS 100M and 300M bundles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding='utf-8'))
    model_id = request.get('model')
    if model_id not in {'pocket100', 'pocket300'}:
        raise ValueError('Pocket request.model must be pocket100 or pocket300')
    threads = max(1, min(16, int(request.get('threads', 4))))
    os.environ.update(OMP_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS=str(threads),
                      MKL_NUM_THREADS=str(threads), CUDA_VISIBLE_DEVICES='',
                      HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      HF_HOME=str(ROOT / 'cache/huggingface'))
    started = time.perf_counter()
    import numpy as np
    import soundfile as sf
    import torch
    import yaml
    from pocket_tts import TTSModel

    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.set_default_device('cpu')
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    assets = ROOT / 'models' / model_id
    reference = ROOT / 'examples/reference/supertonic-f1.wav'
    if not reference.is_file():
        raise FileNotFoundError(f'Missing shared synthetic voice reference: {reference}')
    config_path = assets / 'local.yaml'
    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    for location in (config['weights_path'], config['weights_path_without_voice_cloning'],
                     config['flow_lm']['lookup_table']['tokenizer_path']):
        if not Path(location).is_file() or not Path(location).resolve().is_relative_to(assets.resolve()):
            raise ValueError('Pocket assets must be local; rerun setup after moving the repository')
    model = TTSModel.load_model(config=config_path, temp=0.3, sampler_decode_steps=1,
                               eos_threshold=-1.0).to('cpu').eval()
    assert all(parameter.device.type == 'cpu' for parameter in model.parameters())
    assert all(buffer.device.type == 'cpu' for buffer in model.buffers())
    # Pocket generates in a background thread; no_grad keeps its mutable caches
    # usable there (inference_mode tensors cannot be mutated from that thread).
    with torch.no_grad():
        voice_state = model.get_state_for_audio_prompt(reference)
    result = {
        'model': model_id, 'device': 'cpu', 'voice': 'synthetic-supertonic-F1',
        'reference': str(reference.relative_to(ROOT)),
        'reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
        'sample_rate': model.sample_rate, 'threads': threads, 'seed': 42,
        'temperature': 0.3, 'sampler_decode_steps': 1, 'eos_threshold': -1.0,
        'offline': True, 'load_seconds': time.perf_counter() - started, 'items': [],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in request['texts']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', item['id']):
            raise ValueError('Invalid sample id')
        if not isinstance(item['text'], str) or not item['text'].strip():
            raise ValueError('Text must not be empty')
        torch.manual_seed(42)
        np.random.seed(42)
        random.seed(42)
        start = time.perf_counter()
        with torch.no_grad():
            waveform = model.generate_audio(voice_state, item['text'], copy_state=True)
        elapsed = time.perf_counter() - start
        assert waveform.device.type == 'cpu'
        audio = waveform.detach().numpy().reshape(-1)
        if not audio.size or not np.isfinite(audio).all():
            raise RuntimeError('Pocket-TTS returned invalid audio')
        path = args.output_dir / (item['id'] + '.wav')
        sf.write(path, audio, model.sample_rate, subtype='PCM_16')
        duration = len(audio) / model.sample_rate
        result['items'].append({**item, 'path': path.name, 'seconds': duration,
                                'generation_seconds': elapsed, 'rtf': elapsed / duration})
        (args.output_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'id': item['id'], 'seconds': duration, 'generation_seconds': elapsed}), flush=True)


if __name__ == '__main__':
    main()
