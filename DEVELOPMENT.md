# Development

## Layout

| Path | What it is |
|---|---|
| `serve.py` | Local page server on `127.0.0.1` (default port 8766). Serves only the feed page and the saved media. `POST /refresh` (same-origin only) starts `refresh.py`; `GET /status` reports progress. `--demo` serves the synthetic fixture and switches Refresh off. |
| `build_feed.py` | Renders `data/posts.jsonl` to `feed.html`, downloads images to `data/media/`, estimates post time from labels such as `3h`, `Yesterday`, `Oct 25`. `--demo` renders `demo/feed.html`. |
| `collect_fb.py` | `friends` mode scrolls your Facebook friends page into `data/fb_friends.json`; `feed` mode scrolls the Friends feed and keeps posts whose author is on that list. |
| `collect_ig.py` | Instagram Following feed, kept only for users in `data/ig_friends.json`; drops Sponsored/Suggested and `data/ig_hidden.txt`. Skips itself while the friends list is missing. |
| `collect_ig_friends.py` | Builds `data/ig_friends.json` (mutual follows). 100 accounts per request, 8 to 15 s apart, saves nothing on the first non-200 answer. |
| `refresh.py` | Runs Facebook, Instagram and build in order. Lock file `data/refresh.lock` holds the PID; a dead or 60-minute-old lock is cleared. Status in `data/refresh_status.json`. |
| `ab.py` | One `agent-browser` command in your logged-in session. Output goes through temp files, never pipes (see below). |
| `config.py` | Settings: environment variable, else `config.json`, else default. |
| `demo.py` | Generates the fictional fixture (names, lorem posts, flat-colour SVG avatars and pictures) into `demo/`. |
| `js/` | Scripts that run inside the page: `fb_feed_extract.js`, `fb_expand.js`, `fb_friends_extract.js`, `ig_feed_extract.js`, `ig_follow_page.js`, `ig_probe.js` (debug helper). |
| `start-hidden.vbs` | Windows: start `serve.py` without a console window. |
| `tests/` | Offline tests (standard library only). |
| `docs/` | GitHub Pages landing page (`docs/index.html`, screenshots in `docs/img/`). |
| `.github/readme/` | Screenshots for the README (demo data only). |

Private, git-ignored, created at runtime: `data/`, `feed.html`, `demo/`, `config.json`, browser session state.

## Commands

```bash
python serve.py --demo                 # synthetic demo page
python build_feed.py --demo            # only render demo/feed.html
python -m unittest discover -s tests   # tests
python collect_fb.py friends           # refresh Facebook friends list (weekly is plenty)
python collect_fb.py feed --scrolls 25 # one Facebook pass
python collect_ig.py --scrolls 20      # one Instagram pass
python refresh.py [--scrolls 25] [--days 14] [--quiet]
python serve.py [--port 8766]
```

## Config

`config.json` (copy `config.example.json`) or environment variables; environment wins.

| Key | Env | Meaning |
|---|---|---|
| `fb_profile` | `ONLYFRIENDS_FB_PROFILE` | Your profile slug (`facebook.com/<slug>`) or numeric id. Needed for `collect_fb.py`. |
| `ig_username` | `ONLYFRIENDS_IG_USERNAME` | Your Instagram username. Needed for `collect_ig_friends.py`. |
| `port` | `ONLYFRIENDS_PORT` | Local page port, default 8766. |
| `session_module` | `ONLYFRIENDS_SESSION_MODULE` | Optional path to a Python file providing `build_launch(platform, args, key)` and `get_encryption_key()` to replace the built-in launcher. |
| `encryption_key` | `ONLYFRIENDS_ENCRYPTION_KEY` | Optional 64-hex key for agent-browser's encrypted session state. |

## Design notes

- **Friends only.** Facebook: the post header's author key must be in `fb_friends.json`. Instagram: author must be in `ig_friends.json`. Everything else is logged to `data/*_rejected_last_run.json` (private) and dropped.
- **Never read agent-browser output through pipes.** A cold start spawns a daemon that inherits the caller's handles; with `capture_output=True` the read waits for an EOF that never comes whenever there is no console (page button, scheduler). `ab.py` and `refresh.py` use temp files.
- **Facebook feed posts** are `[aria-posinset]` articles; off-screen ones are virtualized (empty text), so the extractor runs on every scroll and merges by id.
- **Shares, reels, events** have no `data-ad-preview=message` node; `fallback_text()` cleans the article text instead.
- **Server surface.** Only the feed page and the media folder are served; `data/*.json*`, source files and `..` paths return 404; a cross-origin POST returns 403.
- **Stop conditions.** A login wall or checkpoint stops the run and saves nothing; a friends list under 20 entries is not saved.

## Tests

`python -m unittest discover -s tests` checks the time estimator, and that the demo fixture is fully synthetic (fictional names, no links, vector art only). They need no network and no account.

## Roadmap

- Month abbreviations (`Oct 25`) are not parsed by `estimate_time` yet (full names like `October 25` are); such posts fall back to the capture time.
- Fixture-based tests for the extractor scripts (saved synthetic DOM snippets).
- Optional per-friend mute list for Facebook (Instagram already has `data/ig_hidden.txt`).
- Cross-platform polish: a `systemd`/`launchd` example next to `start-hidden.vbs`.
- Marker checks that warn loudly when the Facebook or Instagram markup changes and the extractor finds nothing.
