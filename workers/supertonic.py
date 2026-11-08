#!/usr/bin/env python3
"""Pinned Supertonic 3 ONNX adapter; CPU execution is enforced."""
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
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding='utf-8'))
    threads = max(1, min(16, int(request.get('threads', 4))))
    os.environ['OMP_NUM_THREADS'] = str(threads)
    os.environ['OPENBLAS_NUM_THREADS'] = str(threads)
    sys.path.insert(0, str(ROOT / 'vendor/supertonic/py'))
    started = time.perf_counter()
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    from helper import TextToSpeech, load_cfgs, load_onnx_all, load_text_processor, load_voice_style
    voice_name = request.get('voice', 'F1')
    if not re.fullmatch(r'[FM][1-5]', voice_name):
        raise ValueError('Invalid voice name')
    assets = ROOT / 'models/supertonic'
    onnx_dir = str(assets / 'onnx')
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    sessions = load_onnx_all(onnx_dir, options, ['CPUExecutionProvider'])
    assert all(session.get_providers() == ['CPUExecutionProvider'] for session in sessions)
    tts = TextToSpeech(load_cfgs(onnx_dir), load_text_processor(onnx_dir), *sessions)
    style = load_voice_style([str(assets / 'voice_styles' / f'{voice_name}.json')])
    result = {'model': 'supertonic', 'device': 'cpu', 'voice': voice_name, 'sample_rate': tts.sample_rate,
              'threads': threads, 'seed': 42, 'steps': 8, 'speed': 1.0,
              'providers': ['CPUExecutionProvider'], 'load_seconds': time.perf_counter() - started, 'items': []}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in request['texts']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', item['id']):
            raise ValueError('Invalid sample id')
        np.random.seed(42)
        start = time.perf_counter()
        audio, durations = tts(item['text'], 'ko', style, total_step=8, speed=1.0)
        elapsed = time.perf_counter() - start
        audio = audio[0, :int(tts.sample_rate * durations[0].item())]
        if not len(audio) or not np.isfinite(audio).all():
            raise RuntimeError('Supertonic returned invalid audio')
        filename = item['id'] + '.wav'
        sf.write(args.output_dir / filename, audio, tts.sample_rate, subtype='PCM_16')
        duration = len(audio) / tts.sample_rate
        result['items'].append({**item, 'path': filename, 'seconds': duration,
                                'generation_seconds': elapsed, 'rtf': elapsed / duration})
        (args.output_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'id': item['id'], 'seconds': duration, 'generation_seconds': elapsed}), flush=True)


if __name__ == '__main__':
    main()
