"""Settings for onlyfriends. Environment variables win over config.json.

config.json (copy config.example.json, it is git-ignored) keys and env names:
  fb_profile     ONLYFRIENDS_FB_PROFILE      your Facebook profile slug (facebook.com/<slug>) or "profile.php?id=..." id
  ig_username    ONLYFRIENDS_IG_USERNAME     your Instagram username
  port           ONLYFRIENDS_PORT            local page port (default 8766)
  session_module ONLYFRIENDS_SESSION_MODULE  optional path to a Python file that provides
                                             build_launch(platform, args, key) and get_encryption_key(),
                                             to replace the built-in agent-browser launcher
  encryption_key ONLYFRIENDS_ENCRYPTION_KEY  optional 64-hex key for agent-browser's encrypted session state
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / 'config.json'
_ENV = {'fb_profile': 'ONLYFRIENDS_FB_PROFILE', 'ig_username': 'ONLYFRIENDS_IG_USERNAME',
        'port': 'ONLYFRIENDS_PORT', 'session_module': 'ONLYFRIENDS_SESSION_MODULE',
        'encryption_key': 'ONLYFRIENDS_ENCRYPTION_KEY'}
_DEFAULTS = {'port': 8766}


def _file():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def get(key, required=False):
    value = os.environ.get(_ENV[key]) or _file().get(key) or _DEFAULTS.get(key)
    if required and not value:
        raise SystemExit(f'Missing setting "{key}": set {_ENV[key]} or add it to config.json '
                         '(see config.example.json).')
    return value
