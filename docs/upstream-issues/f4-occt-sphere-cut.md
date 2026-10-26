## [build123d 0.13 / OCCT] Sphere minus cylinder returns a zero-volume invalid shell

Cross-posted here because smlibpy computes the exact answer; primary target:
build123d repo.

### Repro

```python
from build123d import Cylinder, Pos, Rot, Sphere
from smlibpy import Cylinder as SmCylinder, Pos as SmPos, Rot as SmRot, Sphere as SmSphere

tool = Pos(-1.86, 0, -2.73) * Rot(0, 90, 0) * Cylinder(9, 13)
b = Sphere(6) - tool
print(b.volume, b.is_valid)   # -0.0 (or 0.0) False  <-- OCCT: empty invalid shell

s = SmSphere(6) - SmPos(-1.86, 0, -2.73) * SmRot(0, 90, 0) * SmCylinder(9, 13)
print(s.volume, s.is_valid()) # 32.2299 True  <-- exact
```

Analytic truth: the cylinder wall does not reach the sphere; only the flat end
faces cut two spherical caps. Removed volume = π·h²(3R−h)/3 with the cap heights
read off the geometry → remaining volume **32.2299 mm³**, which smlibpy returns
exactly and OCCT collapses to an empty shell (found by a seeded CSG fuzzer,
case reproducible deterministically).

Expected: a valid solid (or a raised error), never a silent 0-volume shell.
