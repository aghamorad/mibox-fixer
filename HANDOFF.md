# Handoff — Mi Box Fixer

## Objective
One repeatable tool that turns a stock Xiaomi Mi Box (or any Android TV box)
into a clean, fast media player over ADB: disable the junk, install the good
apps, apply the tweaks.

## Current state
Version 1.1.0. Tests, the CLI smoke test and the GUI import all pass. Every
app download URL in the catalog resolves.

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
  `INSTALL_FAILED_VERIFICATION_FAILURE`. Deliberately not worked around; that
  is a security setting and needs Morad's approval. Removing the mis-installed
  `com.phlox.tvwebbrowser.gecko` was the other half of that detour.

## Open
- Whether to bypass Play Protect to move TV Bro to 3.0.5. The upside is the
  3.x *Home screen → Bookmarks row* channel, which pins a bookmark to the Mi Box
  home screen. Note the 3.x `geckoExcluded` asset is only ~3.6 MB and drops the
  bundled Gecko engine (WebView only), so this is a behaviour change, not a
  straight upgrade.
- The box's own firmware: "up to date" as of 2026-11-17. Nothing to do.

## Adjacent work
`../MiBox Remote/` holds the separate no-remote control notes and a
remote-v2-protocol client (`mibox.py`). ADB turned out to be enough, so that
client was never paired — do not treat it as verified.

## Next action
Nothing pending on the code. Ask Morad about the Play Protect call before
changing any TV Bro asset in the catalog.
