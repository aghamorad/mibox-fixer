#!/usr/bin/env python3
"""Keep a small favorites group ahead of the complete Free-TV playlist."""
from pathlib import Path
from urllib.request import Request, urlopen

UPSTREAM = "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"
OUTPUT = Path(__file__).parent / "playlists" / "world.m3u"
FAVORITES = [
    ("Dry Bar Comedy", "https://drybar-drybarcomedy-1-us.samsung.wurl.tv/playlist.m3u8"),
    ("30A TV Classic Movies", "https://30a-tv.com/feeds/pzaz/30atvmovies.m3u8"),
    ("Magnificent Movies", "https://mmn1.b-cdn.net/hls/MMN-HLS.m3u8"),
    ("Al Jazeera English", "https://live-hls-apps-aje-fa.getaj.net/AJE/index.m3u8"),
]


def build(source: str) -> str:
    lines = source.splitlines()
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("Upstream is not an M3U playlist")
    if sum(line.startswith("#EXTINF") for line in lines) < 1000:
        raise ValueError("Upstream list is unexpectedly small; keeping the existing playlist")
    favorites = []
    for name, url in FAVORITES:
        favorites.extend([f'#EXTINF:-1 tvg-name="{name}" group-title="Top Picks",{name}', url])
    return "\n".join(["#EXTM3U", *favorites, *lines[1:]]) + "\n"


def main() -> None:
    request = Request(UPSTREAM, headers={"User-Agent": "MiBox-Fixer/1.0"})
    with urlopen(request, timeout=45) as response:
        source = response.read().decode("utf-8-sig")
    output = build(source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(output, encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Wrote {OUTPUT}: {output.count('#EXTINF')} entries")


if __name__ == "__main__":
    main()
