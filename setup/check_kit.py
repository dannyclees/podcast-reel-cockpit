#!/usr/bin/env python3
"""check_kit.py --banned <file>: the shipping gate. Run it on the kit before it goes to anyone.

Fails on: words from the banned list (in file contents and in file names), things that look like keys, colour literals outside the
brand files, absolute paths into someone's machine, big binaries, media or font files, and generated files left behind by a test.
The banned list is a separate file that does not ship, one word or phrase per line. Lines starting with # are comments.

  python3 setup/check_kit.py --banned /some/private/banned.txt
  python3 setup/check_kit.py --banned list.txt --allow-colors "app/public/logos.js" --allow-colors "brand/marks/*"
"""
import argparse
import fnmatch
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', '.venv-align', '.vercel'}
BIG_MB = 2.0
BINARY_EXT = {'.mp4', '.mov', '.m4a', '.mp3', '.wav', '.aac', '.flac', '.cube', '.3dl', '.ttf', '.otf', '.woff', '.woff2', '.mkv', '.webm', '.zip', '.tar', '.gz', '.psd', '.bin', '.pt', '.onnx'}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.pdf'}
# built by the owner's own setup, so nothing here may exist in a clean kit
GENERATED = ['brand/brand.json', 'brand/brand.lock', 'brand/brand.css', 'brand/answers.json', 'brand/build_report.json', 'brand/.build_cache.json', 'brand/grabbed.json', 'brand/logo.png',
             'brand/fonts', 'brand/textures', 'brand/sfx', 'brand/music', 'brand/preview', 'brand/grabbed', 'brand/directions',
             'motion/kit/brand.css', 'motion/kit/fonts', 'motion/kit/img', 'motion-library/shared/brand.css', 'motion-library/shared/fonts', 'motion-library/shared/logo.png',
             'app/public/brand.css', 'app/public/brand.js', 'app/public/fonts', 'app/public/img', 'app/api/_brand.js', '.env', 'bin/face_track', 'bin/frame_scan', 'bin/models', 'rules/MY-RULES.md', 'BUILD-CONTRACT.md']
# colours are allowed in the brand template, the setup code that draws brands, and the kit's own copy of third-party minified code
COLOR_OK = ['brand/*', 'setup/*', '*.min.js', 'docs/*', 'app/public/logos.js', 'app/tests/*']
NEUTRAL = re.compile(r'\b(?:rgba?)\(\s*(?:0\s*,\s*0\s*,\s*0|255\s*,\s*255\s*,\s*255)\b|#(?:000|fff|333)(?:000|fff)?\b', re.I)
STATUS = ['#FF0033', '#25F4EE', '#FE2C55', '#2F5FD0', '#1F9D55', '#C2362F', '47,95,208', '31,157,85', '#808080', '#111', '#8A1F1F', '#a82c26', '#2552BC', '#FEDA75', '#FA7E1E', '#D62976', '#962FBF', '#4F5BD5', '#285AEB', '#D6249F', '#FD5949', '#FDF497']   # platform and status colours: meaning, not brand
COLOR = re.compile(r'(?<![\w&/-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b(?![\w-])|\b(?:rgba?|hsla?)\(\s*\d')
SECRET = [('long hex string', re.compile(r'\b[0-9a-fA-F]{32,}\b')),
          ('JWT', re.compile(r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')),
          ('secret key prefix', re.compile(r'\b(?:sk|pk|rk)[_-](?:live|test|ant|proj)?[_-]?[A-Za-z0-9_-]{16,}')),
          ('key= with a value', re.compile(r'(?i)\b[\w-]*(?:api[_-]?key|secret|token|password|passwd|service[_-]?key)\b\s*[=:]\s*["\']?[A-Za-z0-9_\-./+]{12,}')),
          ('key in a URL', re.compile(r'(?i)[?&](?:api[_-]?key|key|token|apikey|secret)=[A-Za-z0-9_\-.]{8,}'))]
PATHS = re.compile(r'(?:/Users/[A-Za-z0-9._-]+|/home/[a-z0-9._-]+/|/private/tmp/|/private/var/|~/(?:Desktop|Documents|Downloads|code|Library|\.[a-z])|C:\\\\Users)')


def matches(rel, patterns):
    return any(fnmatch.fnmatch(rel, p) for p in patterns)


def main():
    ap = argparse.ArgumentParser(description='The shipping gate for the kit.')
    ap.add_argument('--banned', required=True, help='a file of banned words, one per line. It does not ship.')
    ap.add_argument('--allow-colors', action='append', default=[], help='a path pattern where colour literals are fine, for example third-party logo files')
    ap.add_argument('--ignore', action='append', default=[], help='a path pattern to skip completely')
    ap.add_argument('--root', default=str(ROOT), help='the folder to scan')
    ap.add_argument('--max', type=int, default=400, help='how many problems to print')
    a = ap.parse_args()

    root = Path(a.root).resolve()
    words = []
    for line in Path(a.banned).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            words.append(line)
    banned = re.compile(r'(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])' % '|'.join(re.escape(w) for w in sorted(words, key=len, reverse=True)), re.I) if words else None
    color_ok = COLOR_OK + a.allow_colors
    problems = []
    scanned = 0

    def add(kind, where, what=''):
        problems.append((kind, where, what))

    for g in GENERATED:
        if (root / g).exists():
            add('left behind', g, 'generated or private file should not ship')

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.resolve() == SELF or p.resolve() == Path(a.banned).resolve():
                continue
            rel = str(p.relative_to(root))
            if matches(rel, a.ignore):
                continue
            scanned += 1
            if banned and banned.search(rel):
                add('banned word in a file name', rel, banned.search(rel).group(0))
            size = p.stat().st_size
            ext = p.suffix.lower()
            if size > BIG_MB * 1e6:
                add('big file', rel, '%.1f MB' % (size / 1e6))
            if ext in BINARY_EXT:
                add('binary file', rel, ext)
                continue
            if ext in IMAGE_EXT:
                add('image file', rel, 'check it is yours to ship')
                continue
            try:
                text = p.read_text(encoding='utf8')
            except (UnicodeDecodeError, OSError):
                add('binary file', rel, 'not text')
                continue
            minified = ext == '.js' and fn.endswith('.min.js')
            for n, line in enumerate(text.splitlines(), 1):
                short = line.strip()[:110]
                if banned and not minified:   # a third-party library's author line is not ours
                    m = banned.search(line)
                    if m:
                        add('banned word', '%s:%d' % (rel, n), '%s: %s' % (m.group(0), short))
                if minified:
                    continue
                for name, rx in SECRET:
                    m = rx.search(line)
                    if m:
                        add('looks like a key (%s)' % name, '%s:%d' % (rel, n), m.group(0)[:6] + '...')     # never print the whole value
                if PATHS.search(line):
                    add('absolute path', '%s:%d' % (rel, n), short)
                if not matches(rel, color_ok):
                    bare = NEUTRAL.sub('', line).replace('#feed', '')
                    for w in STATUS:
                        bare = bare.replace(w, '')
                    m = COLOR.search(bare)
                    if m:
                        add('colour literal', '%s:%d' % (rel, n), short)

    if problems:
        kinds = {}
        for k, w, x in problems:
            kinds[k] = kinds.get(k, 0) + 1
        for k, w, x in problems[:a.max]:
            print('FAIL  %-30s %s  %s' % (k, w, x))
        if len(problems) > a.max:
            print('... and %d more.' % (len(problems) - a.max))
        print()
        print('Scanned %d files. %d problems:' % (scanned, len(problems)))
        for k in sorted(kinds, key=lambda z: -kinds[z]):
            print('  %d  %s' % (kinds[k], k))
        sys.exit(1)
    print('PASS: scanned %d files. Nothing found.' % scanned)


if __name__ == '__main__':
    main()
