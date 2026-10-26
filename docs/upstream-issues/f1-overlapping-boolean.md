## [0.3.3 & 0.5.0] Booleans between non-piercing overlapping solids: wrong results (containment misclassification)

**Versions**: smlibpy 0.3.3 and 0.5.0 (PyPI manylinux wheels), different wrong answers.
**Arbitration**: 200M-point Monte-Carlo on analytic membership (no kernel involved,
±1 mm³) and build123d/OCCT agrees with the analytic value bit-exactly.

### Repro

```python
import math
from smlibpy import Cylinder, Torus, Pos

A = Cylinder(20, 8)                      # 10053.096491487338 = 3200*pi
T = Torus(20, 2).moved(Pos(0, 0, 4))     # center circle exactly on the cylinder wall

print((A + T).volume)  # 0.3.3: 1579.1367041742974 (= T alone, 1 face)
                       # 0.5.0: 11254.2038 (correct + 378.0286 = half the overlap)
print((A & T).volume)  # 0.3.3: 10053.09649148734 (= A alone)
                       # 0.5.0: 378.0290 (= exactly half of the true 756.0580)
print((A - T).volume)  # 0.3.3: 0.0, 0 faces, is_valid() False, NO exception
```

Truth: A∪T = 10876.1752, A∩T = 756.0580 (Pappus on the inner half-disk:
2π·(20 − 8/(3π))·2π), A−T = 9297.0385.

The 0.3.3 triple (union = tool, intersect = base, cut = empty) is exactly what
"kernel believes T contains A" produces — the containment/intersection
classification between curved solids appears inverted. 0.5.0 computes but
systematically counts half the inner overlap region.

### Related modes (both versions unless noted)

- `Cylinder(20,8) + Cylinder(5,4)` fully nested: +157.0796 phantom (= half the tool).
- `A + Torus(10,2)` fully inside A: whole torus added back on 0.3.3 (2 overlapping
  solids), half of it on 0.5.0.
- `A + Sphere(8)` half-embedded at the top face: exact on 0.3.3, **regressed** on
  0.5.0 (+737.23).
- `A + Torus(10,2)@(25,0,4)` (off-axis crossing): hangs > 150 s on 0.3.3.
- 3-cell part fused with a non-piercing tool: a whole cell silently evaporates
  (6.327 mm³, scales with the model).

### Verified-safe paths (exact on both 0.3.3 and vs OCCT)

piercing cuts (tool extends past the faces), face-contact fuses, disjoint fuses,
coaxial through-cuts.

Full analysis with Monte-Carlo numbers: available on request; benchmark parts and
a two-kernel verification harness that reproduces all of the above live in
this workspace.
