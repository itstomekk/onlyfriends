"""Thin wrapper: run one agent-browser command in your own logged-in session.

Default: the `agent-browser` CLI (npm i -g agent-browser) with one persistent,
isolated session per platform (onlyfriends-facebook, onlyfriends-instagram).
Optional: point `session_module` in config.json at your own launcher module
(build_launch(platform, args, key) + get_encryption_key()).
Read-only use: open, scroll, eval, screenshot. Never clicks Like/Comment/Share.

First login (once per platform, a visible window opens, you log in by hand):
  python ab.py facebook open https://www.facebook.com/ --headed
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import config

NAMESPACE = 'onlyfriends'


def _agent_browser():
    exe = shutil.which('agent-browser')
    if not exe:
        raise RuntimeError('agent-browser is not installed: npm i -g agent-browser')
    if sys.platform == 'win32' and exe.lower().endswith('.cmd'):
        # Avoid cmd.exe interpreting &, |, <, > in JavaScript arguments.
        native = Path(exe).parent / 'node_modules' / 'agent-browser' / 'bin' / 'agent-browser-win32-x64.exe'
        if native.is_file():
            exe = str(native)
    return exe


def _custom_launcher(path):
    spec = importlib.util.spec_from_file_location('onlyfriends_session', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_launch(platform, args):
    custom = config.get('session_module')
    if custom:
        mod = _custom_launcher(custom)
        return mod.build_launch(platform, list(args), mod.get_encryption_key())
    env = os.environ.copy()
    key = config.get('encryption_key')
    if key:
        env['AGENT_BROWSER_ENCRYPTION_KEY'] = key
    command = [_agent_browser(), '--namespace', NAMESPACE, '--session', f'{NAMESPACE}-{platform}',
               '--restore', *args]
    return command, env


def run(platform, *args, timeout=90):
    command, env = build_launch(platform, args)
    # Temp files, not pipes: a cold start spawns the agent-browser daemon, which
    # inherits our handles. With pipes, reading waits for EOF that never comes
    # (hung forever when launched without a console: page button, cron).
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.run(command, env=env, stdin=subprocess.DEVNULL, stdout=out,
                              stderr=err, timeout=timeout)
        out.seek(0)
        text = out.read().decode('utf-8', errors='replace')
    lines = [l for l in text.splitlines() if not l.startswith('[agent-browser]')]
    return proc.returncode, '\n'.join(lines).strip()


if __name__ == '__main__':
    platform = sys.argv[1]
    args = sys.argv[2:]
    if args and args[0] == 'evalfile':
        args = ['eval', Path(args[1]).read_text(encoding='utf-8')]
    code, out = run(platform, *args)
    sys.stdout.reconfigure(encoding='utf-8')
    print(out)
    raise SystemExit(code)
