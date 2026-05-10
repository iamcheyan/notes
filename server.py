#!/usr/bin/env python3
"""Local dev server for 片语 — serves static files + handles /api/save + auto-push"""
import http.server
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
ROOT = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.join(ROOT, 'notes')
BUILD_SCRIPT = os.path.join(ROOT, 'build.py')
GIT_REMOTE = 'origin'


def git_auto_push():
    """Auto-commit and push changes to remote in background."""
    try:
        subprocess.run(['git', 'add', '-A'], cwd=ROOT,
                       capture_output=True, timeout=30)
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'],
                                cwd=ROOT, capture_output=True, timeout=30)
        if result.returncode == 0:
            return  # nothing to commit
        subprocess.run(['git', 'commit', '-m', 'auto: update notes'],
                       cwd=ROOT, capture_output=True, timeout=30)
        subprocess.run(['git', 'push', GIT_REMOTE, 'main'],
                       cwd=ROOT, capture_output=True, timeout=60)
    except Exception:
        pass  # silent fail for auto-push


class NotesHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/api/save':
            self.handle_save()
        elif self.path == '/api/delete':
            self.handle_delete()
        else:
            self.send_error(404)

    def handle_delete(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            note_id = body.get('id', '')
            if not note_id:
                raise ValueError('id is empty')
            fpath = os.path.join(NOTES_DIR, f'{note_id}.md')
            if os.path.exists(fpath):
                os.remove(fpath)
            subprocess.run([sys.executable, BUILD_SCRIPT],
                           cwd=ROOT, capture_output=True)
            threading.Thread(target=git_auto_push, daemon=True).start()
            self.send_json({'ok': True})
        except Exception as e:
            self.send_json({'ok': False, 'error': str(e)}, status=400)

    def handle_save(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            text = body.get('text', '').strip()
            if not text:
                raise ValueError('text is empty')

            # Derive filename from first line
            first_line = text.split('\n')[0].strip()
            safe = re.sub(r'[\\/:*?"<>|]', '', first_line)[:30] or '未命名'
            now = datetime.now()
            date_str = now.strftime('%Y-%m-%d')
            filename = f'{date_str}-{safe}.md'
            filepath = os.path.join(NOTES_DIR, filename)

            # Write the markdown file
            os.makedirs(NOTES_DIR, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)

            # Regenerate notes.json
            subprocess.run([sys.executable, BUILD_SCRIPT],
                           cwd=ROOT, capture_output=True)
            threading.Thread(target=git_auto_push, daemon=True).start()

            self.send_json({'ok': True, 'id': filename[:-3], 'filename': filename})

        except Exception as e:
            self.send_json({'ok': False, 'error': str(e)}, status=400)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    # Silence default logging noise for static files
    def log_message(self, fmt, *args):
        if args and args[0] == 'POST':
            super().log_message(fmt, *args)


if __name__ == '__main__':
    os.chdir(ROOT)
    server = http.server.HTTPServer(('0.0.0.0', PORT), NotesHandler)
    print(f'🚀 片語 ローカルサーバー起動: http://localhost:{PORT}')
    print(f'📁 ノート保存先: {NOTES_DIR}')
    print('Ctrl+C で停止')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
        server.server_close()
