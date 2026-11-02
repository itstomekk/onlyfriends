"""Render data/posts.jsonl into a private, ad-free friends feed: feed.html.

- Downloads post images into data/media/ (Facebook/Instagram CDN links expire).
- Sorts newest first using the relative time shown on the post ("3h", "2d", dates).
Usage: python build_feed.py [--days 14] [--demo]

--demo renders the built-in synthetic fixture (see demo.py) into demo/feed.html.
"""
import argparse
import hashlib
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
MEDIA = DATA / 'media'
POSTS = DATA / 'posts.jsonl'
OUT = ROOT / 'feed.html'
DEMO = False
MONTHS = {m: i for i, m in enumerate(
    ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
     'september', 'october', 'november', 'december'], 1)}


def use_demo():
    """Point every path at the synthetic fixture and (re)generate it."""
    global DATA, MEDIA, POSTS, OUT, DEMO
    import demo
    DATA = ROOT / 'demo'
    MEDIA, POSTS, OUT, DEMO = DATA / 'media', DATA / 'posts.jsonl', DATA / 'feed.html', True
    demo.generate(DATA)


def estimate_time(time_text, captured_at):
    """Best-effort post time from Facebook/Instagram relative labels."""
    cap = datetime.fromisoformat(captured_at)
    t = (time_text or '').strip().lower()
    m = re.fullmatch(r'(\d+)\s*(m|min|mins|h|hr|hrs|d|w|y)', t)
    if m:
        n, u = int(m.group(1)), m.group(2)[0]
        delta = {'m': timedelta(minutes=n), 'h': timedelta(hours=n), 'd': timedelta(days=n),
                 'w': timedelta(weeks=n), 'y': timedelta(days=365 * n)}[u]
        return cap - delta
    m = re.match(r'(\d+)\s+(minute|hour|day|week)s?\s+ago', t)
    if m:
        n, u = int(m.group(1)), m.group(2)
        return cap - timedelta(**{u + 's': n})
    if t.startswith('just now'):
        return cap
    if t.startswith('yesterday'):
        return cap - timedelta(days=1)
    m = re.match(r'([a-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?', t)
    if m and m.group(1) in MONTHS:
        year = int(m.group(3)) if m.group(3) else cap.year
        try:
            d = datetime(year, MONTHS[m.group(1)], int(m.group(2)), 12, tzinfo=timezone.utc)
            return d if d <= cap else d.replace(year=year - 1)
        except ValueError:
            return None
    return None


def local_image(url):
    if not url.startswith(('http://', 'https://')):  # demo fixture: a file already under ROOT
        return url if (ROOT / url).is_file() else None
    MEDIA.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha1(url.split('?')[0].encode()).hexdigest()[:16] + '.jpg'
    path = MEDIA / name
    if not path.exists():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                path.write_bytes(r.read())
        except Exception:
            return None
    return MEDIA.relative_to(ROOT).as_posix() + '/' + name


def load_posts():
    posts = []
    for line in POSTS.read_text(encoding='utf-8').splitlines():
        if line.strip():
            p = json.loads(line)
            if 'est_time' not in p:
                est = estimate_time(p.get('time_text'), p['captured_at'])
                p['est_time'] = est.isoformat() if est else p['captured_at']
            posts.append(p)
    return posts


def ago(iso):
    d = datetime.now(timezone.utc) - datetime.fromisoformat(iso)
    if d < timedelta(hours=1):
        return f'{max(1, int(d.total_seconds() // 60))} min ago'
    if d < timedelta(days=1):
        return f'{int(d.total_seconds() // 3600)} h ago'
    if d < timedelta(days=7):
        return f'{d.days} d ago'
    return datetime.fromisoformat(iso).strftime('%b %d')


def card(p):
    e = html.escape
    imgs = []
    for im in (p.get('images') or [])[:4]:
        src = local_image(im['src'])
        if src:
            imgs.append(f'<img loading="lazy" src="{e(src)}" alt="{e(im.get("alt", ""))}">')
    grid = f'<div class="imgs n{len(imgs)}">{"".join(imgs)}</div>' if imgs else ''
    video = '<div class="tag">▶ video</div>' if p.get('has_video') and not imgs else ''
    group = f' <span class="muted">in {e(p["group"])}</span>' if p.get('group') else ''
    head = (p.get('header') or '').strip()
    if not group and head.startswith(p['author']) and len(head) > len(p['author']) + 2:
        group = f' <span class="muted">{e(head[len(p["author"]):].strip())}</span>'
    icon = {'facebook': 'f', 'instagram': '◎'}.get(p['platform'], '•')
    link = p.get('permalink') or p.get('author_url') or '#'
    text = e(p.get('text') or '').replace('\n', '<br>')
    av = f'<img class="av" src="{e(p["avatar"])}" alt="">' if p.get('avatar') else ''
    return f'''<article data-platform="{e(p['platform'])}">
  <header>{av}<span class="pf {e(p['platform'])}">{icon}</span>
    <a class="who" href="{e(p.get('author_url') or '#')}" target="_blank" rel="noopener">{e(p['author'])}</a>{group}
    <a class="when" href="{e(link)}" target="_blank" rel="noopener">{e(ago(p['est_time']))}</a></header>
  <div class="text">{text}</div>{grid}{video}
</article>'''


def build(days):
    posts = load_posts()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    posts = [p for p in posts if datetime.fromisoformat(p['est_time']) >= cutoff]
    posts.sort(key=lambda p: (p['est_time'], p['captured_at'], -p.get('seq', 0)), reverse=True)
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    counts = {k: sum(1 for p in posts if p['platform'] == k) for k in ('facebook', 'instagram')}
    demo_note = ' · demo data: every name, post and picture is fictional' if DEMO else ''
    body = '\n'.join(card(p) for p in posts) or '<p class="muted">No friend posts yet.</p>'
    OUT.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Friends feed</title><style>
:root{{color-scheme:light dark;--bg:#f4f2ee;--card:#fff;--fg:#1d1d1f;--mut:#6e6e73;--line:#e3e0da;--acc:#c2410c}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121212;--card:#1c1c1e;--fg:#f2f2f2;--mut:#9a9aa0;--line:#2c2c2e;--acc:#fb923c}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:620px;margin:0 auto;padding:24px 14px 80px}}
h1{{font-size:22px;margin:0 0 4px}}.sub{{color:var(--mut);font-size:14px;margin-bottom:14px}}
.filters{{display:flex;gap:8px;margin-bottom:18px}}.filters button{{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:99px;padding:6px 14px;font:inherit;font-size:14px;cursor:pointer}}
.filters button.on{{background:var(--fg);color:var(--bg);border-color:var(--fg)}}#rf{{margin-left:auto}}#rf:disabled{{opacity:.6;cursor:default}}#rfs{{margin:-8px 0 14px}}
article{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:14px}}
header{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}}
.pf{{width:22px;height:22px;border-radius:6px;display:inline-grid;place-items:center;font-weight:700;font-size:13px;color:#fff}}
.pf.facebook{{background:#1877f2}}.pf.instagram{{background:linear-gradient(45deg,#f58529,#dd2a7b,#8134af)}}
.av{{width:32px;height:32px;border-radius:50%;display:block}}
.who{{font-weight:600;color:var(--fg);text-decoration:none}}.when{{margin-left:auto;color:var(--mut);font-size:13px;text-decoration:none}}
.muted{{color:var(--mut);font-size:14px}}.text{{white-space:normal;overflow-wrap:anywhere}}
.imgs{{display:grid;gap:4px;margin-top:10px;border-radius:10px;overflow:hidden}}.imgs.n2,.imgs.n3,.imgs.n4{{grid-template-columns:1fr 1fr}}
.imgs img{{width:100%;height:100%;max-height:520px;object-fit:cover;display:block}}.imgs.n1 img{{object-fit:contain;max-height:640px;background:var(--bg)}}
.tag{{display:inline-block;margin-top:8px;font-size:13px;color:var(--mut);border:1px solid var(--line);border-radius:6px;padding:2px 8px}}
a:hover{{text-decoration:underline}}
</style></head><body><main>
<h1>👋 Friends feed</h1>
<div class="sub">Only friends. No ads, no pages, no suggestions. Built {built} · {len(posts)} posts (last {days} days){demo_note}</div>
<div class="filters"><button class="on" data-f="all">All</button><button data-f="facebook">Facebook {counts['facebook']}</button><button data-f="instagram">Instagram {counts['instagram']}</button><button id="rf" hidden>↻ Refresh</button></div>
<div id="rfs" class="muted" hidden></div>
{body}
</main><script>
document.querySelectorAll('.filters button[data-f]').forEach(b=>b.onclick=()=>{{
document.querySelectorAll('.filters button[data-f]').forEach(x=>x.classList.toggle('on',x===b));
document.querySelectorAll('article').forEach(a=>a.style.display=(b.dataset.f==='all'||a.dataset.platform===b.dataset.f)?'':'none');}});
if(location.protocol.startsWith('http')&&!{str(DEMO).lower()}){{
const rf=document.getElementById('rf'),rfs=document.getElementById('rfs');rf.hidden=false;
const show=s=>{{rfs.hidden=false;rfs.textContent=s;}};
const poll=async first=>{{const st=await (await fetch('/status',{{cache:'no-store'}})).json();
if(st.state==='running'){{rf.disabled=true;rf.textContent='↻ Refreshing…';show('Reading friends\\' posts, about 5 to 10 minutes. You can leave this page open.');setTimeout(()=>poll(false),5000);return;}}
rf.disabled=false;rf.textContent='↻ Refresh';
if(st.state==='error')show('Last refresh failed: '+(st.summary||[]).filter(l=>/FAILED/.test(l)).join(' · '));
else if(!first&&st.state==='done')location.reload();
else if(st.finished)show('Last refresh '+st.finished.replace('T',' ').slice(0,16));}};
rf.onclick=async()=>{{await fetch('/refresh',{{method:'POST'}});poll(false);}};poll(true);}}
</script></body></html>''', encoding='utf-8')
    print(f'feed.html: {len(posts)} posts -> {OUT}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=14)
    ap.add_argument('--demo', action='store_true', help='render the synthetic demo fixture')
    a = ap.parse_args()
    if a.demo:
        use_demo()
    build(a.days)
