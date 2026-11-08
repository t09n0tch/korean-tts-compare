#!/usr/bin/env python3
"""Local, CPU-only Korean TTS comparison runner. The controller needs only stdlib."""
import argparse
import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = {
    'supertonic': {'name': 'Supertonic 3', 'note': '공식 지원 종료 · 아카이브 모델 · 기본 F1 음성'},
    'melo': {'name': 'MeloTTS Korean', 'note': '한국어 KR 음성 · PyTorch CPU'},
    'piper': {'name': 'Piper KSS', 'note': '한국어 단일 화자 · ONNX CPU · 데이터셋 비상업 라이선스 표기'},
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def python_for(model):
    return ROOT / '.venvs' / model / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def available(model):
    marker = ROOT / 'data' / f'{model}.ready.json'
    return python_for(model).exists() and marker.exists() and read_json(marker).get('ready', False)


def machine_info():
    cpu = platform.processor() or platform.machine()
    if sys.platform == 'darwin':
        cpu = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip()
    return {'cpu': cpu, 'arch': platform.machine(), 'platform': platform.platform(),
            'logical_cpus': os.cpu_count(), 'device': 'CPU only'}


def validate_request(payload):
    if not isinstance(payload, dict):
        raise ValueError('요청은 JSON 객체여야 합니다.')
    texts = payload.get('texts')
    models = payload.get('models', list(MODELS))
    if not isinstance(texts, list) or not 1 <= len(texts) <= 20:
        raise ValueError('비교할 문장을 1~20개 입력해 주세요.')
    normalized = []
    for index, item in enumerate(texts, 1):
        text = item.get('text') if isinstance(item, dict) else item
        if not isinstance(text, str) or not text.strip() or len(text) > 500:
            raise ValueError('문장마다 1~500자를 입력해 주세요.')
        sample = {'id': f's{index:02}', 'text': text.strip()}
        if isinstance(item, dict) and isinstance(item.get('category'), str):
            sample['category'] = item['category']
        normalized.append(sample)
    if not isinstance(models, list) or not models or any(m not in MODELS for m in models):
        raise ValueError('지원하는 모델을 하나 이상 선택해 주세요.')
    models = list(dict.fromkeys(models))
    missing = [MODELS[m]['name'] for m in models if not available(m)]
    if missing:
        raise ValueError('설치가 완료되지 않은 모델: ' + ', '.join(missing))
    threads = payload.get('threads', 4)
    if type(threads) is not int or not 1 <= threads <= 16:
        raise ValueError('CPU 스레드는 1~16 사이 정수여야 합니다.')
    voice = payload.get('supertonic_voice', 'F1')
    if voice not in ['F1', 'F2', 'F3', 'F4', 'F5', 'M1', 'M2', 'M3', 'M4', 'M5']:
        raise ValueError('지원하지 않는 Supertonic 음성입니다.')
    return {'texts': normalized, 'models': models, 'threads': threads, 'supertonic_voice': voice}


def create_job(payload):
    request = validate_request(payload)
    job_id = dt.datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
    job = {**request, 'id': job_id, 'status': 'queued', 'progress': '합성을 준비합니다.',
           'created_at': dt.datetime.now().astimezone().isoformat(), 'machine': machine_info(),
           'results': {}, 'errors': {}}
    write_json(ROOT / 'outputs' / job_id / 'job.json', job)
    return job


def run_job(job):
    job_dir = ROOT / 'outputs' / job['id']
    status_path = job_dir / 'job.json'
    job['status'] = 'running'
    write_json(status_path, job)
    env = os.environ.copy()
    env.update({'HF_HOME': str(ROOT / 'cache/huggingface'), 'NLTK_DATA': str(ROOT / 'cache/nltk'),
                'OMP_NUM_THREADS': str(job['threads']), 'OPENBLAS_NUM_THREADS': str(job['threads']),
                'MKL_NUM_THREADS': str(job['threads']), 'TOKENIZERS_PARALLELISM': 'false',
                'CUDA_VISIBLE_DEVICES': '', 'PYTHONUNBUFFERED': '1'})
    for index, model in enumerate(job['models'], 1):
        name = MODELS[model]['name']
        job['progress'] = f'{name} 합성 중 ({index}/{len(job["models"])})'
        write_json(status_path, job)
        print(job['progress'], flush=True)
        model_dir = job_dir / model
        model_dir.mkdir(parents=True, exist_ok=True)
        request = {'texts': job['texts'], 'threads': job['threads'],
                   'voice': job['supertonic_voice'] if model == 'supertonic' else 'KR'}
        write_json(model_dir / 'request.json', request)
        started = time.perf_counter()
        try:
            with (model_dir / 'run.log').open('w', encoding='utf-8') as log:
                subprocess.run([str(python_for(model)), str(ROOT / 'workers' / f'{model}.py'),
                                '--request', str(model_dir / 'request.json'), '--output-dir', str(model_dir)],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                               check=True, timeout=1800)
            result = read_json(model_dir / 'result.json')
            if result.get('device') != 'cpu' or len(result.get('items', [])) != len(job['texts']):
                raise RuntimeError('CPU 합성 결과 개수가 요청과 일치하지 않습니다.')
            for item in result['items']:
                path = Path(item['path'])
                if path.name != str(path) or not (model_dir / path).is_file() or item['seconds'] <= 0:
                    raise RuntimeError('생성된 오디오 파일을 확인할 수 없습니다.')
                item['audio_url'] = f'/outputs/{job["id"]}/{model}/{path.name}'
            result['process_seconds'] = time.perf_counter() - started
            job['results'][model] = result
        except Exception as error:
            log_path = model_dir / 'run.log'
            tail = log_path.read_text(encoding='utf-8', errors='replace')[-5000:] if log_path.exists() else ''
            job['errors'][model] = f'{type(error).__name__}: {error}\n{tail}'
        write_json(status_path, job)
    job['status'] = 'error' if job['errors'] else 'done'
    job['progress'] = '일부 모델 합성에 실패했습니다. 오류를 확인해 주세요.' if job['errors'] else '모든 음성이 준비되었습니다.'
    job['completed_at'] = dt.datetime.now().astimezone().isoformat()
    write_json(status_path, job)
    write_json(ROOT / 'data/latest.json', {'id': job['id']})
    return job


def main():
    parser = argparse.ArgumentParser(description='한국어 CPU TTS 비교 음성 생성')
    parser.add_argument('--models', nargs='+', choices=list(MODELS), default=list(MODELS))
    parser.add_argument('--text', action='append', help='비교 문장. 여러 번 지정할 수 있습니다.')
    parser.add_argument('--samples', type=Path, default=ROOT / 'data/samples.json')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--voice', default='F1')
    args = parser.parse_args()
    job = create_job({'texts': args.text or read_json(args.samples), 'models': args.models,
                      'threads': args.threads, 'supertonic_voice': args.voice})
    result = run_job(job)
    print(f'결과: {ROOT / "outputs" / job["id"]}')
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
