# Mi Box Fixer

Turn a slow, ad-ridden Xiaomi Mi Box (or any Android TV box) into a fast, clean
media player — from your computer, over Wi-Fi, with checkboxes.

No custom ROM. No unlocked bootloader. No chance of bricking the box: everything
this tool does is either an app install or a *reversible* `pm disable-user`.

```
  ┌─ Mi Box Fixer ─────────────────────────────────────────────┐
  │ [What to remove] [What to install] [Tweaks] [Help]         │
  │                                                            │
  │  Streaming bloat                            [toggle]       │
  │   ☑ Netflix          Removes the home-screen row too.      │
  │   ☑ Amazon Prime     Preloaded Prime Video.                │
  │  ...                                                       │
  │                                     [Check device] [Apply]  │
  └────────────────────────────────────────────────────────────┘
```

## What it does

| Tab | What you get |
|---|---|
| **What to remove** | 46 packages you can switch off, grouped by category (streaming bloat, IPTV reseller junk, redundant VPN trials, Google TV ads, telemetry, Mi services). All disabled, never uninstalled. |
| **What to install** | 13 open-source TV apps, with the correct 32-bit or 64-bit APK picked automatically for your box. |
| **Tweaks** | Faster animations, stay-awake, clear recommendation rows, set the launcher, push an IPTV playlist, set a wallpaper. |
| **Help** | The exact steps to turn on debugging, plus what this tool will and won't touch. |

Everything is also available headless (see *Terminal use* below).

The default IPTV playlist is Free-TV/IPTV's worldwide list, organized into
country and topic groups. MyTV can use its upstream URL directly for updates;
the fixer's playlist option instead copies a snapshot to the box. Availability
varies by channel, location and streaming provider. The optional iptv-org lists
remain available in the playlist selector.

Tested end to end against a real **Mi Box 4**: the recommended profile applied
cleanly **57/57 steps, 0 failures**.

## Why this exists

A stock Mi Box ships with Netflix, Prime Video, Apple TV, YouTube, two Play
services, Xioami telemetry, and — on many units — paid IPTV reseller apps like
"Family 4K Pro" and "Smarters Player Lite" that nobody asked for. The home
screen is a wall of recommendations and ads, and the box has 2 GB of RAM to run
all of it.

This tool is the distilled, repeatable version of the manual fix: verified
package-by-package against a real **Mi Box 4** (`MIBOX4` / `oneday`, Android 9,
`armeabi-v7a`, SDK 28). Every package name in the catalog was read off the
device with `pm list packages`, not copied from a forum.

## Install

Requires **Python 3.9+** (tkinter is included with the python.org and Homebrew
builds; on Debian/Ubuntu install `python3-tk`) and **adb**.

```bash
git clone https://github.com/aghamorad/mibox-fixer && cd mibox-fixer

# adb, if you don't have it:
brew install --cask android-platform-tools   # macOS
sudo apt install adb                         # Debian/Ubuntu

python3 -m fixer          # opens the window
```

Prefer not to clone? Download the ZIP from GitHub and run `python3 -m fixer`
inside the extracted folder — there are no dependencies to install.

If adb lives somewhere unusual, point at it directly:

```bash
export ADB_PATH=/path/to/adb
```

## Step 1 — let your computer talk to the box

On the Mi Box:

1. **Settings → Device Preferences → About → Build**, and click it 7 times to
   unlock Developer options.
2. **Settings → Device Preferences → Developer options** → turn on
   **USB debugging** and **Network debugging**.
3. Note the IP address shown there (e.g. `192.168.1.45`).

Then in Mi Box Fixer click **Connect Wi-Fi…**, type the IP and hit Connect. The
box must be on the same Wi-Fi network as your computer. USB works too — just
plug it in and press **Rescan**.

## Step 2 — tick what you want

The defaults are the configuration that was actually deployed: the safe bloat
off, and Beam + SmartTube + TV Bro + Lantern + AmneziaVPN + AirPlay + Miracast
+ xplayer + Material Files installed. Nothing is applied until you press
**Apply changes**, and you get a confirmation summary first.

## Undo

Every removal is `pm disable-user`, so nothing is deleted:

- Tick the packages and press **Restore selected**, or
- `python3 -m fixer --host <ip> --restore-all`

## Terminal use

```bash
python3 -m fixer --list                         # see everything available
python3 -m fixer --host 192.168.1.45 --recommended --dry-run
python3 -m fixer --host 192.168.1.45 --recommended
python3 -m fixer --host 192.168.1.45 --remove netflix --install smarttube
python3 -m fixer --host 192.168.1.45 --restore-all
```

## Safety notes

- **Nothing is uninstalled.** Removal is `disable-user`, which is reversible
  and survives reboot.
- **No bootloader work.** Most Mi Boxes have a locked bootloader; this tool
  does not attempt to change that, and it never flashes anything.
- **Two items are marked ⚠** in the interface (the stock launcher and Mi TV
  Home). Disable those only *after* a replacement launcher is installed and
  working, or the box has no home screen.
- **`com.google.android.apps.mediashell`** is what makes the box a Chromecast
  target. If you cast to it from your phone, leave that one on.
- Downloading APKs happens directly from each project's official GitHub
  release page. APKs are cached in `~/.cache/mibox-fixer`.

## When an install is refused

**Play Protect says the app is harmful.** Nothing this tool installs is in the
Play catalogue, and Play Protect blocks what it does not recognise. The APK is
not the problem; the box is. Allow it once — Play Store → your profile → Play
Protect → gear icon → turn scanning off — and install again. Or turn the
verifier off from the terminal:

```bash
adb shell settings put global package_verifier_enable 0
```

The tool now says this in plain words instead of leaving you with
`INSTALL_FAILED_VERIFICATION_FAILURE`, and explains the other common refusals
(wrong signing key, downgrade, no space) the same way. It also retries the
install itself with the verifier off and puts the setting back afterwards, so
you do not have to leave the box with scanning permanently disabled — a
`package_verifier_enable 0` left behind weakens every later install.

**An app's own updater does nothing.** Apps that update themselves need the
install permission before Android lets them start the installer. The fixer
grants it for the ones that ship an updater (the Beam launcher does).

## TV Bro: take the `geckoExcluded` build

TV Bro ships two flavours, and on 3.x the names are a trap. The
`geckoIncluded` APKs carry `applicationIdSuffix = ".gecko"`, so they install a
**second, separate app** (`com.phlox.tvwebbrowser.gecko`) and leave the browser
you already have untouched — it looks like the install worked and nothing
changed. The fixer therefore always takes
`tvbro-<version>-generic-geckoExcluded.apk`.

That build is WebView-only and architecture-independent: about 3.6 MB instead
of ~149 MB, and it upgrades an existing 2.1.6 install in place, keeping
bookmarks and settings. The trade-off is that the bundled Gecko engine is gone
and pages render with the system WebView, which is fine on Android 9.

## If you have lost the remote

The box is still perfectly drivable. Two ways in, in the order worth trying:

```bash
adb connect 192.168.1.45:5555        # then press OK on the On-TV prompt
adb shell input keyevent KEYCODE_HOME
adb shell input keyevent 20          # DPAD_DOWN; 19/20/21/22/23 = U/D/L/R/OK
```

Over HDMI-CEC the television's own remote drives the box once *Anynet+*
(Samsung) is on and the box's CEC is on — no configuration on this side:

```bash
adb shell dumpsys hdmi_control | head -20    # shows presses arriving from the TV
```

Two things that cost real time when driving the box this way:

- A full-screen keyboard is not the obstacle you think. When a dialog swallows
  the delete key, `adb shell settings put secure show_ime_with_hard_keyboard 1`
  brings up Gboard, after which deletes reach the field. Hide it again before
  tapping any button in the lower half of the dialog.
- `adb exec-out screencap -p` gives you the pixels and `uiautomator dump` gives
  you the tree. The tree is usually the faster answer — but not always: against
  MyTV it answers `ERROR: null root node returned by UiTestAutomationBridge` and
  every retry fails the same way, while against a launcher it works first time.
  Keep `screencap` as the fallback rather than the last resort.

### Reading the screen when `uiautomator` refuses

A screenshot is just pixels until something reads it. macOS can, with no
install — Vision is reachable from JXA:

```bash
adb exec-out screencap -p > /tmp/tv.png
```

```javascript
ObjC.import('Vision'); ObjC.import('Foundation');
const url = $.NSURL.fileURLWithPath('/tmp/tv.png');
const req = $.VNRecognizeTextRequest.alloc.init;
req.recognitionLevel = 0;              // 0 = accurate, 1 = fast
const handler = $.VNImageRequestHandler.alloc.initWithURLOptions(url, $());
handler.performRequestsError($([req]), $());
for (let i = 0; i < req.results.count; i++)
  console.log(ObjC.unwrap(req.results.objectAtIndex(i).topCandidates(1).objectAtIndex(0).string));
```

Run it with `osascript -l JavaScript ocr.js /tmp/tv.png`. Read
`observation.boundingBox` too (it is normalised with the origin at the bottom
left, so flip `y`) and you get coordinates, which is what makes the pointer
question answerable.

`adb shell input tap x y` does **not** work here: the box has no touchscreen and
the apps ignore synthetic touches. D-pad events do work, but nothing tells you
where focus is — so take a screenshot, send one key, take another, and diff
them. The focus ring's repaint is the only thing that changes, which gives you
its rectangle; match that against the OCR boxes and you know which label you
just landed on. `input keyevent` numbers: 19 up, 20 down, 21 left, 22 right,
23 select.

### MyTV's web panel, when the pixels are not enough

MyTV ("TV Live", `com.github.mytv.android`) serves its own control panel on
**port 10591** — `http://192.168.1.45:10591/` — and it is a far better control
surface than the D-pad. Two endpoints carry the weight:

- `GET /api/logs` is the app's structured log. It reports the loaded source,
  group and channel counts, the playing channel, and the URL sent to the player.
- `GET`/`POST /api/configs` reads and writes all 138 settings (`epgEnable`,
  `appStartupScreen`, `iptvSourceList`, …). **Post the whole object back** —
  the panel's own UI does, and a partial body lets the app re-derive the rest.
  `GET` first, keep a copy, change one key, `POST`.

`appStartupScreen` accepts `Dashboard`, `Live`, `EpgGuide`, `Channels`,
`Favorites`, `Search`, `MultiView`. `Live` skips the dashboard entirely and
starts the first channel full-screen; combined with the box's HDMI-CEC the
television remote then zaps channels with no app navigation at all.

On this box the bundled EPG was disabled after it matched none of the previous
Iran-only playlist. Programme-guide coverage for the worldwide list has not
been verified; it may be enabled and configured separately if wanted.

## What's in here

```
fixer/
  adb.py          thin wrapper around the adb binary
  catalog.py      the verified package list + app manifest
  downloader.py   picks the right armv7/arm64 APK and downloads it
  tasks.py        the operations (disable / install / tune / restore)
  gui.py          tkinter interface
  cli.py          headless interface
  __main__.py     entry point
```

## Credits

This tool only installs other people's work. All apps are the property of their
respective authors, fetched from their own release pages:

[Beam](https://github.com/tonisaf/beam-launcher) ·
[SmartTube](https://github.com/yuliskov/SmartTube) ·
[TV Bro](https://github.com/truefedex/tv-bro) ·
[Lantern](https://github.com/getlantern/lantern) ·
[AmneziaVPN](https://github.com/amnezia-vpn/amnezia-client) ·
[AirPlay Server](https://github.com/jqssun/android-airplay-server) ·
[MiracastReceiver](https://github.com/weekdayjast/MiracastReceiver) ·
[xplayer](https://github.com/TNT-Likely/xplayer) ·
[Material Files](https://github.com/zhanghai/MaterialFiles) ·
[Fossify File Manager](https://github.com/FossifyOrg/File-Manager) ·
[FLauncher](https://github.com/osrosal/flauncher) ·
[LTvLauncher](https://github.com/leanbitlab-org/LtvLauncher) ·
[SlamVision](https://github.com/jhatren927-ai/slamvision-tv) ·
[iptv-org](https://github.com/iptv-org/iptv)

## License

MIT — see `LICENSE`.

## Security

This project never asks for your GitHub password or a token. Pushing is done with SSH keys.
