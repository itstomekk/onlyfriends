"""Collect friends' posts from your Instagram Following feed (read-only).

Usage: python collect_ig.py [--scrolls N]

Keeps posts only from accounts in data/ig_friends.json ({"friends": {username: name}}),
minus Sponsored, Suggested, and anything in data/ig_hidden.txt (one username per line).
Without ig_friends.json it skips Instagram: "not verified" alone let creators through.
Never likes, comments or follows. Stops on a login wall/checkpoint.
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ab import run

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
JS = ROOT / 'js'
POSTS = DATA / 'posts.jsonl'
HIDDEN = DATA / 'ig_hidden.txt'
FRIENDS = DATA / 'ig_friends.json'
REJECTS = DATA / 'ig_rejected_last_run.json'
FEED_URL = 'https://www.instagram.com/?variant=following'


def ig(*args, timeout=90):
    code, out = run('instagram', *args, timeout=timeout)
    if code != 0:
        raise RuntimeError(f'agent-browser {args[0]} failed: {out[:200]}')
    return out


def eval_json(js_file):
    out = ig('eval', (JS / js_file).read_text(encoding='utf-8'), timeout=120)
    value = json.loads(out)
    return json.loads(value) if isinstance(value, str) else value


def pause(lo=2.5, hi=5.0):
    time.sleep(random.uniform(lo, hi))


def hidden():
    if not HIDDEN.exists():
        return set()
    return {l.strip().lstrip('@').lower() for l in HIDDEN.read_text(encoding='utf-8').splitlines() if l.strip()}


def load_seen():
    seen = set()
    if POSTS.exists():
        for line in POSTS.read_text(encoding='utf-8').splitlines():
            try:
                seen.add(json.loads(line)['id'])
            except Exception:
                pass
    return seen


def collect(scrolls):
    if not FRIENDS.exists():
        print('instagram skipped: no data/ig_friends.json friends list yet')
        return
    friends = {k.lower() for k in json.loads(FRIENDS.read_text(encoding='utf-8'))['friends']}
    ig('open', FEED_URL, timeout=120)
    pause(5, 7)
    url = ig('get', 'url')
    walls = ig('get', 'count', 'input[name=password]').strip()
    if 'login' in url or 'challenge' in url or 'checkpoint' in url or walls not in ('0', ''):
        raise SystemExit(f'STOP: Instagram login wall or checkpoint at {url}. You must clear it in the session window.')
    skip, seen = hidden(), load_seen()
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    found, rejected = {}, {}
    for i in range(scrolls):
        for p in eval_json('ig_feed_extract.js'):
            if not p.get('permalink') or not p.get('user'):
                continue
            pid = 'ig:' + p['permalink'].rstrip('/').rsplit('/', 1)[-1]
            why = ('sponsored' if p['sponsored'] else 'suggested' if p['suggested'] else
                   'hidden' if p['user'].lower() in skip else
                   'not a friend' if p['user'].lower() not in friends else None)
            if why:
                rejected[pid] = {'user': p['user'], 'why': why}
                continue
            if pid in seen:
                continue
            rec = {'id': pid, 'platform': 'instagram', 'captured_at': now,
                   'author': p['user'], 'author_key': 'ig:' + p['user'].lower(),
                   'author_url': f"https://www.instagram.com/{p['user']}/",
                   'permalink': p['permalink'], 'time_text': None,
                   'est_time': p.get('datetime') and p['datetime'].replace('.000Z', '+00:00'),
                   'text': p.get('text') or '', 'images': p.get('images') or [],
                   'has_video': p.get('has_video')}
            if not rec['est_time']:
                rec['est_time'] = now
            old = found.get(pid)
            if old:
                if len(rec['text']) > len(old['text']):
                    old['text'] = rec['text']
                if len(rec['images']) > len(old['images']):
                    old['images'] = rec['images']
            else:
                rec['seq'] = len(found)
                found[pid] = rec
        print(f'  scroll {i + 1}/{scrolls}: friends {len(found)}, filtered {len(rejected)}', flush=True)
        ig('scroll', 'down', str(random.randint(1200, 1900)))
        pause()
    DATA.mkdir(exist_ok=True)
    with POSTS.open('a', encoding='utf-8') as out:
        for rec in found.values():
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
    REJECTS.write_text(json.dumps(rejected, ensure_ascii=False, indent=1), encoding='utf-8')
    ig('close')  # driver-owned window only; saved login state is kept
    print(f'instagram done: {len(found)} new posts, {len(rejected)} filtered (verified/ads/suggested/hidden)')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('--scrolls', type=int, default=20)
    collect(ap.parse_args().scrolls)
