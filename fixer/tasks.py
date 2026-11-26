"""The actual fixer operations. Each one is idempotent and reports a result."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

from . import catalog
from .adb import PLAY_PROTECT_HINT, Adb
from .downloader import fetch_apk, human_size


@dataclass
class Result:
    ok: bool
    message: str


@dataclass
class Plan:
    """What the user ticked."""
    packages: list[str] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)
    tune_animations: bool = True
    stay_awake: bool = True
    set_home: bool = True
    clear_recommendations: bool = True
    push_iptv: bool = False
    wallpaper: Optional[Path] = None
    iptv_playlist: str = catalog.IPTV_PLAYLISTS["All channels"]


Reporter = Callable[[str], None]


def _noop(_: str) -> None:
    pass


class Fixer:
    def __init__(self, adb: Adb, cache_dir: Path, report: Reporter = _noop):
        self.adb = adb
        self.cache = Path(cache_dir)
        self.report = report

    # ------------------------------------------------------------------ debloat

    def do_debloat(self, packages: Iterable[str]) -> list[Result]:
        results: list[Result] = []
        for pkg in packages:
            item = catalog.BLOAT_BY_PACKAGE.get(pkg)
            label = item.title if item else pkg
            if not self.adb.is_installed(pkg):
                self.report(f"skip   {label} (not present)")
                results.append(Result(True, f"{label}: not present"))
                continue
            if not self.adb.is_enabled(pkg):
                self.report(f"ok     {label} (already disabled)")
                results.append(Result(True, f"{label}: already disabled"))
                continue
            ok, detail = self.adb.disable(pkg)
            self.report(("ok     " if ok else "FAIL   ") + f"{label}")
            results.append(Result(ok, f"{label}: {detail}"))
        return results

    def do_restore(self, packages: Iterable[str]) -> list[Result]:
        results: list[Result] = []
        for pkg in packages:
            item = catalog.BLOAT_BY_PACKAGE.get(pkg)
            label = item.title if item else pkg
            ok, detail = self.adb.enable(pkg)
            self.report(("ok     " if ok else "skip   ") + f"{label}")
            results.append(Result(ok, f"{label}: {detail}"))
        return results

    # ------------------------------------------------------------------ installs

    def do_install(self, app_keys: Iterable[str]) -> list[Result]:
        abis = self.adb.abis()
        self.report(f"device ABIs: {', '.join(abis) or 'unknown'}")
        results: list[Result] = []

        for key in app_keys:
            app = catalog.APPS_BY_KEY.get(key)
            if not app:
                results.append(Result(False, f"{key}: unknown app"))
                continue
            self.report(f"--- {app.title}")
            try:
                def prog(done: int, total: int) -> None:
                    if total:
                        self.report(f"    downloading {done * 100 // total}%")

                apk = fetch_apk(app, abis, self.cache, progress=prog)
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                self.report(f"FAIL   download: {exc}")
                results.append(Result(False, f"{app.title}: download failed: {exc}"))
                continue

            self.report(f"    got {apk.name} ({human_size(apk.stat().st_size)})")
            ok, detail = self.adb.install(apk)
            if not ok and detail == PLAY_PROTECT_HINT:
                # Play Protect refused it before the installer read the file.
                # Retry once with the verifier off, then put the setting back.
                self.report("note   Play Protect refused it; retrying with the verifier off")
                ok, detail = self.adb.install_past_play_protect(apk)
            if ok:
                self.report(f"ok     installed {app.title}")
                if app.self_updates:
                    if self.adb.allow_install_packages(app.package):
                        self.report(
                            f"ok     {app.title} may update itself from the box"
                        )
                    else:
                        self.report(
                            f"note   could not grant the install permission to "
                            f"{app.package}; its built-in updater may ask for it"
                        )
            else:
                self.report(f"FAIL   install {app.title}: {detail}")
            results.append(Result(ok, f"{app.title}: {'installed' if ok else detail}"))
        return results

    # ------------------------------------------------------------------ tuning

    def do_tune(self, plan: Plan) -> list[Result]:
        results: list[Result] = []

        if plan.tune_animations:
            for key in catalog.ANIMATION_KEYS:
                ok = self.adb.put_setting("global", key, "0.5")
                results.append(Result(ok, f"{key} = 0.5"))
            self.report("ok     animation scales set to 0.5x")

        if plan.stay_awake:
            has_aerial = self.adb.is_installed("com.neilturner.aerialviews")
            # Keep sleep_timeout=-1 and HDMI-CEC auto-off disabled; when Aerial Views is
            # present let the 5-minute screen_off_timeout trigger the 4K DreamService screensaver
            # while MoBox's KeepAwakeService holds PARTIAL_WAKE_LOCK so the box never enters
            # Amlogic deep-sleep coma.
            awake_settings = [
                ("global", "stay_on_while_plugged_in", 0 if has_aerial else 7),
                ("global", "hdmi_control_enabled", 1),
                ("global", "hdmi_control_one_touch_play_enabled", 1),
                ("global", "hdmi_control_auto_device_off_enabled", 0),
                ("global", "hdmi_control_auto_wakeup_enabled", 1),
                ("secure", "sleep_timeout", -1),
                ("secure", "screensaver_enabled", 1 if has_aerial else 0),
                ("system", "screen_off_timeout", 300000 if has_aerial else 2147483647),
            ]
            all_ok = True
            for ns, key, val in awake_settings:
                ok = self.adb.put_setting(ns, key, val)
                all_ok = all_ok and ok
                results.append(Result(ok, f"{ns}/{key} = {val}"))
            if has_aerial:
                self.adb.enable_aerial_views_screensaver()
            if self.adb.is_installed("com.morad.mobox"):
                self.adb.shell_ok("dumpsys deviceidle whitelist +com.morad.mobox")
                self.adb.shell_ok("am start-foreground-service -n com.morad.mobox/.KeepAwakeService")
            self.report(
                "ok     stay awake & HDMI-CEC TV-remote wake protection applied"
                if all_ok
                else "note   some stay-awake / HDMI-CEC settings failed"
            )

        if plan.clear_recommendations:
            ok = self.adb.shell_ok("pm clear com.android.providers.tv")
            results.append(Result(ok, "recommendation cache cleared"))
            self.report("ok     recommendation rows cleared")

        return results

    # ------------------------------------------------------------------ launcher

    def do_set_home(self, app_key: str = "hume") -> Result:
        app = catalog.APPS_BY_KEY.get(app_key)
        if not app or not app.component:
            return Result(False, "unknown launcher")
        if not self.adb.is_installed(app.package):
            return Result(False, f"{app.title} is not installed yet")

        ok = self.adb.set_home(app.component)
        if ok:
            self.adb.go_home()
            self.report(f"ok     home screen is now {app.title}")
            return Result(True, f"home -> {app.title}")
        return Result(False, f"could not set {app.title} as home")

    # ------------------------------------------------------------------ extras

    def do_push_iptv(self, plan: Plan) -> Result:
        from .downloader import download

        dest = self.cache / "iptv-org.m3u"
        try:
            download(plan.iptv_playlist, dest)
        except Exception as exc:  # noqa: BLE001
            self.report(f"FAIL   playlist download: {exc}")
            return Result(False, str(exc))
        remote = "/sdcard/Download/iptv-org.m3u"
        ok = self.adb.push(dest, remote)
        self.report(
            ("ok     " if ok else "FAIL   ")
            + f"playlist -> {remote} ({human_size(dest.stat().st_size)})"
        )
        return Result(ok, remote)

    def do_push_wallpaper(self, path: Path) -> Result:
        path = Path(path)
        if not path.is_file():
            return Result(False, f"no such file: {path}")
        remote = f"/sdcard/Wallpapers/{path.name}"
        self.adb.shell("mkdir -p /sdcard/Wallpapers")
        ok = self.adb.push(path, remote)
        self.report(
            ("ok     " if ok else "FAIL   ") + f"wallpaper -> {remote}"
        )
        return Result(ok, remote)

    # ------------------------------------------------------------------ runner

    def run(self, plan: Plan) -> list[Result]:
        results: list[Result] = []
        if plan.packages:
            self.report(f"=== Removing {len(plan.packages)} package(s)")
            results += self.do_debloat(plan.packages)
        if plan.apps:
            self.report(f"=== Installing {len(plan.apps)} app(s)")
            results += self.do_install(plan.apps)
        if plan.tune_animations or plan.stay_awake or plan.clear_recommendations:
            self.report("=== Tuning")
            results += self.do_tune(plan)
        if plan.wallpaper:
            self.report("=== Wallpaper")
            results.append(self.do_push_wallpaper(plan.wallpaper))
        if plan.push_iptv:
            self.report("=== IPTV playlist")
            results.append(self.do_push_iptv(plan))
        if plan.set_home:
            self.report("=== Home screen")
            results.append(self.do_set_home())
        return results

    # ------------------------------------------------------------------ MoBox 1-click (Simple Mode)

    MOBOX_SIMPLE_APPS = (
        "hume",
        "mobox",
        "tvbro",
        "mytv",
        "slamvision",
        "smarttube",
        "matvt",
        "aerialviews",
    )

    def do_enable_aerialviews(self) -> Result:
        if not self.adb.is_installed("com.neilturner.aerialviews"):
            return Result(False, "Aerial Views is not installed yet")
        ok = self.adb.enable_aerial_views_screensaver()
        self.report(
            "ok     4K Space & Nature slideshow (Aerial Views) set as screensaver"
            if ok
            else "note   could not set Aerial Views screensaver automatically"
        )
        return Result(ok, "Aerial Views screensaver")

    def do_enable_matvt(self) -> Result:
        if not self.adb.is_installed("io.github.virresh.matvt"):
            return Result(False, "MATVT is not installed yet")
        ok = self.adb.enable_matvt_service()
        self.report(
            "ok     mouse & scroll helper (MATVT) activated"
            if ok
            else "note   could not enable MATVT accessibility automatically"
        )
        return Result(ok, "MATVT accessibility service")

    def do_mobox_simple_setup(
        self,
        progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[Result]:
        """The 75-year-old-friendly all-in-one setup: safe, non-destructive, idempotent."""
        total = 5
        results: list[Result] = []

        def step(idx: int, label: str) -> None:
            self.report(f"=== Step {idx}/{total}: {label}")
            if progress:
                progress(idx, total, label)

        # 1. Install only missing MoBox apps (keep all existing apps & data intact)
        step(1, "Installing missing MoBox apps (keeping your existing apps safe)")
        missing = [
            key
            for key in self.MOBOX_SIMPLE_APPS
            if not self.adb.is_installed(catalog.APPS_BY_KEY[key].package)
        ]
        if missing:
            results += self.do_install(missing)
        else:
            self.report("ok     all MoBox apps are already installed")
            results.append(Result(True, "all MoBox apps present"))

        # 2. Activate MATVT mouse & scroll helper + Aerial Views 4K Space & Nature slideshow
        step(2, "Turning on Mouse Helper (MATVT) & 4K Space/Nature Slideshow")
        results.append(self.do_enable_matvt())
        results.append(self.do_enable_aerialviews())

        # 3. Fix HDMI-CEC + Never-Sleep so TV power-on always finds the box awake
        step(3, "Setting up TV-remote auto-wake (HDMI-CEC + Never-Sleep)")
        results += self.do_tune(
            Plan(tune_animations=True, stay_awake=True, clear_recommendations=False, set_home=False)
        )

        # 4. Set Hume Apple TV-style home screen + grant wallpaper storage permission
        step(4, "Setting your clean Apple TV-style home screen (Hume + 4K Wallpapers)")
        self.adb.shell_ok("pm grant com.petrobot.hume android.permission.READ_EXTERNAL_STORAGE")
        results.append(self.do_set_home("hume"))

        # 5. Refresh Live TV playlist if TV Live's local panel is reachable
        step(5, "Checking Live TV channels (Top Picks + Worldwide)")
        try:
            from urllib.request import Request, urlopen
            import json
            import os
            import time

            rc, port_str, _ = self.adb.run(["forward", "tcp:0", "tcp:10591"], timeout=10)
            if rc == 0 and port_str.strip().isdigit():
                local_port = int(port_str.strip())
                try:
                    url = f"http://127.0.0.1:{local_port}/api/configs"
                    with urlopen(Request(url), timeout=4) as resp:
                        cfg = json.load(resp)
                    playlist = (
                        "https://raw.githubusercontent.com/aghamorad/mibox-fixer/main/playlists/world.m3u"
                    )
                    sources = cfg.get("iptvSourceList", {}).get("value", [])
                    idx = next((i for i, s in enumerate(sources) if s.get("url") == playlist), None)
                    if idx is None:
                        sources.append({
                            "name": "Top Picks + Worldwide",
                            "url": playlist,
                            "sourceType": 0,
                            "mac": None,
                            "userName": None,
                            "password": None,
                            "format": None,
                            "transformJs": None,
                            "httpUserAgent": None,
                            "httpProxy": None,
                        })
                        idx = len(sources) - 1
                    cfg["iptvSourceCurrentIdx"] = idx
                    cfg["appStartupScreen"] = "Channels"
                    # Private backup before writing
                    self.cache.mkdir(parents=True, exist_ok=True)
                    bak = self.cache / f"mytv-backup-{int(time.time())}.json"
                    fd = os.open(bak, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "w") as out:
                        json.dump(cfg, out, ensure_ascii=False, indent=2)
                    req = Request(
                        url,
                        data=json.dumps(cfg).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                    )
                    with urlopen(req, timeout=6) as resp:
                        res = json.load(resp)
                    # MyTV resets iptvSourceCurrentIdx to -1 whenever iptvSourceList changes;
                    # re-fetch and POST a second time to lock in the active source index.
                    with urlopen(Request(url), timeout=4) as resp:
                        cfg2 = json.load(resp)
                    cfg2["iptvSourceCurrentIdx"] = idx
                    req2 = Request(
                        url,
                        data=json.dumps(cfg2).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                    )
                    with urlopen(req2, timeout=6) as resp:
                        res = json.load(resp)
                    ok = res.get("code") == 0
                    self.report(
                        "ok     TV Live set to Top Picks + Worldwide"
                        if ok
                        else "note   TV Live will finish setup after you open it once on the TV"
                    )
                    results.append(Result(True, "TV Live playlist checked"))
                finally:
                    self.adb.run(["forward", "--remove", f"tcp:{local_port}"], timeout=10)
            else:
                self.report("note   open TV Live once on the TV to finish channel setup")
                results.append(Result(True, "TV Live pending first launch"))
        except Exception:  # noqa: BLE001 - non-fatal if TV Live hasn't opened yet
            self.report("note   open TV Live once on the TV to finish channel setup")
            results.append(Result(True, "TV Live pending first launch"))

        return results


def diagnose(adb: Adb, report: Reporter = _noop) -> dict:
    """Read-only summary of the device's current state."""
    info = adb.info()
    disabled = [
        line.replace("package:", "").strip()
        for line in adb.shell("pm list packages -d").splitlines()
        if line.startswith("package:")
    ]
    mem = adb.mem_available_kb()
    state = {
        **info,
        "ip": adb.wlan_ip(),
        "abis": adb.abis(),
        "disabled": sorted(disabled),
        "mem_available_mb": round(mem / 1024) if mem else None,
        "installed": {
            a.key: adb.is_installed(a.package) for a in catalog.APPS
        },
    }
    report(f"{info.get('model')} / {info.get('product')} (Android {info.get('release')}, SDK {info.get('sdk')})")
    report(f"ABI: {', '.join(state['abis'])}")
    report(f"Disabled packages: {len(disabled)}")
    if state["mem_available_mb"]:
        report(f"Free RAM: {state['mem_available_mb']} MB")
    return state
