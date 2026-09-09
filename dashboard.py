"""Local processing console. Run: python dashboard.py"""
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = Path(__file__).resolve().parent
EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.bmp'}
_NO_WINDOW_FLAGS = 0x08000000 if sys.platform == 'win32' else 0
_SCRIPT_NAME = 'automate_docling_oneplus_sort.py'


def _find_existing_run():
    if sys.platform == 'win32':
        command = "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?(.exe)?$' -and $_.CommandLine -like '*automate_docling_oneplus_sort.py*' } | Select-Object -ExpandProperty ProcessId"
        result = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True, creationflags=_NO_WINDOW_FLAGS)
        return bool(result.stdout.strip())
    proc_root = Path('/proc')
    for entry in proc_root.iterdir() if proc_root.is_dir() else []:
        if entry.name.isdigit():
            try:
                if any(_SCRIPT_NAME.encode() in part for part in (entry / 'cmdline').read_bytes().split(b'\0')):
                    return True
            except OSError:
                pass
    return False


class ProcessRunner:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.logs = deque(maxlen=1500)
        log_path = ROOT / 'sorted' / 'processing.log'
        if log_path.exists():
            self.logs.extend(log_path.read_text(encoding='utf-8', errors='replace').splitlines()[-1500:])
        self.exit_code = None

    def start(self, pages):
        with self.lock:
            if self.process and self.process.poll() is None:
                raise ValueError('Processing is already running')
            if _find_existing_run():
                raise ValueError('A sorting script is running in another terminal. Stop it first.')
            launch = {}
            if os.name == 'nt':
                launch['creationflags'] = 0x08000000
            self.process = subprocess.Popen([sys.executable, '-u', str(ROOT / 'automate_docling_oneplus_sort.py'), '--pages', str(pages)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', **launch)
            self.exit_code = None
            threading.Thread(target=self.read, args=(self.process,), daemon=True).start()

    def read(self, process):
        for line in process.stdout:
            with self.lock:
                self.logs.append(line.rstrip())
        code = process.wait()
        with self.lock:
            self.exit_code = code
            self.logs.append(f'Process exited with code {code}')

    def stop(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.logs.append('Stop requested. Check OnePlus status: server work may continue.')

    def snapshot(self):
        with self.lock:
            running = self.process is not None and self.process.poll() is None
            return dict(running=running, pid=self.process.pid if running else None,
                        exit_code=self.exit_code, logs=list(self.logs))


def probe(url):
    try:
        r = requests.get(url, timeout=3)
        r.raise_for_status()
        return {'ok': True, 'data': r.json()}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}


runner = ProcessRunner()
state_lock = threading.Lock()
state = {'updated': None, 'files': [], 'servers': {}, 'results': []}


def monitor():
    endpoints = {'docling': 'http://192.168.68.63:5001/health',
                 'oneplus': 'http://192.168.68.60:8080/health',
                 'slots': 'http://192.168.68.60:8080/slots'}
    with ThreadPoolExecutor(max_workers=3) as pool:
        while True:
            servers = dict(zip(endpoints, pool.map(probe, endpoints.values())))
            files = []
            for p in (ROOT / 'input').rglob('*'):
                try:
                    if p.is_file() and p.suffix.lower() in EXTENSIONS:
                        stat = p.stat()
                        files.append({'name': str(p.relative_to(ROOT / 'input')), 'size': stat.st_size})
                except OSError:
                    pass
            results = {}
            manifest = ROOT / 'sorted' / 'manifest.jsonl'
            if manifest.exists():
                for line in manifest.read_text(encoding='utf-8', errors='replace').splitlines():
                    try:
                        record = json.loads(line)
                        results[record['source']] = record
                    except (ValueError, KeyError):
                        pass
            with state_lock:
                state.update(updated=time.time(), files=files, servers=servers, results=list(results.values()))
            time.sleep(3)


class Handler(BaseHTTPRequestHandler):
    def respond(self, body, status=200, content_type='application/json'):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            return self.respond((ROOT / 'dashboard.html').read_bytes(), content_type='text/html; charset=utf-8')
        if self.path == '/api/status':
            with state_lock:
                snapshot = dict(state)
            snapshot['process'] = runner.snapshot()
            return self.respond(snapshot)
        self.respond({'error': 'Not found'}, 404)

    def do_POST(self):
        # Only same-origin UI requests may control the local process. In a
        # container, Host is the ZimaOS address rather than 127.0.0.1.
        origin = self.headers.get('Origin')
        host = self.headers.get('Host', '')
        allowed_origins = {'http://127.0.0.1:8765', 'http://localhost:8765',
                           f'http://{host}', f'https://{host}'}
        if origin and origin not in allowed_origins:
            return self.respond({'error': 'Origin rejected'}, 403)
        try:
            if self.path == '/api/start':
                body = json.loads(self.rfile.read(min(int(self.headers.get('Content-Length', 0)), 1024)))
                pages = body.get('pages', 2)
                if pages not in (1, 2, 3):
                    raise ValueError('Pages must be 1, 2 or 3')
                runner.start(pages)
            elif self.path == '/api/stop':
                runner.stop()
            else:
                return self.respond({'error': 'Not found'}, 404)
            self.respond({'ok': True})
        except Exception as exc:
            self.respond({'error': str(exc)}, 400)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    threading.Thread(target=monitor, daemon=True).start()
    host = os.environ.get('DASHBOARD_HOST', '127.0.0.1')
    port = int(os.environ.get('DASHBOARD_PORT', '8765'))
    print(f'Document console: http://{host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
