"""The actual fixer operations. Each one is idempotent and reports a result."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

from . import catalog
from .adb import Adb
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
            if ok:
                self.report(f"ok     installed {app.title}")
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
            ok = self.adb.put_setting("global", "stay_on_while_plugged_in", 3)
            results.append(Result(ok, "stay awake while plugged in"))
            self.report("ok     stay awake while plugged in")

        if plan.clear_recommendations:
            ok = self.adb.shell_ok("pm clear com.android.providers.tv")
            results.append(Result(ok, "recommendation cache cleared"))
            self.report("ok     recommendation rows cleared")

        return results

    # ------------------------------------------------------------------ launcher

    def do_set_home(self, app_key: str = "beam") -> Result:
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
