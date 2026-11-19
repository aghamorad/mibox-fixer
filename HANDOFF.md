# Handoff — Mi Box Fixer (MoBox)

## 2026-11-19 Native macOS `MoBox.app` + Phone-Side Web App + Paul Rand Liquid-Glass Icon — completed
Built and installed the native universal macOS application **`/Applications/MoBox.app`** (`arm64` + `x86_64`, modelled on `ZLT X28.app`), the mobile-first **Phone & Browser Web App** (`http://192.168.0.195:8765`, `fixer/web.py` + `web/index.html`), and a custom **Paul Rand mid-century geometric retro + Liquid Glass app icon** (`MoBoxApp/make_icon.py` → `AppIcon.icns` & `icon-preview.png`):
- **Paul Rand + Liquid Glass Icon (`MoBoxApp/make_icon.py`)**: Full-bleed midnight-charcoal canvas, asymmetric Paul Rand vermilion-orange TV cabinet (`#EA4A28`), Bauhaus gold & electric cyan rabbit-ear antenna spheres, geometric `"Mo"` monogram inside the CRT screen, and a translucent Apple tvOS 26 Liquid Glass dock pill & specular glass refraction sheen.
- **Native Universal macOS App (`MoBoxApp/` → `/Applications/MoBox.app`)**: Pure Swift/SwiftUI (`App.swift`, `Model.swift`, `Views.swift`, `build.sh`), compiled for `arm64` + `x86_64` via `swiftc` + `lipo`, ad-hoc signed, with monochrome template menu bar item (`NSStatusItem`), segmented `Simple (75)` / `Advanced (35)` switcher, model-aware APK installer, safe debloater, Couch TV Remote, 4K Space & Nature Slideshow launcher, native CoreImage QR code for instant phone pairing, `"Made by Morad"` credit, and commit-based self-updater (`MoBoxBuildCommit`).
- **Phone-Side & Online Web App (`fixer/web.py` & `web/index.html`)**: Automatically launched by `MoBox.app` on port `8765` (or standalone via `python3 -m fixer.web`); provides `Simple (75)`, `TV Remote` (tactile D-pad + 1-tap app launchers), and `Advanced (35)` modes on any iPhone/Android phone on the Wi-Fi.
- **Verification**: `39/39` unit tests pass; live HTTP/API test against `MIBOX4` (`192.168.0.117:5555`) verified end-to-end (`WEB API CONNECTED: True MODEL: MIBOX4 LAN: 192.168.0.195 APPS: 17`); universal binary verified via `lipo -info` and installed at `/Applications/MoBox.app`. Guide updated at `~/Desktop/MoBox — a noob's guide.md`.

## 2026-11-19 MoBox 2.1.0 (Simple 75-Year-Old Mode + Advanced 35-Year-Old Mode + 4K Space & Nature Slideshow) — completed
Upgraded `mibox-fixer` into **MoBox 2.1.0** with dual-mode GUI, zero-IP Wi-Fi auto-discovery, live firmware/kernel-HID/CEC health inspection, **Aerial Views v1.8.5** 4K Space & Nature slideshow screensaver, 15 local 4K NASA Space & Nature wallpapers in `/sdcard/Wallpapers`, `"Made by Morad"` credit, and commit-based self-updater:
- **`fixer/discover.py`**: `discover_miboxes()` probes local ARP candidates on TCP `5555` (ADB) & `6466` (Android TV Remote v2) in parallel; `inspect_firmware(adb)` reads model, Android/SDK, build ID, security patch, kernel, ABI, free RAM/storage, HDMI-CEC/sleep health, `/sys/bus/hid/drivers`, MATVT AccessibilityService state, Aerial Views screensaver state, and installed MoBox apps.
- **`fixer/updater.py`**: commit-based self-updater comparing local `HEAD` against `aghamorad/mibox-fixer` `main` via GitHub API, with explicit confirmation before `git pull --ff-only`.
- **`fixer/adb.py`**: automatic macOS `5037 → 5038` isolated ADB server fallback on `No route to host`, plus `enable_matvt_service()`, `enable_aerial_views_screensaver()`, `start_screensaver_now()`, and `open_bluetooth_settings()`.
- **`fixer/tasks.py`**: `Fixer.do_mobox_simple_setup()` safely installs missing MoBox apps (`hume`, `tvbro`, `mytv`, `slamvision`, `smarttube`, `matvt`, `aerialviews`), activates MATVT + Aerial Views 5-minute 4K Space & Nature slideshow (`screen_off_timeout=300000`, `sleep_timeout=-1` so the box dreams without ever entering deep sleep), applies HDMI-CEC TV-remote auto-wake fix (`hdmi_control_auto_device_off_enabled=0`), sets Hume home screen, and configures MyTV Top Picks + Worldwide playlist.
- **Local 4K NASA Space & Nature Wallpapers**: pushed 5 public-domain NASA James Webb / ISS / Blue Marble 4K wallpapers (`NASA_JWST_Pillars_of_Creation_4K.jpg`, `NASA_JWST_Carina_Cosmic_Cliffs_4K.jpg`, `NASA_JWST_Southern_Ring_Nebula_4K.jpg`, `NASA_Earth_From_ISS_Aurora_4K.jpg`, `NASA_Blue_Marble_Earth_Space_4K.jpg`) alongside the 10 existing 4K Space/Nature wallpapers in `/sdcard/Wallpapers` and `/sdcard/Pictures/Wallpapers` (15 total, indexed in MediaStore).
- **`fixer/gui.py` & `MoBox.command`**: dual-mode switcher (`Simple (75-Year-Old Mode)` default + `Advanced (35-Year-Old Mode)`), 1-click **"Start 4K Space & Nature Slideshow Now"** button, double-clickable `MoBox.command` launcher, persistent `"Made by Morad"` footer + self-updater bar.
- **Verified**: `38/38` unit tests pass (`tests/test_mobox.py`); live end-to-end auto-discovery + firmware inspection verified against Morad's Mi Box 4 (`MIBOX4`, `192.168.0.117:5555`, `PI.3933`, `776 MB` free, `TV_WAKE_READY: True`, `MATVT: Active`, `4K Slideshow: Active`, `HID: ['apple', 'hid-generic']`). Desktop guide: `~/Desktop/MoBox — a noob's guide.md`.

## 2026-11-19 Apple Magic Mouse helper (MATVT) & HDMI-CEC TV-wake fix — completed
Verified live against Morad's Mi Box 4 (`MIBOX4`, Android 9 / SDK 28, `armeabi-v7a`, Linux `4.9.113`) at `192.168.0.117:5555` (via isolated ADB server port `5038` so the Quest 3 on `5037` stayed untouched):
- **Kernel HID audit**: `/sys/bus/hid/drivers` contains only `apple` and `hid-generic` — Xiaomi omitted `hid-magicmouse` from kernel `4.9.113`. Direct Bluetooth pairing gives optical pointer + left/right click (no glass multi-touch scroll/trackpad on-box without an external Linux USB HID bridge like a Pi Zero 2 W).
- **MATVT v1.0.6 (`io.github.virresh.matvt`)** installed from `virresh/matvt` (`matvt-app-release-v1.0.6.apk`, via temporary Play Protect verifier toggle with verified restore to `1`), granted `SYSTEM_ALERT_WINDOW`, and enabled `io.github.virresh.matvt/.services.MouseEventService` in `secure/enabled_accessibility_services` (`accessibility_enabled=1`, PID `32226` running). Added `matvt` to `fixer/catalog.py`.
- **HDMI-CEC / Never-Sleep fix** (eliminates the Android 9 + Samsung Anynet+ deep-sleep coma when the TV turns off so the box is always awake and ready for the Samsung TV remote when the TV turns on): set `global/stay_on_while_plugged_in=7`, `global/hdmi_control_enabled=1`, `global/hdmi_control_one_touch_play_enabled=1`, `global/hdmi_control_auto_device_off_enabled=0` (verified `mAutoTvOff:false` in `dumpsys hdmi_control`), `global/hdmi_control_auto_wakeup_enabled=1`, `secure/sleep_timeout=-1`, `secure/screensaver_enabled=0`, `system/screen_off_timeout=2147483647`. Folded into `Fixer.do_tune()` in `fixer/tasks.py`.
- **Verification**: `python3 -m unittest discover -s tests -v` passed `31/31`; noob's guide written to `~/Desktop/Mi Box Mouse & Auto-Wake — a noob's guide.md`.
- **Manual on-TV step remaining for Morad**: Pair the Apple Magic Mouse in **Settings → Remotes & Accessories → Add accessory**, and optionally open **MATVT** once to pick a preferred BossKey on the Samsung remote.

## 2026-11-17 personalized TV and portable setup — in progress
Prioritize comedy, classic films, wrestling and independent/non-establishment
news while retaining the full Free-TV worldwide list including Iran. User also
wants an easy installable setup for another Mi Box, consolidated in this repo.
Do not promise premium PPVs or TCM without a verified licensed source. Current
MyTV favorites are empty; 2,200 worldwide channels loaded previously. Inspect
how MyTV stores favorites and configure with verified, reachable choices.
Develop a repeatable setup and distinguish automatic steps from on-device steps.
The portable setup is `setup_mibox.py` and `Install MiBox.command`; it installs
missing apps without removing existing ones, appends a source, backs up MyTV
settings privately, and sets Hume. Hume onboarding and TV Bro homepage/bookmark
remain manual; no second-box test has been performed. `build_world_playlist.py`
generates `playlists/world.m3u` from Free-TV, prepending four tested candidates
in Top Picks; GitHub Actions refreshes it daily. Stream checks were from the Mac,
not a guarantee of playback on the box. The first three picks were published,
selected on the box, and MyTV logged 98 groups and 2,203 parsed channels. The
fourth pick (Magnificent Movies) passed an end-to-end Mac stream check and was
published at 59b6dbd; the box may cache the previous playlist for an hour. Actual
playback on the box and installation on a fresh second Mi Box remain unverified.
CI passed for commit b234f56. Prior config backup: /tmp/mytv-world-before-picks.json.

## 2026-11-17 home screen and cleanup audit
Morad wants a clean, easy Apple TV-like experience, with no unwanted clutter or
adware. Audit enabled packages and the actual Beam home screen; investigate
compatible Apple-style alternatives without disrupting TV Bro, IPTV or remote
control. Keep changes reversible, preserve app data and avoid broad debloating.
Box is Android 9/32-bit. Hume Launcher 7.8 installed from its official release
and set as default; Beam remains enabled for recovery. Hume's recommendations,
news, weather, and presentation mode are off. Dock starts TV Bro, TV Live,
SlamVision, SmartTube and VLC. TV Bro cold launch reached the Download-e Rooz
login page; its separate Beam bookmark tile is not available on Hume. The TV Live
worldwide configuration was not changed. Play Protect remains enabled. Many
advertising/telemetry and reseller packages were already disabled; enabled
third-party apps include multiple browsers, file managers, VPNs and casting
apps, whose use or adware status has not been established. None were removed.
Storage was 795 MB free before Hume installation. Home resolution and D-pad
navigation were checked via ADB; physical Samsung remote and reboot untested.
The fixer's existing Set Home action still defaults to Beam: do not run it if
Hume should remain default. Restore Beam with `adb shell cmd package
set-home-activity com.home.tiles/.MainActivity`.

## 2026-11-17 correction — worldwide IPTV
Morad explicitly wants the complete Free-TV/IPTV worldwide playlist, not an
Iran-only service or a separate iptv-ir project. Consolidate configuration and
documentation here. Preserve existing device configuration and do not delete
the separate repository. Verify actual loading and representative playback;
individual upstream channels may be unavailable or geographically restricted.
MyTV now selects `https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8`
directly, and its log reports 97 groups and 2,200 channels versus 2,203 entries
in the downloaded source. Startup is set to Channels; screen OCR confirms country
groups appear. Catalog defaults to that worldwide source; iptv-org remains an
option. EPG is still disabled and coverage has not been assessed for worldwide.
The old Iran-only settings and claims below are historical and superseded.
Individual channel playback, the three missing entries, and EPG coverage remain
unverified; upstream geo-blocking and stream failures may affect availability.

## Objective
One repeatable tool that turns a stock Xiaomi Mi Box (or any Android TV box)
into a clean, fast media player over ADB: disable the junk, install the good
apps, apply the tweaks.

## Current state
Version 1.2.1. 28 tests pass, the CLI smoke test and the GUI import pass. Every
app download URL in the catalog resolves, TV Bro's included.

## What changed in 1.2.1 (2026-11-17)
- **Catalog**: `IPTV_PLAYLISTS` gained **Iran (verified)** — the 20-channel list
  from `../iptv-ir/`, rebuilt and end-to-end verified daily. The existing
  iptv-org entries stay; they are still the right answer for "everything".
- **README**: the "If you have lost the remote" section claimed `uiautomator
  dump` was "usually the faster answer". It is not, against MyTV: the app
  returns `ERROR: null root node returned by UiTestAutomationBridge` on every
  retry. Added two worked alternatives — reading the screen with Vision OCR over
  JXA, and driving MyTV through its own web panel on port 10591 — plus the
  finding that `input tap` does nothing on this box and `appStartupScreen:
  "Live"` skips the dashboard entirely.

## IPTV on the box (2026-11-17)

MyTV ("TV Live", `com.github.mytv.android`) is the player. Its web panel on
`http://192.168.1.45:10591/` is the control surface that matters — `GET
/api/logs` is the app's structured log and the honest answer to "did this
work", `GET`/`POST /api/configs` is the 138-setting store.

Verified by the panel's own log, not by eyeballing the TV:

- `加载订阅源（Iran TV (verified)）：1个分组，20个频道` — the source is the
  `iptv-ir` playlist and 20 channels loaded.
- `首次启动，选择第一个频道: IRIB TV1` followed by the URL handed to Media3,
  with `dumpsys SurfaceFlinger` showing `PlayerActivity` and its `SurfaceView`
  resumed and wlan0 moving ~3.5 Mbit/s. That is playback, not a menu.
- MyTV's bundled EPG covers **none** of these channels — `加载节目单：0个频道`
  against 787 loaded — so `epgEnable` is now `false`, removing a download and a
  parse from every launch.
- `appStartupScreen` is now `Live`: the app opens straight into IRIB TV1
  full-screen, so the television remote zaps channels through HDMI-CEC with no
  app navigation.

## What changed in 1.2.0 (2026-11-17)
- **Catalog**: TV Bro moved 2.1.6 → **3.0.5**, and the entry now takes
  `tvbro-3.0.5-generic-geckoExcluded.apk` as a single `asset` instead of an
  `arch_assets` map. The old entry's comment ("stay on 2.1.6") was the wrong
  conclusion from a correct observation: on 3.x `geckoIncluded` carries
  `applicationIdSuffix = ".gecko"` and installs a *second* app, but
  `geckoExcluded` is the real browser, is arch-independent, and upgrades a
  2.1.6 install in place with bookmarks and settings intact. Verified on the
  box: 3.0.5 runs, home page and bookmarks survived.
- **adb.py**: new `Adb.install_past_play_protect()`. Reads
  `package_verifier_enable`, sets it to `0`, installs, and restores the previous
  value in a `finally` — including when the install fails. An unset/`null`
  value restores to `1`, and a box that already had it off keeps it off.
- **tasks.py**: `do_install` retries once through
  `install_past_play_protect()` when the first attempt comes back as the Play
  Protect hint, so a sideload no longer needs a manual detour.
- **tests**: `test_catalog` now asserts the TV Bro asset is never a
  `geckoIncluded` one and that it matches the pinned tag;
  `test_install_errors` covers the verifier off/restore cycle with a fake Adb.
- **README**: new "TV Bro: take the `geckoExcluded` build" section; the Play
  Protect section now says the tool restores the setting itself.

## What changed in 1.1.0 (2026-11-17)
- **Catalog**: added **SlamVision** (`com.slamvision.tv`, `jhatren927-ai/slamvision-tv`
  v1.4.0, single asset `SlamVision.apk`). Verified installed and launching on the
  real box. Not enabled by default: it is a niche streaming app.
- **Catalog**: documented why the TV Bro entry must stay on the 2.1.6 assets.
  From 3.0.0 the `geckoIncluded` flavour gained
  `applicationIdSuffix = ".gecko"`, so `tvbro-*-geckoIncluded-*.apk` installs a
  *second* app (`com.phlox.tvwebbrowser.gecko`) and leaves the browser alone.
  In 2.1.6 the suffix did not exist and that asset is the browser itself.
- **adb.py**: install failures are now translated for the user instead of
  dumped raw — Play Protect (`INSTALL_FAILED_VERIFICATION_FAILURE`), signing
  mismatch, downgrade, no space. `Adb.allow_install_packages()` added.
- **catalog.py / tasks.py**: new `AppItem.self_updates` flag. Apps that ship
  their own updater get the install permission granted after a successful
  install, so their updater works without a trip through Settings. Beam is
  flagged; it is the only app in the catalog with a built-in updater.
- **README**: added "When an install is refused" and "If you have lost the
  remote" sections.
- **tests**: `tests/test_install_errors.py` covers the failure messages and the
  `self_updates` flag.

## Verified against the real device
Xiaomi Mi Box 4 (`MIBOX4` / `oneday`, Android 9 / SDK 28, `armeabi-v7a`,
192.168.1.45) over ADB on Wi-Fi:
- SlamVision installs from the catalog URL and launches.
- Beam updated 1.0.1 → 1.0.2 **through its own updater**, which needed
  `appops set com.home.tiles REQUEST_INSTALL_PACKAGES allow` first. That is the
  observation the `self_updates` flag encodes.
- TV Bro 2.1.6 → 3.0.5 was refused by Play Protect with
  `INSTALL_FAILED_VERIFICATION_FAILURE`. Morad approved the workaround;
  `package_verifier_enable 0` → install → back to `1` (confirmed restored).
  Removing the mis-installed `com.phlox.tvwebbrowser.gecko` was the other half
  of that detour.
- TV Bro's **Android TV home screen → Bookmarks row** works with Beam 1.0.2:
  the channel publishes 9 programs and Beam reports `Cards: 9`. Two things
  needed doing that are not obvious from either project's docs:
  - Beam must be **force-stopped** before it re-reads a channel whose programs
    changed; a plain relaunch shows the old row.
  - The row's own setting is `Bookmarks in the row`, defaulting to *Home page
    bookmarks* — TV Bro's eight stock demo bookmarks. Set it to **All
    bookmarks** or to a folder, or the user's own bookmark never appears.
- Beam's `Channel rows` panel (Appearance → Channel rows) is the fastest way to
  see what Beam actually reads: it prints `Cards: N` per channel.

## Open
- **TV Bro channel posters never load in Beam.** `ChannelPostersProvider`
  (`isAllowedCaller`) only serves the app itself, the system uid, or apps
  flagged `FLAG_SYSTEM`. Beam is a sideloaded third-party launcher, so every
  poster request throws `SecurityException: Not allowed` and the tiles render
  as flat grey boxes with just their titles. Fixing it means patching and
  re-signing TV Bro, which changes the signing key and therefore forces an
  uninstall — losing bookmarks and settings. Not worth it for artwork; left
  documented instead.
- Bookmark tiles appear in provider insertion order, so a bookmark added after
  the row was first published lands at the far right. TV Bro publishes a
  `COLUMN_WEIGHT` but Beam passes no sort order and the provider ignores it.
  Reordering means deleting and republishing the channel, which risks losing
  the system's browsable approval.
- The box's own firmware: "up to date" as of 2026-11-17. Nothing to do.

## Adjacent work
`../iptv-ir/` builds the Iranian playlist this repo's catalog now points at; it
has its own handoff and is where the TLS and segment-verification lessons live.
`../MiBox Remote/` holds the separate no-remote control notes and a
remote-v2-protocol client (`mibox.py`). ADB turned out to be enough, so that
client was never paired — do not treat it as verified.

## Next action
Nothing pending on the code. Two ideas worth a session if the need shows up:
`do_push_iptv` could set MyTV's source through the panel (`POST /api/configs`)
instead of pushing a file to `/sdcard/Download/`, which would give the box a
self-updating URL rather than a frozen copy; and the grey poster tiles could be
fixed by patching `ChannelPostersProvider.isAllowedCaller` in TV Bro's smali,
though read the signing-key consequence above first.
