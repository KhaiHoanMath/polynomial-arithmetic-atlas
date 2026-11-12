#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Create an optional owner backup of the original website source under author-only/."""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_ONLY = ROOT / 'author-only'
COPYRIGHT = '© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.'
SOURCE_FOLDERS = ('content', 'scripts', 'static', '.github')
SOURCE_FILES = ('README.md', 'EDITORIAL.md', 'LICENSE', 'package.json', 'package-lock.json', '.gitignore')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=AUTHOR_ONLY / 'backups',
                        help='Output directory under author-only/ (default: author-only/backups).')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    backup = (output / 'polynomial-atlas-owner-backup.zip').resolve()
    checksums = (output / 'SHA256SUMS.txt').resolve()
    for path in (output, backup, checksums):
        if any(path.is_relative_to(ROOT / folder) for folder in ('dist', 'static')):
            parser.error('Generated files must not be written under dist/ or static/.')
        if not path.is_relative_to(AUTHOR_ONLY):
            parser.error('Generated files must remain under the repository author-only/ directory.')

    if not (ROOT / 'LICENSE').is_file():
        parser.error('The repository LICENSE is required for an owner backup.')
    catalogue = json.loads((ROOT / 'content/references.json').read_text())
    review_date = date.fromisoformat(catalogue['checked_through'])
    stamp = (review_date.year, review_date.month, review_date.day, 0, 0, 0)
    output.mkdir(parents=True, exist_ok=True)

    def add(archive, name, data):
        info = ZipInfo('polynomial-arithmetic-atlas/' + name, stamp)
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, data)

    with ZipFile(backup, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        archive.comment = COPYRIGHT.encode('utf-8')
        for folder in SOURCE_FOLDERS:
            for path in sorted((ROOT / folder).rglob('*')):
                relative = path.relative_to(ROOT)
                if (not path.is_file() or path.is_symlink()
                        or '__pycache__' in relative.parts or path.suffix == '.pyc'
                        or 'downloads' in relative.parts):
                    continue
                add(archive, relative.as_posix(), path.read_bytes())
        for name in SOURCE_FILES:
            path = ROOT / name
            if path.is_file() and not path.is_symlink():
                add(archive, name, path.read_bytes())
        add(archive, 'COPYRIGHT.txt', (
            COPYRIGHT + '\n\n'
            'Owner backup of the Polynomial Arithmetic Atlas source.\n'
            'This archive is not part of the published website.\n'
            'The repository LICENSE governs the original atlas material.\n'
            'Cited works and third-party components retain their respective rights.\n'
        ).encode('utf-8'))

    digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    checksums.write_text(digest + '  ' + backup.name + '\n', encoding='utf-8')
    print(f'Created owner backup: {backup} ({backup.stat().st_size:,} bytes).')


if __name__ == '__main__':
    main()
