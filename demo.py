"""Synthetic demo fixture for onlyfriends: 100% fictional, no network, no real data.

`generate(dir)` writes <dir>/posts.jsonl plus flat-colour SVG avatars and pictures into
<dir>/media/. Post times are relative to "now", so the demo always looks fresh.
Used by `python serve.py --demo` and `python build_feed.py --demo`.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PEOPLE = [  # (name, colour)
    ('Alex Doe', '#c2410c'), ('Jamie Roe', '#0f766e'), ('Sam Example', '#4338ca'),
    ('Taylor Sample', '#a21caf'), ('Robin Placeholder', '#b45309'), ('Morgan Test', '#0369a1'),
    ('Quinn Demo', '#15803d'), ('Avery Fiction', '#be123c'),
]

# (name index, platform, time label, group, text, pictures, video)
POSTS = [
    (0, 'facebook', '12m', None, 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. First coffee of the day, '
     'and the sun is out.', ['dawn'], False),
    (1, 'instagram', '1h', None, 'Sed ut perspiciatis unde omnis iste natus. Sunday walk, no filter needed.',
     ['hills', 'lake'], False),
    (2, 'facebook', '3h', None, 'Short and sweet: we finally finished the garden shed! Ut enim ad minim veniam.', [], False),
    (3, 'facebook', '5h', 'Weekend Hikers (demo)', 'Nemo enim ipsam voluptatem. Anyone up for the ridge trail on Saturday?',
     ['ridge'], False),
    (4, 'instagram', '9h', None, 'Quis autem vel eum iure reprehenderit. Four shades of one evening.',
     ['dusk', 'hills', 'lake', 'dawn'], False),
    (5, 'facebook', 'Yesterday', None, 'Duis aute irure dolor in reprehenderit in voluptate velit esse.\n\n'
     'Second paragraph: excepteur sint occaecat cupidatat non proident.', [], False),
    (6, 'facebook', '1d', None, 'Clip from the trip. Sunt in culpa qui officia deserunt mollit anim.', [], True),
    (7, 'instagram', '2d', None, 'Nulla pariatur. Small things that made this week good: tea, rain, a long book.',
     ['lake'], False),
    (1, 'facebook', '3d', None, 'At vero eos et accusamus et iusto odio dignissimos. New bike, who dis?', ['ridge'], False),
    (3, 'instagram', '5d', None, 'Temporibus autem quibusdam et aut officiis debitis. Good morning from the hills.',
     ['hills'], False),
]


def _scene(kind):
    sky, a, b, c = {
        'dawn': ('#fcd9b6', '#f59e0b', '#c2410c', '#7c2d12'),
        'hills': ('#cfe8f5', '#86c28b', '#3f8f5c', '#276749'),
        'lake': ('#dbeafe', '#7dd3fc', '#38bdf8', '#0369a1'),
        'ridge': ('#e9d5ff', '#a78bfa', '#7c3aed', '#4c1d95'),
        'dusk': ('#fbcfe8', '#f472b6', '#be185d', '#500724'),
    }[kind]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" role="img" aria-label="demo picture">'
            f'<rect width="800" height="600" fill="{sky}"/><circle cx="600" cy="150" r="70" fill="{a}"/>'
            f'<path d="M0 420 L180 250 L340 400 L520 230 L800 440 V600 H0Z" fill="{b}"/>'
            f'<path d="M0 500 L220 370 L430 480 L640 360 L800 470 V600 H0Z" fill="{c}"/></svg>')


def _avatar(name, colour):
    initials = ''.join(w[0] for w in name.split()[:2]).upper()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="{name}">'
            f'<circle cx="32" cy="32" r="32" fill="{colour}"/>'
            f'<text x="32" y="33" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" '
            f'font-size="26" font-weight="700" fill="#fff">{initials}</text></svg>')


def generate(out):
    out = Path(out)
    media = out / 'media'
    media.mkdir(parents=True, exist_ok=True)
    rel = media.relative_to(ROOT).as_posix()
    for kind in ('dawn', 'hills', 'lake', 'ridge', 'dusk'):
        (media / f'scene_{kind}.svg').write_text(_scene(kind), encoding='utf-8')
    for i, (name, colour) in enumerate(PEOPLE):
        (media / f'avatar_{i}.svg').write_text(_avatar(name, colour), encoding='utf-8')
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    lines = []
    for seq, (who, platform, when, group, text, pics, video) in enumerate(POSTS):
        name = PEOPLE[who][0]
        lines.append(json.dumps({
            'id': f'demo:{seq}', 'platform': platform, 'captured_at': now, 'author': name,
            'author_key': f'demo:{who}', 'author_url': '#', 'header': name, 'group': group,
            'permalink': '#', 'time_text': when, 'text': text, 'seq': seq,
            'avatar': f'{rel}/avatar_{who}.svg', 'has_video': video,
            'images': [{'src': f'{rel}/scene_{p}.svg', 'alt': 'Demo picture'} for p in pics],
        }, ensure_ascii=False))
    (out / 'posts.jsonl').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return out


if __name__ == '__main__':
    print(f'demo fixture written to {generate(ROOT / "demo")}')
