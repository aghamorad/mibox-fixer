"""MoBox Phone-Side & Browser Web App Server.

Serves the mobile-first MoBox web interface on your home Wi-Fi (default port 8765)
so any iPhone, Android phone, iPad, or browser on the couch can:
  - Auto-discover the Mi Box / Android TV box and inspect its exact model,
    firmware, 32-bit/64-bit CPU architecture, HDMI-CEC sleep health, and apps
  - Run the 1-tap Simple (75-Year-Old Mode) All-in-One Setup
  - Use the Advanced (35-Year-Old Mode) per-app installer, debloater, and tweaks
  - Drive the TV from the couch with a built-in Phone D-Pad Remote, 1-tap App
    Launcher, 4K Space & Nature Slideshow trigger, and Bluetooth Mouse pairing
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from . import __version__, catalog
from .adb import Adb, AdbError
from .discover import FirmwareReport, discover_miboxes, inspect_firmware
from .downloader import pick_asset, resolve_url
from .tasks import Fixer, Plan
from .updater import check_for_updates, get_local_commit

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
ICON_PATH = (
    REPO_ROOT / "MoBoxApp" / "icon-preview.png"
    if (REPO_ROOT / "MoBoxApp" / "icon-preview.png").is_file()
    else REPO_ROOT / "MoBoxIcon.png"
)

REMOTE_KEYCODES: dict[str, int] = {
    "UP": 19,
    "DOWN": 20,
    "LEFT": 21,
    "RIGHT": 22,
    "OK": 23,
    "BACK": 4,
    "HOME": 3,
    "MENU": 82,
    "VOL_UP": 24,
    "VOL_DOWN": 25,
    "MUTE": 164,
    "PLAY_PAUSE": 85,
}


def get_lan_ip() -> str:
    """Return this computer's primary LAN IPv4 address for phone QR/links."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.168.0.1", 80))
        ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        sock.close()
    return "127.0.0.1"


class MoBoxWebState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.adb: Optional[Adb] = None
        self.fw: Optional[FirmwareReport] = None
        self.busy: bool = False
        self.step_idx: int = 0
        self.step_total: int = 5
        self.step_label: str = "Ready"
        self.logs: list[str] = []
        self.last_refresh: float = 0.0
        self.cache_dir = Path(
            os.environ.get("MIBOX_FIXER_CACHE")
            or Path.home() / ".cache" / "mibox-fixer"
        )

    def log(self, line: str) -> None:
        with self.lock:
            self.logs.append(line)
            if len(self.logs) > 250:
                self.logs = self.logs[-250:]

    def ensure_connected(self, force_scan: bool = False) -> tuple[Optional[Adb], Optional[FirmwareReport]]:
        if self.adb and self.fw and not force_scan and (time.time() - self.last_refresh < 12):
            return self.adb, self.fw
        try:
            adb = self.adb or Adb()
            if not adb.serial or force_scan:
                ready = [
                    d for d in Adb.devices(adb.binary, server_port=adb.server_port)
                    if d.is_ready and "Quest" not in d.model
                ]
                if ready:
                    adb.serial = ready[0].serial
                else:
                    boxes = discover_miboxes()
                    connected = False
                    for b in boxes:
                        if b.has_adb and adb.connect(b.ip):
                            connected = True
                            break
                    if not connected:
                        from .discover import _arp_candidates
                        for ip in _arp_candidates():
                            if adb.connect(ip, timeout=4):
                                break
            if adb.serial:
                fw = inspect_firmware(adb)
                with self.lock:
                    self.adb = adb
                    self.fw = fw
                    self.last_refresh = time.time()
                return adb, fw
        except Exception as exc:  # noqa: BLE001
            self.log(f"Connection check: {exc}")
        return self.adb, self.fw

    def to_dict(self, force_scan: bool = False) -> dict[str, Any]:
        adb, fw = self.ensure_connected(force_scan=force_scan)
        abis = fw.abis if fw else ["armeabi-v7a"]
        apps_payload = []
        for a in catalog.APPS:
            try:
                url, asset_name = resolve_url(a, abis)
            except Exception:  # noqa: BLE001
                url, asset_name = "", a.asset or ""
            apps_payload.append({
                "key": a.key,
                "title": a.title,
                "package": a.package,
                "detail": a.detail,
                "version": a.version,
                "asset": asset_name,
                "download_url": url,
                "installed": bool(fw and fw.installed_apps.get(a.key)),
                "simple_default": a.key in Fixer.MOBOX_SIMPLE_APPS,
                "can_launch": bool(a.component),
            })

        disabled_set: set[str] = set()
        if adb and adb.serial:
            try:
                out = adb.shell("pm list packages -d", timeout=10)
                disabled_set = {
                    ln.replace("package:", "").strip()
                    for ln in out.splitlines()
                    if ln.startswith("package:")
                }
            except Exception:  # noqa: BLE001
                pass

        bloat_payload = [
            {
                "package": b.package,
                "title": b.title,
                "category": b.category,
                "detail": b.detail,
                "default": b.default,
                "danger": b.danger,
                "disabled": b.package in disabled_set,
            }
            for b in catalog.BLOAT
        ]

        return {
            "version": __version__,
            "commit": get_local_commit()[:7] or "local",
            "lan_ip": get_lan_ip(),
            "connected": bool(adb and adb.serial and fw),
            "serial": adb.serial if adb else None,
            "busy": self.busy,
            "progress": {
                "step": self.step_idx,
                "total": self.step_total,
                "label": self.step_label,
            },
            "logs": self.logs[-60:],
            "firmware": {
                "model": fw.model,
                "product": fw.product,
                "android_release": fw.android_release,
                "sdk": fw.sdk,
                "build_id": fw.build_id,
                "security_patch": fw.security_patch,
                "kernel": fw.kernel,
                "arch_label": fw.arch_label,
                "abis": fw.abis,
                "free_storage_mb": fw.free_storage_mb,
                "free_ram_mb": fw.free_ram_mb,
                "hdmi_cec_enabled": fw.hdmi_cec_enabled,
                "hdmi_auto_device_off": fw.hdmi_auto_device_off,
                "sleep_timeout_ms": fw.sleep_timeout_ms,
                "tv_wake_ready": fw.tv_wake_ready,
                "hid_drivers": fw.hid_drivers,
                "has_magicmouse_driver": fw.has_magicmouse_driver,
                "matvt_active": fw.matvt_active,
                "aerialviews_active": fw.aerialviews_active,
                "plain_summary": fw.plain_summary(),
            } if fw else None,
            "apps": apps_payload,
            "bloat": bloat_payload,
        }


STATE = MoBoxWebState()


class MoBoxHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return  # Keep terminal quiet

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        elif parsed.path == "/icon.png":
            self._send_file(ICON_PATH, "image/png")
        elif parsed.path == "/api/status":
            force = "scan=1" in (parsed.query or "")
            self._send_json(STATE.to_dict(force_scan=force))
        elif parsed.path == "/api/progress":
            self._send_json({
                "busy": STATE.busy,
                "step": STATE.step_idx,
                "total": STATE.step_total,
                "label": STATE.step_label,
                "logs": STATE.logs[-60:],
            })
        elif parsed.path == "/api/update-check":
            st = check_for_updates()
            self._send_json({
                "local": st.short_local,
                "remote": st.short_remote,
                "message": st.remote_message,
                "update_available": st.update_available,
            })
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        body: dict[str, Any] = {}
        if length > 0:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:  # noqa: BLE001
                body = {}

        if parsed.path == "/api/connect":
            host = str(body.get("host", "")).strip()
            if not host:
                self._send_json({"ok": False, "error": "Please enter an IP address."}, 400)
                return
            try:
                adb = Adb()
                if adb.connect(host):
                    fw = inspect_firmware(adb)
                    with STATE.lock:
                        STATE.adb = adb
                        STATE.fw = fw
                        STATE.last_refresh = time.time()
                    STATE.log(f"Connected to {fw.model} at {adb.serial}")
                    self._send_json({"ok": True, "state": STATE.to_dict()})
                else:
                    self._send_json({"ok": False, "error": f"Could not connect to {host} on port 5555."})
            except Exception as exc:  # noqa: BLE001
                self._send_json({"ok": False, "error": str(exc)})
            return

        if parsed.path == "/api/simple-setup":
            if STATE.busy:
                self._send_json({"ok": False, "error": "Setup is already running."})
                return
            adb, _ = STATE.ensure_connected()
            if not adb or not adb.serial:
                self._send_json({"ok": False, "error": "No Mi Box connected yet."})
                return

            STATE.busy = True
            STATE.step_idx = 0
            STATE.step_total = 5
            STATE.step_label = "Starting MoBox All-in-One Setup..."

            def worker() -> None:
                try:
                    fixer = Fixer(adb, STATE.cache_dir, report=STATE.log)

                    def prog(i: int, t: int, lbl: str) -> None:
                        STATE.step_idx = i
                        STATE.step_total = t
                        STATE.step_label = lbl

                    results = fixer.do_mobox_simple_setup(progress=prog)
                    STATE.fw = inspect_firmware(adb)
                    STATE.last_refresh = time.time()
                    good = sum(1 for r in results if r.ok)
                    STATE.step_label = f"All done! ({good}/{len(results)} steps completed)"
                except Exception as exc:  # noqa: BLE001
                    STATE.log(f"Error: {exc}")
                    STATE.step_label = f"Setup paused: {exc}"
                finally:
                    STATE.busy = False

            threading.Thread(target=worker, daemon=True).start()
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/action":
            adb, _ = STATE.ensure_connected()
            if not adb or not adb.serial:
                self._send_json({"ok": False, "error": "Connect to your Mi Box first."})
                return
            kind = str(body.get("kind", ""))

            if kind == "key":
                key_name = str(body.get("key", "")).upper()
                code = REMOTE_KEYCODES.get(key_name)
                if not code:
                    self._send_json({"ok": False, "error": f"Unknown key {key_name}"})
                    return
                ok = adb.shell_ok(f"input keyevent {code}")
                self._send_json({"ok": ok})
                return

            if kind == "slideshow":
                adb.enable_aerial_views_screensaver()
                ok = adb.start_screensaver_now()
                STATE.log("Started 4K Space & Nature slideshow on TV.")
                self._send_json({"ok": ok, "message": "4K Space & Nature slideshow started on TV!"})
                return

            if kind == "bluetooth":
                ok = adb.open_bluetooth_settings()
                STATE.log("Opened Bluetooth pairing on TV.")
                self._send_json({"ok": ok, "message": "Bluetooth pairing opened on your TV screen."})
                return

            if kind == "tv_wake_fix":
                fixer = Fixer(adb, STATE.cache_dir, report=STATE.log)
                fixer.do_tune(Plan(tune_animations=True, stay_awake=True, clear_recommendations=False, set_home=False))
                STATE.fw = inspect_firmware(adb)
                self._send_json({"ok": True, "message": "TV-remote auto-wake & Never-Sleep protection applied!"})
                return

            if kind == "enable_matvt":
                ok = adb.enable_matvt_service()
                STATE.fw = inspect_firmware(adb)
                self._send_json({"ok": ok, "message": "MATVT Mouse & Scroll Helper activated!"})
                return

            if kind == "launch_app":
                key = str(body.get("app", ""))
                app = catalog.APPS_BY_KEY.get(key)
                if not app or not app.component:
                    self._send_json({"ok": False, "error": "App cannot be launched directly."})
                    return
                ok = adb.launch(app.component)
                STATE.log(f"Launched {app.title} on TV.")
                self._send_json({"ok": ok, "message": f"Opened {app.title} on your TV."})
                return

            if kind == "set_home":
                key = str(body.get("app", "hume"))
                fixer = Fixer(adb, STATE.cache_dir, report=STATE.log)
                res = fixer.do_set_home(key)
                self._send_json({"ok": res.ok, "message": res.message})
                return

            if kind == "install_app":
                key = str(body.get("app", ""))
                if STATE.busy or key not in catalog.APPS_BY_KEY:
                    self._send_json({"ok": False, "error": "Busy or unknown app."})
                    return
                STATE.busy = True
                app_title = catalog.APPS_BY_KEY[key].title
                STATE.step_label = f"Installing {app_title}..."

                def worker() -> None:
                    try:
                        fixer = Fixer(adb, STATE.cache_dir, report=STATE.log)
                        fixer.do_install([key])
                        if key == "matvt":
                            fixer.do_enable_matvt()
                        elif key == "aerialviews":
                            fixer.do_enable_aerialviews()
                        STATE.fw = inspect_firmware(adb)
                        STATE.step_label = f"Installed {app_title}."
                    finally:
                        STATE.busy = False

                threading.Thread(target=worker, daemon=True).start()
                self._send_json({"ok": True, "message": f"Installing {app_title}..."})
                return

            if kind == "toggle_package":
                pkg = str(body.get("package", ""))
                disable = bool(body.get("disable", True))
                ok, detail = adb.disable(pkg) if disable else adb.enable(pkg)
                STATE.log(f"{'Disabled' if disable else 'Restored'} {pkg}: {detail}")
                self._send_json({"ok": ok, "message": detail})
                return

            if kind == "debloat_safe":
                if STATE.busy:
                    self._send_json({"ok": False, "error": "Busy"})
                    return
                STATE.busy = True
                STATE.step_label = "Disabling safe bloatware..."

                def worker() -> None:
                    try:
                        fixer = Fixer(adb, STATE.cache_dir, report=STATE.log)
                        pkgs = [b.package for b in catalog.BLOAT if b.default and not b.danger]
                        fixer.do_debloat(pkgs)
                        STATE.step_label = "Safe debloat complete."
                    finally:
                        STATE.busy = False

                threading.Thread(target=worker, daemon=True).start()
                self._send_json({"ok": True, "message": "Disabling safe bloatware..."})
                return

        self.send_error(404)


def start_background_server(preferred_port: int = 8765) -> tuple[ThreadingHTTPServer, int]:
    """Start the MoBox Phone Web Server on a daemon thread and return (server, port)."""
    for port in range(preferred_port, preferred_port + 15):
        try:
            httpd = ThreadingHTTPServer(("0.0.0.0", port), MoBoxHTTPHandler)
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            return httpd, port
        except OSError:
            continue
    raise RuntimeError("Could not bind a local port for the MoBox Phone Web App.")


def main() -> int:
    parser = argparse.ArgumentParser(description="MoBox Phone & Browser Web App Server")
    parser.add_argument("--port", type=int, default=8765, help="TCP port (default 8765)")
    args = parser.parse_args()
    httpd, port = start_background_server(args.port)
    lan = get_lan_ip()
    print(f"MoBox Phone & Web App running at:")
    print(f"  • On this Mac : http://127.0.0.1:{port}")
    print(f"  • On your Phone (same Wi-Fi): http://{lan}:{port}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
