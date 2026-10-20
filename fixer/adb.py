"""Thin, dependency-free ADB wrapper.

We deliberately shell out to the `adb` binary instead of using a Python
binding: it is what actually ships with the Android platform tools and it
behaves identically on macOS, Linux and Windows.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


class AdbError(RuntimeError):
    pass


def _default_search_paths() -> list[Path]:
    here = Path(__file__).resolve().parent.parent
    candidates: list[Path] = [
        here / "vendor" / "platform-tools",
        Path.home() / "bin" / "scrcpy",
        Path("/private/tmp/platform-tools"),
        Path("/usr/local/bin"),
        Path("/opt/homebrew/bin"),
    ]
    env = os.environ.get("ADB_PATH")
    if env:
        candidates.insert(0, Path(env).expanduser())
    return candidates


def find_adb() -> Optional[str]:
    """Locate an adb binary: explicit env var, bundled copy, then PATH."""
    env = os.environ.get("ADB_PATH")
    if env and Path(env).expanduser().is_file():
        return str(Path(env).expanduser())
    for base in _default_search_paths():
        exe = base / ("adb.exe" if os.name == "nt" else "adb")
        if exe.is_file() and os.access(exe, os.X_OK):
            return str(exe)
    return shutil.which("adb")


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    model: str = ""
    product: str = ""

    @property
    def is_ready(self) -> bool:
        return self.state == "device"

    @property
    def is_network(self) -> bool:
        return ":" in self.serial and not self.serial.startswith("emulator-")

    def __str__(self) -> str:
        label = self.model or self.product or "Android device"
        kind = "Wi-Fi" if self.is_network else "USB"
        return f"{label} [{kind} {self.serial}]"


class Adb:
    """A connected adb client, optionally pinned to one device serial."""

    def __init__(self, binary: Optional[str] = None, serial: Optional[str] = None):
        self.binary = binary or find_adb()
        self.serial = serial
        if not self.binary:
            raise AdbError(
                "Could not find the 'adb' binary. Install Android platform-tools, "
                "or set the ADB_PATH environment variable to the adb executable."
            )

    # ------------------------------------------------------------------ low level

    def _base(self) -> list[str]:
        cmd = [self.binary]
        if self.serial:
            cmd += ["-s", self.serial]
        return cmd

    def run(
        self,
        args: Iterable[str],
        *,
        timeout: int = 60,
        check: bool = False,
        binary_out: bool = False,
    ):
        args = [str(a) for a in args]
        cmd = self._base() + args
        proc = self._run_with_recovery(cmd, args, timeout)
        if binary_out:
            out = proc.stdout
        else:
            out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace").strip()
        if check and proc.returncode != 0:
            raise AdbError(err or f"adb {' '.join(args)} failed")
        return proc.returncode, out, err

    # Wi-Fi adb drops out for a second or two fairly often on these boxes.
    # When that happens we transparently reconnect and replay the command,
    # so a one-second blip does not turn into a failed install.
    _TRANSIENT = (
        "device offline",
        "device not found",
        "no devices/emulators found",
        "connection closed",
        "connection reset",
        "cannot connect to daemon",
        "adb: closed",
    )

    def _run_with_recovery(self, cmd: list[str], args: list[str], timeout: int):
        attempts = 4 if not self._is_session_command(args) else 1
        last = None
        for attempt in range(attempts):
            last = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            blob = (last.stdout + last.stderr).decode("utf-8", "replace").lower()
            if not any(t in blob for t in self._TRANSIENT):
                return last
            if attempt == attempts - 1:
                break
            self._reconnect()
        return last

    @staticmethod
    def _is_session_command(args: list[str]) -> bool:
        """Commands that manage the connection itself must not be retried."""
        return bool(args) and args[0] in {
            "connect", "disconnect", "kill-server", "start-server", "devices",
        }

    def _reconnect(self) -> None:
        if self.serial and ":" in self.serial:
            host = self.serial
            subprocess.run(
                [self.binary, "disconnect", host],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
            )
            subprocess.run(
                [self.binary, "connect", host],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
            )
        time.sleep(1.0)

    def shell(self, command: str, *, timeout: int = 60, check: bool = False) -> str:
        rc, out, err = self.run(["shell", command], timeout=timeout)
        if check and rc != 0 and not out.strip():
            raise AdbError(err or f"shell failed: {command}")
        return out

    def shell_ok(self, command: str, *, timeout: int = 60) -> bool:
        """True when the command's own output/exit status indicates success."""
        try:
            out = self.shell(command, timeout=timeout)
        except (AdbError, subprocess.TimeoutExpired):
            return False
        low = out.lower()
        return "exception" not in low and "error" not in low and "failure" not in low

    # ------------------------------------------------------------------ discovery

    @classmethod
    def devices(cls, binary: Optional[str] = None) -> list[Device]:
        client = cls(binary=binary)
        rc, out, _ = client.run(["devices", "-l"], timeout=30)
        found: list[Device] = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            kv = dict(p.split(":", 1) for p in parts[2:] if ":" in p)
            found.append(
                Device(
                    serial=serial,
                    state=state,
                    model=kv.get("model", ""),
                    product=kv.get("product", ""),
                )
            )
        return found

    def connect(self, host: str, port: int = 5555, *, timeout: int = 25) -> bool:
        """Connect over Wi-Fi. `host` may already include a port."""
        target = host if ":" in host else f"{host}:{port}"
        try:
            self.run(["connect", target], timeout=timeout)
        except (AdbError, subprocess.TimeoutExpired):
            return False
        deadline = time.time() + 6
        while time.time() < deadline:
            for dev in self.devices(self.binary):
                if dev.serial == target and dev.is_ready:
                    self.serial = target
                    return True
            time.sleep(0.5)
        return False

    def disconnect(self, target: Optional[str] = None) -> None:
        self.run(["disconnect"] + ([target] if target else []), timeout=15)

    def start_server(self) -> None:
        self.run(["start-server"], timeout=25)

    def enable_tcpip(self, port: int = 5555) -> bool:
        """Switch a USB-connected device into Wi-Fi adb mode."""
        return self.shell_ok(f"setprop service.adb.tcp.port {port}") and self.shell_ok(
            "stop adbd; start adbd"
        )

    # ------------------------------------------------------------------ device info

    def prop(self, name: str) -> str:
        return self.shell(f"getprop {name}").strip()

    def wlan_ip(self) -> Optional[str]:
        out = self.shell("ip -f inet addr show wlan0 2>/dev/null")
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
        return m.group(1) if m else None

    def info(self) -> dict:
        return {
            "model": self.prop("ro.product.model"),
            "product": self.prop("ro.product.name"),
            "sdk": self.prop("ro.build.version.sdk"),
            "release": self.prop("ro.build.version.release"),
            "abi": self.prop("ro.product.cpu.abi"),
            "build": self.prop("ro.build.version.incremental")
            or self.prop("ro.build.display.id"),
        }

    def abis(self) -> list[str]:
        """All ABIs the device supports, best first."""
        raw = self.prop("ro.product.cpu.abilist") or self.prop("ro.product.cpu.abi")
        return [a.strip() for a in raw.split(",") if a.strip()]

    def mem_available_kb(self) -> Optional[int]:
        out = self.shell("cat /proc/meminfo")
        m = re.search(r"MemAvailable:\s+(\d+)", out)
        return int(m.group(1)) if m else None

    def is_installed(self, package: str) -> bool:
        return package in self.shell(f"pm list packages -u {package}").strip()

    def is_enabled(self, package: str) -> bool:
        out = self.shell(f"dumpsys package {package}")
        m = re.search(r"enabled=(\d+)", out)
        if not m:
            return self.is_installed(package) and package not in self.shell(
                "pm list packages -d"
            )
        return m.group(1) == "0"

    def launcher_activity(self, package: str) -> Optional[str]:
        """Find a MAIN/LAUNCHER component for a package, if it has one."""
        out = self.shell(
            "cmd package query-activities --brief "
            "-a android.intent.action.MAIN -c android.intent.category.LAUNCHER"
        )
        for line in out.splitlines():
            line = line.strip()
            if line.startswith(package + "/"):
                return line
        return None

    # ------------------------------------------------------------------ mutations

    def disable(self, package: str) -> tuple[bool, str]:
        out = self.shell(f"pm disable-user --user 0 {package}").strip()
        ok = "new state: disabled" in out or "disabled-user" in out
        if ok and self.shell(f"pm list packages -d {package}").strip():
            return True, "disabled"
        return False, out or "no-op"

    def enable(self, package: str) -> tuple[bool, str]:
        out = self.shell(f"pm enable --user 0 {package}").strip()
        ok = "new state: enabled" in out
        return ok, out or "no-op"

    def set_home(self, component: str) -> bool:
        return self.shell_ok(f"cmd package set-home-activity --user 0 {component}")

    def launch(self, component: str) -> bool:
        out = self.shell(f"am start -n {component} 2>&1")
        return "Error" not in out and "Exception" not in out

    def put_setting(self, namespace: str, key: str, value) -> bool:
        return self.shell_ok(f"settings put {namespace} {key} {value}")

    def get_setting(self, namespace: str, key: str) -> str:
        return self.shell(f"settings get {namespace} {key}").strip()

    def push(self, local: Path, remote: str) -> bool:
        rc, _, err = self.run(["push", str(local), remote], timeout=300)
        return rc == 0

    def install(self, apk: Path, *, reinstall: bool = True, downgrade: bool = True) -> tuple[bool, str]:
        args = ["install"]
        if reinstall:
            args.append("-r")
        if downgrade:
            args.append("-d")
        args.append(str(apk))
        try:
            rc, out, err = self.run(args, timeout=600)
        except subprocess.TimeoutExpired:
            return False, "timed out"
        text = (out + err).strip()
        return ("Success" in text), text

    def wake(self) -> None:
        self.shell("input keyevent KEYCODE_WAKEUP")

    def go_home(self) -> None:
        self.shell("input keyevent KEYCODE_HOME")


def current_platform_tools_hint() -> str:
    if sys.platform == "darwin":
        return "brew install --cask android-platform-tools"
    if sys.platform.startswith("linux"):
        return "sudo apt install adb"
    return "Download platform-tools from developer.android.com/tools/releases/platform-tools"
