#!/usr/bin/env python3
"""Install the portable Mi Box setup without removing existing apps or data."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

from fixer.adb import Adb, AdbError
from fixer.catalog import APPS_BY_KEY
from fixer.downloader import fetch_apk

PLAYLIST = "https://raw.githubusercontent.com/aghamorad/mibox-fixer/main/playlists/world.m3u"
SOURCE = {"name": "Top Picks + Worldwide", "url": PLAYLIST, "sourceType": 0,
          "mac": None, "userName": None, "password": None, "format": None,
          "transformJs": None, "httpUserAgent": None, "httpProxy": None}


def configure_source(config):
    sources = config["iptvSourceList"]["value"]
    index = next((i for i, item in enumerate(sources) if item.get("url") == PLAYLIST), None)
    if index is None:
        sources.append(SOURCE.copy())
        index = len(sources) - 1
    config["iptvSourceCurrentIdx"] = index
    config["appStartupScreen"] = "Channels"
    return index


def request_config(port, config=None):
    data = None if config is None else json.dumps(config).encode()
    request = Request(f"http://127.0.0.1:{port}/api/configs", data=data,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        result = json.load(response)
    if config is not None and result.get("code") != 0:
        raise RuntimeError(f"TV Live rejected the configuration: {result}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="ADB serial or IP address:5555")
    args = parser.parse_args()
    serial = args.serial or input("Mi Box IP address (or ADB serial): ").strip()
    if not serial:
        raise ValueError("A device address is required")
    if "." in serial and ":" not in serial:
        serial += ":5555"
    adb = Adb(serial=serial)
    if ":" in serial:
        Adb(binary=adb.binary).run(["connect", serial], check=True)
    adb.run(["get-state"], check=True)
    print("Approve the debugging prompt on the TV if requested.")
    abis = adb.abis()
    cache = Path.home() / ".cache" / "mibox-fixer" / "apks"
    for key in ("hume", "tvbro", "mytv", "slamvision", "smarttube"):
        app = APPS_BY_KEY[key]
        if adb.is_installed(app.package):
            print(f"Keeping existing {app.title}")
            continue
        print(f"Downloading and installing {app.title}...")
        apk = fetch_apk(app, abis, cache)
        ok, message = adb.install(apk, reinstall=False, downgrade=False)
        if not ok:
            raise RuntimeError(f"{app.title}: {message}. Check the TV for an install prompt.")
    print("Opening TV Live. Accept its first-run agreement on the TV, then press Enter here.")
    adb.launch(APPS_BY_KEY["mytv"].component)
    input()
    rc, port, err = adb.run(["forward", "tcp:0", "tcp:10591"], check=True)
    port = int(port.strip())
    try:
        config = request_config(port)
        backup_dir = Path.home() / ".cache" / "mibox-fixer"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"mytv-backup-{int(time.time())}.json"
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump(config, out, ensure_ascii=False, indent=2)
        index = configure_source(config)
        request_config(port, config)
        config = request_config(port)
        config["iptvSourceCurrentIdx"] = index
        request_config(port, config)
        actual = request_config(port)
        if actual["iptvSourceCurrentIdx"] != index or actual["iptvSourceList"]["value"][index]["url"] != PLAYLIST:
            raise RuntimeError("TV Live did not retain the chosen source")
        print(f"Worldwide playlist selected. Previous TV Live settings saved privately at {backup}")
    finally:
        adb.run(["forward", "--remove", f"tcp:{port}"])
    if not adb.set_home(APPS_BY_KEY["hume"].component):
        raise RuntimeError("Could not set Hume as the home screen")
    print("Hume is the home screen. Finish its on-TV setup and arrange its dock.")
    print("Set TV Bro's home page/bookmark to https://kristina.orson-welles.net/ manually.")
    print("No apps were removed and Play Protect was not disabled.")


if __name__ == "__main__":
    try:
        main()
    except (AdbError, OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"Setup stopped: {exc}", file=sys.stderr)
        sys.exit(1)
