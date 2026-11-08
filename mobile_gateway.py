#!/usr/bin/env python3
"""Authenticated loopback gateway for a temporary HTTPS mobile tunnel."""
import argparse
import http.client
import json
import re
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / '.mobile-access.json'
UPSTREAM = ('127.0.0.1', 8766)
COOKIE_NAME = 'tts_access'


class MobileGateway(BaseHTTPRequestHandler):
    config_path = CONFIG_PATH
    server_version = 'KoreanTTSGateway'
    sys_version = ''

    def log_message(self, *args):
        # Request targets can contain the one-time entry credential.
        pass

    def log_error(self, *args):
        pass

    def privacy_headers(self):
        self.send_header('Cache-Control', 'private, no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Connection', 'close')
        self.close_connection = True

    def message(self, code, text):
        body = ('<!doctype html><html lang="ko"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>한국어 음성 비교</title><body style="font-family:sans-serif;'
                'padding:32px;line-height:1.7"><h1>한국어 음성 비교</h1><p>'
                + text + '</p></body></html>').encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.privacy_headers()
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def settings(self):
        try:
            config = json.loads(self.config_path.read_text(encoding='utf-8'))
            host, token = config.get('public_host'), config.get('token')
            if (not isinstance(host, str)
                    or not re.fullmatch(r'[a-z0-9-]+\.trycloudflare\.com', host)
                    or not isinstance(token, str)
                    or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token)):
                raise ValueError('Invalid gateway configuration')
            return host, token
        except (OSError, ValueError, TypeError, AttributeError):
            self.message(503, '모바일 접속을 준비하고 있습니다. 잠시 후 다시 열어 주세요.')
            return None

    def authorized(self, token):
        try:
            cookies = SimpleCookie()
            cookies.load(self.headers.get('Cookie', ''))
            value = cookies[COOKIE_NAME].value if COOKIE_NAME in cookies else ''
            return secrets.compare_digest(value.encode('utf-8'), token.encode('utf-8'))
        except Exception:
            return False

    def handle_proxy(self):
        config = self.settings()
        if not config:
            return
        host, token = config
        if self.headers.get_all('Host') != [host]:
            return self.message(421, '올바른 모바일 접속 링크를 사용해 주세요.')
        if self.headers.get('Transfer-Encoding'):
            return self.message(400, '지원하지 않는 요청입니다.')
        try:
            target = urlsplit(self.path)
            if target.scheme or target.netloc or not self.path.startswith('/'):
                return self.message(400, '올바른 접속 경로가 아닙니다.')
            query = parse_qs(target.query, keep_blank_values=True, max_num_fields=50)
        except ValueError:
            return self.message(400, '올바른 접속 경로가 아닙니다.')
        if 'key' in query:
            values = query['key']
            valid = (self.command == 'GET' and target.path == '/' and len(values) == 1
                     and secrets.compare_digest(values[0].encode('utf-8'), token.encode('utf-8')))
            if not valid:
                return self.message(401, '접속 링크가 올바르지 않습니다. 전달받은 링크를 다시 열어 주세요.')
            self.send_response(303)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', f'{COOKIE_NAME}={token}; Max-Age=86400; Path=/; Secure; HttpOnly; SameSite=Lax')
            self.send_header('Content-Length', '0')
            self.privacy_headers()
            self.end_headers()
            return
        if not self.authorized(token):
            return self.message(401, '전달받은 전용 접속 링크로 먼저 열어 주세요.')
        body = None
        headers = {'Host': f'{UPSTREAM[0]}:{UPSTREAM[1]}'}
        if self.command == 'POST':
            if self.headers.get_all('Origin') != [f'https://{host}']:
                return self.message(403, '이 페이지에서만 음성을 생성할 수 있습니다.')
            content_type = self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
            if content_type != 'application/json':
                return self.message(415, 'JSON 요청이 필요합니다.')
            lengths = self.headers.get_all('Content-Length', [])
            try:
                if len(lengths) != 1:
                    raise ValueError()
                length = int(lengths[0])
                if not 0 < length <= 65536:
                    raise ValueError()
            except ValueError:
                return self.message(413, '요청 크기를 줄여 주세요.')
            self.connection.settimeout(15)
            try:
                body = self.rfile.read(length)
            except (OSError, TimeoutError):
                return self.message(400, '요청을 읽을 수 없습니다.')
            if len(body) != length:
                return self.message(400, '요청이 완전하지 않습니다.')
            headers['Content-Type'] = 'application/json'
        elif self.headers.get('Range'):
            headers['Range'] = self.headers['Range']
        connection = http.client.HTTPConnection(*UPSTREAM, timeout=15)
        started = False
        try:
            # Origin and Cookie are intentionally not forwarded after validation.
            connection.request('GET' if self.command == 'HEAD' else self.command,
                               self.path, body=body, headers=headers)
            response = connection.getresponse()
            self.send_response(response.status)
            for name in ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges'):
                value = response.getheader(name)
                if value is not None:
                    self.send_header(name, value)
            self.privacy_headers()
            self.end_headers()
            started = True
            if self.command != 'HEAD':
                while chunk := response.read(65536):
                    self.wfile.write(chunk)
        except (OSError, http.client.HTTPException):
            if not started:
                self.message(502, '로컬 음성 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.')
        finally:
            connection.close()

    do_GET = handle_proxy
    do_POST = handle_proxy
    do_HEAD = handle_proxy

    def reject_method(self):
        self.message(405, '지원하지 않는 요청 방식입니다.')

    do_OPTIONS = do_PUT = do_PATCH = do_DELETE = do_CONNECT = do_TRACE = reject_method


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8790)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), MobileGateway)
    print(f'Mobile gateway ready on 127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
