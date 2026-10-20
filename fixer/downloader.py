"""Resolve and download the right APK build for the device's architecture."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from .catalog import AppItem

USER_AGENT = "MiBoxFixer/1.0 (+https://github.com/)"

ProgressFn = Optional[Callable[[int, int], None]]


class DownloadError(RuntimeError):
    pass


def _request(url: str, *, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def _is_64bit(abis: list[str]) -> bool:
    return any(a.startswith("arm64") or a == "x86_64" for a in abis)


def pick_asset(app: AppItem, abis: list[str]) -> Optional[str]:
    """Choose the best asset name for the given device ABIs."""
    if app.asset:
        return app.asset
    if not app.arch_assets:
        return None

    order: list[str] = []
    if abis:
        order.append(abis[0])
        if _is_64bit(abis):
            order += ["arm64-v8a", "x86_64"]
        else:
            order += ["armeabi-v7a", "x86"]
    else:
        order.append("universal")
    order.append("universal")

    for key in order:
        if key in app.arch_assets:
            return app.arch_assets[key]
    # Last resort: any asset whose name mentions one of the device ABIs.
    for name in app.arch_assets.values():
        if any(a in name for a in abis):
            return name
    return next(iter(app.arch_assets.values()), None)


def resolve_url(app: AppItem, abis: list[str]) -> tuple[str, str]:
    """Return (url, asset_name) for an app, using the GitHub API when needed."""
    if app.kind == "url":
        if not app.url:
            raise DownloadError(f"{app.title}: no URL configured")
        return app.url, app.url.rsplit("/", 1)[-1]

    if app.kind == "github" and app.repo and app.version:
        name = pick_asset(app, abis)
        if not name:
            raise DownloadError(f"{app.title}: no downloadable build for {abis}")
        url = (
            f"https://github.com/{app.repo}/releases/download/"
            f"{app.version}/{name}"
        )
        return url, name

    raise DownloadError(f"{app.title}: incomplete source definition")


def download(
    url: str,
    dest: Path,
    *,
    progress: ProgressFn = None,
    timeout: int = 900,
) -> Path:
    """Stream a URL to `dest`. Resumes nothing; overwrites atomically."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with _request(url, timeout=timeout) as resp, open(tmp, "wb") as fh:
            total = int(resp.headers.get("Content-Length") or 0)
            read = 0
            while True:
                chunk = resp.read(262_144)
                if not chunk:
                    break
                fh.write(chunk)
                read += len(chunk)
                if progress:
                    progress(read, total)
        os.replace(tmp, dest)
    except urllib.error.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"Network error for {url}: {exc.reason}") from exc
    return dest


def fetch_apk(
    app: AppItem,
    abis: list[str],
    cache_dir: Path,
    *,
    progress: ProgressFn = None,
    force: bool = False,
) -> Path:
    """Download (or reuse a cached copy of) the APK for this app."""
    url, name = resolve_url(app, abis)
    dest = cache_dir / f"{app.key}-{name}"
    if dest.is_file() and dest.stat().st_size > 0 and not force:
        return dest
    return download(url, dest, progress=progress)


def human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024
    return f"{num:.1f} GB"
