#!/usr/bin/env python3
"""Loopback-only UI, job API and audio playback. No external service is used."""
import argparse
import json
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from compare import ROOT, MODELS, available, create_job, machine_info, read_json, run_job, write_json

JOB_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def json_response(self, value, code=200):
        body = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/config':
            latest_file = ROOT / 'data/latest.json'
            return self.json_response({'app_id': 'korean-tts-compare', 'models': [{'id': m, **info, 'available': available(m)} for m, info in MODELS.items()],
                                       'samples': read_json(ROOT / 'data/samples.json'), 'machine': machine_info(),
                                       'latest': read_json(latest_file)['id'] if latest_file.exists() else None})
        if re.fullmatch(r'/api/jobs/[0-9]{8}-[0-9]{6}-[a-f0-9]{6}', path):
            file = ROOT / 'outputs' / path.rsplit('/', 1)[-1] / 'job.json'
            return self.json_response(read_json(file)) if file.exists() else self.json_response({'error': '결과가 없습니다.'}, 404)
        if path in ['/', '/index.html']:
            return self.send_file(ROOT / 'web/index.html')
        if re.fullmatch(r'/outputs/[0-9]{8}-[0-9]{6}-[a-f0-9]{6}/(supertonic|melo|piper)/s[0-9]{2}\.wav', path):
            return self.send_file(ROOT / path.lstrip('/'))
        return self.json_response({'error': '찾을 수 없습니다.'}, 404)

    def send_file(self, path):
        if not path.is_file():
            return self.json_response({'error': '파일이 없습니다.'}, 404)
        size = path.stat().st_size
        start, end, partial = 0, size - 1, False
        request_range = self.headers.get('Range')
        if request_range:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', request_range)
            if not match or not any(match.groups()):
                return self.json_response({'error': '잘못된 범위'}, 416)
            first, last = match.groups()
            start = int(first) if first else max(0, size - int(last))
            end = min(int(last), size - 1) if first and last else size - 1
            if start > end or start >= size:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            partial = True
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with path.open('rb') as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if self.path != '/api/jobs':
            return self.json_response({'error': '찾을 수 없습니다.'}, 404)
        expected = f'http://{self.headers.get("Host", "")}'
        origin = self.headers.get('Origin')
        if origin and origin != expected:
            return self.json_response({'error': '로컬 페이지에서만 실행할 수 있습니다.'}, 403)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.json_response({'error': 'application/json 요청이 필요합니다.'}, 415)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('요청 크기를 줄여 주세요.')
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError) as error:
            return self.json_response({'error': str(error)}, 400)
        if not JOB_LOCK.acquire(blocking=False):
            return self.json_response({'error': '현재 합성이 진행 중입니다. 완료 후 다시 실행해 주세요.'}, 409)
        try:
            job = create_job(payload)
        except (ValueError, TypeError) as error:
            JOB_LOCK.release()
            return self.json_response({'error': str(error)}, 400)

        def work():
            try:
                run_job(job)
            except Exception as error:
                job.update(status='error', progress='비교 실행 중 오류가 발생했습니다.')
                job['errors']['runner'] = str(error)
                write_json(ROOT / 'outputs' / job['id'] / 'job.json', job)
            finally:
                JOB_LOCK.release()
        threading.Thread(target=work, daemon=True).start()
        return self.json_response({'id': job['id']}, 202)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'한국어 TTS 비교: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
