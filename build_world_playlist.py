#!/usr/bin/env python3
"""Build a verified, Android-9-friendly worldwide IPTV playlist with curated groups."""
from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

UPSTREAM = "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"
IRAN_VERIFIED = "https://raw.githubusercontent.com/aghamorad/iptv-ir/main/ir.m3u"
OUTPUT = Path(__file__).parent / "playlists" / "world.m3u"

# Every curated stream below is HTTPS-only and verified for complete Android 9
# TLS chains + live HLS media segment delivery.
CURATED: list[tuple[str, str, str]] = [
    # ---- Top Picks (first group in TV Live)
    ("Top Picks", "CNN International (HD)", "https://d3bp6dwmpbdajl.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-ury0meh5m4nzm/index.m3u8"),
    ("Top Picks", "CNN (720p)", "https://tvsen6.aynaott.com/cnn/index.m3u8"),
    ("Top Picks", "BBC News (HD)", "https://vs-hls-push-ww-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_news_channel_hd/t=3840/v=pv14/b=5070016/main.m3u8"),
    ("Top Picks", "Al Jazeera English (HD)", "https://live-hls-apps-aje-fa.getaj.net/AJE/index.m3u8"),
    ("Top Picks", "Iran International (HD)", "https://hlspackager.akamaized.net/live/DB/IRAN_INTERNATIONAL/HLS/IRAN_INTERNATIONAL.m3u8"),
    ("Top Picks", "Sky News", "https://dash4.antik.sk/live/test_skynews/playlist.m3u8"),
    ("Top Picks", "DW English (HD)", "https://amg01644-amg01644c1-amgplt0343.playout.now3.amagi.tv/ts-eu-w1-n2/playlist/amg01644-amg01644c1-amgplt0343/playlist.m3u8"),
    ("Top Picks", "Euronews English (HD)", "https://dash4.antik.sk/live/test_euronews/playlist.m3u8"),
    ("Top Picks", "Bloomberg TV", "https://bloomberg.com/media-manifest/streams/eu.m3u8"),
    ("Top Picks", "Dry Bar Comedy", "https://drybar-drybarcomedy-1-us.samsung.wurl.tv/playlist.m3u8"),
    ("Top Picks", "MovieSphere (HD)", "https://amg00353-lionsgatestudio-moviesphere-xumo-zh5u0.amagi.tv/playlist.m3u8"),
    ("Top Picks", "30A TV Classic Movies", "https://30a-tv.com/feeds/pzaz/30atvmovies.m3u8"),
    ("Top Picks", "Magnificent Movies", "https://mmn1.b-cdn.net/hls/MMN-HLS.m3u8"),
    ("Top Picks", "TNA Wrestling", "https://jmp2.uk/plu-59b722526996084038c01e1b.m3u8"),
    ("Top Picks", "Red Bull TV (HD)", "https://3ea22335.wurl.com/master/f36d25e7e52f1ba8d7e56eb859c636563214f541/UmFrdXRlblRWLWdiX1JlZEJ1bGxUVl9ITFM/playlist.m3u8"),
    ("Top Picks", "Curiosity NOW (HD)", "https://amg00170-amg00170c4-samsung-gb-4232.playouts.now.amagi.tv/playlist.m3u8"),

    # ---- World News
    ("World News", "CNN International (HD)", "https://d3bp6dwmpbdajl.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-ury0meh5m4nzm/index.m3u8"),
    ("World News", "CNN International North America (HD)", "https://d2sybdl23b9psq.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-bocx3i7bjz0dg/CNNFAST_GB.m3u8"),
    ("World News", "CNN (720p)", "https://tvsen6.aynaott.com/cnn/index.m3u8"),
    ("World News", "BBC News (HD)", "https://vs-hls-push-ww-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_news_channel_hd/t=3840/v=pv14/b=5070016/main.m3u8"),
    ("World News", "BBC News South Asia", "https://mumbai-edge.smartplaytv.in/BBCNews/index.m3u8"),
    ("World News", "Al Jazeera English (HD)", "https://live-hls-apps-aje-fa.getaj.net/AJE/index.m3u8"),
    ("World News", "Sky News", "https://dash4.antik.sk/live/test_skynews/playlist.m3u8"),
    ("World News", "France 24 English (HD)", "https://freem3u.xyz/api/live/play.m3u8?vid=96"),
    ("World News", "DW English (HD)", "https://amg01644-amg01644c1-amgplt0343.playout.now3.amagi.tv/ts-eu-w1-n2/playlist/amg01644-amg01644c1-amgplt0343/playlist.m3u8"),
    ("World News", "Euronews English (HD)", "https://dash4.antik.sk/live/test_euronews/playlist.m3u8"),
    ("World News", "Bloomberg TV Europe", "https://bloomberg.com/media-manifest/streams/eu.m3u8"),
    ("World News", "Bloomberg TV US", "https://bloomberg.com/media-manifest/streams/us.m3u8"),
    ("World News", "Bloomberg Originals (HD)", "https://bloomberg.com/media-manifest/streams/qt.m3u8"),
    ("World News", "NBC News NOW (HD)", "https://d1si3n1st4nkgb.cloudfront.net/10502/88896001/hls/master.m3u8?ads.xumo_channelId=88896001"),
    ("World News", "ABC News Australia", "https://abc-news-dmd-streams-1.akamaized.net/out/v1/701126012d044971b3fa89406a440133/index.m3u8"),
    ("World News", "CBS News 24/7", "https://jmp2.uk/plu-6350fdd266e9ea0007bedec5.m3u8"),
    ("World News", "Reuters TV (HD)", "https://amg00453-reuters-amg00453c1-rakuten-uk-2110.playouts.now.amagi.tv/playlist/amg00453-reuters-reuters-rakutenuk/playlist.m3u8"),
    ("World News", "NHK World Japan", "https://media-osa.hls.nhkworld.jp/hls/w/live/master.m3u8"),
    ("World News", "TRT World", "https://tv-trtworld.medya.trt.com.tr/master.m3u8"),

    # ---- Iran & Persian (satellite + Persiana; IRIB channels are appended below from iptv-ir)
    ("Iran & Persian", "Iran International (HD)", "https://hlspackager.akamaized.net/live/DB/IRAN_INTERNATIONAL/HLS/IRAN_INTERNATIONAL.m3u8"),
    ("Iran & Persian", "Persiana Cinema", "https://cinehls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Comedy", "https://comedyhls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Iranian", "https://irhls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Series", "https://onehls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Nostalgia", "https://noshls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Docs", "https://scihls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Family", "https://familyhls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Fight", "https://fighthls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Travel", "https://ptravelhls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Persiana Plus", "https://euhls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "Grand Cinema", "https://gcinemahls.wns.live/hls/stream.m3u8"),
    ("Iran & Persian", "Cafe Film", "https://cafefhls.wns.live/hls/stream.m3u8"),
    ("Iran & Persian", "Classic TV", "https://clshls.wns.live/hls/stream.m3u8"),
    ("Iran & Persian", "AVA Series", "https://avaserieshls.wns.live/hls/stream.m3u8"),
    ("Iran & Persian", "Avang TV (HD)", "https://hls.avang.live/hls/stream.m3u8"),
    ("Iran & Persian", "PBC Tapesh TV", "https://iptv.tapesh.tv/tapesh/playlist.m3u8"),
    ("Iran & Persian", "4 Music", "https://musichls.persiana.live/hls/stream.m3u8"),
    ("Iran & Persian", "RJTV (HD)", "https://rjtvhls.wns.live/hls/stream.m3u8"),

    # ---- Movies & Classic Cinema
    ("Movies & Classic Cinema", "MovieSphere (HD)", "https://amg00353-lionsgatestudio-moviesphere-xumo-zh5u0.amagi.tv/playlist.m3u8"),
    ("Movies & Classic Cinema", "MovieSphere UK (HD)", "https://moviesphereuk-samsunguk.amagi.tv/playlist.m3u8"),
    ("Movies & Classic Cinema", "30A TV Classic Movies", "https://30a-tv.com/feeds/pzaz/30atvmovies.m3u8"),
    ("Movies & Classic Cinema", "Classic Movies Channel", "https://jmp2.uk/plu-561c5b0dada51f8004c4d855.m3u8"),
    ("Movies & Classic Cinema", "Classic Movie Westerns", "https://jmp2.uk/plu-61f33318210549000806a530.m3u8"),
    ("Movies & Classic Cinema", "Magnificent Movies Network", "https://mmn1.b-cdn.net/hls/MMN-HLS.m3u8"),

    # ---- Comedy & Wrestling
    ("Comedy & Wrestling", "Dry Bar Comedy", "https://drybar-drybarcomedy-1-us.samsung.wurl.tv/playlist.m3u8"),
    ("Comedy & Wrestling", "Dry Bar Comedy+", "https://drybar-drybarcomedy-1-au.samsung.wurl.tv/playlist.m3u8"),
    ("Comedy & Wrestling", "TNA Wrestling Channel", "https://jmp2.uk/plu-59b722526996084038c01e1b.m3u8"),
    ("Comedy & Wrestling", "Ultimate Classic Wrestling", "https://service-stitcher.clusters.pluto.tv/v1/stitch/embed/hls/channel/652516fb7971630008a58e74/master.m3u8?deviceId=channel&deviceModel=web&deviceVersion=1.0&appVersion=1.0&deviceType=rokuChannel&deviceMake=rokuChannel&deviceDNT=1&advertisingId=channel&embedPartner=rokuChannel&appName=rokuchannel&is_lat=1&bmodel=bm1&content=channel&platform=web&tags=ROKU_CONTENT_TAGS&coppa=false&content_type=livefeed&rdid=channel&genre=ROKU_ADS_CONTENT_GENRE&content_rating=ROKU_ADS_CONTENT_RATING&studio_id=viacom&channel_id=channel"),

    # ---- Documentaries & Sports
    ("Documentaries & Sports", "Red Bull TV (HD)", "https://3ea22335.wurl.com/master/f36d25e7e52f1ba8d7e56eb859c636563214f541/UmFrdXRlblRWLWdiX1JlZEJ1bGxUVl9ITFM/playlist.m3u8"),
    ("Documentaries & Sports", "Curiosity NOW (HD)", "https://amg00170-amg00170c4-samsung-gb-4232.playouts.now.amagi.tv/playlist.m3u8"),
    ("Documentaries & Sports", "Documentary+ (HD)", "https://ef79b15c8c7c46c7a9de9d33001dbd07.mediatailor.us-west-2.amazonaws.com/v1/master/ba62fe743df0fe93366eba3a257d792884136c7f/LINEAR-859-DOCUMENTARYPLUS-DOCUMENTARYPLUS/mt/documentaryplus/859/hls/master/playlist.m3u8"),
    ("Documentaries & Sports", "Autentic History (HD)", "https://9e754fa707344ccca6d84955c8fcaf36.mediatailor.us-east-1.amazonaws.com/v1/master/44f73ba4d03e9607dcd9bebdcb8494d86964f1d8/RlaxxTV-eu_AutenticHistory/playlist.m3u8"),
    ("Documentaries & Sports", "CGTN Documentary (HD)", "https://amg00405-rakutentv-cgtndocumentary-rakuten-0ql8j.amagi.tv/master.m3u8"),
    ("Documentaries & Sports", "Asharq Documentary (HD)", "https://svs.itworkscdn.net/asharqdocumentarylive/asharqdocumentary.smil/playlist_dvr.m3u8"),
]

FAVORITES: list[tuple[str, str]] = [
    (name, url) for group, name, url in CURATED if group == "Top Picks"
]


def _extract_iran_entries(ir_source: str) -> list[str]:
    out: list[str] = []
    lines = ir_source.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            name = line.split(",", 1)[1].strip() if "," in line else "IRIB"
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines):
                url = lines[j].strip()
                if url.startswith("https://"):
                    out.append(f'#EXTINF:-1 tvg-name="{name}" group-title="Iran & Persian",{name}')
                    out.append(url)
            i = j + 1
        else:
            i += 1
    return out


def _filter_https_upstream(lines: list[str]) -> list[str]:
    """Keep only HTTPS entries from the worldwide upstream (Android 9 blocks cleartext HTTP)."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            j = i + 1
            extra: list[str] = []
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                if lines[j].strip():
                    extra.append(lines[j].strip())
                j += 1
            if j < len(lines):
                url = lines[j].strip()
                if url.startswith("https://"):
                    out.append(line)
                    out.extend(extra)
                    out.append(url)
            i = j + 1
        else:
            i += 1
    return out


def build(source: str, ir_source: str = "") -> str:
    lines = source.splitlines()
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("Upstream is not an M3U playlist")
    if sum(line.startswith("#EXTINF") for line in lines) < 1000:
        raise ValueError("Upstream list is unexpectedly small; keeping the existing playlist")
    curated_lines: list[str] = []
    for group, name, url in CURATED:
        curated_lines.extend([
            f'#EXTINF:-1 tvg-name="{name}" group-title="{group}",{name}',
            url,
        ])
    if ir_source:
        curated_lines.extend(_extract_iran_entries(ir_source))
    world_https = _filter_https_upstream(lines[1:])
    return "\n".join(["#EXTM3U", *curated_lines, *world_https]) + "\n"


def _fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "MiBox-Fixer/2.2"})
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8-sig")


def main() -> None:
    source = _fetch(UPSTREAM)
    try:
        ir_source = _fetch(IRAN_VERIFIED)
    except Exception:  # noqa: BLE001
        ir_source = ""
    output = build(source, ir_source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(output, encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Wrote {OUTPUT}: {output.count('#EXTINF')} entries (HTTPS-only + curated groups)")


if __name__ == "__main__":
    main()
