#!/usr/bin/env python3
"""Build script: scan notes/ directory and generate notes.json"""
import json, os, re
from datetime import datetime

NOTES_DIR = 'notes'
OUTPUT = 'notes.json'

def parse_filename(name):
    stem = name[:-3]  # remove .md
    date = None
    # Try YYYY-MM-DD-标题 or YYYY_MM_DD-标题
    m = re.match(r'^(\d{4})[-_](\d{2})[-_](\d{2})[-_\s]*(.*)', stem)
    if m:
        date = f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
        title = m.group(4).strip()
    else:
        title = stem
        filepath = os.path.join(NOTES_DIR, name)
        try:
            ts = os.path.getmtime(filepath)
            date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except:
            date = datetime.now().strftime('%Y-%m-%d')
    return date, title or stem

notes = []
for fname in sorted(os.listdir(NOTES_DIR), reverse=True):
    if not fname.endswith('.md'):
        continue
    fpath = os.path.join(NOTES_DIR, fname)
    date, title = parse_filename(fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        text = f.read()
    # Use first line as title, fallback to filename-derived title
    first_line = text.split('\n')[0].strip()[:50] if text.strip() else title
    display_title = first_line or title
    notes.append({
        'filename': fname,
        'title': display_title,
        'date': date,
        'id': fname[:-3],
        'text': text,
    })

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(notes, f, ensure_ascii=False, indent=2)

print(f'✓ {OUTPUT} を生成しました（{len(notes)}件のノート）')
