#!/usr/bin/env python3
"""Create reproducible source and offline distributions from the completed build."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib
import re
import json
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
DOWNLOADS = DIST / 'downloads'
review_date = date.fromisoformat(json.loads((ROOT/'content/references.json').read_text())['checked_through'])
STAMP = (review_date.year, review_date.month, review_date.day, 0, 0, 0)

def add(archive, name, data):
    info = ZipInfo(name, STAMP)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)

source = DOWNLOADS / 'polynomial-atlas-source.zip'
with ZipFile(source, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
    for folder in ['content', 'scripts', 'static', '.github']:
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                add(archive, 'polynomial-arithmetic-atlas/' + path.relative_to(ROOT).as_posix(), path.read_bytes())
    for name in ['README.md', 'EDITORIAL.md', 'package.json', 'package-lock.json', '.gitignore']:
        add(archive, 'polynomial-arithmetic-atlas/' + name, (ROOT / name).read_bytes())

offline = DOWNLOADS / 'polynomial-atlas-offline.zip'
with ZipFile(offline, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(DIST.rglob('*')):
        if not path.is_file() or path == offline or path.name == 'SHA256SUMS.txt':
            continue
        data = path.read_bytes()
        if path.suffix == '.html':
            html = data.decode('utf-8')
            html = re.sub(r'<a href="downloads/polynomial-atlas-offline\.zip"[^>]*>[^<]*</a>',
                          '<span>Offline website — this is your downloaded copy</span>', html)
            data = html.encode('utf-8')
        add(archive, path.relative_to(DIST).as_posix(), data)
    add(archive, 'START-HERE.txt', (
        'POLYNOMIAL ARITHMETIC ATLAS\n\n'
        'Extract the entire archive, then open index.html in a browser.\n'
        'No installation, account, internet connection, or server is needed\n'
        'for the handbook, search, filters, mathematics, and examples.\n'
        'External source links require internet access.\n\n'
        'Open handbook.html for one continuous printable edition.\n'
        'The complete typeset PDF and editable TeX are in downloads/.\n'
        'Downloadable reference data and editable source are in downloads/.\n'
        'The original 188-source PDF is an older fixed edition; use the\n'
        'current pages and exports for additions and corrections.\n'
    ).encode('utf-8'))

hashes = []
for path in sorted(DOWNLOADS.iterdir()):
    if path.is_file() and path.name != 'SHA256SUMS.txt':
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name)
(DOWNLOADS / 'SHA256SUMS.txt').write_text('\n'.join(hashes) + '\n')
print(f'Packaged source ({source.stat().st_size:,} bytes) and offline edition ({offline.stat().st_size:,} bytes).')
