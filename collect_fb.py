"""Collect your Facebook friends list and friends-only feed posts (read-only).

Usage:
  python collect_fb.py friends            # refresh data/fb_friends.json
  python collect_fb.py feed [--scrolls N]  # append friends' posts to data/posts.jsonl

Uses your own logged-in Facebook session via ab.py (settings: config.py).
Never likes, comments, shares or posts. Stops on a login wall/checkpoint.
"""
import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import config
from ab import run

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
JS = ROOT / 'js'
FRIENDS = DATA / 'fb_friends.json'
POSTS = DATA / 'posts.jsonl'
REJECTS = DATA / 'fb_rejected_last_run.json'
FEED_URL = 'https://www.facebook.com/?filter=friends&sk=h_chr'


def profile():
    return str(config.get('fb_profile', required=True)).strip().strip('/')


def friends_url():
    me = profile()
    if me.isdigit():
        return f'https://www.facebook.com/profile.php?id={me}&sk=friends_all'
    return f'https://www.facebook.com/{me}/friends_all'


def fb(*args, timeout=90):
    code, out = run('facebook', *args, timeout=timeout)
    if code != 0:
        raise RuntimeError(f'agent-browser {args[0]} failed: {out[:200]}')
    return out


def eval_json(js_file):
    me = profile()
    self_key = ('id:' + me) if me.isdigit() else me.lower()
    code = (JS / js_file).read_text(encoding='utf-8').replace('__SELF__', self_key)
    out = fb('eval', code, timeout=120)
    value = json.loads(out)
    return json.loads(value) if isinstance(value, str) else value


def check_logged_in():
    url = fb('get', 'url')
    walls = fb('get', 'count', 'input[name=pass]')
    if 'login' in url or 'checkpoint' in url or walls.strip() not in ('0', ''):
        raise SystemExit(f'STOP: Facebook login wall or checkpoint at {url}. You must clear it in the session window.')


def pause(lo=2.5, hi=5.0):
    time.sleep(random.uniform(lo, hi))


def collect_friends(max_scrolls=400):
    fb('open', friends_url(), timeout=120)
    pause(5, 7)
    check_logged_in()
    friends, stale = {}, 0
    for i in range(max_scrolls):
        found = eval_json('fb_friends_extract.js')
        before = len(friends)
        friends.update(found)
        stale = stale + 1 if len(friends) == before else 0
        if i % 10 == 0:
            print(f'  scroll {i}: {len(friends)} friends', flush=True)
        if stale >= 6:
            break
        fb('press', 'End')
        pause(2, 3.5)
    if len(friends) < 20:
        raise SystemExit(f'STOP: only {len(friends)} friends found, probably a login wall. Not saving.')
    DATA.mkdir(exist_ok=True)
    FRIENDS.write_text(json.dumps({
        'captured_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'count': len(friends), 'friends': friends}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'friends saved: {len(friends)} -> {FRIENDS}')


def load_seen():
    seen = set()
    if POSTS.exists():
        for line in POSTS.read_text(encoding='utf-8').splitlines():
            try:
                seen.add(json.loads(line)['id'])
            except Exception:
                pass
    return seen


JUNK = re.compile(r'^(\d+[mhdwy]|\d+\s*(min|mins|hrs?)|.*\bago|just now|yesterday.*|·|· ?follow|follow|sponsored|see more|see less|'
                  r'like|comment|share|send|reply|all reactions:|\d[\d.,]*[km]?|\d+ comments?|\d+ shares?|'
                  r'\d+:\d+ / \d+:\d+|original audio|.*· original audio|online status indicator|active|interested|going)$', re.I)
TIME = re.compile(r'^(\d+[mhdwy]|just now|yesterday.*|[a-z]+ \d{1,2}( at .*)?(, \d{4})?)$', re.I)


def fallback_text(p):
    """Readable body for posts without a message node (shares, reels, events)."""
    lines = [l.strip() for l in (p.get('raw_text') or '').split('\n')]
    body, seen = [], set()
    skip = {(p.get('author') or '').strip(), (p.get('header') or '').strip()}
    for l in lines:
        if l.startswith('All reactions') or l in ('Like', 'Comment'):
            break
        if not l or l in skip or JUNK.match(l) or l in seen:
            continue
        seen.add(l)
        body.append(l)
    return '\n'.join(body)[:3000]


def guess_time(p):
    if p.get('time_text') and TIME.match(p['time_text']):
        return p['time_text']
    for l in (p.get('raw_text') or '').split('\n')[:8]:
        l = l.strip()
        if re.fullmatch(r'\d+[mhdwy]|just now', l, re.I):
            return l
    return p.get('time_text')


def post_id(p):
    if p.get('permalink'):
        u = urlsplit(p['permalink'])
        q = parse_qs(u.query)
        keep = '&'.join(f'{k}={q[k][0]}' for k in ('story_fbid', 'fbid', 'id', 'v') if k in q)
        return 'fb:' + u.path.rstrip('/') + ('?' + keep if keep else '')
    return 'fb:' + (p.get('author_key') or '') + ':' + (p.get('text') or '')[:80]


def collect_feed(scrolls=30):
    if not FRIENDS.exists():
        raise SystemExit('Run "python collect_fb.py friends" first.')
    friends = json.loads(FRIENDS.read_text(encoding='utf-8'))['friends']
    fb('open', FEED_URL, timeout=120)
    pause(5, 7)
    check_logged_in()
    seen = load_seen()
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    kept, rejected, found = 0, {}, {}
    DATA.mkdir(exist_ok=True)
    for i in range(scrolls):
        fb('eval', (JS / 'fb_expand.js').read_text(encoding='utf-8'))
        pause(1.0, 1.8)
        if 'facebook.com/?' not in fb('get', 'url'):
            fb('back')
            pause(3, 4)
        for p in eval_json('fb_feed_extract.js'):
            pid = post_id(p)
            key = p.get('author_key')
            if key not in friends:
                rejected[pid] = {'author': p.get('author'), 'key': key,
                                 'head': (p.get('raw_text') or '')[:100]}
                continue
            if pid in seen:
                continue
            text = re.sub(r'\s*(See less|Zobacz mniej)\s*$', '', p.get('text') or fallback_text(p))
            rec = {'id': pid, 'platform': 'facebook', 'captured_at': now,
                   'author': friends.get(key) or p['author'], 'author_key': key,
                   'author_url': p.get('author_url'), 'header': p.get('header'),
                   'group': p.get('group'), 'permalink': p.get('permalink'),
                   'time_text': guess_time(p), 'text': text,
                   'images': p.get('images') or [], 'has_video': p.get('has_video')}
            old = found.get(pid)
            if old:  # keep the richest capture (expanded text, loaded images)
                if len(text) > len(old['text'] or ''):
                    old['text'] = text
                if len(rec['images']) > len(old['images']):
                    old['images'] = rec['images']
            else:
                rec['seq'] = len(found)
                found[pid] = rec
        print(f'  scroll {i + 1}/{scrolls}: friends {len(found)}, filtered {len(rejected)}', flush=True)
        fb('scroll', 'down', str(random.randint(1400, 2200)))
        pause()
    with POSTS.open('a', encoding='utf-8') as out:
        for rec in found.values():
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            kept += 1
    REJECTS.write_text(json.dumps(rejected, ensure_ascii=False, indent=1), encoding='utf-8')
    fb('close')  # driver-owned window only; saved login state is kept
    print(f'feed done: {kept} new friend posts, {len(rejected)} filtered (pages/ads/others)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['friends', 'feed'])
    ap.add_argument('--scrolls', type=int, default=30)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    if a.mode == 'friends':
        collect_friends()
    else:
        collect_feed(a.scrolls)


if __name__ == '__main__':
    main()
