#!/usr/bin/env python3
"""doctor.py: checks this Mac has what the system needs, and builds what it can.

It never uses sudo and never prints a key. Big downloads only happen after you say yes.

  python3 setup/doctor.py                     check everything, build the two small tools. Asks before big downloads if you are at a terminal.
  python3 setup/doctor.py --tools             brew install the missing tools
  python3 setup/doctor.py --python-deps       install numpy, Pillow and fontTools for this python3
  python3 setup/doctor.py --venv              create the word aligner (about 1 GB, Python 3.12, torch)
  python3 setup/doctor.py --models large-v3-turbo,small.en     download speech models to bin/models
"""
import argparse
import importlib.util
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / 'bin'
MODELS = BIN / 'models'
VENV = BIN / '.venv-align'
HF_URL = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-%s.bin'
# Sizes are what the whisper.cpp model pages list. large-v3-turbo is the one the pipeline re-reads each clip with (retext.py).
MODEL_SIZES = {'large-v3-turbo': '1.6 GB', 'medium.en': '1.5 GB', 'small.en': '470 MB', 'base.en': '140 MB'}
NEEDED_MODEL = 'large-v3-turbo'
BREW = {'ffmpeg': 'ffmpeg', 'ffprobe': 'ffmpeg', 'node': 'node', 'npx': 'node', 'uv': 'uv', 'whisper-cli': 'whisper-cpp'}
ENV_NAMES = ['RIVERSIDE_API_KEY', 'RIVERSIDE_SHARE_KEY', 'RIVERSIDE_STUDIO_SLUG', 'AUPHONIC_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_KEY']

results = []


def line(ok, name, detail='', fix=None):
    results.append((ok, name))
    print('%s  %s%s' % ('PASS' if ok else 'FAIL', name, '  (%s)' % detail if detail else ''))
    if fix and not ok:
        print('      Fix: %s' % fix)


def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)


def version(cmd):
    try:
        out = run(cmd, timeout=30).stdout.strip().splitlines()
        return out[0][:70] if out else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def ask(question, flag):
    """A flag on the command line means the owner already said yes in chat. At a terminal we ask. Otherwise we skip."""
    if flag:
        return True
    if sys.stdin.isatty():
        return input(question + ' [y/N] ').strip().lower() in ('y', 'yes')
    return False


def check_system():
    mac = platform.system() == 'Darwin'
    line(mac, 'macOS', platform.mac_ver()[0] if mac else platform.system(), 'This system runs on a Mac only, because face tracking uses Apple Vision.')
    if not mac:
        print('Stopping here: nothing else will work on this computer.')
        sys.exit(1)
    py_ok = sys.version_info >= (3, 9)
    line(py_ok, 'python3', platform.python_version(), 'brew install python')


def check_tools(install):
    has_brew = shutil.which('brew')
    missing = sorted({BREW[t] for t in BREW if not shutil.which(t)})
    if missing and has_brew and ask('Install with Homebrew: %s?' % ', '.join(missing), install):
        for pkg in missing:
            print('Installing %s...' % pkg)
            r = subprocess.run(['brew', 'install', pkg])
            if r.returncode:
                print('      brew could not install %s. See the lines above.' % pkg)
    for tool, ver in (('ffmpeg', ['ffmpeg', '-version']), ('ffprobe', ['ffprobe', '-version']), ('node', ['node', '--version']), ('npx', ['npx', '--version']), ('uv', ['uv', '--version'])):
        ok = bool(shutil.which(tool))
        fix = 'brew install %s' % BREW[tool] if has_brew else 'Install Homebrew from https://brew.sh, then: brew install %s' % BREW[tool]
        line(ok, tool, version(ver) if ok else 'not found', fix)
    if shutil.which('node'):
        v = version(['node', '--version']).lstrip('v').split('.')[0]
        if v.isdigit() and int(v) < 20:
            line(False, 'node 20 or newer', 'you have %s' % v, 'brew upgrade node')
    swift = shutil.which('swiftc')
    ok = bool(swift) and run(['swiftc', '--version'], timeout=60).returncode == 0
    line(ok, 'swiftc', version(['swiftc', '--version']) if ok else 'not found', 'xcode-select --install   (a Mac window opens, click Install)')
    return ok


def check_python_deps(install):
    need = [('numpy', 'numpy', True), ('PIL', 'pillow', True), ('fontTools', 'fonttools', False)]
    missing = [pip for mod, pip, _ in need if not importlib.util.find_spec(mod)]
    if missing and ask('Install %s for this python3 (about 60 MB)?' % ', '.join(missing), install):
        base = [sys.executable, '-m', 'pip', 'install', '--user', '--quiet']
        r = run(base + missing)
        if r.returncode and 'externally-managed' in r.stdout:
            r = run(base + ['--break-system-packages'] + missing)    # Homebrew's python refuses --user without this. It stays in your home folder.
        if r.returncode:
            print(r.stdout[-500:])
        importlib.invalidate_caches()
    for mod, pip, required in need:
        ok = bool(importlib.util.find_spec(mod))
        if ok or required:
            line(ok, 'python: %s' % pip, '' if ok else 'not found', 'python3 setup/doctor.py --python-deps')
        else:
            print('note  python: %s is only needed for a variable font file. Add it with: python3 setup/doctor.py --python-deps' % pip)


def build_swift(can_compile):
    BIN.mkdir(exist_ok=True)
    for name, src in (('face_track', ROOT / 'pipeline' / 'vendor' / 'face_track.swift'), ('frame_scan', ROOT / 'pipeline' / 'frame_scan.swift')):
        out = BIN / name
        if not src.exists():
            line(False, 'bin/%s' % name, 'source %s is missing' % src.name, 'The kit is incomplete. Unzip it again.')
            continue
        if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
            line(True, 'bin/%s' % name, 'already built')
            continue
        if not can_compile:
            line(False, 'bin/%s' % name, 'needs swiftc', 'xcode-select --install   then run this again')
            continue
        print('Building bin/%s...' % name)
        r = run(['swiftc', '-O', str(src), '-o', str(out)], timeout=600)
        line(r.returncode == 0 and out.exists(), 'bin/%s' % name, 'built' if r.returncode == 0 else r.stdout[-300:], 'swiftc -O %s -o bin/%s' % (src.relative_to(ROOT), name))


def check_whisper():
    """The pipeline calls whisper two ways: `npx hyperframes transcribe` for the episode (it fetches its own model on the first run),
    and `whisper-cli -m bin/models/ggml-large-v3-turbo.bin` to re-read each clip."""
    w = shutil.which('whisper-cli')
    ok = bool(w) and run(['whisper-cli', '--help'], timeout=30).returncode in (0, 1)
    line(ok, 'whisper-cli', 'found' if ok else 'not found', 'brew install whisper-cpp')


def download(model):
    url = HF_URL % model
    MODELS.mkdir(parents=True, exist_ok=True)
    out = MODELS / ('ggml-%s.bin' % model)
    part = out.with_suffix('.part')
    print('Downloading %s (%s)...' % (out.name, MODEL_SIZES.get(model, 'unknown size')))
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8'})
    with urllib.request.urlopen(req, timeout=60) as r, open(part, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        done, step = 0, 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total and done * 10 // total > step:
                step = done * 10 // total
                print('  %d%%' % (step * 10), flush=True)
    if total and part.stat().st_size != total:
        part.unlink()
        raise OSError('the download was cut short')
    part.replace(out)


def check_models(wanted):
    want = [m.strip() for m in wanted.split(',') if m.strip()] if wanted else []
    for m in want:
        if m not in MODEL_SIZES:
            print('Unknown model "%s". Pick from: %s.' % (m, ', '.join(MODEL_SIZES)))
            continue
        if not (MODELS / ('ggml-%s.bin' % m)).exists():
            try:
                download(m)
            except OSError as e:
                print('      The download failed: %s. Run it again, it starts fresh.' % e)
    path = MODELS / ('ggml-%s.bin' % NEEDED_MODEL)
    if not path.exists() and not want and ask('Download the speech model %s (%s) to bin/models?' % (NEEDED_MODEL, MODEL_SIZES[NEEDED_MODEL]), False):
        try:
            download(NEEDED_MODEL)
        except OSError as e:
            print('      The download failed: %s.' % e)
    line(path.exists(), 'speech model %s' % NEEDED_MODEL, 'in bin/models' if path.exists() else '%s download, not there yet' % MODEL_SIZES[NEEDED_MODEL], 'python3 setup/doctor.py --models %s' % NEEDED_MODEL)
    print('note  The first /shorts run also fetches a free model through hyperframes, into your home cache folder: medium.en, about 1.5 GB, with no prompt.')


def check_venv(create):
    py = VENV / 'bin' / 'python'
    if not py.exists() and ask('Create the word aligner in bin/.venv-align (Python 3.12, torch, torchaudio, numpy, about 1 GB)?', create):
        if not shutil.which('uv'):
            print('      uv is needed first: brew install uv')
        else:
            print('Creating bin/.venv-align. This takes a few minutes...')
            subprocess.run(['uv', 'venv', '-p', '3.12', str(VENV)])
            subprocess.run(['uv', 'pip', 'install', '-p', str(py), 'torch', 'torchaudio', 'numpy'])
    ok = py.exists() and run([str(py), '-c', 'import torch, torchaudio, numpy'], timeout=120).returncode == 0
    line(ok, 'word aligner (bin/.venv-align)', 'ready' if ok else 'not there yet, about 1 GB', 'python3 setup/doctor.py --venv')


def check_brand():
    bj = ROOT / 'brand' / 'brand.json'
    line(bj.exists(), 'brand/brand.json', '', 'Type /shorts-setup in Claude Code.')
    line((ROOT / 'brand' / 'brand.lock').exists(), 'brand approved', '', 'Approve the preview in /shorts-setup.')


def check_env():
    """Says which keys are filled in. Never says what they are."""
    f = ROOT / '.env'
    if not f.exists():
        print('note  There is no .env yet. Copy .env.example to .env when you have your keys. Only the keys you use are needed.')
        return
    have = {}
    for ln in f.read_text().splitlines():
        if '=' in ln and not ln.lstrip().startswith('#'):
            k, v = ln.split('=', 1)
            have[k.strip()] = bool(v.strip().strip('"'))
    for name in ENV_NAMES:
        print('note  .env %s: %s' % (name, 'filled in' if have.get(name) else 'blank'))


def main():
    ap = argparse.ArgumentParser(description='Check this Mac has what the system needs.')
    ap.add_argument('--tools', action='store_true', help='brew install missing tools')
    ap.add_argument('--python-deps', action='store_true', help='install numpy, Pillow and fontTools for this python3')
    ap.add_argument('--venv', action='store_true', help='create the word aligner, about 1 GB')
    ap.add_argument('--models', default='', help='comma list of speech models to download to bin/models: ' + ', '.join('%s (%s)' % kv for kv in MODEL_SIZES.items()))
    a = ap.parse_args()

    print('Checking this Mac. Nothing big downloads without a yes.\n')
    check_system()
    can_compile = check_tools(a.tools)
    check_python_deps(a.python_deps)
    build_swift(can_compile)
    check_whisper()
    check_models(a.models)
    check_venv(a.venv)
    check_brand()
    check_env()
    fails = [n for ok, n in results if not ok]
    print()
    if fails:
        print('%d passed, %d to fix: %s.' % (len(results) - len(fails), len(fails), ', '.join(fails)))
        sys.exit(1)
    print('All %d checks passed.' % len(results))


if __name__ == '__main__':
    main()
