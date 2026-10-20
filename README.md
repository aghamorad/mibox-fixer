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
| **What to install** | 12 open-source TV apps, with the correct 32-bit or 64-bit APK picked automatically for your box. |
| **Tweaks** | Faster animations, stay-awake, clear recommendation rows, set the launcher, push an IPTV playlist, set a wallpaper. |
| **Help** | The exact steps to turn on debugging, plus what this tool will and won't touch. |

Everything is also available headless (see *Terminal use* below).

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
[iptv-org](https://github.com/iptv-org/iptv)

## License

MIT — see `LICENSE`.

## Security

This project never asks for your GitHub password or a token. Pushing is done with SSH keys.
