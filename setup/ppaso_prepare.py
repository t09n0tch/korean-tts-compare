"""Fetch only the pinned Ppaso CPU runtime, models, dictionaries and license."""
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'akamotaco/ppaso-tts-v1'
REVISION = '53d09664c4f636a5fb6f2ebe3ec22cd83ee249b9'
ASSETS = ROOT / 'models/ppaso'


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.part')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            temporary.replace(path)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def main():
    ready = ROOT / 'data/ppaso.ready.json'
    ready.parent.mkdir(parents=True, exist_ok=True)
    ready.write_text(json.dumps({'model': 'ppaso', 'ready': False,
                                 'source_revision': REVISION}), encoding='utf-8')
    manifest_path = ROOT / 'data/ppaso.provenance.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    previous_files = {entry['path']: entry for entry in previous.get('files', [])}
    api = f'https://huggingface.co/api/models/{REPOSITORY}/revision/{REVISION}'
    with urllib.request.urlopen(api, timeout=60) as response:
        metadata = json.load(response)
    if metadata['sha'] != REVISION:
        raise RuntimeError('Hugging Face returned an unexpected revision')
    files = sorted(entry['rfilename'] for entry in metadata['siblings']
                   if entry['rfilename'].startswith(('onnx/', 'runtime/'))
                   or entry['rfilename'] in ('example/ppaso_tts.py', 'config.json',
                                             'LICENSE', 'NOTICE', 'README.md', 'README_ko.md'))
    if not any(name.endswith('.onnx') for name in files):
        raise RuntimeError('Pinned Ppaso revision contains no ONNX models')
    recorded = []
    for name in files:
        target = ASSETS / name
        old = previous_files.get(name)
        digest = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        if previous.get('source_revision') != REVISION or not old or digest != old['sha256']:
            print('Downloading', name, flush=True)
            url = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/' + urllib.parse.quote(name)
            download(url, target)
        recorded.append({'path': name, 'bytes': target.stat().st_size,
                         'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    provenance = {
        'model': 'ppaso', 'model_repository': REPOSITORY,
        'source_repository': f'https://huggingface.co/{REPOSITORY}',
        'source_revision': REVISION, 'model_revision': REVISION,
        'license': 'Apache-2.0 (upstream LICENSE retained)',
        'files': recorded, 'download_bytes': sum(entry['bytes'] for entry in recorded),
        'patches': [],
        'adapter_changes': [
            'Force CPUExecutionProvider for all four ONNX sessions.',
            'Set intra_op_num_threads=request.threads and inter_op_num_threads=1.',
            'No changes to upstream model, pronunciation dictionary or runtime files.',
        ],
    }
    manifest_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
    (ASSETS / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'data/ppaso-smoke.json').write_text(json.dumps({
        'texts': [{'id': 'smoke', 'text': '안녕하세요. 한국어 발음 비교를 시작합니다.'}],
        'threads': 4}, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
