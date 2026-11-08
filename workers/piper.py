"""CPU-only Piper Korean adapter. Run with its own .venvs/piper Python."""
import argparse
import json
import os
import re
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path = [p for p in sys.path if Path(p or '.').resolve() != Path(__file__).resolve().parent]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding='utf-8'))
    threads = max(1, min(16, int(request.get('threads', 4))))
    os.environ['OMP_NUM_THREADS'] = str(threads)
    os.environ['OPENBLAS_NUM_THREADS'] = str(threads)
    started = time.perf_counter()
    import onnxruntime as ort
    from piper import PiperVoice
    from piper.config import PiperConfig

    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    ort.set_seed(42)
    config = json.loads((ROOT / 'models/piper.onnx.json').read_text())
    session = ort.InferenceSession(str(ROOT / 'models/piper.onnx'),
                                  sess_options=options, providers=['CPUExecutionProvider'])
    voice = PiperVoice(config=PiperConfig.from_dict(config), session=session)
    assert session.get_providers() == ['CPUExecutionProvider']
    result = {'model': 'piper', 'device': 'cpu', 'providers': session.get_providers(),
              'voice': 'ko_KR-kss-medium', 'threads': threads, 'seed': 42,
              'load_seconds': time.perf_counter() - started, 'items': []}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in request['texts']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', item['id']):
            raise ValueError('Invalid sample id')
        path = args.output_dir / (item['id'] + '.wav')
        start = time.perf_counter()
        chunks = [(chunk.sample_rate, chunk.sample_width, chunk.sample_channels, chunk.audio_int16_bytes)
                  for chunk in voice.synthesize(item['text'])]
        elapsed = time.perf_counter() - start
        if not chunks:
            raise RuntimeError('Piper returned empty audio')
        with wave.open(str(path), 'wb') as output:
            output.setframerate(chunks[0][0])
            output.setsampwidth(chunks[0][1])
            output.setnchannels(chunks[0][2])
            for _, _, _, data in chunks:
                output.writeframes(data)
        with wave.open(str(path), 'rb') as output:
            duration = output.getnframes() / output.getframerate()
        result['items'].append({**item, 'path': path.name, 'seconds': duration,
                                'generation_seconds': elapsed, 'rtf': elapsed / duration})
        (args.output_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({'id': item['id'], 'seconds': duration, 'generation_seconds': elapsed}), flush=True)


if __name__ == '__main__':
    main()
