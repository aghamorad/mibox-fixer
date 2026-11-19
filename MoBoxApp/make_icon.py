#!/usr/bin/env python3
"""Generates the MoBox app icon: Paul Rand mid-century geometric retro + Liquid Glass.

Design language:
  - Full-bleed deep charcoal-cobalt canvas (#141824) so macOS never adds a white tray.
  - Paul Rand asymmetric mid-century modernist color blocks:
      * Warm vermilion-orange TV cabinet (#E84A27) with offset shadow block
      * Bauhaus mustard-gold tuning badge (#F2B705) & primary cyan/coral antenna spheres
      * Bold geometric "Mo" monogram inside the CRT screen
  - Apple tvOS Liquid Glass finish:
      * Translucent frosted glass screen lens & floating glass dock pill
      * Crisp diagonal specular refraction band & top-left glass rim highlight
  - Rendered at 512x512 with smooth anti-aliased signed-distance shapes, then scaled to
    all macOS iconset sizes (16..1024) and compiled via `iconutil -c icns`.
"""

from __future__ import annotations

import math
import os
import struct
import subprocess
import zlib


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = clamp((x - edge0) / (edge1 - edge0) if edge1 != edge0 else 0.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix_rgb(c1: tuple[float, float, float], c2: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    t = clamp(t)
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def sd_round_box(px: float, py: float, cx: float, cy: float, hw: float, hh: float, r: float) -> float:
    dx = abs(px - cx) - hw + r
    dy = abs(py - cy) - hh + r
    outside = math.hypot(max(dx, 0.0), max(dy, 0.0))
    inside = min(max(dx, dy), 0.0)
    return outside + inside - r


def sd_circle(px: float, py: float, cx: float, cy: float, r: float) -> float:
    return math.hypot(px - cx, py - cy) - r


def sd_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    pax, pay = px - ax, py - ay
    bax, bay = bx - ax, by - ay
    denom = bax * bax + bay * bay
    h = clamp((pax * bax + pay * bay) / denom) if denom > 0 else 0.0
    return math.hypot(pax - bax * h, pay - bay * h)


def render_icon(size: int = 256) -> list[list[tuple[int, int, int]]]:
    # Palette (0..255)
    BG_TOP = (20.0, 25.0, 38.0)       # Deep midnight indigo
    BG_BOT = (12.0, 15.0, 24.0)       # Bauhaus ink charcoal
    RAND_RED = (234.0, 74.0, 40.0)    # Paul Rand vermilion orange-red
    RAND_RED_HI = (248.0, 112.0, 76.0)
    RAND_GOLD = (244.0, 184.0, 12.0)  # Bauhaus mustard yellow-gold
    RAND_CYAN = (42.0, 202.0, 222.0)  # Mid-century electric cyan
    RAND_CORAL = (244.0, 92.0, 124.0) # Playful magenta-coral
    CREAM = (248.0, 243.0, 230.0)     # Warm gallery cream
    SCREEN_TOP = (18.0, 36.0, 64.0)   # Deep space navy inside screen
    SCREEN_BOT = (26.0, 78.0, 112.0)  # Horizon cyan-blue glow
    INK = (15.0, 17.0, 24.0)

    aa = 1.25 / size
    rows: list[list[tuple[int, int, int]]] = []

    for iy in range(size):
        ny = (iy + 0.5) / size  # 0..1 top to bottom
        row: list[tuple[int, int, int]] = []
        for ix in range(size):
            nx = (ix + 0.5) / size  # 0..1 left to right

            # 1. Background gradient + subtle radial studio vignette
            col = mix_rgb(BG_TOP, BG_BOT, ny)
            rad = math.hypot(nx - 0.5, ny - 0.45)
            col = mix_rgb(col, (32.0, 40.0, 62.0), clamp(1.0 - rad * 1.4) * 0.35)

            # 2. Subtle Paul Rand geometric background circle accent (offset top-right)
            d_bg_orb = sd_circle(nx, ny, 0.77, 0.22, 0.13)
            orb_cov = 1.0 - smoothstep(-aa, aa, d_bg_orb)
            if orb_cov > 0:
                col = mix_rgb(col, (36.0, 48.0, 76.0), orb_cov * 0.55)

            # 3. Retro rabbit-ear antennas (bold geometric rods + colorful spheres)
            d_ant_l = sd_segment(nx, ny, 0.43, 0.29, 0.27, 0.12) - 0.016
            d_ant_r = sd_segment(nx, ny, 0.57, 0.29, 0.72, 0.11) - 0.016
            ant_cov = 1.0 - smoothstep(-aa, aa, min(d_ant_l, d_ant_r))
            if ant_cov > 0:
                col = mix_rgb(col, CREAM, ant_cov)

            # Left antenna tip sphere (Paul Rand cyan)
            d_tip_l = sd_circle(nx, ny, 0.26, 0.115, 0.044)
            tip_l_cov = 1.0 - smoothstep(-aa, aa, d_tip_l)
            if tip_l_cov > 0:
                tip_c = mix_rgb(RAND_CYAN, (255.0, 255.0, 255.0), clamp(1.0 - math.hypot(nx - 0.245, ny - 0.10) * 18.0) * 0.55)
                col = mix_rgb(col, tip_c, tip_l_cov)

            # Right antenna tip sphere (Bauhaus gold)
            d_tip_r = sd_circle(nx, ny, 0.725, 0.105, 0.050)
            tip_r_cov = 1.0 - smoothstep(-aa, aa, d_tip_r)
            if tip_r_cov > 0:
                tip_c = mix_rgb(RAND_GOLD, (255.0, 250.0, 210.0), clamp(1.0 - math.hypot(nx - 0.71, ny - 0.09) * 16.0) * 0.5)
                col = mix_rgb(col, tip_c, tip_r_cov)

            # 4. Drop shadow under TV cabinet
            d_shadow = sd_round_box(nx, ny, 0.515, 0.585, 0.34, 0.27, 0.085)
            sh_cov = 1.0 - smoothstep(-0.04, 0.04, d_shadow)
            if sh_cov > 0:
                col = mix_rgb(col, (4.0, 6.0, 10.0), sh_cov * 0.55)

            # 5. Main Paul Rand TV Cabinet (vermilion orange-red with warm top bevel)
            d_cab = sd_round_box(nx, ny, 0.50, 0.56, 0.34, 0.27, 0.085)
            cab_cov = 1.0 - smoothstep(-aa, aa, d_cab)
            if cab_cov > 0:
                cab_base = mix_rgb(RAND_RED_HI, RAND_RED, clamp((ny - 0.29) / 0.54))
                # Liquid glass inner rim along top and left edge of cabinet
                rim = clamp(1.0 - abs(d_cab + 0.008) * 90.0) * clamp(1.2 - (nx + ny) * 0.7)
                cab_base = mix_rgb(cab_base, (255.0, 220.0, 200.0), rim * 0.55)
                col = mix_rgb(col, cab_base, cab_cov)

            # 6. Geometric CRT Screen Cutout (asymmetric left-weighted, leaving right control strip)
            d_scr_frame = sd_round_box(nx, ny, 0.445, 0.56, 0.245, 0.205, 0.055)
            frame_cov = 1.0 - smoothstep(-aa, aa, d_scr_frame)
            if frame_cov > 0:
                col = mix_rgb(col, INK, frame_cov)

            d_scr = sd_round_box(nx, ny, 0.445, 0.56, 0.230, 0.190, 0.046)
            scr_cov = 1.0 - smoothstep(-aa, aa, d_scr)
            if scr_cov > 0:
                scr_c = mix_rgb(SCREEN_TOP, SCREEN_BOT, clamp((ny - 0.37) / 0.38))
                # Cosmic star / nebula glow inside the 4K screen
                neb = clamp(1.0 - math.hypot((nx - 0.38) * 1.1, (ny - 0.48) * 1.3) * 3.2)
                scr_c = mix_rgb(scr_c, (68.0, 165.0, 215.0), neb * 0.45)
                neb2 = clamp(1.0 - math.hypot((nx - 0.54) * 1.2, (ny - 0.62) * 1.2) * 3.8)
                scr_c = mix_rgb(scr_c, RAND_CORAL, neb2 * 0.35)

                # Liquid Glass diagonal sheen across screen
                diag = (nx * 0.85 + ny * 0.55)
                if 0.56 < diag < 0.69:
                    sheen = math.sin((diag - 0.56) / 0.13 * math.pi)
                    scr_c = mix_rgb(scr_c, (255.0, 255.0, 255.0), sheen * 0.18)

                # Bold Paul Rand geometric "M" + "o" inside the screen
                # "M" built from two crisp vertical pillars + V chevron
                d_m1 = sd_segment(nx, ny, 0.305, 0.60, 0.305, 0.47) - 0.020
                d_m2 = sd_segment(nx, ny, 0.305, 0.47, 0.365, 0.555) - 0.019
                d_m3 = sd_segment(nx, ny, 0.365, 0.555, 0.425, 0.47) - 0.019
                d_m4 = sd_segment(nx, ny, 0.425, 0.47, 0.425, 0.60) - 0.020
                d_m = min(d_m1, d_m2, d_m3, d_m4)
                m_cov = 1.0 - smoothstep(-aa, aa, d_m)
                if m_cov > 0:
                    scr_c = mix_rgb(scr_c, CREAM, m_cov)

                # "o" built as a playful Paul Rand geometric ring in mustard-gold + cyan core
                d_o_outer = sd_circle(nx, ny, 0.535, 0.54, 0.062)
                d_o_inner = sd_circle(nx, ny, 0.535, 0.54, 0.026)
                o_ring_cov = (1.0 - smoothstep(-aa, aa, d_o_outer)) * smoothstep(-aa, aa, d_o_inner)
                if o_ring_cov > 0:
                    scr_c = mix_rgb(scr_c, RAND_GOLD, o_ring_cov)
                o_core_cov = 1.0 - smoothstep(-aa, aa, d_o_inner + 0.004)
                if o_core_cov > 0:
                    scr_c = mix_rgb(scr_c, RAND_CYAN, o_core_cov)

                # Liquid Glass floating tvOS dock pill at bottom of screen
                d_dock = sd_round_box(nx, ny, 0.445, 0.695, 0.165, 0.026, 0.018)
                dock_cov = 1.0 - smoothstep(-aa, aa, d_dock)
                if dock_cov > 0:
                    scr_c = mix_rgb(scr_c, (235.0, 248.0, 255.0), dock_cov * 0.42)
                    # Three tiny colorful app dots inside the Liquid Glass dock
                    for dx, dcol in ((0.385, RAND_RED_HI), (0.445, RAND_GOLD), (0.505, RAND_CYAN)):
                        d_dot = sd_circle(nx, ny, dx, 0.695, 0.012)
                        dot_cov = 1.0 - smoothstep(-aa, aa, d_dot)
                        if dot_cov > 0:
                            scr_c = mix_rgb(scr_c, dcol, dot_cov * 0.95)

                # Specular Liquid Glass inner border around the screen
                scr_rim = clamp(1.0 - abs(d_scr + 0.005) * 120.0)
                scr_c = mix_rgb(scr_c, (210.0, 245.0, 255.0), scr_rim * 0.55)
                col = mix_rgb(col, scr_c, scr_cov)

            # 7. Right-side Paul Rand geometric tuning dials on the TV cabinet
            d_dial1 = sd_circle(nx, ny, 0.745, 0.46, 0.044)
            dial1_cov = 1.0 - smoothstep(-aa, aa, d_dial1)
            if dial1_cov > 0:
                col = mix_rgb(col, CREAM, dial1_cov)
                # Dial pointer notch
                d_notch = sd_segment(nx, ny, 0.745, 0.46, 0.768, 0.437) - 0.008
                n_cov = 1.0 - smoothstep(-aa, aa, d_notch)
                if n_cov > 0:
                    col = mix_rgb(col, INK, n_cov)

            d_dial2 = sd_circle(nx, ny, 0.745, 0.58, 0.036)
            dial2_cov = 1.0 - smoothstep(-aa, aa, d_dial2)
            if dial2_cov > 0:
                col = mix_rgb(col, RAND_GOLD, dial2_cov)

            # Speaker grille bars below dials
            for gy in (0.665, 0.695, 0.725):
                d_grille = sd_round_box(nx, ny, 0.745, gy, 0.034, 0.006, 0.004)
                g_cov = 1.0 - smoothstep(-aa, aa, d_grille)
                if g_cov > 0:
                    col = mix_rgb(col, INK, g_cov * 0.75)

            # 8. Mid-century splayed feet under cabinet
            d_foot_l = sd_segment(nx, ny, 0.31, 0.83, 0.27, 0.885) - 0.018
            d_foot_r = sd_segment(nx, ny, 0.69, 0.83, 0.73, 0.885) - 0.018
            foot_cov = 1.0 - smoothstep(-aa, aa, min(d_foot_l, d_foot_r))
            if foot_cov > 0:
                col = mix_rgb(col, RAND_GOLD, foot_cov)

            row.append((int(clamp(col[0], 0, 255)), int(clamp(col[1], 0, 255)), int(clamp(col[2], 0, 255))))
        rows.append(row)
    return rows


def scale_rows(rows: list[list[tuple[int, int, int]]], target: int) -> list[list[tuple[int, int, int]]]:
    src = len(rows)
    if target == src:
        return rows
    out: list[list[tuple[int, int, int]]] = []
    for y in range(target):
        sy = min(src - 1, (y * src) // target)
        src_row = rows[sy]
        out.append([src_row[min(src - 1, (x * src) // target)] for x in range(target)])
    return out


def write_png(path: str, rows: list[list[tuple[int, int, int]]]) -> None:
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", len(rows[0]), len(rows), 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    res = os.path.join(here, "Resources")
    iconset = os.path.join(res, "AppIcon.iconset")
    os.makedirs(iconset, exist_ok=True)

    master = render_icon(512)
    targets = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for name, px in targets.items():
        write_png(os.path.join(iconset, name), scale_rows(master, px))

    preview = os.path.join(here, "icon-preview.png")
    write_png(preview, master)

    icns = os.path.join(res, "AppIcon.icns")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns], check=True)
    print("Wrote", icns, "and", preview)


if __name__ == "__main__":
    main()
