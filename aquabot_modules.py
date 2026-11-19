#!/usr/bin/env python3
"""
AquaBot ARB-2026 — Refined print-ready CAD modules
----------------------------------------------------
Refinements:
  • More hull detail (bow taper, deck ribs, cable glands, drain)
  • MG996R servo mounts (scoop pivot)
  • BLDC 4-hole mount pattern inside thruster duct
  • Waterproof electronics lid (gasket groove + M3 holes)
  • SCALE=1 POC and SCALE=4 full prototype outputs

Units: mm
"""
from __future__ import annotations
import math, struct
from pathlib import Path
import numpy as np

# Global scale set in build_all()
SCALE = 1.0
WALL = 2.4  # base wall at SCALE=1; scaled with SCALE

OUT_ROOT = Path(__file__).resolve().parent


def S(v: float) -> float:
    return v * SCALE


def wall() -> float:
    # Cap wall growth on full-size so large prints stay practical
    return min(WALL * SCALE, 4.0) if SCALE > 1 else WALL * SCALE


# ========================= primitives =======================================

def _box(x0, x1, y0, y1, z0, z1):
    v = np.array([
        [x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
        [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],
    ], dtype=np.float64)
    faces = [
        [0,2,1],[0,3,2], [4,5,6],[4,6,7],
        [0,1,5],[0,5,4], [3,7,6],[3,6,2],
        [0,4,7],[0,7,3], [1,2,6],[1,6,5],
    ]
    return v[faces]


def _hollow_box(x0, x1, y0, y1, z0, z1, t, open_top=False, open_bottom=False):
    parts = []
    if not open_bottom:
        parts.append(_box(x0, x1, y0, y1, z0, z0 + t))
    if not open_top:
        parts.append(_box(x0, x1, y0, y1, z1 - t, z1))
    parts.append(_box(x0, x1, y0, y0 + t, z0, z1))
    parts.append(_box(x0, x1, y1 - t, y1, z0, z1))
    parts.append(_box(x0, x0 + t, y0 + t, y1 - t, z0, z1))
    parts.append(_box(x1 - t, x1, y0 + t, y1 - t, z0, z1))
    return np.vstack(parts)


def _cylinder(cx, cy, cz, r, h, axis="z", segments=28):
    tris = []
    n = max(8, int(segments))
    for i in range(n):
        a0, a1 = 2*math.pi*i/n, 2*math.pi*(i+1)/n
        c0, s0 = math.cos(a0), math.sin(a0)
        c1, s1 = math.cos(a1), math.sin(a1)
        def pt(c, s, along):
            if axis == "z": return [cx+r*c, cy+r*s, cz+along]
            if axis == "x": return [cx+along, cy+r*c, cz+r*s]
            return [cx+r*c, cy+along, cz+r*s]
        def ctr(along):
            if axis == "z": return [cx, cy, cz+along]
            if axis == "x": return [cx+along, cy, cz]
            return [cx, cy+along, cz]
        p0, p1 = pt(c0,s0,0), pt(c1,s1,0)
        q0, q1 = pt(c0,s0,h), pt(c1,s1,h)
        tris += [[p0,q0,p1],[p1,q0,q1],[ctr(0),p1,p0],[ctr(h),q0,q1]]
    return np.array(tris, dtype=np.float64)


def _pipe(cx, cy, cz, r_out, r_in, length, axis="z", segments=32):
    tris = []
    n = max(12, int(segments))
    for i in range(n):
        a0, a1 = 2*math.pi*i/n, 2*math.pi*(i+1)/n
        c0, s0 = math.cos(a0), math.sin(a0)
        c1, s1 = math.cos(a1), math.sin(a1)
        def P(r, c, s, along):
            if axis == "x": return [cx+along, cy+r*c, cz+r*s]
            if axis == "y": return [cx+r*c, cy+along, cz+r*s]
            return [cx+r*c, cy+r*s, cz+along]
        o00,o10 = P(r_out,c0,s0,0), P(r_out,c1,s1,0)
        o01,o11 = P(r_out,c0,s0,length), P(r_out,c1,s1,length)
        i00,i10 = P(r_in,c0,s0,0), P(r_in,c1,s1,0)
        i01,i11 = P(r_in,c0,s0,length), P(r_in,c1,s1,length)
        tris += [[o00,o01,o10],[o10,o01,o11],[i00,i10,i01],[i10,i11,i01],
                 [o00,o10,i00],[o10,i10,i00],[o01,i01,o11],[o11,i01,i11]]
    return np.array(tris, dtype=np.float64)


def _hole_y(cx, cy, cz, r, length, segments=12):
    """Solid cylinder used as drill guide / negative placeholder along Y.
    For FDM we keep as thin marker ring (annulus) the user drills out."""
    return _pipe(cx, cy, cz, r + 0.6*SCALE, r, length, axis="y", segments=segments)


def _combine(*parts):
    return np.vstack([p for p in parts if p is not None and len(p)])


def save_stl(folder: Path, name: str, tris: np.ndarray):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.stl"
    n = tris.shape[0]
    v0, v1, v2 = tris[:,0], tris[:,1], tris[:,2]
    normals = np.cross(v1 - v0, v2 - v0)
    lens = np.linalg.norm(normals, axis=1)
    lens[lens < 1e-12] = 1.0
    normals = normals / lens[:, None]
    with open(path, "wb") as f:
        hdr = f"AquaBot SCALE={SCALE}".encode()[:80]
        f.write(hdr + b"\0" * (80 - len(hdr)))
        f.write(struct.pack("<I", n))
        for i in range(n):
            f.write(struct.pack("<3f", *normals[i]))
            for j in range(3):
                f.write(struct.pack("<3f", *tris[i, j]))
            f.write(struct.pack("<H", 0))
    vol = abs(float(np.sum(v0 * np.cross(v1, v2)) / 6.0))
    print(f"  {path.name:44s} tris={n:5d}  vol≈{vol/1000:.1f} cm³")
    return path


# ========================= refined modules ==================================

def module_hull_base():
    """Hull with bow taper, deck ribs, cable gland, bilge drain boss, servo pad."""
    t = wall()
    hull_l, hull_w, hull_h = S(230), S(155), S(72)
    x0 = -hull_l/2 + S(5)
    y0 = -hull_w/2
    z0 = 0.0

    # main open-top shell
    shell = _hollow_box(x0, x0+hull_l, y0, y0+hull_w, z0, z0+hull_h, t, open_top=True)

    # bow taper wedges (two side fillets approximated as stepped blocks)
    bow_len = S(28)
    steps = 4
    bow_parts = []
    for i in range(steps):
        frac = (i + 1) / steps
        inset = (hull_w * 0.12) * frac
        bx0 = x0 + hull_l - bow_len + i * (bow_len / steps)
        bx1 = x0 + hull_l - bow_len + (i + 1) * (bow_len / steps)
        # left taper fill
        bow_parts.append(_box(bx0, bx1, y0 - S(2), y0 + inset, z0, z0 + hull_h * 0.85))
        # right taper fill
        bow_parts.append(_box(bx0, bx1, y0 + hull_w - inset, y0 + hull_w + S(2), z0, z0 + hull_h * 0.85))

    # deck ribs (longitudinal)
    ribs = []
    for yy in [y0 + hull_w*0.33, y0 + hull_w*0.67]:
        ribs.append(_box(x0 + t + S(8), x0 + hull_l - t - S(20),
                         yy - S(1.5), yy + S(1.5),
                         z0 + t, z0 + t + S(4)))

    # bilge drain boss (rear floor) — drill through after print
    drain = _cylinder(x0 + S(20), 0, z0, S(6), t + S(2), segments=16)

    # cable gland boss on port wall
    gland = _cylinder(x0 + hull_l*0.4, y0, z0 + hull_h*0.55, S(7), t + S(3), axis="y", segments=16)

    # side pontoon rails
    rail_w, rail_h = S(10), S(28)
    left_rail = _box(x0+S(15), x0+hull_l-S(15), y0-rail_w, y0, z0, z0+rail_h)
    right_rail = _box(x0+S(15), x0+hull_l-S(15), y0+hull_w, y0+hull_w+rail_w, z0, z0+rail_h)

    # MG996R dual-servo mount pad at front (two servos side by side for scoop)
    # MG996R body ≈ 40.7 × 19.7 × 42.9 mm; mounting ear hole spacing ≈ 10 mm on tab
    pad_x0 = x0 + hull_l - S(50)
    pad_z0 = z0 + hull_h - S(8)
    pad = _box(pad_x0, x0 + hull_l, y0 + S(20), y0 + hull_w - S(20), pad_z0, pad_z0 + S(14))

    # two MG996R footprints (solid pockets walls — cavity marked by inner floor)
    servo_parts = []
    for sy in [-S(22), S(22)]:
        # base plate under servo
        servo_parts.append(_box(
            pad_x0 + S(4), pad_x0 + S(4) + S(41),
            sy - S(10), sy + S(10),
            pad_z0 + S(2), pad_z0 + S(4),
        ))
        # mounting ear posts (4 per servo) — M3 drill centers
        # ear holes: ~2.5 mm, 10 mm apart on each tab; tabs at ends of 40.7 body
        for ex, ey in [
            (pad_x0 + S(4) + S(5), sy - S(10)),
            (pad_x0 + S(4) + S(5), sy + S(10)),
            (pad_x0 + S(4) + S(36), sy - S(10)),
            (pad_x0 + S(4) + S(36), sy + S(10)),
        ]:
            servo_parts.append(_cylinder(ex, ey, pad_z0 + S(2), S(3.5), S(8), segments=10))

    # floor M3 bosses
    bosses = []
    inset = S(18)
    for bx, by in [
        (x0+inset, y0+inset), (x0+hull_l-inset, y0+inset),
        (x0+inset, y0+hull_w-inset), (x0+hull_l-inset, y0+hull_w-inset),
    ]:
        bosses.append(_cylinder(bx, by, z0 + t, S(5), S(6), segments=14))

    # deck lip
    lip_w, lip_h = S(8), S(3)
    lips = [
        _box(x0+t, x0+hull_l-t, y0+t, y0+t+lip_w, z0+hull_h-lip_h, z0+hull_h),
        _box(x0+t, x0+hull_l-t, y0+hull_w-t-lip_w, y0+hull_w-t, z0+hull_h-lip_h, z0+hull_h),
        _box(x0+t, x0+t+lip_w, y0+t+lip_w, y0+hull_w-t-lip_w, z0+hull_h-lip_h, z0+hull_h),
        _box(x0+hull_l-t-lip_w, x0+hull_l-t, y0+t+lip_w, y0+hull_w-t-lip_w, z0+hull_h-lip_h, z0+hull_h),
    ]

    return _combine(shell, *bow_parts, *ribs, drain, gland, left_rail, right_rail,
                    pad, *servo_parts, *bosses, *lips)


def module_electronics_housing():
    """Open-bottom electronics box with lid screw bosses + camera turret."""
    t = wall()
    eh_l, eh_w, eh_h = S(88), S(68), S(30)
    x0, y0, z0 = -eh_l/2, -eh_w/2, 0.0
    shell = _hollow_box(x0, x0+eh_l, y0, y0+eh_w, z0, z0+eh_h, t, open_bottom=True)

    turret = _cylinder(S(12), 0, z0+eh_h, S(12), S(10), segments=24)
    gland = _cylinder(-eh_l/2, 0, z0+eh_h/2, S(6), t+S(2), axis="x", segments=16)

    # lid screw bosses (4 corners) — M3 heat-set insert friendly
    bosses = []
    for bx, by in [
        (x0+S(10), y0+S(10)), (x0+eh_l-S(10), y0+S(10)),
        (x0+S(10), y0+eh_w-S(10)), (x0+eh_l-S(10), y0+eh_w-S(10)),
    ]:
        bosses.append(_cylinder(bx, by, z0+eh_h-t-S(8), S(4.5), S(8), segments=12))

    # gasket shelf (inner rim under lid)
    shelf = S(2.5)
    shelves = [
        _box(x0+t, x0+eh_l-t, y0+t, y0+t+shelf, z0+eh_h-t-S(1.5), z0+eh_h-t),
        _box(x0+t, x0+eh_l-t, y0+eh_w-t-shelf, y0+eh_w-t, z0+eh_h-t-S(1.5), z0+eh_h-t),
        _box(x0+t, x0+t+shelf, y0+t+shelf, y0+eh_w-t-shelf, z0+eh_h-t-S(1.5), z0+eh_h-t),
        _box(x0+eh_l-t-shelf, x0+eh_l-t, y0+t+shelf, y0+eh_w-t-shelf, z0+eh_h-t-S(1.5), z0+eh_h-t),
    ]
    return _combine(shell, turret, gland, *bosses, *shelves)


def module_electronics_lid():
    """
    Waterproof lid: flat plate + perimeter gasket groove + 4× M3 clearance posts.
    Print groove-up; drop 1–2 mm silicone gasket or O-ring cord into groove.
    """
    t = wall()
    eh_l, eh_w = S(88), S(68)
    lid_t = max(S(3.0), t)
    # outer plate slightly larger than box OD for drip edge
    over = S(1.5)
    x0, y0 = -eh_l/2 - over, -eh_w/2 - over
    plate = _box(x0, x0+eh_l+2*over, y0, y0+eh_w+2*over, 0, lid_t)

    # gasket groove (rectangular channel) — 2 mm wide × 1.2 mm deep
    gw, gd = S(2.0), S(1.2)
    # groove sits where box wall meets lid
    gx0, gy0 = -eh_l/2 + wall()*0.3, -eh_w/2 + wall()*0.3
    gx1, gy1 = eh_l/2 - wall()*0.3, eh_w/2 - wall()*0.3
    # approximate groove as 4 thin slots cut by NOT removing — instead raise inner island
    # Inner island leaves a channel between outer rim and island
    inner = _box(gx0+gw, gx1-gw, gy0+gw, gy1-gw, lid_t - gd, lid_t + S(0.8))

    # M3 clearance posts (through holes → solid cylinders; drill 3.2 mm after print)
    posts = []
    for bx, by in [
        (-eh_l/2+S(10), -eh_w/2+S(10)), (eh_l/2-S(10), -eh_w/2+S(10)),
        (-eh_l/2+S(10), eh_w/2-S(10)), (eh_l/2-S(10), eh_w/2-S(10)),
    ]:
        posts.append(_cylinder(bx, by, 0, S(5), lid_t + S(1), segments=12))
        # smaller pilot core (drill target)
        posts.append(_cylinder(bx, by, S(0.5), S(1.4), lid_t, segments=10))

    # handle rib
    handle = _box(-S(15), S(15), -S(3), S(3), lid_t, lid_t + S(4))
    return _combine(plate, inner, *posts, handle)


def module_trash_bin():
    t = wall()
    bin_l, bin_w, bin_h = S(68), S(100), S(52)
    x0, y0, z0 = 0.0, -bin_w/2, 0.0
    shell = _hollow_box(x0, x0+bin_l, y0, y0+bin_w, z0, z0+bin_h, t, open_top=True)
    ribs = []
    for i in range(1, 4):
        ry = y0 + t + i*(bin_w-2*t)/4
        ribs.append(_box(x0+t, x0+bin_l-t, ry-S(1.2), ry+S(1.2), z0+t, z0+t+S(3)))
    hinge = _box(x0+bin_l-S(10), x0+bin_l, y0+S(12), y0+bin_w-S(12),
                 z0+bin_h-S(4), z0+bin_h+S(4))
    return _combine(shell, *ribs, hinge)


def module_scoop_arm():
    """Scoop arm with MG996R horn clearance and pivot bosses (M3)."""
    arm_len, t, arm_h, span = S(95), S(6), S(8), S(108)
    y_l, y_r = -span/2, span/2 - t
    left = _box(0, arm_len, y_l, y_l+t, 0, arm_h)
    right = _box(0, arm_len, y_r, y_r+t, 0, arm_h)
    cross1 = _box(S(12), S(12)+t, y_l, y_r+t, 0, arm_h)
    cross2 = _box(arm_len-S(22), arm_len-S(22)+t, y_l, y_r+t, 0, arm_h)

    net_l, rim = S(50), S(4)
    nx0 = arm_len - net_l - S(4)
    ny0, ny1 = y_l+S(4), y_r+t-S(4)
    rims = [
        _box(nx0, nx0+net_l, ny0, ny0+rim, 0, arm_h*0.7),
        _box(nx0, nx0+net_l, ny1-rim, ny1, 0, arm_h*0.7),
        _box(nx0, nx0+rim, ny0, ny1, 0, arm_h*0.7),
        _box(nx0+net_l-rim, nx0+net_l, ny0, ny1, 0, arm_h*0.7),
    ]
    # pivot bosses — drill M3 after print
    pl = _cylinder(S(6), y_l+t/2, arm_h/2, S(7), t, axis="y", segments=16)
    pr = _cylinder(S(6), y_r+t/2, arm_h/2, S(7), t, axis="y", segments=16)
    # servo horn link tab near pivot
    horn = _box(S(10), S(28), -S(4), S(4), arm_h, arm_h+S(3))
    return _combine(left, right, cross1, cross2, *rims, pl, pr, horn)


def module_scoop_roller():
    return _cylinder(0, 0, 0, S(9), S(95), axis="y", segments=28)


def module_thruster_duct():
    """
    Duct + flange + BLDC mount.
    Standard small BLDC cross pattern: 16 mm and 19 mm hole spacings (M3).
    """
    t = wall()
    r_out = S(22)
    r_in = r_out - t
    length = S(30)
    duct = _pipe(0, 0, 0, r_out, r_in, length, axis="z", segments=32)

    fl = r_out + S(8)
    flange = _box(-fl, fl, -fl, fl, -S(3), 0)

    # flange M3 corner holes (drill guides)
    rings = []
    for sx, sy in [(-fl+S(6),-fl+S(6)),(fl-S(6),-fl+S(6)),
                   (-fl+S(6),fl-S(6)),(fl-S(6),fl-S(6))]:
        rings.append(_cylinder(sx, sy, -S(3), S(3.5), S(3), segments=12))

    # BLDC mount plate inside duct (thin cross + ring)
    # 16 mm and 19 mm diagonal patterns common on 2204–2207 motors
    mount_z = S(4)
    mount_ring = _pipe(0, 0, mount_z, S(12), S(5), S(2.5), axis="z", segments=24)
    # 16 mm square pattern (half-spacing 8 mm)
    bldc = []
    for pitch, rr in [(S(16), S(3.0)), (S(19), S(2.8))]:
        h = pitch / 2
        for sx, sy in [(-h, -h), (h, -h), (-h, h), (h, h)]:
            bldc.append(_cylinder(sx, sy, mount_z, rr, S(2.5), segments=10))

    # stator vanes
    vt = max(S(1.6), 1.2)
    v1 = _box(-r_in, r_in, -vt/2, vt/2, S(2), length - S(2))
    v2 = _box(-vt/2, vt/2, -r_in, r_in, S(2), length - S(2))

    return _combine(duct, flange, *rings, mount_ring, *bldc, v1, v2)


def module_antenna_mast():
    base = _cylinder(0, 0, 0, S(8), S(3), segments=20)
    mast = _cylinder(0, 0, S(3), S(2.8), S(45), segments=16)
    tip = _cylinder(0, 0, S(48), S(4.5), S(4), segments=12)
    return _combine(base, mast, tip)


def module_assembly_reference():
    L, W = S(300), S(174)
    hull = module_hull_base()
    eh = module_electronics_housing().copy(); eh[:,:,0]+=S(15); eh[:,:,2]+=S(72)
    lid = module_electronics_lid().copy(); lid[:,:,0]+=S(15); lid[:,:,2]+=S(72)+S(30)
    tb = module_trash_bin().copy(); tb[:,:,0]+= -L/2+S(8); tb[:,:,2]+=S(6)
    arm = module_scoop_arm().copy(); arm[:,:,0]+= L/2-S(50); arm[:,:,2]+=S(40)
    roller = module_scoop_roller().copy()
    roller[:,:,0]+= L/2-S(20); roller[:,:,1]-=S(47.5); roller[:,:,2]+=S(44)
    def duct(ys):
        d = module_thruster_duct().copy()
        d[:,:,0]+= -S(40); d[:,:,1]+= ys*(W*0.38); d[:,:,2]+=S(15)
        return d
    ant = module_antenna_mast().copy()
    ant[:,:,0]+=S(25); ant[:,:,1]+=S(20); ant[:,:,2]+=S(102)
    return _combine(hull, eh, lid, tb, arm, roller, duct(-1), duct(1), ant)


def build_scale(scale: float, folder_name: str):
    global SCALE
    SCALE = scale
    folder = OUT_ROOT / folder_name
    tag = f"SCALE={scale}"
    print(f"\n=== {tag}  wall={wall():.1f} mm  → {folder} ===")
    parts = [
        ("01_hull_base", module_hull_base),
        ("02_electronics_housing", module_electronics_housing),
        ("02b_electronics_lid_waterproof", module_electronics_lid),
        ("03_trash_bin", module_trash_bin),
        ("04_scoop_arm", module_scoop_arm),
        ("05_scoop_roller", module_scoop_roller),
        ("06_thruster_duct", module_thruster_duct),
        ("07_antenna_mast", module_antenna_mast),
        ("00_assembly_reference", module_assembly_reference),
    ]
    for name, fn in parts:
        save_stl(folder, name, fn())


def build_all():
    build_scale(1.0, "stl_poc")
    build_scale(4.0, "stl_fullsize")
    (OUT_ROOT / "README.md").write_text("""# AquaBot ARB-2026 — Refined Print Modules

## Folders
| Folder | Scale | Overall size |
|--------|-------|----------------|
| `stl_poc/` | 1.0 | 30 × 17.4 × 10.7 cm (proof of concept) |
| `stl_fullsize/` | 4.0 | 120 × 69.6 × 42.8 cm (prototype) |

Wall thickness: 2.4 mm (POC) · capped at 4.0 mm (full-size)

## New / refined features
- **Hull:** bow taper, deck ribs, bilge drain boss, cable gland, dual **MG996R** mount pad
- **Thruster duct:** **BLDC** 16 mm + 19 mm M3 patterns, flange holes, vanes
- **Electronics lid:** waterproof plate with **gasket groove** + M3 posts
- **Scoop arm:** pivot bosses + servo horn tab

## Print notes
- PETG/ABS for water trials; PLA for dry fit
- 0.4 mm nozzle · 0.20 mm layers (0.12 mm ducts)
- ≥3 perimeters · brim on hull/arm
- **Full-size hull** will exceed most beds — split in slicer or print POC first
- Drill M3 (3.2 mm) at marked bosses after printing
- Seat 1–2 mm silicone cord in lid groove before screwing down

## Parts list (each folder)
1. `01_hull_base.stl`
2. `02_electronics_housing.stl`
3. `02b_electronics_lid_waterproof.stl`
4. `03_trash_bin.stl`
5. `04_scoop_arm.stl`
6. `05_scoop_roller.stl`
7. `06_thruster_duct.stl` — print **2×**
8. `07_antenna_mast.stl`
9. `00_assembly_reference.stl` — fit-check only
""", encoding="utf-8")
    print("\nAll scales done.")


if __name__ == "__main__":
    build_all()
