"""Headless mode, for people who would rather use a terminal.

Examples:
    python -m fixer --list
    python -m fixer --host 192.168.1.45 --recommended --dry-run
    python -m fixer --host 192.168.1.45 --recommended
    python -m fixer --host 192.168.1.45 --restore-all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, catalog
from .adb import Adb, AdbError
from .tasks import Fixer, Plan, diagnose


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mibox-fixer",
        description="Debloat, de-Google and re-app a Xiaomi Mi Box (or any Android TV box) over ADB.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--host", help="Box IP address, e.g. 192.168.1.45")
    p.add_argument("--serial", help="Exact adb serial (overrides --host)")
    p.add_argument("--list", action="store_true", help="List what can be removed/installed, then exit.")
    p.add_argument("--dry-run", action="store_true", help="Show what would happen without changing anything.")

    g = p.add_argument_group("actions")
    g.add_argument("--recommended", action="store_true",
                   help="Remove the safe default bloat and install the recommended apps.")
    g.add_argument("--remove", metavar="PKG", action="append", default=[],
                   help="Disable one package (repeatable). '--remove all' removes every safe item.")
    g.add_argument("--install", metavar="KEY", action="append", default=[],
                   help="Install one app by key (repeatable). '--install all' installs recommended.")
    g.add_argument("--restore-all", action="store_true", help="Re-enable every package this tool knows about.")

    g2 = p.add_argument_group("tweaks")
    g2.add_argument("--no-animations", action="store_true", help="Do NOT change animation speed.")
    g2.add_argument("--no-stay-awake", action="store_true", help="Do NOT set stay-awake.")
    g2.add_argument("--no-clear-recommendations", action="store_true",
                    help="Do NOT clear the recommendation cache.")
    g2.add_argument("--no-home", action="store_true", help="Do NOT set Beam as the home screen.")
    g2.add_argument("--wallpaper", metavar="FILE", help="Push an image and use it as wallpaper.")
    g2.add_argument("--iptv", metavar="URL", help="Push an M3U playlist to /sdcard/Download.")
    g2.add_argument("--cache", metavar="DIR", help="Where to keep downloaded APKs.")
    return p


def do_list() -> int:
    print("Packages that can be removed (nothing is uninstalled, only disabled):\n")
    for cat in catalog.CATEGORY_ORDER:
        items = [b for b in catalog.BLOAT if b.category == cat]
        if not items:
            continue
        print(f"  {cat}")
        for b in items:
            mark = "  " if b.default else "  (opt-in) "
            flag = " [risky]" if b.danger else ""
            print(f"   {mark}{b.package:52s}{flag}")
        print()
    print("Apps that can be installed:\n")
    for a in catalog.APPS:
        mark = " " if a.default else " (opt-in)"
        print(f"   {a.key:14s}{mark:10s} {a.title}")
    print("\nRun with --host <ip> --recommended to apply the defaults.")
    return 0


def resolve_packages(args) -> list[str]:
    selected: list[str] = []
    if args.recommended:
        selected += [b.package for b in catalog.BLOAT if b.default and not b.danger]
    for raw in args.remove:
        if raw.lower() == "all":
            selected += [b.package for b in catalog.BLOAT if not b.danger]
        elif raw in catalog.BLOAT_BY_PACKAGE:
            selected.append(raw)
        else:
            known = [b.package for b in catalog.BLOAT if raw.lower() in b.package.lower()
                     or raw.lower() in b.title.lower()]
            if not known:
                print(f"warning: no package matches '{raw}'", file=sys.stderr)
            selected += known
    # de-duplicate, keep order
    return list(dict.fromkeys(selected))


def resolve_apps(args) -> list[str]:
    selected: list[str] = []
    if args.recommended:
        selected += [a.key for a in catalog.APPS if a.default]
    for raw in args.install:
        low = raw.lower()
        if low == "all":
            selected += [a.key for a in catalog.APPS if a.default]
        elif raw in catalog.APPS_BY_KEY:
            selected.append(raw)
        else:
            known = [a.key for a in catalog.APPS if low in a.key or low in a.title.lower()]
            if not known:
                print(f"warning: no app matches '{raw}'", file=sys.stderr)
            selected += known
    return list(dict.fromkeys(selected))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        return do_list()

    try:
        adb = Adb()
    except AdbError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.serial:
        adb.serial = args.serial
    elif args.host:
        if not adb.connect(args.host):
            print(f"error: could not connect to {args.host}", file=sys.stderr)
            return 2

    print("== device ==")
    try:
        info = diagnose(adb, report=lambda s: print(f"  {s}"))
    except AdbError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.restore_all:
        if args.dry_run:
            print("\n[dry-run] would re-enable every known package")
            return 0
        fixer = Fixer(adb, Path(args.cache or Path.home() / ".cache" / "mibox-fixer"),
                      report=lambda s: print(f"  {s}"))
        print("\n== restoring ==")
        fixer.do_restore([b.package for b in catalog.BLOAT])
        return 0

    plan = Plan(
        packages=resolve_packages(args),
        apps=resolve_apps(args),
        tune_animations=not args.no_animations,
        stay_awake=not args.no_stay_awake,
        clear_recommendations=not args.no_clear_recommendations,
        set_home=not args.no_home,
        push_iptv=bool(args.iptv),
        iptv_playlist=args.iptv or catalog.IPTV_PLAYLISTS["All channels"],
        wallpaper=Path(args.wallpaper) if args.wallpaper else None,
    )

    print(f"\n== plan ==\n  remove {len(plan.packages)} package(s)"
          f"\n  install {len(plan.apps)} app(s)"
          f"\n  animations={'off' if plan.tune_animations else 'skip'}"
          f"  awake={'on' if plan.stay_awake else 'skip'}"
          f"  home={'beam' if plan.set_home else 'skip'}")

    if args.dry_run:
        for p in plan.packages:
            print(f"  would disable: {p}")
        for a in plan.apps:
            print(f"  would install: {a}")
        return 0

    if not (plan.packages or plan.apps or plan.wallpaper or plan.push_iptv):
        print("\nnothing to do (try --recommended, or see --list)")
        return 0

    fixer = Fixer(adb, Path(args.cache or Path.home() / ".cache" / "mibox-fixer"),
                  report=lambda s: print(f"  {s}"))
    results = fixer.run(plan)
    good = sum(1 for r in results if r.ok)
    print(f"\n== done: {good}/{len(results)} steps succeeded ==")
    return 0 if good == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
