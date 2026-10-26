## [build123d 0.13] sweep() with a misplaced profile silently returns an empty shell

Cross-post: primary target build123d; smlibpy's behavior documented for contrast.

### Repro

```python
from build123d import CenterArc, Circle, sweep

arc = CenterArc((0, 0), 20, 0, 270)
S = sweep(Circle(5), arc)          # profile NOT placed at the path start
print(S.volume, len(S.faces()), S.is_valid)   # 0.0 1 True  <-- silent empty shell
```

`sweep(Pos(20,0,0) * Rot(90,0,0) * Circle(5), arc)` (profile at the path start,
perpendicular to the start tangent) returns the correct three-quarter torus,
volume 750π² = 7402.203300817018, 3 faces — bit-identical to smlibpy's
auto-placed result. So the geometry kernel is fine; the failure is a silent
empty instead of either auto-placement (smlibpy semantics) or a raised error.

Expected: raise (or auto-place) instead of a valid-looking empty shell.
