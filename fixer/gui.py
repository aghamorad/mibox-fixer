"""Mi Box Fixer - a small Tkinter front-end.

Everything runs on a worker thread so the window stays responsive while ADB
talks to the box, and every checkbox maps 1:1 to an operation that was
verified on a real Mi Box 4.
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__, catalog
from .adb import Adb, AdbError, Device, current_platform_tools_hint, find_adb
from .tasks import Fixer, Plan, diagnose

APP_TITLE = f"Mi Box Fixer {__version__}"


class FixerApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=10)
        self.grid(row=0, column=0, sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.adb = None
        self.state: dict = {}
        self.pkg_vars: dict = {}
        self.app_vars: dict = {}
        self.busy = False
        self.msg_queue: queue.Queue = queue.Queue()
        self.cache_dir = Path(
            os.environ.get("MIBOX_FIXER_CACHE")
            or Path.home() / ".cache" / "mibox-fixer"
        )

        self._build_header()
        self._build_tabs()
        self._build_footer()

        self.after(120, self._drain)
        self.after(300, self.auto_connect)

    # ------------------------------------------------------------------ header

    def _build_header(self) -> None:
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ttk.Label(bar, text="Device:").grid(row=0, column=0, padx=(0, 6))
        self.device_var = tk.StringVar(value="not connected")
        ttk.Combobox(
            bar, textvariable=self.device_var, state="readonly", width=52
        ).grid(row=0, column=1, sticky="ew")
        ttk.Button(bar, text="Rescan", command=self.rescan).grid(row=0, column=2, padx=4)
        ttk.Button(bar, text="Connect Wi-Fi...", command=self.connect_dialog).grid(
            row=0, column=3, padx=4
        )

        self.summary_var = tk.StringVar(value="Click Rescan to look for your box.")
        ttk.Label(self, textvariable=self.summary_var, foreground="#555").grid(
            row=1, column=0, sticky="w", pady=(6, 8)
        )

    # ------------------------------------------------------------------ tabs

    def _build_tabs(self) -> None:
        nb = ttk.Notebook(self)
        nb.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)

        self.tab_remove = ttk.Frame(nb, padding=8)
        self.tab_install = ttk.Frame(nb, padding=8)
        self.tab_tune = ttk.Frame(nb, padding=8)
        self.tab_help = ttk.Frame(nb, padding=8)
        nb.add(self.tab_remove, text="What to remove")
        nb.add(self.tab_install, text="What to install")
        nb.add(self.tab_tune, text="Tweaks")
        nb.add(self.tab_help, text="Help")

        self._build_remove_tab()
        self._build_install_tab()
        self._build_tune_tab()
        self._build_help_tab()

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
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-e.delta / 40), "units"),
        )
        return inner

    def _build_remove_tab(self) -> None:
        ttk.Label(
            self.tab_remove,
            text="Nothing is uninstalled. These are disabled (pm disable-user) and can be "
                 "switched back on at any time.",
            foreground="#555",
            wraplength=760,
            justify="left",
        ).pack(anchor="w")

        btns = ttk.Frame(self.tab_remove)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Select all safe", command=lambda: self._set_all(True)).pack(side="left")
        ttk.Button(btns, text="Select none", command=lambda: self._set_all(False)).pack(side="left", padx=6)
        ttk.Button(btns, text="Restore selected", command=self.restore_selected).pack(side="right")

        body = self._scrolled(self.tab_remove)
        for cat in catalog.CATEGORY_ORDER:
            items = [b for b in catalog.BLOAT if b.category == cat]
            if not items:
                continue
            head = ttk.Frame(body)
            head.pack(fill="x", pady=(8, 2))
            ttk.Label(head, text=cat, font=("", 11, "bold")).pack(side="left")
            ttk.Button(
                head, text="toggle", width=8,
                command=lambda c=cat: self._toggle_cat(c),
            ).pack(side="right")

            for item in items:
                row = ttk.Frame(body)
                row.pack(fill="x", padx=(12, 0), pady=1)
                var = tk.BooleanVar(value=item.default)
                self.pkg_vars[item.package] = var
                ttk.Checkbutton(row, text=item.title, variable=var, width=32).pack(side="left")
                note = ("\u26a0 " if item.danger else "") + item.detail
                ttk.Label(row, text=note, foreground="#777", wraplength=470).pack(
                    side="left", fill="x", expand=True
                )

    def _build_install_tab(self) -> None:
        ttk.Label(
            self.tab_install,
            text="Downloads the correct 32-bit / 64-bit APK for your box and installs it.",
            foreground="#555",
        ).pack(anchor="w", pady=(0, 6))

        body = self._scrolled(self.tab_install)
        for app in catalog.APPS:
            row = ttk.Frame(body)
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=app.default)
            self.app_vars[app.key] = var
            ttk.Checkbutton(row, text=app.title, variable=var, width=34).pack(side="left")
            ttk.Label(row, text=app.detail, foreground="#777", wraplength=460).pack(
                side="left", fill="x", expand=True
            )

    def _build_tune_tab(self) -> None:
        f = self.tab_tune
        self.opt_anim = tk.BooleanVar(value=True)
        self.opt_awake = tk.BooleanVar(value=True)
        self.opt_recs = tk.BooleanVar(value=True)
        self.opt_home = tk.BooleanVar(value=True)
        self.opt_iptv = tk.BooleanVar(value=False)

        def add(var, title, note):
            row = ttk.Frame(f)
            row.pack(fill="x", pady=3)
            ttk.Checkbutton(row, text=title, variable=var, width=38).pack(side="left")
            ttk.Label(row, text=note, foreground="#777", wraplength=430).pack(
                side="left", fill="x", expand=True
            )

        add(self.opt_anim, "Speed up animations (0.5x)",
            "Menu transitions feel roughly twice as fast.")
        add(self.opt_awake, "Stay awake while plugged in",
            "Stops the box sleeping and dropping your adb connection.")
        add(self.opt_recs, "Clear recommendation rows",
            "Wipes the cached 'Recommended / Continue watching' data.")
        add(self.opt_home, "Set Beam as the home screen",
            "Only takes effect if Beam is installed.")
        add(self.opt_iptv, "Push IPTV playlist to the box",
            "Downloads a free channel list to /sdcard/Download.")

        row = ttk.Frame(f)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Playlist:").pack(side="left")
        self.playlist_var = tk.StringVar(value="All channels")
        ttk.Combobox(
            row, textvariable=self.playlist_var, state="readonly",
            values=list(catalog.IPTV_PLAYLISTS),
        ).pack(side="left", padx=6)

        row2 = ttk.Frame(f)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Wallpaper (optional):").pack(side="left")
        self.wall_var = tk.StringVar(value="")
        ttk.Entry(row2, textvariable=self.wall_var, width=40).pack(side="left", padx=6)
        ttk.Button(row2, text="Choose...", command=self.pick_wallpaper).pack(side="left")

    def _build_help_tab(self) -> None:
        f = self.tab_help
        text = tk.Text(f, wrap="word", height=20, relief="flat", background="#fbfbfb")
        text.pack(fill="both", expand=True)
        adb_path = find_adb() or "NOT FOUND"
        text.insert(
            "1.0",
            "Before you start\n"
            "  1. On the box: Settings -> Device Preferences -> About -> click Build "
            "7 times to unlock Developer options.\n"
            "  2. Settings -> Device Preferences -> Developer options -> turn on "
            "'USB debugging' and 'Network debugging'.\n"
            "  3. Put the box and this computer on the same Wi-Fi, then click "
            "'Connect Wi-Fi...'.\n\n"
            "What this tool does\n"
            "  Every checkbox maps to a command tested on a real Xiaomi Mi Box 4 "
            "(MIBOX4 / oneday, Android 9). Removal uses 'pm disable-user', so nothing "
            "is deleted and 'Restore selected' undoes it.\n\n"
            "Safety\n"
            "  No custom ROM and no lock bypass. If your box has a locked bootloader "
            "(most Mi Boxes do), nothing here changes that.\n\n"
            f"adb in use: {adb_path}\n"
            f"If missing, install it with:\n    {current_platform_tools_hint()}\n\n"
            f"Downloaded APKs are cached in {self.cache_dir}\n",
        )
        text.configure(state="disabled")

    # ------------------------------------------------------------------ footer

    def _build_footer(self) -> None:
        wrap = ttk.Frame(self)
        wrap.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(0, weight=1)

        self.log = tk.Text(wrap, height=9, wrap="word", relief="solid", borderwidth=1)
        self.log.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=sb.set, state="disabled")

        bar = ttk.Frame(self)
        bar.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.apply_btn = ttk.Button(bar, text="Apply changes", command=self.apply)
        self.apply_btn.pack(side="right")
        self.diag_btn = ttk.Button(bar, text="Check device", command=self.run_diagnose)
        self.diag_btn.pack(side="right", padx=6)
        self.progress = ttk.Progressbar(bar, mode="determinate", length=220)
        self.progress.pack(side="left")

    # ------------------------------------------------------------------ plumbing

    def say(self, text: str) -> None:
        self.msg_queue.put(text)

    def _drain(self) -> None:
        try:
            while True:
                line = self.msg_queue.get_nowait()
                if line == "__CLEAR__":
                    self.log.configure(state="normal")
                    self.log.delete("1.0", "end")
                    self.log.configure(state="disabled")
                    continue
                if line == "__DONE__":
                    self._busy(False)
                    continue
                self.log.configure(state="normal")
                self.log.insert("end", line + "\n")
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(120, self._drain)

    def _busy(self, on: bool) -> None:
        self.busy = on
        state = "disabled" if on else "normal"
        for btn in (self.apply_btn, self.diag_btn):
            btn.configure(state=state)
        if on:
            self.progress.configure(mode="indeterminate")
            self.progress.start(15)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)

    def _thread(self, fn, *args) -> None:
        if self.busy:
            return
        self._busy(True)

        def runner():
            try:
                fn(*args)
            except Exception as exc:  # noqa: BLE001 - report, never crash the UI
                self.say(f"ERROR: {exc}")
            finally:
                self.msg_queue.put("__DONE__")

        threading.Thread(target=runner, daemon=True).start()

    # ------------------------------------------------------------------ connect

    def auto_connect(self) -> None:
        try:
            devices = Adb.devices()
        except AdbError as exc:
            self.say(str(exc))
            self.say(f"Install adb with: {current_platform_tools_hint()}")
            return
        ready = [d for d in devices if d.is_ready]
        if ready:
            self._use_device(ready[0])
        else:
            self.say("No device found yet. Turn on debugging, then use 'Connect Wi-Fi...'.")

    def rescan(self) -> None:
        self.msg_queue.put("__CLEAR__")
        self.auto_connect()

    def _use_device(self, dev: Device) -> None:
        self.device_var.set(str(dev))
        try:
            self.adb = Adb(serial=dev.serial)
        except AdbError as exc:
            self.say(str(exc))
            return
        self.say(f"Connected to {dev}")
        self.run_diagnose()

    def connect_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title("Connect over Wi-Fi")
        win.transient(self)
        win.grab_set()
        ttk.Label(win, text="Box IP address (shown on the Network debugging screen):").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 4), sticky="w"
        )
        entry = ttk.Entry(win, width=28)
        entry.grid(row=1, column=0, columnspan=2, padx=12, sticky="w")
        entry.insert(0, "192.168.1.")
        entry.focus_set()

        def submit():
            host = entry.get().strip()
            win.destroy()
            if host:
                self._thread(self._do_connect, host)

        ttk.Button(win, text="Connect", command=submit).grid(
            row=2, column=1, padx=12, pady=12, sticky="e"
        )
        win.bind("<Return>", lambda _e: submit())

    def _do_connect(self, host: str) -> None:
        self.say(f"Connecting to {host} ...")
        try:
            client = Adb()
        except AdbError as exc:
            self.say(str(exc))
            return
        if client.connect(host):
            self.adb = client
            self.say(f"Connected to {host}")
            self.run_diagnose()
        else:
            self.say(
                "Could not connect. Check that 'Network debugging' is ON and that the "
                "box is on the same Wi-Fi."
            )

    # ------------------------------------------------------------------ actions

    def run_diagnose(self) -> None:
        if not self.adb:
            self.say("Not connected.")
            return
        if self.busy:
            return
        self._thread(self._do_diagnose)

    def _do_diagnose(self) -> None:
        self.state = diagnose(self.adb, self.say)
        installed = sum(1 for v in self.state["installed"].values() if v)
        self.say(f"Suggested apps already installed: {installed}/{len(self.state['installed'])}")
        self.summary_var.set(
            f"{self.state['model']} \u00b7 Android {self.state['release']} \u00b7 "
            f"{self.state['abi']} \u00b7 {len(self.state['disabled'])} packages disabled"
        )

    def _set_all(self, value: bool) -> None:
        for pkg, var in self.pkg_vars.items():
            if catalog.BLOAT_BY_PACKAGE[pkg].danger and value:
                continue
            var.set(value)

    def _toggle_cat(self, cat: str) -> None:
        items = [b for b in catalog.BLOAT if b.category == cat]
        target = not all(self.pkg_vars[i.package].get() for i in items)
        for i in items:
            self.pkg_vars[i.package].set(target)

    def pick_wallpaper(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a wallpaper",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if path:
            self.wall_var.set(path)

    def _collect_plan(self) -> Plan:
        wallpaper = self.wall_var.get().strip()
        return Plan(
            packages=[p for p, v in self.pkg_vars.items() if v.get()],
            apps=[k for k, v in self.app_vars.items() if v.get()],
            tune_animations=self.opt_anim.get(),
            stay_awake=self.opt_awake.get(),
            clear_recommendations=self.opt_recs.get(),
            set_home=self.opt_home.get(),
            push_iptv=self.opt_iptv.get(),
            iptv_playlist=catalog.IPTV_PLAYLISTS[self.playlist_var.get()],
            wallpaper=Path(wallpaper) if wallpaper else None,
        )

    def apply(self) -> None:
        if not self.adb:
            messagebox.showwarning(APP_TITLE, "Connect to the box first.")
            return
        plan = self._collect_plan()
        if not (plan.packages or plan.apps or plan.wallpaper or plan.push_iptv
                or plan.tune_animations or plan.stay_awake or plan.clear_recommendations):
            messagebox.showinfo(APP_TITLE, "Nothing is ticked.")
            return
        summary = (
            f"Remove {len(plan.packages)} package(s)\n"
            f"Install {len(plan.apps)} app(s)\n"
            f"Speed up animations: {plan.tune_animations}\n"
            f"Stay awake: {plan.stay_awake}\n"
            f"Clear recommendations: {plan.clear_recommendations}\n"
            f"Wallpaper: {plan.wallpaper or 'skip'}\n"
            f"IPTV playlist: {plan.push_iptv}\n"
            f"Set Beam as home: {plan.set_home}"
        )
        if not messagebox.askokcancel(APP_TITLE, summary + "\n\nProceed?"):
            return
        self._thread(self._do_apply, plan)

    def _do_apply(self, plan: Plan) -> None:
        fixer = Fixer(self.adb, self.cache_dir, report=self.say)
        results = fixer.run(plan)
        good = sum(1 for r in results if r.ok)
        self.say(f"=== done: {good}/{len(results)} steps succeeded")
        if good != len(results):
            self.say("Some steps failed - see the log above.")

    def restore_selected(self) -> None:
        if not self.adb:
            messagebox.showwarning(APP_TITLE, "Connect to the box first.")
            return
        chosen = [p for p, v in self.pkg_vars.items() if v.get()]
        if not chosen:
            messagebox.showinfo(APP_TITLE, "Tick the packages you want back first.")
            return
        if not messagebox.askokcancel(
            APP_TITLE, f"Re-enable {len(chosen)} package(s) on the box?"
        ):
            return
        self._thread(self._do_restore, chosen)

    def _do_restore(self, packages) -> None:
        fixer = Fixer(self.adb, self.cache_dir, report=self.say)
        fixer.do_restore(packages)
        self.say("Restore complete.")


def main() -> int:
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("960x780")
    root.minsize(820, 620)
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    FixerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
