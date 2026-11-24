#!/usr/bin/env python3
"""
3D Spinning ASCII Art Animation: Pouring Water & Blooming Six-Flower Bouquet
- Pure Python Standard Library (math, time, sys, os, shutil, random)
- True 3D parametric geometry, surface normals, Blinn-Phong lighting, perspective projection, z-buffering
- Organic pouring water stream with gravity, turbulence, droplets, splashes, and expanding base ripples
- Six distinct 3D flowers (Lirio, Orquidea, Gardenia, Tulip, Sunflower, Gerbera) that sprout, bloom,
  and converge into a balanced 3D spinning bouquet at the water's impact zone.
"""

import math
import os
import random
import shutil
import sys
import time

# Enable ANSI escape sequences on Windows
if os.name == "nt":
    os.system("")

# ASCII luminance ramp (low to high density)
SHADE_CHARS = " .·:;+*#%@"

# 24-bit TrueColor ANSI helper
def rgb_ansi(r, g, b):
    return f"\033[38;2;{int(max(0, min(255, r)))};{int(max(0, min(255, g)))};{int(max(0, min(255, b)))}m"


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0 + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def normalize(vx, vy, vz):
    mag = math.sqrt(vx * vx + vy * vy + vz * vz)
    if mag < 1e-9:
        return 0.0, 1.0, 0.0
    return vx / mag, vy / mag, vz / mag


def rotate_point_and_normal(x, y, z, nx, ny, nz, rx, ry, rz):
    # Rotate around Z (roll)
    cz, sz = math.cos(rz), math.sin(rz)
    x, y = x * cz - y * sz, x * sz + y * cz
    nx, ny = nx * cz - ny * sz, nx * sz + ny * cz
    # Rotate around X (pitch)
    cx, sx = math.cos(rx), math.sin(rx)
    y, z = y * cx - z * sx, y * sx + z * cx
    ny, nz = ny * cx - nz * sx, ny * sx + nz * cx
    # Rotate around Y (yaw)
    cy, sy = math.cos(ry), math.sin(ry)
    x, z = x * cy + z * sy, -x * sy + z * cy
    nx, nz = nx * cy + nz * sy, -nx * sy + nz * cy
    return x, y, z, nx, ny, nz


# ---------------------------------------------------------------------------
# 3D Flower Parametric Generators
# Each returns a list of (x, y, z, nx, ny, nz, r, g, b, spec_weight, bloom_order)
# Local flower coordinates: flower head centered at (0, 0, 0), facing +Y
# ---------------------------------------------------------------------------

def build_stem_and_leaves(tx, ty, tz, leaf_type="standard"):
    """Builds a curved 3D stem from bouquet tie-point (0, -4.5, 0) to flower head (tx, ty, tz)."""
    pts = []
    p0 = (0.0, -4.5, 0.0)
    p1 = (tx * 0.45, lerp(-4.5, ty, 0.5), tz * 0.45)
    p2 = (tx, ty, tz)

    steps = 28
    for i in range(steps + 1):
        t = i / steps
        it = 1.0 - t
        bx = it * it * p0[0] + 2 * it * t * p1[0] + t * t * p2[0]
        by = it * it * p0[1] + 2 * it * t * p1[1] + t * t * p2[1]
        bz = it * it * p0[2] + 2 * it * t * p1[2] + t * t * p2[2]

        for a_idx in range(5):
            ang = a_idx * (2 * math.pi / 5)
            rad = 0.14
            nx, nz = math.cos(ang), math.sin(ang)
            pts.append((
                bx + nx * rad, by, bz + nz * rad,
                nx, 0.15, nz,
                42, 135, 58, 0.2, t * 0.4
            ))

    # Add foliage leaves along the stem
    out_nx, _, out_nz = normalize(tx, 0.0, tz)
    if abs(tx) + abs(tz) < 0.1:
        out_nx, out_nz = 1.0, 0.0

    leaf_count = 3 if leaf_type == "lush" else 2
    for l_idx in range(leaf_count):
        lt = 0.38 + l_idx * 0.22
        ilt = 1.0 - lt
        lx0 = ilt * ilt * p0[0] + 2 * ilt * lt * p1[0] + lt * lt * p2[0]
        ly0 = ilt * ilt * p0[1] + 2 * ilt * lt * p1[1] + lt * lt * p2[1]
        lz0 = ilt * ilt * p0[2] + 2 * ilt * lt * p1[2] + lt * lt * p2[2]

        yaw_off = (l_idx - 0.5) * 0.85
        ca, sa = math.cos(yaw_off), math.sin(yaw_off)
        dx = out_nx * ca - out_nz * sa
        dz = out_nx * sa + out_nz * ca
        px, pz = -dz, dx

        u_steps, v_steps = 10, 5
        for iu in range(u_steps + 1):
            u = iu / u_steps
            for iv in range(-v_steps, v_steps + 1):
                v = iv / v_steps
                width = math.sin(u * math.pi) * (0.55 if leaf_type == "lush" else 0.38)
                length = u * (1.55 if leaf_type == "lush" else 1.25)
                arch = math.sin(u * math.pi) * 0.42 - u * u * 0.35

                x = lx0 + dx * length + px * (v * width)
                y = ly0 + arch + abs(v) * 0.08
                z = lz0 + dz * length + pz * (v * width)

                lnx, lny, lnz = normalize(dx * 0.3 + px * v * 0.4, 1.0, dz * 0.3 + pz * v * 0.4)
                g_col = int(lerp(110, 175, u))
                r_col = int(lerp(28, 65, u))
                pts.append((x, y, z, lnx, lny, lnz, r_col, g_col, 48, 0.45, 0.25 + u * 0.25))

    return pts


def generate_lirio():
    """1. Lirio (Lily): 6 recurved/flared tepals in 2 whorls + 6 long stamens with anthers."""
    pts = []
    for p in range(6):
        base_ang = p * (math.pi / 3.0)
        is_inner = p % 2 == 1
        u_steps, v_steps = 16, 6
        for iu in range(u_steps + 1):
            u = iu / u_steps  # 0 (center) to 1 (tip)
            for iv in range(-v_steps, v_steps + 1):
                v = iv / v_steps
                width = math.sin(u * math.pi) * (0.48 if is_inner else 0.38) * (1.0 - 0.2 * u)
                # Trumpet flare then dramatic recurve at tips
                rad = 0.15 + 1.55 * u + 0.45 * (u ** 2)
                height = 1.15 * u - 1.35 * (u ** 2.7) + (0.08 if is_inner else 0.0)
                cup = (1.0 - abs(v) ** 1.8) * 0.16 * math.sin(u * math.pi)

                ca, sa = math.cos(base_ang), math.sin(base_ang)
                px, pz = -sa, ca

                lx = ca * rad + px * (v * width)
                ly = height - cup
                lz = sa * rad + pz * (v * width)

                # Outward/upward normal curving backward at tip
                dr = 1.55 + 0.9 * u
                dh = 1.15 - 3.64 * (u ** 1.7)
                nx, ny, nz = normalize(-ca * dh + px * v * 0.5, dr, -sa * dh + pz * v * 0.5)

                # Color: Deep magenta/crimson center blending to soft pink and white edges
                if abs(v) > 0.72:
                    r, g, b = 252, 240, 246
                else:
                    r = int(lerp(235, 255, u))
                    g = int(lerp(55, 185, u))
                    b = int(lerp(130, 215, u))
                    # Dark nectar speckles near base
                    if 0.2 < u < 0.62 and ((iu + iv * 3) % 5 == 0):
                        r, g, b = 135, 20, 65

                pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.5, u))

    # 6 long curved stamens + golden/rust anthers
    for s in range(6):
        sang = s * (math.pi / 3.0) + 0.25
        ca, sa = math.cos(sang), math.sin(sang)
        for i in range(12):
            t = i / 11.0
            rad = 0.08 + 0.65 * (t ** 1.6)
            ht = 1.35 * t
            pts.append((ca * rad, ht, sa * rad, ca, 0.5, sa, 210, 245, 160, 0.3, 0.7 + 0.3 * t))
        # Anther at tip
        ax, ay, az = ca * 0.73, 1.35, sa * 0.73
        for d in (-0.08, 0.0, 0.08):
            pts.append((ax - sa * d, ay, az + ca * d, 0.0, 1.0, 0.0, 235, 115, 25, 0.6, 1.0))

    return pts


def generate_orquidea():
    """2. Orquidea (Orchid): 3 star-like sepals, 2 broad lateral petals, and 1 ruffled labellum (lip)."""
    pts = []
    # 3 Sepals (top dorsal, two lower lateral)
    sepal_angles = [math.pi * 0.5, math.pi * 1.22, math.pi * 1.78]
    for ang in sepal_angles:
        ca, sa = math.cos(ang), math.sin(ang)
        for iu in range(14):
            u = iu / 13.0
            for iv in range(-4, 5):
                v = iv / 4.0
                w = math.sin(u * math.pi) * 0.36
                dist = 0.15 + u * 1.55
                lx = ca * dist - sa * (v * w)
                ly = dist * sa * 0.65 + (1.0 - u) * 0.2
                lz = 0.25 * math.sin(u * math.pi) + abs(v) * 0.08
                nx, ny, nz = normalize(lx * 0.2, 0.85, 0.6)
                r = int(lerp(185, 225, u))
                g = int(lerp(95, 145, u))
                b = int(lerp(240, 255, u))
                pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.45, u))

    # 2 Broad lateral winged petals
    for side in (-1.0, 1.0):
        ang = (0.12 if side > 0 else math.pi - 0.12)
        ca, sa = math.cos(ang), math.sin(ang)
        for iu in range(15):
            u = iu / 14.0
            for iv in range(-6, 7):
                v = iv / 6.0
                w = math.sin(u * math.pi) * 0.72
                dist = 0.18 + u * 1.65
                lx = ca * dist - sa * (v * w)
                ly = sa * dist * 0.5 + v * w * ca * 0.4 + 0.15
                lz = 0.42 * math.sin(u * math.pi) - (v * v) * 0.12
                nx, ny, nz = normalize(side * 0.3, 0.8, 0.6)
                r = int(lerp(210, 245, u))
                g = int(lerp(110, 175, u))
                b = int(lerp(245, 255, u))
                pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.5, u))

    # Distinctive Labellum (3-lobed protruding ruffled cup at bottom-front)
    for iu in range(14):
        u = iu / 13.0
        for iv in range(-6, 7):
            v = iv / 6.0
            w = (0.28 + 0.52 * math.sin(u * math.pi)) * (1.0 + 0.2 * math.cos(v * math.pi * 2))
            ruffle = 0.09 * math.sin(v * 9.0) * u
            lx = v * w
            ly = -0.15 - u * 0.85 + (v * v) * 0.35 + ruffle
            lz = 0.25 + u * 1.15 - (v * v) * 0.25
            nx, ny, nz = normalize(v * 0.5, 0.65, 0.75)
            if u < 0.45 and abs(v) < 0.5:
                # Golden-yellow spotted throat
                r, g, b = 255, 215, 45
            else:
                # Rich magenta-crimson lip edge
                r, g, b = 225, 25, 145
            pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.6, 0.3 + 0.7 * u))

    return pts


def generate_gardenia():
    """3. Gardenia: Lush spiral tiers of overlapping creamy-white velvety rounded petals."""
    pts = []
    tiers = [
        (5, 0.48, 0.82, 0.15),
        (7, 0.88, 0.62, 0.55),
        (9, 1.32, 0.42, 0.95),
        (11, 1.72, 0.22, 1.35),
    ]
    for t_idx, (num_petals, max_r, pitch, rot_off) in enumerate(tiers):
        for p in range(num_petals):
            ang = p * (2.0 * math.pi / num_petals) + rot_off
            ca, sa = math.cos(ang), math.sin(ang)
            px, pz = -sa, ca
            for iu in range(11):
                u = iu / 10.0
                for iv in range(-5, 6):
                    v = iv / 5.0
                    # Rounded obovate gardenia petal
                    w = math.sin(u * math.pi * 0.88) * (0.32 + 0.14 * t_idx)
                    rad = 0.08 + u * max_r
                    curl = math.sin(u * math.pi) * (0.28 + 0.06 * t_idx) - (u ** 3) * 0.22
                    cup = (1.0 - v * v) * 0.12

                    lx = ca * rad + px * (v * w)
                    ly = u * max_r * math.sin(pitch) + curl + cup - t_idx * 0.08
                    lz = sa * rad + pz * (v * w)

                    # Swirl twist for inner bud tiers
                    if t_idx <= 1:
                        swirl = (1.0 - u) * 0.35
                        cs, ss = math.cos(swirl), math.sin(swirl)
                        lx, lz = lx * cs - lz * ss, lx * ss + lz * cs

                    nx, ny, nz = normalize(ca * (1.0 - pitch * 0.6) + px * v * 0.3, 0.75 + pitch * 0.4, sa * (1.0 - pitch * 0.6) + pz * v * 0.3)

                    # Creamy ivory center transitioning to pure silky white outer petals
                    cream = (1.0 - u) * (1.0 - t_idx / 4.0)
                    r = int(lerp(250, 255, 1.0 - cream * 0.3))
                    g = int(lerp(246, 232, cream))
                    b = int(lerp(242, 190, cream))

                    pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.55, (t_idx + u) / 4.0))

    return pts


def generate_tulip():
    """4. Tulip: 6 cupped chalice petals curving upward from base and inward at the crown."""
    pts = []
    for p in range(6):
        ang = p * (math.pi / 3.0)
        is_outer = p % 2 == 0
        ca, sa = math.cos(ang), math.sin(ang)
        px, pz = -sa, ca
        for iu in range(16):
            u = iu / 15.0
            for iv in range(-5, 6):
                v = iv / 5.0
                # Chalice wall profile: bulges outward in middle, cups gracefully at top
                rad = 0.16 + 0.92 * math.sin(u * math.pi * 0.78) + (0.07 if is_outer else 0.0)
                w = math.sin(u * math.pi * 0.92) * 0.56
                ht = 1.68 * (u ** 0.85) - (v * v) * 0.14
                # Wrap curvature around chalice circumference
                wrap_ang = (v * w) / max(0.25, rad)
                total_ang = ang + wrap_ang
                lx = rad * math.cos(total_ang)
                ly = ht
                lz = rad * math.sin(total_ang)

                nx, ny, nz = normalize(math.cos(total_ang), 0.35 - 0.55 * u, math.sin(total_ang))

                # Sunset flame gradient: ruby-red base -> coral orange -> golden yellow rim
                if u < 0.55:
                    t_c = u / 0.55
                    r = int(lerp(215, 255, t_c))
                    g = int(lerp(20, 95, t_c))
                    b = int(lerp(65, 35, t_c))
                else:
                    t_c = (u - 0.55) / 0.45
                    r = 255
                    g = int(lerp(95, 215, t_c))
                    b = int(lerp(35, 55, t_c))

                if abs(v) > 0.78 and u > 0.4:
                    g = min(255, g + 35)

                pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.45, u))

    return pts


def generate_sunflower():
    """5. Sunflower: Golden-angle phyllotaxis seed disc ringed by two layers of radiant golden petals."""
    pts = []
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    num_seeds = 140
    disc_rad = 0.92

    for i in range(num_seeds):
        f = i / num_seeds
        r = disc_rad * math.sqrt(f)
        theta = i * golden_angle
        lx = r * math.cos(theta)
        lz = r * math.sin(theta)
        # Domed central capitulum with subtle seed dimples
        ly = 0.26 * (1.0 - f * f) + 0.03 * math.cos(i * 1.7)
        nx, ny, nz = normalize(lx * 0.55, 1.0, lz * 0.55)

        if f < 0.32:
            cr, cg, cb = 65, 38, 16
        elif f < 0.78:
            cr, cg, cb = 105, 62, 22
        else:
            cr, cg, cb = 165, 105, 24
        pts.append((lx, ly, lz, nx, ny, nz, cr, cg, cb, 0.25, f * 0.5))

    # 22 Radiating ray florets in 2 staggered rings
    num_petals = 22
    for p in range(num_petals):
        ang = p * (2.0 * math.pi / num_petals)
        ring = p % 2
        ca, sa = math.cos(ang), math.sin(ang)
        px, pz = -sa, ca
        for iu in range(11):
            u = iu / 10.0
            for iv in range(-3, 4):
                v = iv / 3.0
                w = math.sin(u * math.pi) * 0.25
                rad = disc_rad * 0.92 + u * 1.18
                arch = math.sin(u * math.pi) * 0.22 - (u * u) * 0.16 + ring * 0.06

                lx = ca * rad + px * (v * w)
                ly = arch - abs(v) * 0.04
                lz = sa * rad + pz * (v * w)

                nx, ny, nz = normalize(ca * (0.4 * u - 0.15) + px * v * 0.25, 1.0, sa * (0.4 * u - 0.15) + pz * v * 0.25)
                r = 255
                g = int(lerp(165, 232, u))
                b = int(lerp(10, 42, u))
                pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.4, 0.4 + 0.6 * u))

    return pts


def generate_gerbera():
    """6. Gerbera Daisy: Prominent button eye + 3 concentric symmetrical tiers of ray petals."""
    pts = []
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(65):
        f = i / 65.0
        r = 0.48 * math.sqrt(f)
        theta = i * golden_angle
        lx = r * math.cos(theta)
        lz = r * math.sin(theta)
        ly = 0.22 * (1.0 - f * f)
        nx, ny, nz = normalize(lx * 0.45, 1.0, lz * 0.45)
        if f < 0.55:
            cr, cg, cb = 240, 190, 45
        else:
            cr, cg, cb = 255, 140, 50
        pts.append((lx, ly, lz, nx, ny, nz, cr, cg, cb, 0.35, f * 0.4))

    # 3 Concentric symmetrical ray layers (trans-florets to outer ray florets)
    layers = [
        (14, 0.42, 0.55, 0.22, 0.0),
        (18, 0.52, 0.92, 0.14, 0.12),
        (22, 0.58, 1.25, 0.04, 0.24),
    ]
    for l_idx, (count, r_start, length, y_off, a_off) in enumerate(layers):
        for p in range(count):
            ang = p * (2.0 * math.pi / count) + a_off
            ca, sa = math.cos(ang), math.sin(ang)
            px, pz = -sa, ca
            for iu in range(9):
                u = iu / 8.0
                for iv in range(-2, 3):
                    v = iv / 2.0
                    w = math.sin(u * math.pi * 0.92) * 0.18
                    rad = r_start + u * length
                    arch = y_off + math.sin(u * math.pi) * 0.18 + u * 0.08 * (2 - l_idx)

                    lx = ca * rad + px * (v * w)
                    ly = arch
                    lz = sa * rad + pz * (v * w)

                    nx, ny, nz = normalize(ca * 0.15 + px * v * 0.2, 1.0, sa * 0.15 + pz * v * 0.2)
                    # Vibrant coral-pink / salmon gerbera hues
                    r = 255
                    g = int(lerp(70, 145, (u + l_idx * 0.25) / 1.5))
                    b = int(lerp(110, 165, u))
                    pts.append((lx, ly, lz, nx, ny, nz, r, g, b, 0.45, 0.35 + 0.65 * u))

    return pts


# ---------------------------------------------------------------------------
# Bouquet Assembly & Blooming Transformation
# ---------------------------------------------------------------------------

class FlowerInstance:
    def __init__(self, name, local_pts, start_pos, target_pos, target_rot, delay, leaf_type="standard"):
        self.name = name
        self.local_pts = local_pts
        self.start_pos = start_pos
        self.target_pos = target_pos
        self.target_rot = target_rot  # (rx, ry, rz)
        self.delay = delay
        self.stem_pts = build_stem_and_leaves(target_pos[0], target_pos[1], target_pos[2], leaf_type)


def create_bouquet():
    """Creates the 6 distinct 3D flowers arranged in a balanced 360-degree dome bouquet."""
    specs = [
        # (Name, Generator, Target(x,y,z), TargetRot(rx,ry,rz), Delay, LeafType)
        ("Gardenia",  generate_gardenia(),  (0.0,  1.25,  0.0),  (0.10, 0.0,  0.0),  0.00, "lush"),
        ("Lirio",     generate_lirio(),     (2.65, 0.55,  0.85), (0.32, 0.0, -0.45), 0.10, "standard"),
        ("Orquidea",  generate_orquidea(),  (0.95, 0.35,  2.55), (0.62, 0.25, 0.12), 0.20, "standard"),
        ("Tulip",     generate_tulip(),     (-2.45, 0.65, 1.25), (0.28, 0.0,  0.42), 0.30, "standard"),
        ("Sunflower", generate_sunflower(), (-1.65, 0.50, -2.30), (-0.42, 0.0, 0.32), 0.40, "standard"),
        ("Gerbera",   generate_gerbera(),   (1.85, 0.45, -2.15), (-0.38, 0.0, -0.35), 0.50, "standard"),
    ]
    instances = []
    for name, pts, tpos, trot, delay, ltype in specs:
        # Start low & slightly wider before rising and converging into the bouquet dome
        spos = (tpos[0] * 1.45, -3.6, tpos[2] * 1.45)
        instances.append(FlowerInstance(name, pts, spos, tpos, trot, delay, ltype))
    return instances


# ---------------------------------------------------------------------------
# Continuous Pouring Water, Droplets, Splashes & Ripples
# ---------------------------------------------------------------------------

class WaterSimulation:
    def __init__(self):
        self.splashes = []
        rng = random.Random(42)
        for _ in range(85):
            ang = rng.uniform(0.0, 2.0 * math.pi)
            spd = rng.uniform(1.4, 3.8)
            vy = rng.uniform(2.5, 5.2)
            phase = rng.uniform(0.0, 1.0)
            self.splashes.append((ang, spd, vy, phase))

    def sample_points(self, elapsed, bloom_global):
        """Generates 3D points & normals for the falling water stream, droplets, splashes, and base ripples."""
        pts = []

        # 1. Continuous Pouring Stream from top (y = +8.8 down to impact zone y = +0.8)
        y_top = 8.8
        y_impact = lerp(-3.8, 0.9, bloom_global)
        stream_steps = 95

        for i in range(stream_steps):
            f = i / (stream_steps - 1)  # 0 at top, 1 at impact
            y = lerp(y_top, y_impact, f)

            # Gravity acceleration: stream narrows initially, then breaks into turbulent waves/droplets
            accel_pinch = 1.0 / math.sqrt(1.0 + 3.5 * f)
            wave1 = math.sin(y * 2.6 + elapsed * 13.0)
            wave2 = math.cos(y * 4.3 + elapsed * 19.0)
            rad = 0.46 * accel_pinch * (1.0 + 0.22 * wave1 + 0.14 * f * wave2)

            # Slight organic meandering of the pouring core
            cx = 0.14 * math.sin(y * 0.9 + elapsed * 4.8) * (0.3 + 0.7 * f)
            cz = 0.14 * math.cos(y * 1.1 + elapsed * 4.1) * (0.3 + 0.7 * f)

            # Longitudinal droplet breakup gaps near lower stream
            breakup = math.sin(y * 6.5 + elapsed * 24.0)
            is_droplet_gap = (f > 0.45 and breakup < -0.55)

            ring_res = 7 if not is_droplet_gap else 3
            for k in range(ring_res):
                ang = k * (2.0 * math.pi / ring_res) + y * 1.8 - elapsed * 9.0
                ca, sa = math.cos(ang), math.sin(ang)
                r_curr = rad * (0.55 if is_droplet_gap else 1.0)
                wx = cx + ca * r_curr
                wz = cz + sa * r_curr

                # Normal has strong radial + upward ripple component for bright specular glint
                ny_ripple = 0.38 * math.cos(y * 5.0 + elapsed * 17.0)
                nx, ny, nz = normalize(ca, ny_ripple, sa)

                # Shimmering aqua-cyan to pure white foam highlights
                foam = clamp(0.5 + 0.5 * math.sin(y * 5.5 + elapsed * 21.0 + k), 0.0, 1.0)
                r_col = int(lerp(80, 235, foam))
                g_col = int(lerp(185, 250, foam))
                b_col = 255
                pts.append((wx, y, wz, nx, ny, nz, r_col, g_col, b_col, 0.95))

        # 2. Detached Falling Satellite Droplets alongside the main stream
        for d_idx in range(28):
            t_drop = ((elapsed * 1.35 + d_idx * 0.137) % 1.0)
            # Quadratic gravity fall
            dy = y_top - (y_top - y_impact) * (t_drop ** 1.55)
            ang = d_idx * 2.39996 + elapsed * 1.5
            spread = 0.28 + 0.65 * t_drop
            dx = math.cos(ang) * spread
            dz = math.sin(ang) * spread
            pts.append((dx, dy, dz, math.cos(ang), 0.6, math.sin(ang), 195, 242, 255, 1.0))

        # 3. Impact Crown Splashes & Cascading Dew Arcs over the Bouquet
        gravity = 9.8
        for s_idx, (ang, spd, vy0, phase) in enumerate(self.splashes):
            t = ((elapsed * 1.45 + phase) % 1.0)
            # Parabolic arc starting from impact zone
            r = 0.25 + spd * t
            sy = y_impact + vy0 * t - 0.5 * gravity * (t * t) * 1.15
            if sy < -4.2:
                continue
            sx = math.cos(ang) * r
            sz = math.sin(ang) * r
            nx, ny, nz = normalize(math.cos(ang), 0.65 - t, math.sin(ang))
            bright = 1.0 - 0.5 * t
            pts.append((
                sx, sy, sz, nx, ny, nz,
                int(165 * bright + 75), int(230 * bright + 25), 255, 0.95
            ))

        # 4. Expanding Concentric Base Ripples at the Water Pool (y = -4.3)
        pool_y = -4.35
        num_rings = 4
        for r_idx in range(num_rings):
            prog = ((elapsed * 0.65 + r_idx / num_rings) % 1.0)
            ring_rad = 0.45 + prog * 4.8
            amp = (1.0 - prog) * 0.22
            ring_pts = int(28 + ring_rad * 14)
            for k in range(ring_pts):
                ang = k * (2.0 * math.pi / ring_pts)
                ca, sa = math.cos(ang), math.sin(ang)
                wave = math.sin(prog * math.pi * 6.0 - elapsed * 8.0)
                ry = pool_y + amp * wave
                nx, ny, nz = normalize(ca * 0.35 * wave, 1.0, sa * 0.35 * wave)
                fade = 1.0 - prog * 0.65
                pts.append((
                    ca * ring_rad, ry, sa * ring_rad,
                    nx, ny, nz,
                    int(90 * fade), int(195 * fade), int(250 * fade), 0.85
                ))

        return pts


# ---------------------------------------------------------------------------
# 3D Renderer (Perspective Projection, Z-Buffer, Blinn-Phong Shading)
# ---------------------------------------------------------------------------

def render_frame(width, height, elapsed, bouquet, water_sim):
    # Screen buffers
    size = width * height
    zbuf = [1e9] * size
    cbuf = [" "] * size
    abuf = [""] * size

    # Camera & projection setup
    cam_dist = 14.5
    fov_y = min(width * 0.5, height) * 1.18
    fov_x = fov_y * 2.0  # Terminal character aspect ratio ~ 2:1
    cx = width * 0.5
    cy = height * 0.54

    # Scene global rotation: continuous yaw spin + subtle pitch tilt for 3D depth
    scene_yaw = elapsed * 0.62
    scene_pitch = 0.32 + 0.10 * math.sin(elapsed * 0.45)

    # Directional Key Light & Half-Vector (for Blinn-Phong specular highlights)
    lx, ly, lz = normalize(0.52, 0.76, -0.38)
    # View vector is (0, 0, -1) toward camera
    hx, hy, hz = normalize(lx, ly, lz - 1.0)

    # Global bloom progression (smoothly blooms over first 10 seconds, then gently breathes)
    bloom_global = smoothstep(0.0, 9.5, elapsed)
    breath = 1.0 + 0.025 * math.sin(elapsed * 2.2)

    def plot_point(wx, wy, wz, nx, ny, nz, r, g, b, spec_w):
        # Apply global scene rotation (yaw then pitch)
        wx, wy, wz, nx, ny, nz = rotate_point_and_normal(
            wx, wy, wz, nx, ny, nz, scene_pitch, scene_yaw, 0.0
        )

        z_cam = wz + cam_dist
        if z_cam < 1.5:
            return

        inv_z = 1.0 / z_cam
        sx = int(cx + wx * fov_x * inv_z)
        sy = int(cy - wy * fov_y * inv_z)

        if 0 <= sx < width and 0 <= sy < height:
            idx = sy * width + sx
            if z_cam < zbuf[idx]:
                zbuf[idx] = z_cam

                # Two-sided surface normal lighting for thin petals
                ndotl = nx * lx + ny * ly + nz * lz
                if ndotl < 0.0:
                    ndotl = -ndotl * 0.65

                ndoth = max(0.0, nx * hx + ny * hy + nz * hz)
                spec = (ndoth ** 14) * spec_w

                # Depth attenuation cue
                depth_fade = clamp(1.38 - (z_cam - 9.0) * 0.045, 0.45, 1.15)
                ambient = 0.24
                lum = clamp((ambient + 0.76 * ndotl) * depth_fade + spec * 0.85, 0.05, 1.0)

                c_idx = int(lum * (len(SHADE_CHARS) - 1))
                cbuf[idx] = SHADE_CHARS[c_idx]

                # Add specular white sheen to RGB
                sr = r * lum + 255.0 * spec * 0.75
                sg = g * lum + 255.0 * spec * 0.75
                sb = b * lum + 255.0 * spec * 0.85
                abuf[idx] = rgb_ansi(sr, sg, sb)

    # 1. Render Blooming & Converging 3D Bouquet
    for fl in bouquet:
        # Per-flower staged bloom factor (0.0 = tight bud at base, 1.0 = full bloom in bouquet)
        fl_bloom = smoothstep(fl.delay * 5.0, fl.delay * 5.0 + 6.5, elapsed)
        if fl_bloom <= 0.005:
            continue

        # Smoothly converge position from sprout zone to final balanced bouquet dome
        fx = lerp(fl.start_pos[0], fl.target_pos[0], fl_bloom)
        fy = lerp(fl.start_pos[1], fl.target_pos[1], fl_bloom)
        fz = lerp(fl.start_pos[2], fl.target_pos[2], fl_bloom)

        # Orientation interpolates from upright bud to angled bouquet placement
        rx = fl.target_rot[0] * fl_bloom
        ry = fl.target_rot[1] * fl_bloom
        rz = fl.target_rot[2] * fl_bloom

        # Render Stem & Foliage
        for sx, sy, sz, snx, sny, snz, sr, sg, sb, sspec, sorder in fl.stem_pts:
            if fl_bloom >= sorder:
                plot_point(sx * fl_bloom, sy, sz * fl_bloom, snx, sny, snz, sr, sg, sb, sspec)

        # Render Flower Head (bud unfurling transformation)
        scale = (0.18 + 0.82 * fl_bloom) * breath
        unfurl = fl_bloom  # Controls how open the petals are

        for px, py, pz, pnx, pny, pnz, pr, pg, pb, pspec, porder in fl.local_pts:
            # Tight bud curls petals inward toward the vertical axis; unfurls as fl_bloom -> 1
            local_open = clamp((unfurl - porder * 0.25) / 0.75, 0.12, 1.0)
            bx = px * scale * local_open
            bz = pz * scale * local_open
            by = py * scale + (1.0 - local_open) * 0.45 * math.sqrt(px * px + pz * pz)

            # Rotate flower head into its bouquet tilt
            wx, wy, wz, wnx, wny, wnz = rotate_point_and_normal(
                bx, by, bz, pnx, pny, pnz, rx, ry, rz
            )
            plot_point(wx + fx, wy + fy, wz + fz, wnx, wny, wnz, pr, pg, pb, pspec)

    # 2. Render Pouring Water Stream, Droplets, Splashes & Ripples
    water_pts = water_sim.sample_points(elapsed, bloom_global)
    for wx, wy, wz, wnx, wny, wnz, wr, wg, wb, wspec in water_pts:
        plot_point(wx, wy, wz, wnx, wny, wnz, wr, wg, wb, wspec)

    # Assemble single flicker-free ANSI frame string
    lines = []
    for y in range(height):
        row_start = y * width
        row_parts = []
        last_ansi = ""
        for x in range(width):
            idx = row_start + x
            ch = cbuf[idx]
            ansi = abuf[idx]
            if ansi != last_ansi:
                row_parts.append(ansi if ansi else "\033[0m")
                last_ansi = ansi
            row_parts.append(ch)
        row_parts.append("\033[0m")
        lines.append("".join(row_parts))

    return "\033[H" + "\n".join(lines)


def main():
    bouquet = create_bouquet()
    water_sim = WaterSimulation()

    # Enter alternate screen buffer, hide cursor, clear screen
    sys.stdout.write("\033[?1049h\033[?25l\033[2J")
    sys.stdout.flush()

    start_time = time.perf_counter()
    target_dt = 1.0 / 30.0  # 30 FPS smooth pacing
    last_size = (0, 0)

    try:
        while True:
            frame_start = time.perf_counter()
            elapsed = frame_start - start_time

            term = shutil.get_terminal_size(fallback=(100, 36))
            width = max(40, term.columns - 1)
            height = max(20, term.lines - 1)

            if (width, height) != last_size:
                sys.stdout.write("\033[2J")
                last_size = (width, height)

            frame_str = render_frame(width, height, elapsed, bouquet, water_sim)
            sys.stdout.write(frame_str)
            sys.stdout.flush()

            frame_time = time.perf_counter() - frame_start
            sleep_time = target_dt - frame_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass
    finally:
        # Restore cursor, reset colors, and leave alternate screen buffer cleanly
        sys.stdout.write("\033[0m\033[?25h\033[?1049l\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()