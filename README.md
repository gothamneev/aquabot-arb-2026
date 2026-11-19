# AquaBot ARB-2026 — Refined Print Modules

Print-ready CAD for the Robofest Gujarat surface trash-collecting USV.

## Folders

| Folder | Scale | Overall size |
|--------|-------|----------------|
| `stl_poc/` | 1.0 | 30 × 17.4 × 10.7 cm (proof of concept) |
| `stl_fullsize/` | 4.0 | 120 × 69.6 × 42.8 cm (prototype) |

Wall thickness: 2.4 mm (POC), capped at 4.0 mm (full-size).

STL files are ASCII so they open in Cura, PrusaSlicer, Bambu Studio, and MeshLab.

## Features

- Hull with bow taper, deck ribs, bilge drain boss, cable gland, dual MG996R mount pad
- Thruster duct with BLDC 16 mm and 19 mm M3 patterns, flange holes, and vanes
- Waterproof electronics lid with gasket groove and M3 posts
- Scoop arm with pivot bosses and servo horn tab

## Print notes

- PETG or ABS for water trials; PLA for dry fit
- 0.4 mm nozzle, 0.20 mm layers (0.12 mm for the duct)
- At least 3 perimeters, brim on the hull and arm
- Full-size hull will exceed most beds — split in the slicer or print the POC first
- Drill M3 (3.2 mm) at marked bosses after printing
- Seat 1–2 mm silicone cord in the lid groove before screwing the lid down
- Print `06_thruster_duct.stl` twice
- `00_assembly_reference.stl` is a fit-check only — do not print it as one piece

## Regenerate

```bash
pip install numpy
python3 aquabot_modules.py
```

Outputs land in `stl_poc/` and `stl_fullsize/`.
