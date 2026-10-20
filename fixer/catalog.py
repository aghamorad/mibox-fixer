"""Everything the fixer knows: what to remove, what to install, how to tune.

The package list is the exact set that was verified against a real
Xiaomi Mi Box 4 (`oneday` / `MIBOX4`, Android 9 / SDK 28, armeabi-v7a).
Nothing here is guessed; each entry was confirmed with `pm list packages`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BloatItem:
    package: str
    title: str
    category: str
    detail: str
    default: bool = True
    danger: bool = False


@dataclass(frozen=True)
class AppItem:
    key: str
    title: str
    package: str
    detail: str
    kind: str  # "github" | "url" | "asset"
    repo: Optional[str] = None
    version: Optional[str] = None
    asset: Optional[str] = None
    url: Optional[str] = None
    component: Optional[str] = None
    arch_assets: dict = field(default_factory=dict)
    default: bool = False


# ---------------------------------------------------------------------------
# Bloat / telemetry / preloaded junk
# ---------------------------------------------------------------------------

CATEGORY_ORDER = [
    "Streaming bloat",
    "IPTV reseller junk",
    "Redundant VPNs",
    "Google TV & ads",
    "Telemetry & logging",
    "Mi/MiTV services",
    "Unused system extras",
]

BLOAT: list[BloatItem] = [
    # ---- Streaming bloat
    BloatItem("com.netflix.ninja", "Netflix", "Streaming bloat",
              "Preloaded Netflix. Removes the home-screen row too."),
    BloatItem("com.amazon.amazonvideo.livingroom", "Amazon Prime Video", "Streaming bloat",
              "Preloaded Prime Video."),
    BloatItem("com.apple.atve.androidtv.appletv", "Apple TV", "Streaming bloat",
              "Preloaded Apple TV app."),
    BloatItem("com.google.android.youtube.tv", "YouTube (stock)", "Streaming bloat",
              "The stock, ad-heavy YouTube app. Install SmartTube instead."),
    BloatItem("com.google.android.youtube.tvmusic", "YouTube Music", "Streaming bloat",
              "Preloaded YouTube Music."),
    BloatItem("com.google.android.videos", "Google Play Movies", "Streaming bloat",
              "Dead Play Movies store."),
    BloatItem("com.google.android.play.games", "Play Games", "Streaming bloat",
              "Games hub, never used on a TV box."),
    BloatItem("com.jio.web.androidtv", "JioTV", "Streaming bloat",
              "Regional streaming app."),

    # ---- IPTV reseller junk
    BloatItem("com.s9hiptvapps.family", "Family 4K Pro", "IPTV reseller junk",
              "IPTV reseller app. Pure clutter."),
    BloatItem("com.nst.smartersplayer", "Smarters Player Lite", "IPTV reseller junk",
              "IPTV reseller player."),
    BloatItem("com.nst.iptvsmarterstvbox", "IPTV Smarters (TV box)", "IPTV reseller junk",
              "Second half of the Smarters bundle."),
    BloatItem("com.toxic.apps.reciever", "Toxic Receiver", "IPTV reseller junk",
              "Unknown preloaded receiver."),

    # ---- Redundant VPNs
    BloatItem("com.expressvpn.vpn", "ExpressVPN (trial)", "Redundant VPNs",
              "Paid VPN trial. Keep Lantern/Amnezia instead."),
    BloatItem("com.windscribe.vpn", "Windscribe (trial)", "Redundant VPNs",
              "Second VPN trial."),

    # ---- Google TV & ads
    BloatItem("com.google.android.tv", "Google TV app", "Google TV & ads",
              "The thing that publishes the YouTube recommendation row.", default=True),
    BloatItem("com.google.android.tvlauncher", "Stock Google TV launcher", "Google TV & ads",
              "Only disable this once a replacement launcher is installed.",
              default=False, danger=True),
    BloatItem("com.google.android.tvrecommendations", "TV Recommendations", "Google TV & ads",
              "The recommendation engine itself."),
    BloatItem("com.google.android.backdrop", "Backdrop (ads)", "Google TV & ads",
              "Serves advertising art on the home screen."),
    BloatItem("com.google.android.katniss", "Google Assistant (Katniss)", "Google TV & ads",
              "Voice search backend. Disable only if you never use voice search."),
    BloatItem("com.google.android.apps.mediashell", "MediaShell (Cast target)", "Google TV & ads",
              "Turns the box into a Chromecast target. Disable if you never cast."),
    BloatItem("com.google.android.tv.frameworkpackagestubs", "File-picker stub", "Google TV & ads",
              "A dead stub that blocks real file pickers."),
    BloatItem("com.google.android.sss.authbridge", "SSS auth bridge", "Google TV & ads",
              "Background auth shim."),
    BloatItem("com.google.android.speech.pumpkin", "Speech Pumpkin", "Google TV & ads",
              "Speech model container for Assistant."),
    BloatItem("com.smartdevice.tv.aircast", "AirCast", "Google TV & ads",
              "Preloaded casting service; Miracast Receiver replaces it."),

    # ---- Telemetry & logging
    BloatItem("tv.alphonso.alphonso_eula", "Alphonso telemetry", "Telemetry & logging",
              "Automatic-content-recognition ad tracking. Removes viewing telemetry."),
    BloatItem("com.miui.tv.analytics", "Mi TV analytics", "Telemetry & logging",
              "Xiaomi usage analytics."),
    BloatItem("com.google.android.feedback", "Google feedback", "Telemetry & logging",
              "Crash/feedback reporter."),
    BloatItem("com.google.android.tv.bugreportsender", "Bug report sender", "Telemetry & logging",
              "Uploads bug reports."),
    BloatItem("com.google.android.partnersetup", "Partner setup", "Telemetry & logging",
              "Preload partner configuration."),
    BloatItem("com.android.wallpaperbackup", "Wallpaper backup", "Telemetry & logging",
              "Unused backup agent."),
    BloatItem("com.android.dreams.basic", "Basic daydream", "Telemetry & logging",
              "Screensaver service."),
    BloatItem("com.android.printspooler", "Print spooler", "Telemetry & logging",
              "Printing on a TV box."),

    # ---- Mi/MiTV services
    BloatItem("com.mitv.tvhome.atv", "Mi TV Home", "Mi/MiTV services",
              "Stock Mi TV launcher shell. Replaced by Beam.",
              default=False, danger=True),
    BloatItem("com.mitv.tvhome.michannel", "Mi Channel", "Mi/MiTV services",
              "Mi content channel / ads."),
    BloatItem("com.mitv.videoplayer", "Mi Video player", "Mi/MiTV services",
              "Stock player, replaced by VLC."),
    BloatItem("com.mitv.download.service", "Mi download service", "Mi/MiTV services",
              "Background downloader."),
    BloatItem("com.xiaomi.mitv.updateservice", "Mi update service", "Mi/MiTV services",
              "Silent firmware updater. Disabling stops surprise updates.", danger=False),
    BloatItem("com.xiaomi.android.tvsetup.partnercustomizer", "Partner customizer", "Mi/MiTV services",
              "Region bloat installer."),
    BloatItem("com.xm.webcontent", "XM web content", "Mi/MiTV services",
              "Mi web content provider."),
    BloatItem("android.autoinstalls.config.xiaomi.mibox3", "Auto-install config (mi)", "Mi/MiTV services",
              "Re-installs partner apps."),
    BloatItem("android.autoinstalls.config.xioami.mibox3", "Auto-install config (xioami)", "Mi/MiTV services",
              "Typo'd duplicate of the same thing. Xiaomi shipped both."),

    # ---- Unused system extras
    BloatItem("com.google.android.marvin.talkback", "TalkBack", "Unused system extras",
              "Screen reader. Keep it if you need accessibility.", default=False),
    BloatItem("com.googlecode.eyesfree.setorientation", "Set Orientation", "Unused system extras",
              "Screen-rotation helper."),
    BloatItem("com.google.android.syncadapters.calendar", "Calendar sync", "Unused system extras",
              "No calendar UI exists on the box."),
    BloatItem("com.google.android.syncadapters.contacts", "Contacts sync", "Unused system extras",
              "No contacts UI exists on the box."),
    BloatItem("com.google.android.tts", "Google TTS", "Unused system extras",
              "Speech synthesis engine.", default=False),
]

BLOAT_BY_PACKAGE = {b.package: b for b in BLOAT}


# ---------------------------------------------------------------------------
# Apps you can install
# ---------------------------------------------------------------------------

APPS: list[AppItem] = [
    AppItem(
        key="beam",
        title="Beam launcher",
        package="com.home.tiles",
        detail="Clean tile launcher with custom wallpaper and no recommendation rows. "
               "This is what makes the home screen look nice.",
        kind="github",
        repo="tonisaf/beam-launcher",
        version="v1.0.1",
        asset="app-release.apk",
        component="com.home.tiles/.MainActivity",
        default=True,
    ),
    AppItem(
        key="smarttube",
        title="SmartTube (ad-free YouTube)",
        package="org.smarttube.stable",
        detail="Ad-free, sponsor-skipping YouTube for TV. Replaces the stock YouTube app.",
        kind="github",
        repo="yuliskov/SmartTube",
        version="32.56s",
        component="org.smarttube.stable/com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity",
        arch_assets={
            "armeabi-v7a": "SmartTube_stable_32.56_armeabi-v7a.apk",
            "arm64-v8a": "SmartTube_stable_32.56_arm64-v8a.apk",
            "x86": "SmartTube_stable_32.56_x86.apk",
            "universal": "SmartTube_stable_32.56_universal.apk",
        },
        default=True,
    ),
    AppItem(
        key="tvbro",
        title="TV Bro (remote-friendly browser)",
        package="com.phlox.tvwebbrowser",
        detail="A real browser you can drive with a D-pad remote.",
        kind="github",
        repo="truefedex/tv-bro",
        version="v2.1.6",
        component="com.phlox.tvwebbrowser/.activity.main.MainActivity",
        arch_assets={
            "armeabi-v7a": "tvbro-2.1.6-generic-geckoIncluded-armeabi-v7a.apk",
            "arm64-v8a": "tvbro-2.1.6-generic-geckoIncluded-arm64-v8a.apk",
            "universal": "tvbro-2.1.6-generic-geckoExcluded.apk",
        },
        default=True,
    ),
    AppItem(
        key="lantern",
        title="Lantern",
        package="org.getlantern.lantern",
        detail="Circumvention/proxy client. Uses the official Android build.",
        kind="github",
        repo="getlantern/lantern",
        version="v10.0.3-beta-10",
        component="org.getlantern.lantern/.MainActivity",
        arch_assets={
            "armeabi-v7a": "lantern-installer-beta-armv7.apk",
            "arm64-v8a": "lantern-installer-beta.apk",
            "x86_64": "lantern-installer-beta.apk",
        },
        default=True,
    ),
    AppItem(
        key="amnezia",
        title="AmneziaVPN",
        package="org.amnezia.vpn",
        detail="Open-source self-hosted VPN client. The Android 9 build is chosen "
               "automatically for older boxes.",
        kind="github",
        repo="amnezia-vpn/amnezia-client",
        version="5.0.3.0",
        component="org.amnezia.vpn/.AmneziaActivity",
        arch_assets={
            "armeabi-v7a": "AmneziaVPN_5.0.3.0_android9-10_armeabi-v7a.apk",
            "arm64-v8a": "AmneziaVPN_5.0.3.0_android9-10_arm64-v8a.apk",
        },
        default=True,
    ),
    AppItem(
        key="airplay",
        title="AirPlay Server",
        package="io.github.jqssun.airplay",
        detail="Mirror an iPhone, iPad or Mac to the box over AirPlay (open source).",
        kind="github",
        repo="jqssun/android-airplay-server",
        version="v0.0.36",
        asset="app-release.apk",
        component="io.github.jqssun.airplay/.MainActivity",
        default=True,
    ),
    AppItem(
        key="miracast",
        title="Miracast Receiver",
        package="com.weekd.miracastreceiver",
        detail="Open-source Miracast / Wi-Fi Display sink. Cast from Android or Windows.",
        kind="github",
        repo="weekdayjast/MiracastReceiver",
        version="v1.2.7",
        component="com.weekd.miracastreceiver/.ui.MainActivity",
        arch_assets={
            "armeabi-v7a": "miracast-receiver-v1.2.7-armeabi-v7a.apk",
            "arm64-v8a": "miracast-receiver-v1.2.7-arm64-v8a.apk",
            "universal": "miracast-receiver-v1.2.7-universal.apk",
        },
        default=True,
    ),
    AppItem(
        key="xplayer",
        title="xplayer (IPTV)",
        package="com.tntlikely.xplayer",
        detail="Open-source IPTV/M3U player with built-in iptv-org sources, EPG and search.",
        kind="github",
        repo="TNT-Likely/xplayer",
        version="2.6.0",
        component="com.tntlikely.xplayer/.MainActivity",
        arch_assets={
            "armeabi-v7a": "xplayer-2.6.0-armeabi-v7a.apk",
            "arm64-v8a": "xplayer-2.6.0-universal.apk",
            "x86_64": "xplayer-2.6.0-x86_64.apk",
        },
        default=True,
    ),
    AppItem(
        key="materialfiles",
        title="Material Files",
        package="me.zhanghai.android.files",
        detail="File manager with a built-in FTP server, so you can drag and drop "
               "files from your computer over Wi-Fi.",
        kind="github",
        repo="zhanghai/MaterialFiles",
        version="v1.7.5",
        # The box ships the F-Droid build; its signing key differs from the
        # universal/Play build, so they cannot be installed over one another.
        asset="app-release-fdroid.apk",
        component="me.zhanghai.android.files/.filelist.FileListActivity",
        default=True,
    ),
    AppItem(
        key="fossify",
        title="Fossify File Manager",
        package="org.fossify.filemanager",
        detail="Small open-source file manager. Useful as a file-picker backend.",
        kind="github",
        repo="FossifyOrg/File-Manager",
        version="1.6.2",
        asset="file-manager-14-foss-release.apk",
        component="org.fossify.filemanager/.activities.SplashActivity.Green",
        default=False,
    ),
    AppItem(
        key="flauncher",
        title="FLauncher (alternative launcher)",
        package="me.efesser.flauncher",
        detail="Another open-source TV launcher. If you install it, switch the home "
               "screen to it and Beam gets disabled instead.",
        kind="github",
        repo="osrosal/flauncher",
        version="v2025.07.001",
        component="me.efesser.flauncher/.MainActivity",
        arch_assets={
            "armeabi-v7a": "flauncher-armeabi-v7a-release.apk",
            "arm64-v8a": "flauncher-arm64-v8a-release.apk",
            "x86": "flauncher-x86-release.apk",
        },
        default=False,
    ),
    AppItem(
        key="ltvlauncher",
        title="LTvLauncher (launcher w/ screensaver)",
        package="com.leanbitlab.ltv",
        detail="A modern FLauncher fork with an OLED-friendly screensaver and data widget. "
               "Popular alternative to Beam.",
        kind="github",
        repo="leanbitlab-org/LtvLauncher",
        version="v2026.10.03",
        component="com.leanbitlab.ltv/.MainActivity",
        arch_assets={
            "armeabi-v7a": "LTvLauncher-armeabi-v7a-release.apk",
            "arm64-v8a": "LTvLauncher-arm64-v8a-release.apk",
            "universal": "LTvLauncher-universal-release.apk",
        },
        default=False,
    ),
]

APPS_BY_KEY = {a.key: a for a in APPS}


# ---------------------------------------------------------------------------
# Small tweaks
# ---------------------------------------------------------------------------

ANIMATION_KEYS = [
    "window_animation_scale",
    "transition_animation_scale",
    "animator_duration_scale",
]

IPTV_PLAYLISTS = {
    "All channels": "https://iptv-org.github.io/iptv/index.m3u",
    "Iran": "https://iptv-org.github.io/iptv/countries/ir.m3u",
    "Persian (by language)": "https://iptv-org.github.io/iptv/languages/fas.m3u",
    "English (by language)": "https://iptv-org.github.io/iptv/languages/eng.m3u",
}
