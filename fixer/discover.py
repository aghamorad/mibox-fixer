"""Auto-discovery and firmware/health inspection for Mi Box / Android TV devices."""

from __future__ import annotations

import concurrent.futures
import os
import re
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from . import catalog
from .adb import Adb, AdbError


@dataclass(frozen=True)
class DiscoveredBox:
    ip: str
    port: int = 5555
    has_adb: bool = True
    has_remote_v2: bool = False
    label: str = ""

    @property
    def serial(self) -> str:
        return f"{self.ip}:{self.port}"

    def __str__(self) -> str:
        tag = self.label or "Mi Box / Android TV"
        return f"{tag} ({self.ip})"


@dataclass
class FirmwareReport:
    model: str = "Unknown"
    product: str = ""
    android_release: str = "?"
    sdk: str = "?"
    build_id: str = ""
    security_patch: str = ""
    kernel: str = ""
    abis: list[str] = field(default_factory=list)
    free_storage_mb: Optional[int] = None
    free_ram_mb: Optional[int] = None
    hdmi_cec_enabled: bool = False
    hdmi_auto_device_off: Optional[bool] = None
    sleep_timeout_ms: Optional[int] = None
    stay_awake_mode: Optional[int] = None
    hid_drivers: list[str] = field(default_factory=list)
    matvt_active: bool = False
    aerialviews_active: bool = False
    installed_apps: dict[str, bool] = field(default_factory=dict)

    @property
    def has_magicmouse_driver(self) -> bool:
        return any("magicmouse" in d.lower() for d in self.hid_drivers)

    @property
    def tv_wake_ready(self) -> bool:
        return (
            self.hdmi_cec_enabled
            and self.hdmi_auto_device_off is False
            and (self.sleep_timeout_ms is not None and self.sleep_timeout_ms < 0)
        )

    @property
    def arch_label(self) -> str:
        if "arm64-v8a" in self.abis:
            return "64-bit (arm64)"
        if "armeabi-v7a" in self.abis:
            return "32-bit (armeabi-v7a)"
        return ", ".join(self.abis) or "unknown"

    def plain_summary(self) -> str:
        """Senior-friendly, jargon-free 3-line summary."""
        lines = [
            f"Box: {self.model}  •  Android {self.android_release} ({self.arch_label})",
        ]
        if self.free_storage_mb is not None:
            lines.append(
                f"Firmware: {self.build_id or 'stock'}  •  Free space: {self.free_storage_mb} MB"
            )
        wake_txt = (
            "TV remote auto-wake: Ready"
            if self.tv_wake_ready
            else "TV remote auto-wake: Needs one-click fix"
        )
        mouse_txt = (
            "Mouse helper (MATVT): Active"
            if self.matvt_active
            else "Mouse helper (MATVT): Not set up yet"
        )
        aerial_txt = (
            "4K Slideshow: Active"
            if self.aerialviews_active
            else "4K Slideshow: Not set up yet"
        )
        lines.append(f"{wake_txt}  •  {mouse_txt}  •  {aerial_txt}")
        return "\n".join(lines)


def _arp_candidates() -> list[str]:
    """Read private IPv4 addresses already seen on the local network."""
    ips: list[str] = []
    arp_bin = "/usr/sbin/arp" if os.path.exists("/usr/sbin/arp") else "arp"
    try:
        proc = subprocess.run(
            [arp_bin, "-an"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        for match in re.finditer(r"\((\d+\.\d+\.\d+\.\d+)\)", proc.stdout):
            ip = match.group(1)
            if ip.endswith(".255") or ip.endswith(".1") or ip.startswith("224."):
                continue
            if ip.startswith(("192.168.", "10.", "172.")):
                ips.append(ip)
    except (OSError, subprocess.SubprocessError):
        pass
    return list(dict.fromkeys(ips))


def _probe_port(ip: str, port: int, timeout: float = 0.35) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def discover_miboxes(extra_ips: Optional[list[str]] = None) -> list[DiscoveredBox]:
    """Fast parallel LAN probe for Android TV / Mi Box devices (ADB 5555 / Remote 6466)."""
    candidates = _arp_candidates()
    if extra_ips:
        candidates = list(dict.fromkeys([*extra_ips, *candidates]))

    found: list[DiscoveredBox] = []

    def check(ip: str) -> Optional[DiscoveredBox]:
        has_adb = _probe_port(ip, 5555)
        has_remote = _probe_port(ip, 6466)
        if has_adb or has_remote:
            return DiscoveredBox(
                ip=ip,
                port=5555,
                has_adb=has_adb,
                has_remote_v2=has_remote,
                label="Mi Box / Android TV" if has_remote else "Android device",
            )
        return None

    if not candidates:
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(candidates))) as pool:
        for res in pool.map(check, candidates):
            if res is not None:
                found.append(res)

    # Prefer devices that expose both ADB and Android TV Remote v2
    found.sort(key=lambda b: (not (b.has_adb and b.has_remote_v2), not b.has_adb, b.ip))
    return found


def _parse_int(value: str) -> Optional[int]:
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return None


def inspect_firmware(adb: Adb) -> FirmwareReport:
    """Collect a comprehensive, read-only firmware and health report from the box."""
    script = (
        "echo MODEL=$(getprop ro.product.model);"
        "echo PRODUCT=$(getprop ro.product.name);"
        "echo RELEASE=$(getprop ro.build.version.release);"
        "echo SDK=$(getprop ro.build.version.sdk);"
        "echo BUILD=$(getprop ro.build.display.id);"
        "echo PATCH=$(getprop ro.build.version.security_patch);"
        "echo KERNEL=$(uname -r);"
        "echo ABIS=$(getprop ro.product.cpu.abilist);"
        "echo CEC=$(settings get global hdmi_control_enabled);"
        "echo AUTOOFF=$(settings get global hdmi_control_auto_device_off_enabled);"
        "echo SLEEP=$(settings get secure sleep_timeout);"
        "echo AWAKE=$(settings get global stay_on_while_plugged_in);"
        "echo ACC=$(settings get secure enabled_accessibility_services);"
        "echo ACC_ON=$(settings get secure accessibility_enabled);"
        "echo DREAM=$(settings get secure screensaver_components);"
        "echo DREAM_ON=$(settings get secure screensaver_enabled);"
        "echo HID=$(ls /sys/bus/hid/drivers 2>/dev/null | tr '\\n' ',');"
        "echo DF=$(df -k /data 2>/dev/null | tail -n 1);"
    )
    raw = adb.shell(script, timeout=15)
    kv: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()

    free_storage_mb: Optional[int] = None
    df_parts = kv.get("DF", "").split()
    if len(df_parts) >= 4:
        avail_kb = _parse_int(df_parts[3])
        if avail_kb is not None:
            free_storage_mb = avail_kb // 1024

    mem_kb = adb.mem_available_kb()
    hid_drivers = [d for d in kv.get("HID", "").split(",") if d]
    abis = [a for a in kv.get("ABIS", "").split(",") if a]

    auto_off_raw = kv.get("AUTOOFF", "")
    auto_off: Optional[bool] = None
    if auto_off_raw in ("0", "1"):
        auto_off = auto_off_raw == "1"

    matvt_active = (
        kv.get("ACC_ON") == "1"
        and "io.github.virresh.matvt" in kv.get("ACC", "")
    )
    aerialviews_active = (
        kv.get("DREAM_ON") == "1"
        and "com.neilturner.aerialviews" in kv.get("DREAM", "")
    )

    installed: dict[str, bool] = {}
    try:
        pkgs_out = adb.shell("pm list packages", timeout=15)
        present = {
            line.replace("package:", "").strip()
            for line in pkgs_out.splitlines()
            if line.startswith("package:")
        }
        for app in catalog.APPS:
            installed[app.key] = app.package in present
    except AdbError:
        pass

    return FirmwareReport(
        model=kv.get("MODEL") or "Unknown",
        product=kv.get("PRODUCT") or "",
        android_release=kv.get("RELEASE") or "?",
        sdk=kv.get("SDK") or "?",
        build_id=kv.get("BUILD") or "",
        security_patch=kv.get("PATCH") or "",
        kernel=kv.get("KERNEL") or "",
        abis=abis,
        free_storage_mb=free_storage_mb,
        free_ram_mb=(mem_kb // 1024) if mem_kb else None,
        hdmi_cec_enabled=kv.get("CEC") == "1",
        hdmi_auto_device_off=auto_off,
        sleep_timeout_ms=_parse_int(kv.get("SLEEP", "")),
        stay_awake_mode=_parse_int(kv.get("AWAKE", "")),
        hid_drivers=hid_drivers,
        matvt_active=matvt_active,
        aerialviews_active=aerialviews_active,
        installed_apps=installed,
    )
