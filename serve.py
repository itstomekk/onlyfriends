"""Serve the friends feed on http://127.0.0.1:8766 with a working Refresh button.

Usage: python serve.py [--port 8766] [--demo]

Localhost only. Serves feed.html and data/media/* and nothing else from data/.
--demo serves a 100% synthetic fixture (demo/) instead, with the Refresh button off.
POST /refresh starts refresh.py in the background (refresh.py's own lock stops
double runs, including the daily cron job); GET /status returns its progress.
"""
import argparse
import json
import subprocess
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
from refresh import lock_active

ROOT = Path(__file__).resolve().parent
STATUS = ROOT / 'data' / 'refresh_status.json'
FEED = '/feed.html'
MEDIA_PREFIX = '/data/media/'
DEMO = False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/status':
            if DEMO:
                return self.send_json(200, {'state': 'idle'})
            st = json.loads(STATUS.read_text(encoding='utf-8')) if STATUS.exists() else {'state': 'idle'}
            # LOCK appears a moment after Popen; treat the first 20 s as running too
            if lock_active() or time.time() - getattr(self.server, 'kicked', 0) < 20:
                st['state'] = 'running'
            elif st.get('state') == 'running':  # run was killed before it could write a result
                st = {'state': 'error', 'summary': ['refresh FAILED: interrupted, click Refresh again']}
            return self.send_json(200, st)
        if path in ('/', '/feed.html'):
            self.path = FEED
            return super().do_GET()
        if path.startswith(MEDIA_PREFIX) and '..' not in path:
            return super().do_GET()
        self.send_error(404)

    def do_POST(self):
        if self.path != '/refresh' or DEMO:
            return self.send_error(404)
        if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{self.server.server_port}',
                                              f'http://localhost:{self.server.server_port}'):
            return self.send_error(403)  # no cross-site triggering
        if lock_active():
            return self.send_json(409, {'state': 'running'})
        subprocess.Popen([sys.executable, 'refresh.py', '--quiet'], cwd=ROOT,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.server.kicked = time.time()
        self.send_json(202, {'state': 'started'})


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=int(config.get('port')))
    ap.add_argument('--demo', action='store_true', help='serve synthetic demo data only')
    a = ap.parse_args()
    port = a.port
    if a.demo:
        import build_feed
        build_feed.use_demo()
        build_feed.build(14)
        DEMO, FEED, MEDIA_PREFIX = True, '/demo/feed.html', '/demo/media/'
    print(f'onlyfriends{" (demo)" if DEMO else ""}: http://127.0.0.1:{port}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
