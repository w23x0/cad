# bench — golden parts

Every subfolder is a "golden part": the same design intent implemented on two
independent kernels. Metrics must match `expected.json` **and** each other.

| Part | Exercises | Volume mm³ |
|---|---|---|
| `01_plate` | boolean cuts, 4-hole pattern, blind pocket, bbox | 43589.3807 |
| `02_l_bracket` | closed polyline → face → extrude → holes | 35978.7614 |
| `03_flange` | revolved solid, centre bore, polar pattern | 23436.2812 |
| `04_thin_wall` | thin walls via boolean (outer − cavity), internal web, side through-hole | 39370.9204 |
| `05_assembly` | multi-solid exploded assembly (4 solids), clearance collar, additive volume | 43893.9637 |
| `06_thread` | revolved V-grooves (Pappus truth); helical-sweep parity investigated | 10145.2499 |
| `07_gear` | simplified straight-flank gear, polar pattern of lines+arcs, exact tooth-area integral | 15905.4873 |
| `08_knob` | cone frustum + hemisphere stack, axial hole pattern, disjoint O-ring torus (2 solids) | 15697.4727 |
| `09_loft_transition` | ruled loft square→rectangle, corner-matched, prismatoid truth | 17066.6667 |
| `10_chamfer_block` | chamfer on 4 vertical edges, property-based edge selection | 47360.0000 |
| `11_sector_ring` | 300° partial revolve (C-ring), angle-scaled Pappus + sector centroid | 7853.9816 |
| `12_dimple_plate` | hemisphere dimple cuts (sphere centered on face), asymmetric truth | 58213.4810 |

## Adding a part

1. Create `bench/NN_name/`.
2. Write `NOTES.md` with dimensions and the **hand-computed** volume.
3. Write `model_b123d.py` and `model_smlibpy.py`, both assigning `result`.
4. Run the verifier; once both kernels agree, put the hand value in `expected.json`.

`expected.json` must contain the hand calculation, never a value copied from a
run — otherwise the test only proves self-consistency.

## Why two kernels

A single kernel can be wrong in ways that still look valid. Two independent
implementations (OCCT vs SMLib) agreeing on volume, bbox, solid count and
validity makes that much less likely. A disagreement is either a kernel bug or
an ambiguous design — both worth finding before export.

This set doubles as an objective scoreboard: change a model, a prompt, or a
kernel, rerun it, and regressions show up immediately.

## Current status

12 parts, 24 implementations, all passing with relative error < 1e-6 (max observed
~9e-9 except `11_sector_ring` smlibpy partial revolve at 4.5e-7 — still within
contract, no tolerance loosened anywhere).

## Kernel findings

Kernel-level divergences are documented in [`../FINDINGS.md`](../FINDINGS.md)
(smlibpy overlapping-union bug with Monte-Carlo arbitration, helical-sweep
non-parity). Summary:

- **Helical sweeps are not kernel-portable.** The same rigid-helical sweep intent
  (axial triangular profile, `binormal=Axis.Z` on the OCCT side) differs by ~0.7%
  between kernels, and smlibpy's sweep reorients the profile perpendicular to the
  path. That is why `06_thread` uses revolved V-grooves with a Pappus-theorem
  truth instead of a real helix.
- **smlibpy overlapping booleans are unreliable** (F-1): union/cut/intersect of
  non-piercing overlapping solids return wrong results on 0.3.3 AND 0.5.0.
  Bench parts therefore stick to the verified-safe paths: piercing cuts,
  face-contact fuses, disjoint fuses. `08_knob` was redesigned v1→v2 for this.
- **Touching solids fuse identically on both kernels.** In `05_assembly`, parts
  in face contact merge into one solid (solids 2, same volume); the final design
  uses explicit gaps so the part really exercises multi-solid handling.
