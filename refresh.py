"""One-shot refresh: collect new friend posts, then rebuild feed.html.

Usage: python refresh.py [--scrolls 25] [--days 14] [--quiet]

Single run at a time: data/refresh.lock (stale after 60 min). Progress and the
last result go to data/refresh_status.json (read by the page's Refresh button).
With --quiet (daily cron job) it prints nothing on success, one line on failure.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
LOCK = DATA / 'refresh.lock'
STATUS = DATA / 'refresh_status.json'
STALE = 60 * 60


def write_status(**kw):
    DATA.mkdir(exist_ok=True)
    STATUS.write_text(json.dumps(kw, ensure_ascii=False), encoding='utf-8')


def pid_alive(pid):
    """Liveness check. Windows needs the Win32 API (os.kill(pid, 0) would terminate it there)."""
    if sys.platform != 'win32':
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == 259  # STILL_ACTIVE


def lock_active():
    """True while a live refresh holds the lock; clears a lock left by a killed run."""
    try:
        pid = int(LOCK.read_text().strip() or 0)
    except (FileNotFoundError, ValueError):
        return LOCK.exists()
    if pid_alive(pid) and time.time() - LOCK.stat().st_mtime < STALE:
        return True
    LOCK.unlink(missing_ok=True)
    return False


def take_lock():
    DATA.mkdir(exist_ok=True)
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if lock_active():
            return False
        return take_lock()
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scrolls', type=int, default=25)
    ap.add_argument('--days', type=int, default=14)
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if not take_lock():
        if not a.quiet:
            print('refresh already running, skipped')
        return 0
    started = datetime.now().isoformat(timespec='seconds')
    write_status(state='running', started=started)
    steps = [('facebook', [sys.executable, '-u', 'collect_fb.py', 'feed', '--scrolls', str(a.scrolls)]),
             ('instagram', [sys.executable, '-u', 'collect_ig.py', '--scrolls', str(a.scrolls)]),
             ('build', [sys.executable, 'build_feed.py', '--days', str(a.days)])]
    lines, failed = [], []
    try:
        for name, cmd in steps:
            try:
                with tempfile.TemporaryFile() as fo, tempfile.TemporaryFile() as fe:
                    rc = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=fo, stderr=fe,
                                        timeout=1800).returncode
                    fo.seek(0)
                    fe.seek(0)
                    stdout = fo.read().decode('utf-8', errors='replace')
                    stderr = fe.read().decode('utf-8', errors='replace')
                out = stdout.strip().splitlines()
                last = out[-1] if out else ''
                if rc != 0:
                    err = (stderr.strip().splitlines() or [''])[-1]
                    failed.append(name)
                    last = f'{name} FAILED: {last if last.startswith("STOP") else err or last}'
            except subprocess.TimeoutExpired:
                failed.append(name)
                last = f'{name} FAILED: timed out after 30 min'
            lines.append(last)
            if not a.quiet:
                print(last, flush=True)
    finally:
        write_status(state='error' if failed else 'done', started=started,
                     finished=datetime.now().isoformat(timespec='seconds'), summary=lines, failed=failed)
        LOCK.unlink(missing_ok=True)
    if failed:
        print('⚠️ Friends feed refresh failed: ' + ' | '.join(l for l in lines if 'FAILED' in l))
        return 1
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
