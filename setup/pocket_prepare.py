"""Download immutable Korean Pocket-TTS bundles and make an offline config."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISIONS = {
    'pocket100': ('seastar105/pocket-tts-korean-100m', 'fed23331d461a7a0bfc6bfa30ca6b0099f4e9ad3'),
    'pocket300': ('seastar105/pocket-tts-korean-300m', 'f353349dbae42ff173d1e8421a1af3d1370f7841'),
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', choices=REVISIONS)
    args = parser.parse_args()
    os.environ['HF_HOME'] = str(ROOT / 'cache/huggingface')
    from huggingface_hub import snapshot_download
    import yaml

    repository, revision = REVISIONS[args.model]
    destination = ROOT / 'models' / args.model
    snapshot_download(repository, revision=revision, local_dir=destination,
                      allow_patterns=['korean.yaml', 'model.safetensors', 'tokenizer.model',
                                      'README.md', 'training_args.yaml'], max_workers=2)
    config = yaml.safe_load((destination / 'korean.yaml').read_text(encoding='utf-8'))
    upstream_paths = {
        'weights': config['weights_path'],
        'tokenizer': config['flow_lm']['lookup_table']['tokenizer_path'],
    }
    config['weights_path'] = str(destination / 'model.safetensors')
    config['weights_path_without_voice_cloning'] = config['weights_path']
    config['flow_lm']['lookup_table']['tokenizer_path'] = str(destination / 'tokenizer.model')
    (destination / 'local.yaml').write_text(yaml.safe_dump(config, allow_unicode=True), encoding='utf-8')
    provenance = {
        'model': args.model, 'model_repository': repository, 'model_revision': revision,
        'source_repository': 'https://github.com/kyutai-labs/pocket-tts',
        'package': 'pocket-tts==4.0.1', 'license': 'CC-BY-4.0',
        'upstream_runtime_paths': upstream_paths,
        'reference': 'examples/reference/supertonic-f1.wav',
        'reference_description': 'Synthetic Supertonic 3 F1 preset; shared by both Pocket models.',
        'files': {name: {'sha256': sha256(destination / name), 'bytes': (destination / name).stat().st_size}
                  for name in ['model.safetensors', 'tokenizer.model', 'korean.yaml']},
        'patches': ['Replace remote asset paths with pinned local files in local.yaml'],
    }
    (destination / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'model': args.model, 'downloaded': True, 'revision': revision}), flush=True)


if __name__ == '__main__':
    main()
