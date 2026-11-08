"""CPU-only Ppaso-TTS adapter for the comparison runner."""
import argparse
import importlib.util
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
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = str(threads)
    started = time.perf_counter()
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf

    assets = ROOT / 'models/ppaso'
    source = assets / 'example/ppaso_tts.py'
    spec = importlib.util.spec_from_file_location('_ppaso_upstream', source)
    upstream = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = upstream
    spec.loader.exec_module(upstream)
    original_session = ort.InferenceSession
    sessions = []

    def cpu_session(path, *positional, **kwargs):
        if positional:
            raise TypeError('Unexpected positional ONNX options in pinned Ppaso source')
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        kwargs['sess_options'] = options
        kwargs['providers'] = ['CPUExecutionProvider']
        session = original_session(path, **kwargs)
        if session.get_providers() != ['CPUExecutionProvider']:
            raise RuntimeError('Ppaso must use CPUExecutionProvider exclusively')
        sessions.append(session)
        return session

    # The upstream constructor has no thread option. Inject options only while
    # it creates the four sessions; preserve the downloaded source byte-for-byte.
    ort.set_seed(42)
    ort.InferenceSession = cpu_session
    try:
        tts = upstream.PpasoTTS(assets, backend='onnx', device='cpu')
    finally:
        ort.InferenceSession = original_session
    if len(sessions) != 4:
        raise RuntimeError(f'Expected 4 Ppaso ONNX sessions, found {len(sessions)}')
    result = {
        'model': 'ppaso', 'device': 'cpu', 'voice': 'single-female',
        'providers': ['CPUExecutionProvider'], 'threads': threads, 'seed': 42,
        'sample_rate': 22050, 'load_seconds': time.perf_counter() - started,
        'items': [],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in request['texts']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', item['id']):
            raise ValueError('Invalid sample id')
        if not isinstance(item['text'], str) or not item['text'].strip():
            raise ValueError('Ppaso requires nonempty text')
        np.random.seed(42)
        start = time.perf_counter()
        # Includes Korean normalization, G2P, all chunks and waveform synthesis.
        audio = np.asarray(tts.synthesize(item['text']), dtype=np.float32)
        elapsed = time.perf_counter() - start
        if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
            raise RuntimeError('Ppaso returned invalid audio')
        filename = item['id'] + '.wav'
        sf.write(args.output_dir / filename, audio, 22050, subtype='PCM_16')
        duration = len(audio) / 22050
        result['items'].append({**item, 'path': filename, 'seconds': duration,
                                'generation_seconds': elapsed, 'rtf': elapsed / duration})
        (args.output_dir / 'result.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'id': item['id'], 'seconds': duration,
                          'generation_seconds': elapsed}), flush=True)


if __name__ == '__main__':
    main()
