#!/usr/bin/env python3
"""Download local posters for YouTube reels entries that have none.

Runs in GitHub Actions after every content/site.json change. Local posters
matter because i.ytimg.com is unreachable for visitors in Russia; a poster
served from our own domain keeps the tile visible for everyone.
Idempotent: a second run after the auto-commit finds nothing to do.
"""
import json
import os
import re
import urllib.request

SITE = 'content/site.json'
YT = re.compile(
    r'(?:youtube(?:-nocookie)?\.com/(?:watch\?[^#]*?v=|shorts/|embed/|live/)|youtu\.be/)([\w-]{11})'
)
# oar2 is the vertical variant (shorts), the rest are 16:9 fallbacks
VARIANTS = ('oar2', 'hq720', 'hqdefault')


def video_id(url):
    url = (url or '').strip()
    if re.fullmatch(r'[\w-]{11}', url):
        return url
    m = YT.search(url)
    return m.group(1) if m else None


def fetch(vid, dest):
    for variant in VARIANTS:
        try:
            req = urllib.request.Request(
                f'https://i.ytimg.com/vi/{vid}/{variant}.jpg',
                headers={'User-Agent': 'Mozilla/5.0'},
            )
            data = urllib.request.urlopen(req, timeout=20).read()
        except Exception:
            continue
        # yt serves a tiny placeholder jpg for missing variants
        if len(data) > 2000:
            with open(dest, 'wb') as f:
                f.write(data)
            return True
    return False


def main():
    with open(SITE, encoding='utf-8') as f:
        site = json.load(f)

    changed = False
    for reel in site.get('media', {}).get('reels', []):
        vid = video_id(reel.get('youtube') or '')
        if not vid:
            continue
        poster = reel.get('poster') or ''
        # a poster the client uploaded himself stays untouched
        if poster and not poster.startswith('http') and os.path.exists(poster):
            continue
        local = f'assets/reels/yt-{vid}.jpg'
        if not os.path.exists(local) and not fetch(vid, local):
            print(f'{vid}: no thumbnail available, leaving as is')
            continue
        if poster != local:
            reel['poster'] = local
            changed = True
            print(f'{vid}: poster -> {local}')

    if changed:
        with open(SITE, 'w', encoding='utf-8') as f:
            json.dump(site, f, ensure_ascii=False, indent=2)
        print('site.json updated')
    else:
        print('nothing to do')


if __name__ == '__main__':
    main()
