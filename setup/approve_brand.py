#!/usr/bin/env python3
"""approve_brand.py: the owner has seen the preview and said yes. Writes brand/brand.lock, the hash of brand.json.

Rendering refuses to start without this file. If brand.json changes later, build_brand.py clears the lock.
Only run this after the owner has said yes in plain words.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / 'brand' / 'brand.json'
REPORT = ROOT / 'brand' / 'build_report.json'
PREVIEW = ROOT / 'brand' / 'preview' / 'index.html'
LOCK = ROOT / 'brand' / 'brand.lock'


def main():
    if not BRAND.exists():
        sys.exit('There is no brand/brand.json yet. Run /shorts-setup first.')
    if not REPORT.exists():
        sys.exit('The brand has not been built. Run: python3 setup/build_brand.py')
    if not PREVIEW.exists():
        sys.exit('There is no preview to approve. Run: python3 setup/preview.py')
    sha = hashlib.sha256(BRAND.read_bytes()).hexdigest()
    report = json.loads(REPORT.read_text())
    if report.get('brand_sha') != sha:
        sys.exit('brand.json changed after the last build. Run: python3 setup/build_brand.py, then python3 setup/preview.py, and look again.')
    if PREVIEW.stat().st_mtime < REPORT.stat().st_mtime:
        sys.exit('The preview is older than the last build. Run: python3 setup/preview.py, and look again.')
    fails = [c for c in report.get('checks', []) if not c.get('ok')]
    if fails:
        for c in fails:
            print('FAIL: %s is %.2f:1 and needs %.1f:1.' % (c['name'], c['ratio'], c['min']))
        sys.exit('Text in the brand cannot be read. Fix these first, then build again.')
    LOCK.write_text('%s approved %s\n' % (sha, time.strftime('%Y-%m-%d %H:%M')))
    print('Approved. The look is locked, and rendering is now allowed.')
    print('To change the look later, edit brand/brand.json and run the build. You will approve again.')


if __name__ == '__main__':
    main()
