"""Build data/ig_friends.json = Instagram mutual follows (you follow them AND they follow you).

Usage: python collect_ig_friends.py [--max-pages 80]

Read-only. Slow on purpose: 100 accounts per request, 8 to 15 s between requests.
Stops at the first non-200 answer (429 = rate limited) and saves nothing partial,
because a half list would silently hide friends. Prints one summary line (easy to forward to a notifier).
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import config
from ab import run

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'ig_friends.json'
JS = (ROOT / 'js' / 'ig_follow_page.js').read_text(encoding='utf-8')


class Blocked(Exception):
    pass


def call(path):
    code, out = run('instagram', 'eval', JS.replace('__PATH__', path), timeout=90)
    if code != 0:
        raise Blocked(f'browser error: {out[:120]}')
    v = json.loads(out)
    v = json.loads(v) if isinstance(v, str) else v
    if v.get('status') != 200:
        raise Blocked(f"Instagram answered {v.get('status')} ({v.get('error', 'rate limit or checkpoint')})")
    return v


def follow_list(uid, kind, max_pages):
    users, max_id = {}, None
    for _ in range(max_pages):
        path = f'/api/v1/friendships/{uid}/{kind}/?count=100'
        if max_id:
            path += '&max_id=' + quote(str(max_id))
        if kind == 'followers':
            path += '&search_surface=follow_list_page'
        page = call(path)
        for u in page['users']:
            users[u['username'].lower()] = u
        max_id = page.get('next_max_id')
        print(f'  {kind}: {len(users)}', file=sys.stderr, flush=True)
        if not max_id:
            return users
        time.sleep(random.uniform(8, 15))
    raise Blocked(f'{kind} list longer than {max_pages} pages, not saved')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-pages', type=int, default=80)
    a = ap.parse_args()
    try:
        run('instagram', 'open', 'https://www.instagram.com/', timeout=120)
        time.sleep(random.uniform(5, 8))
        url = run('instagram', 'get', 'url')[1]
        if 'login' in url or 'challenge' in url or 'checkpoint' in url:
            raise Blocked(f'login wall or checkpoint at {url}')
        me = call(f'/api/v1/users/web_profile_info/?username={config.get("ig_username", required=True)}')
        time.sleep(random.uniform(8, 15))
        following = follow_list(me['id'], 'following', a.max_pages)
        time.sleep(random.uniform(10, 20))
        followers = follow_list(me['id'], 'followers', a.max_pages)
    except Blocked as e:
        print(f'⚠️ Instagram friends list not built: {e}. Nothing saved; Instagram stays off in the feed.')
        return 1
    finally:
        run('instagram', 'close')
    # sanity: the lists must roughly match the profile counters
    if len(following) < 0.9 * me['following'] or len(followers) < 0.9 * me['followers']:
        print(f"⚠️ Instagram friends list incomplete (following {len(following)}/{me['following']}, "
              f"followers {len(followers)}/{me['followers']}). Nothing saved.")
        return 1
    mutual = {k: following[k]['full_name'] or k for k in following if k in followers}
    OUT.write_text(json.dumps({'captured_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                               'rule': 'mutual follows', 'count': len(mutual), 'friends': mutual},
                              ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'✅ Instagram friends list ready: {len(mutual)} mutual follows (you follow {len(following)}, '
          f'{len(followers)} follow you). Instagram posts from them appear in the feed from the next refresh.')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
