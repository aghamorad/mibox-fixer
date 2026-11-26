"""MoBox (Mi Box Fixer) - Dual-mode Tkinter front-end.

Two first-class modes in one window:
  - Simple Mode (75-Year-Old Friendly): auto-discovers your Mi Box on Wi-Fi,
    checks its firmware and TV-remote wake health, and applies the full safe
    MoBox setup in one click with plain-English guidance.
  - Advanced Mode (35-Year-Old / Power User): full firmware & kernel HID
    inspector, per-package debloat/restore, full app catalog, custom launcher,
    IPTV, wallpaper, and live ADB log.
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from . import __version__, catalog
from .adb import Adb, AdbError, Device, current_platform_tools_hint, find_adb
from .discover import DiscoveredBox, FirmwareReport, discover_miboxes, inspect_firmware
from .tasks import Fixer, Plan
from .updater import UpdateStatus, apply_update, check_for_updates, get_local_commit

APP_TITLE = f"MoBox {__version__} — Easy Mi Box Setup"


class MoBoxApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=14)
        self.grid(row=0, column=0, sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.adb: Optional[Adb] = None
        self.report_data: Optional[FirmwareReport] = None
        self.discovered: list[DiscoveredBox] = []
        self.pkg_vars: dict[str, tk.BooleanVar] = {}
        self.app_vars: dict[str, tk.BooleanVar] = {}
        self.busy = False
        self.mode_var = tk.StringVar(value="simple")
        self.msg_queue: queue.Queue = queue.Queue()
        self.update_status: Optional[UpdateStatus] = None
        self.cache_dir = Path(
            os.environ.get("MIBOX_FIXER_CACHE")
            or Path.home() / ".cache" / "mibox-fixer"
        )

        self._setup_styles()
        self._build_top_bar()
        self._build_mode_containers()
        self._build_footer()

        self.after(100, self._drain)
        self.after(250, self.auto_discover_and_connect)
        self.after(800, self._check_updates_async)

    # ------------------------------------------------------------------ styles

    def _setup_styles(self) -> None:
        style = ttk.Style()
        try:
            if "aqua" in style.theme_names():
                style.theme_use("aqua")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("", 20, "bold"))
        style.configure("Subtitle.TLabel", font=("", 13), foreground="#555555")
        style.configure("CardTitle.TLabel", font=("", 14, "bold"))
        style.configure("CardBody.TLabel", font=("", 13))
        style.configure("Muted.TLabel", font=("", 11), foreground="#666666")
        style.configure("Big.TButton", font=("", 15, "bold"), padding=(18, 12))
        style.configure("Medium.TButton", font=("", 13), padding=(12, 8))
        style.configure("ModeActive.TButton", font=("", 13, "bold"), padding=(14, 8))

    # ------------------------------------------------------------------ top bar

    def _build_top_bar(self) -> None:
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top.columnconfigure(0, weight=1)

        brand = ttk.Frame(top)
        brand.grid(row=0, column=0, sticky="w")
        ttk.Label(brand, text="MoBox", style="Title.TLabel").pack(side="left")
        ttk.Label(
            brand,
            text=f"  v{__version__}  •  Mi Box Setup & Helper",
            style="Subtitle.TLabel",
        ).pack(side="left", pady=(4, 0))

        switcher = ttk.Frame(top)
        switcher.grid(row=0, column=1, sticky="e")
        self.btn_simple = ttk.Button(
            switcher,
            text="Simple (75-Year-Old Mode)",
            command=lambda: self._switch_mode("simple"),
            style="ModeActive.TButton",
        )
        self.btn_simple.pack(side="left", padx=(0, 6))
        self.btn_advanced = ttk.Button(
            switcher,
            text="Advanced (35-Year-Old Mode)",
            command=lambda: self._switch_mode("advanced"),
            style="Medium.TButton",
        )
        self.btn_advanced.pack(side="left")

    def _switch_mode(self, mode: str) -> None:
        self.mode_var.set(mode)
        if mode == "simple":
            self.advanced_frame.grid_remove()
            self.simple_frame.grid()
            self.btn_simple.configure(style="ModeActive.TButton")
            self.btn_advanced.configure(style="Medium.TButton")
        else:
            self.simple_frame.grid_remove()
            self.advanced_frame.grid()
            self.btn_simple.configure(style="Medium.TButton")
            self.btn_advanced.configure(style="ModeActive.TButton")

    # ------------------------------------------------------------------ containers

    def _build_mode_containers(self) -> None:
        self.simple_frame = ttk.Frame(self)
        self.simple_frame.grid(row=1, column=0, sticky="nsew")
        self.simple_frame.columnconfigure(0, weight=1)

        self.advanced_frame = ttk.Frame(self)
        self.advanced_frame.grid(row=1, column=0, sticky="nsew")
        self.advanced_frame.columnconfigure(0, weight=1)
        self.advanced_frame.rowconfigure(2, weight=1)
        self.advanced_frame.grid_remove()

        self._build_simple_ui()
        self._build_advanced_ui()

    # ------------------------------------------------------------------ SIMPLE MODE (75-Year-Old)

    def _build_simple_ui(self) -> None:
        f = self.simple_frame

        # Step 1 card: Connection & Firmware status
        card1 = ttk.LabelFrame(f, text="  1. Your Mi Box  ", padding=16)
        card1.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        card1.columnconfigure(0, weight=1)

        self.simple_status_title = tk.StringVar(
            value="Looking for your Mi Box on home Wi-Fi..."
        )
        ttk.Label(
            card1,
            textvariable=self.simple_status_title,
            style="CardTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")

        self.simple_status_body = tk.StringVar(
            value="Make sure your TV and Mi Box are turned on and on the same Wi-Fi."
        )
        ttk.Label(
            card1,
            textvariable=self.simple_status_body,
            style="CardBody.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 12))

        c1_btns = ttk.Frame(card1)
        c1_btns.grid(row=2, column=0, sticky="w")
        ttk.Button(
            c1_btns,
            text="Find My Mi Box",
            style="Medium.TButton",
            command=self.auto_discover_and_connect,
        ).pack(side="left", padx=(0, 10))
        ttk.Button(
            c1_btns,
            text="Enter IP Address...",
            style="Medium.TButton",
            command=self.connect_dialog,
        ).pack(side="left")

        # Step 2 card: One-Click Setup
        card2 = ttk.LabelFrame(f, text="  2. Make My Mi Box Ready  ", padding=16)
        card2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        card2.columnconfigure(0, weight=1)

        ttk.Label(
            card2,
            text=(
                "One safe click sets up everything on your Mi Box:\n"
                "  • Clean Apple TV-style home screen (Hume), Live TV, Ad-free YouTube, Browser & SlamVision\n"
                "  • 4K Outer Space & Nature Slideshow (Aerial Views) after 5 minutes of idle time\n"
                "  • Fixes TV-remote auto-wake so turning on your TV always finds the Mi Box awake\n"
                "  • Turns on the Mouse & Scroll Helper (MATVT) — and keeps all your existing apps safe"
            ),
            style="CardBody.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))

        self.btn_simple_go = ttk.Button(
            card2,
            text="Set Up My Mi Box (All-in-One)",
            style="Big.TButton",
            command=self.run_simple_setup,
        )
        self.btn_simple_go.grid(row=1, column=0, sticky="w")

        self.simple_progress = ttk.Progressbar(card2, mode="determinate", maximum=5)
        self.simple_progress.grid(row=2, column=0, sticky="ew", pady=(14, 6))

        self.simple_progress_text = tk.StringVar(value="Ready whenever you are.")
        ttk.Label(
            card2,
            textvariable=self.simple_progress_text,
            style="Subtitle.TLabel",
            wraplength=760,
        ).grid(row=3, column=0, sticky="w")

        # Step 3 card: Magic Mouse & 4K Space/Nature Slideshow
        card3 = ttk.LabelFrame(
            f, text="  3. Apple Magic Mouse & 4K Space/Nature Slideshow  ", padding=14
        )
        card3.grid(row=2, column=0, sticky="ew")
        card3.columnconfigure(0, weight=1)

        ttk.Label(
            card3,
            text=(
                "• Pair Apple Magic Mouse: flip the mouse off and back on, then click 'Open Bluetooth Pairing on TV'.\n"
                "• 4K Space & Nature Slideshow: starts automatically after 5 minutes idle, or click below to preview it now."
            ),
            style="CardBody.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        c3_btns = ttk.Frame(card3)
        c3_btns.grid(row=1, column=0, sticky="w")
        ttk.Button(
            c3_btns,
            text="Open Bluetooth Pairing on TV",
            style="Medium.TButton",
            command=self.open_bluetooth_on_tv,
        ).pack(side="left", padx=(0, 10))
        ttk.Button(
            c3_btns,
            text="Start 4K Space & Nature Slideshow Now",
            style="Medium.TButton",
            command=self.start_slideshow_on_tv,
        ).pack(side="left")

    # ------------------------------------------------------------------ ADVANCED MODE (35-Year-Old)

    def _build_advanced_ui(self) -> None:
        f = self.advanced_frame

        # Device bar
        bar = ttk.Frame(f)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ttk.Label(bar, text="Device:").grid(row=0, column=0, padx=(0, 6))
        self.device_var = tk.StringVar(value="not connected")
        self.device_combo = ttk.Combobox(
            bar, textvariable=self.device_var, state="readonly", width=48
        )
        self.device_combo.grid(row=0, column=1, sticky="ew")
        ttk.Button(bar, text="Auto-Find", command=self.auto_discover_and_connect).grid(
            row=0, column=2, padx=4
        )
        ttk.Button(bar, text="Connect Wi-Fi...", command=self.connect_dialog).grid(
            row=0, column=3, padx=4
        )

        self.summary_var = tk.StringVar(value="Click Auto-Find to scan Wi-Fi for your Mi Box.")
        ttk.Label(f, textvariable=self.summary_var, style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(6, 8)
        )

        # Notebook tabs
        nb = ttk.Notebook(f)
        nb.grid(row=2, column=0, sticky="nsew")

        self.tab_fw = ttk.Frame(nb, padding=10)
        self.tab_install = ttk.Frame(nb, padding=8)
        self.tab_remove = ttk.Frame(nb, padding=8)
        self.tab_tune = ttk.Frame(nb, padding=10)
        nb.add(self.tab_fw, text="Firmware & Health")
        nb.add(self.tab_install, text="Apps")
        nb.add(self.tab_remove, text="Debloat")
        nb.add(self.tab_tune, text="Tweaks & Remote")

        self._build_firmware_tab()
        self._build_install_tab()
        self._build_remove_tab()
        self._build_tune_tab()

        # Action bar + Log
        act = ttk.Frame(f)
        act.grid(row=3, column=0, sticky="ew", pady=(8, 4))
        self.adv_go_btn = ttk.Button(
            act, text="Apply Selected Changes", command=self.apply_advanced
        )
        self.adv_go_btn.pack(side="left")
        ttk.Button(
            act, text="Run Simple All-in-One", command=self.run_simple_setup
        ).pack(side="left", padx=8)
        ttk.Button(
            act, text="Open Bluetooth on TV", command=self.open_bluetooth_on_tv
        ).pack(side="left")
        ttk.Button(
            act, text="Start 4K Slideshow", command=self.start_slideshow_on_tv
        ).pack(side="left", padx=8)
        ttk.Button(act, text="Clear Log", command=self.clear_log_action if hasattr(self, "clear_log_action") else self._clear_log).pack(side="right")

        self.log = tk.Text(f, height=7, wrap="word", state="disabled")
        self.log.grid(row=4, column=0, sticky="ew")

    def _scrolled(self, parent) -> ttk.Frame:
        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return inner

    def _build_firmware_tab(self) -> None:
        self.fw_text = tk.Text(self.tab_fw, height=14, wrap="word", state="disabled")
        self.fw_text.pack(fill="both", expand=True)
        self._set_fw_text("Connect a Mi Box to inspect firmware, kernel HID drivers, and HDMI-CEC health.")

    def _build_install_tab(self) -> None:
        ttk.Label(
            self.tab_install,
            text="Downloaded directly from each project's GitHub release. 32-bit vs 64-bit is chosen automatically.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(0, 6))

        body = self._scrolled(self.tab_install)
        for app in catalog.APPS:
            row = ttk.Frame(body)
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=app.key in Fixer.MOBOX_SIMPLE_APPS)
            self.app_vars[app.key] = var
            ttk.Checkbutton(row, text=app.title, variable=var, width=34).pack(side="left")
            ttk.Label(row, text=app.detail, foreground="#666", wraplength=440).pack(
                side="left", fill="x", expand=True
            )

    def _build_remove_tab(self) -> None:
        ttk.Label(
            self.tab_remove,
            text="Nothing is uninstalled. Packages are disabled (pm disable-user) and can be restored anytime.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w")

        btns = ttk.Frame(self.tab_remove)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Select all safe", command=lambda: self._set_all_bloat(True)).pack(side="left")
        ttk.Button(btns, text="Select none", command=lambda: self._set_all_bloat(False)).pack(side="left", padx=6)
        ttk.Button(btns, text="Restore selected", command=self.restore_selected).pack(side="right")

        body = self._scrolled(self.tab_remove)
        for cat in catalog.CATEGORY_ORDER:
            items = [b for b in catalog.BLOAT if b.category == cat]
            if not items:
                continue
            ttk.Label(body, text=cat, font=("", 11, "bold")).pack(anchor="w", pady=(8, 2))
            for item in items:
                row = ttk.Frame(body)
                row.pack(fill="x", padx=(12, 0), pady=1)
                var = tk.BooleanVar(value=False)
                self.pkg_vars[item.package] = var
                ttk.Checkbutton(row, text=item.title, variable=var, width=32).pack(side="left")
                note = ("\u26a0 " if item.danger else "") + item.detail
                ttk.Label(row, text=note, foreground="#666", wraplength=440).pack(
                    side="left", fill="x", expand=True
                )

    def _build_tune_tab(self) -> None:
        self.var_anim = tk.BooleanVar(value=True)
        self.var_awake = tk.BooleanVar(value=True)
        self.var_matvt = tk.BooleanVar(value=True)
        self.var_home = tk.BooleanVar(value=True)
        self.var_home_choice = tk.StringVar(value="hume")
        self.var_recs = tk.BooleanVar(value=False)
        self.var_iptv = tk.BooleanVar(value=False)
        self.var_playlist = tk.StringVar(value="All channels")
        self.var_wallpaper = tk.StringVar(value="")

        ttk.Checkbutton(
            self.tab_tune, text="Speed up menu animations (0.5x)", variable=self.var_anim
        ).pack(anchor="w", pady=3)
        ttk.Checkbutton(
            self.tab_tune,
            text="TV-remote auto-wake fix (HDMI-CEC ON, Auto-Device-Off OFF, Never Sleep)",
            variable=self.var_awake,
        ).pack(anchor="w", pady=3)
        ttk.Checkbutton(
            self.tab_tune,
            text="Enable MATVT Mouse & Scroll Helper (Overlay + AccessibilityService)",
            variable=self.var_matvt,
        ).pack(anchor="w", pady=3)

        home_row = ttk.Frame(self.tab_tune)
        home_row.pack(fill="x", pady=4)
        ttk.Checkbutton(home_row, text="Set default home screen:", variable=self.var_home).pack(side="left")
        ttk.Combobox(
            home_row,
            textvariable=self.var_home_choice,
            values=["hume", "flauncher", "ltvlauncher"],
            state="readonly",
            width=16,
        ).pack(side="left", padx=8)

        ttk.Checkbutton(
            self.tab_tune, text="Clear stock TV recommendation cache", variable=self.var_recs
        ).pack(anchor="w", pady=3)

        ip_row = ttk.Frame(self.tab_tune)
        ip_row.pack(fill="x", pady=(8, 3))
        ttk.Checkbutton(ip_row, text="Push M3U playlist to /sdcard/Download:", variable=self.var_iptv).pack(side="left")
        ttk.Combobox(
            ip_row,
            textvariable=self.var_playlist,
            values=list(catalog.IPTV_PLAYLISTS.keys()),
            state="readonly",
            width=26,
        ).pack(side="left", padx=8)

        wp_row = ttk.Frame(self.tab_tune)
        wp_row.pack(fill="x", pady=4)
        ttk.Label(wp_row, text="Wallpaper:").pack(side="left")
        ttk.Entry(wp_row, textvariable=self.var_wallpaper, width=42).pack(side="left", padx=6)
        ttk.Button(wp_row, text="Choose...", command=self._pick_wallpaper).pack(side="left")

    # ------------------------------------------------------------------ persistent footer (Rules #1 & #2)

    def _build_footer(self) -> None:
        foot = ttk.Frame(self)
        foot.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        foot.columnconfigure(1, weight=1)

        ttk.Label(foot, text="Made by Morad", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        self.update_var = tk.StringVar(
            value=f"MoBox v{__version__} ({get_local_commit()[:7] or 'local'})  •  Checking for updates..."
        )
        ttk.Label(foot, textvariable=self.update_var, style="Muted.TLabel").grid(
            row=0, column=1, sticky="e", padx=(10, 8)
        )
        self.btn_update = ttk.Button(
            foot, text="Check Updates", command=self.on_update_button
        )
        self.btn_update.grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------------ background queue

    def _post(self, kind: str, payload) -> None:
        self.msg_queue.put((kind, payload))

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                elif kind == "simple_status":
                    title, body = payload
                    self.simple_status_title.set(title)
                    self.simple_status_body.set(body)
                elif kind == "simple_progress":
                    step_idx, total, label = payload
                    self.simple_progress.configure(maximum=total, value=step_idx)
                    self.simple_progress_text.set(f"Step {step_idx} of {total}: {label}")
                elif kind == "connected":
                    self._on_connected(payload)
                elif kind == "update_status":
                    self._on_update_status(payload)
                elif kind == "done":
                    self._set_busy(False)
                    if payload:
                        self.simple_progress_text.set(str(payload))
        except queue.Empty:
            pass
        self.after(100, self._drain)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.btn_simple_go.configure(state=state)
        self.adv_go_btn.configure(state=state)

    def _append_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _set_fw_text(self, text: str) -> None:
        self.fw_text.configure(state="normal")
        self.fw_text.delete("1.0", "end")
        self.fw_text.insert("1.0", text)
        self.fw_text.configure(state="disabled")

    # ------------------------------------------------------------------ discovery & connect

    def auto_discover_and_connect(self) -> None:
        if self.busy:
            return
        if not find_adb():
            self.simple_status_title.set("One quick thing needed on this computer")
            self.simple_status_body.set(current_platform_tools_hint())
            return
        self._set_busy(True)
        self.simple_status_title.set("Looking for your Mi Box on home Wi-Fi...")
        self.simple_status_body.set("Scanning your local network (takes about 2 seconds)...")

        def worker() -> None:
            try:
                adb = Adb()
                # 1. Check already-attached USB/Wi-Fi devices first
                ready = [d for d in Adb.devices(adb.binary) if d.is_ready and "Quest" not in d.model]
                if ready:
                    adb.serial = ready[0].serial
                    fw = inspect_firmware(adb)
                    self._post("connected", (adb, fw, [ready[0].serial]))
                    return

                # 2. Fast LAN discovery for ADB port 5555 / Android TV Remote 6466
                boxes = discover_miboxes()
                self.discovered = boxes
                for box in boxes:
                    if not box.has_adb:
                        continue
                    self._post("log", f"Found Android TV at {box.ip}, connecting...")
                    if adb.connect(box.ip):
                        fw = inspect_firmware(adb)
                        self._post("connected", (adb, fw, [b.serial for b in boxes]))
                        return

                self._post(
                    "simple_status",
                    (
                        "Could not find a Mi Box automatically",
                        "Make sure your TV and Mi Box are turned on and connected to the same Wi-Fi, "
                        "then click 'Find My Mi Box' or 'Enter IP Address...'.",
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                self._post("log", f"Discovery note: {exc}")
                self._post(
                    "simple_status",
                    (
                        "Could not reach the Mi Box yet",
                        "Check that the Mi Box is awake on your Wi-Fi, or click 'Enter IP Address...'.",
                    ),
                )
            finally:
                self._post("done", "")

        threading.Thread(target=worker, daemon=True).start()

    def _on_connected(self, payload) -> None:
        adb, fw, serials = payload
        self.adb = adb
        self.report_data = fw
        self.device_combo.configure(values=serials)
        self.device_var.set(f"{fw.model} ({adb.serial})")
        self.summary_var.set(
            f"{fw.model} • Android {fw.android_release} (SDK {fw.sdk}) • {fw.arch_label} • "
            f"Kernel {fw.kernel} • Free: {fw.free_storage_mb or '?'} MB"
        )
        self.simple_status_title.set(f"\u2713 Connected to your {fw.model} ({adb.serial})")
        self.simple_status_body.set(fw.plain_summary())

        # Populate Advanced Firmware & Health tab
        hid_note = (
            "YES (hid-magicmouse present)"
            if fw.has_magicmouse_driver
            else "NO (only " + (", ".join(fw.hid_drivers) or "generic") + " — pointer+click work; use MATVT for scroll)"
        )
        installed_lines = [
            f"  {'[installed]' if fw.installed_apps.get(k) else '[missing]  '} {catalog.APPS_BY_KEY[k].title}"
            for k in Fixer.MOBOX_SIMPLE_APPS
        ]
        detail = "\n".join([
            f"Model / Product : {fw.model} / {fw.product}",
            f"ADB Address     : {adb.serial}",
            f"Android / SDK   : Android {fw.android_release} (SDK {fw.sdk})",
            f"Firmware Build  : {fw.build_id or 'unknown'} (patch {fw.security_patch or 'unknown'})",
            f"Linux Kernel    : {fw.kernel or 'unknown'}",
            f"CPU Architecture: {fw.arch_label} ({', '.join(fw.abis)})",
            f"Free Storage    : {fw.free_storage_mb} MB   |   Free RAM: {fw.free_ram_mb} MB",
            "",
            "--- TV Remote & Power Health ---",
            f"HDMI-CEC Enabled         : {'YES' if fw.hdmi_cec_enabled else 'NO'}",
            f"TV Auto-Device-Off (bug) : {'OFF (safe!)' if fw.hdmi_auto_device_off is False else 'ON (causes deep sleep!)'}",
            f"Sleep Timeout            : {'Never (-1)' if (fw.sleep_timeout_ms is not None and fw.sleep_timeout_ms < 0) else str(fw.sleep_timeout_ms) + ' ms'}",
            f"Stay Awake Mode          : {fw.stay_awake_mode}",
            "",
            "--- Apple Magic Mouse & 4K Slideshow ---",
            f"Kernel hid-magicmouse    : {hid_note}",
            f"MATVT Mouse/Scroll Helper: {'ACTIVE' if fw.matvt_active else 'Not enabled yet'}",
            f"Aerial Views 4K Slideshow: {'ACTIVE (5-min timeout)' if fw.aerialviews_active else 'Not enabled yet'}",
            "",
            "--- Core MoBox Apps ---",
            *installed_lines,
        ])
        self._set_fw_text(detail)

    def connect_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title("Connect to Mi Box by IP")
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(
            frm,
            text="Enter your Mi Box Wi-Fi IP address (find it in Settings → Network → Wi-Fi):",
            wraplength=360,
        ).pack(anchor="w")
        ip_var = tk.StringVar(value="192.168.0.117")
        entry = ttk.Entry(frm, textvariable=ip_var, width=28, font=("", 13))
        entry.pack(fill="x", pady=10)
        entry.focus_set()

        def go() -> None:
            host = ip_var.get().strip()
            win.destroy()
            if not host:
                return
            self._set_busy(True)
            self.simple_status_title.set(f"Connecting to {host}...")

            def worker() -> None:
                try:
                    adb = Adb()
                    if adb.connect(host):
                        fw = inspect_firmware(adb)
                        self._post("connected", (adb, fw, [adb.serial or host]))
                    else:
                        self._post(
                            "simple_status",
                            (
                                f"Could not reach {host}",
                                "Check the IP address on your TV and approve the 'Allow USB debugging' prompt if it appears.",
                            ),
                        )
                except Exception as exc:  # noqa: BLE001
                    self._post("log", f"Connect failed: {exc}")
                finally:
                    self._post("done", "")

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(frm, text="Connect", style="Medium.TButton", command=go).pack(side="right")
        entry.bind("<Return>", lambda _e: go())

    # ------------------------------------------------------------------ actions

    def run_simple_setup(self) -> None:
        if self.busy:
            return
        if not self.adb:
            messagebox.showinfo(
                "Find your Mi Box first",
                "Please connect to your Mi Box first by clicking 'Find My Mi Box'.",
            )
            return
        self._set_busy(True)
        self.simple_progress.configure(value=0, maximum=5)

        def worker() -> None:
            try:
                fixer = Fixer(
                    self.adb,
                    self.cache_dir,
                    report=lambda s: self._post("log", s),
                )
                results = fixer.do_mobox_simple_setup(
                    progress=lambda i, t, lbl: self._post("simple_progress", (i, t, lbl))
                )
                fw = inspect_firmware(self.adb)
                self._post("connected", (self.adb, fw, [self.adb.serial or ""]))
                good = sum(1 for r in results if r.ok)
                self._post(
                    "done",
                    f"\u2713 All done! Your Mi Box is ready ({good}/{len(results)} checks passed).",
                )
            except Exception as exc:  # noqa: BLE001
                self._post("log", f"Setup error: {exc}")
                self._post("done", "Something interrupted setup — please try clicking the button again.")

        threading.Thread(target=worker, daemon=True).start()

    def apply_advanced(self) -> None:
        if self.busy or not self.adb:
            return
        plan = Plan(
            packages=[p for p, v in self.pkg_vars.items() if v.get()],
            apps=[k for k, v in self.app_vars.items() if v.get()],
            tune_animations=self.var_anim.get(),
            stay_awake=self.var_awake.get(),
            clear_recommendations=self.var_recs.get(),
            set_home=False,
            push_iptv=self.var_iptv.get(),
            iptv_playlist=catalog.IPTV_PLAYLISTS.get(
                self.var_playlist.get(), catalog.IPTV_PLAYLISTS["All channels"]
            ),
            wallpaper=Path(self.var_wallpaper.get()) if self.var_wallpaper.get().strip() else None,
        )
        home_choice = self.var_home_choice.get() if self.var_home.get() else ""
        enable_matvt = self.var_matvt.get()
        self._set_busy(True)

        def worker() -> None:
            try:
                fixer = Fixer(
                    self.adb,
                    self.cache_dir,
                    report=lambda s: self._post("log", s),
                )
                results = fixer.run(plan)
                if enable_matvt:
                    results.append(fixer.do_enable_matvt())
                if home_choice:
                    results.append(fixer.do_set_home(home_choice))
                fw = inspect_firmware(self.adb)
                self._post("connected", (self.adb, fw, [self.adb.serial or ""]))
                good = sum(1 for r in results if r.ok)
                self._post("log", f"=== Done: {good}/{len(results)} succeeded ===")
                self._post("done", f"Advanced changes finished ({good}/{len(results)} succeeded).")
            except Exception as exc:  # noqa: BLE001
                self._post("log", f"Error: {exc}")
                self._post("done", "Finished with errors — see log.")

        threading.Thread(target=worker, daemon=True).start()

    def open_bluetooth_on_tv(self) -> None:
        if not self.adb:
            messagebox.showinfo(
                "Not connected", "Click 'Find My Mi Box' first so MoBox can open Bluetooth on your TV."
            )
            return

        def worker() -> None:
            ok = self.adb.open_bluetooth_settings()
            self._post(
                "log",
                "Opened Bluetooth pairing screen on TV." if ok else "Could not open Bluetooth screen.",
            )

        threading.Thread(target=worker, daemon=True).start()

    def start_slideshow_on_tv(self) -> None:
        if not self.adb:
            messagebox.showinfo(
                "Not connected", "Click 'Find My Mi Box' first so MoBox can start the 4K slideshow on your TV."
            )
            return

        def worker() -> None:
            self.adb.enable_aerial_views_screensaver()
            ok = self.adb.start_screensaver_now()
            self._post(
                "log",
                "Started 4K Space & Nature slideshow on TV." if ok else "Could not start screensaver.",
            )

        threading.Thread(target=worker, daemon=True).start()

    def restore_selected(self) -> None:
        if self.busy or not self.adb:
            return
        pkgs = [p for p, v in self.pkg_vars.items() if v.get()]
        if not pkgs:
            return
        self._set_busy(True)

        def worker() -> None:
            try:
                fixer = Fixer(self.adb, self.cache_dir, report=lambda s: self._post("log", s))
                fixer.do_restore(pkgs)
            finally:
                self._post("done", "Selected packages restored.")

        threading.Thread(target=worker, daemon=True).start()

    def _set_all_bloat(self, state: bool) -> None:
        for b in catalog.BLOAT:
            if b.package in self.pkg_vars:
                self.pkg_vars[b.package].set(state and not b.danger)

    def _pick_wallpaper(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a wallpaper image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if path:
            self.var_wallpaper.set(path)

    # ------------------------------------------------------------------ self-updater (Rule #2)

    def _check_updates_async(self) -> None:
        def worker() -> None:
            status = check_for_updates()
            self._post("update_status", status)

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_status(self, status: UpdateStatus) -> None:
        self.update_status = status
        if status.error:
            self.update_var.set(f"MoBox v{__version__} ({status.short_local})  •  Offline")
        elif status.update_available:
            self.update_var.set(
                f"Update available: {status.short_remote} ({status.remote_message[:36]})"
            )
            self.btn_update.configure(text="Update MoBox")
        else:
            self.update_var.set(f"MoBox v{__version__} ({status.short_local})  •  Up to date")
            self.btn_update.configure(text="Check Updates")

    def on_update_button(self) -> None:
        if self.update_status and self.update_status.update_available:
            ok = messagebox.askyesno(
                "Update MoBox",
                f"A newer MoBox build ({self.update_status.short_remote}) is on GitHub:\n\n"
                f"\"{self.update_status.remote_message}\"\n\n"
                "This will run 'git pull --ff-only' in your MoBox folder without touching your Mi Box.\n"
                "Proceed?",
            )
            if not ok:
                return

            def worker() -> None:
                success, msg = apply_update()
                self._post("log", f"Updater: {msg}")
                self._post("update_status", check_for_updates())
                if success:
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            "MoBox Updated",
                            "MoBox has been updated! Close and reopen MoBox to use the new version.",
                        ),
                    )
                else:
                    self.after(0, lambda: messagebox.showwarning("Update Note", msg))

            threading.Thread(target=worker, daemon=True).start()
        else:
            self.update_var.set("Checking GitHub for updates...")
            self._check_updates_async()


# Backwards-compatible alias for existing imports/tests
FixerApp = MoBoxApp


def launch() -> int:
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("880x680")
    root.minsize(760, 560)
    MoBoxApp(root)
    root.mainloop()
    return 0
