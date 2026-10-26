# 06 thread

Simplified screw stock: a cylinder with 5 stacked annular V-grooves. Both kernels build the
identical revolve-based geometry (no helix anywhere).

## Design
- Cylinder R = 12, L = 24 (z -12..12) -> bbox 24 x 24 x 24.
- 5 annular V-grooves centred at z = -8, -4, 0, +4, +8 (spacing 4 mm > groove width, no overlap).
- Cutter profile drawn in the axial half-plane (Plane.XZ / Plane.front, x = radius, y = height):
  triangle with apex (10, zc) and base (13, zc +- 1.5) - 2 mm deep below the surface, base
  width 3. The base sits 1 mm outside the cylinder so the boolean is purely transversal
  (cutter-overshoot style of 03_flange). The groove actually cut into the material has apex
  (10, zc) and mouth (12, zc +- 1).

## Why not a real helical thread (demotion recorded per plan)
The primary plan (cylinder minus a rigid helical sweep of the triangle, truth V = Theta*rbar*A)
is not reachable at 1e-6:
- smlibpy's documented sweep along a Helix places the profile perpendicular to the path
  (tilted by the helix angle, not kept in the axial half-plane) and rolls it about the path;
  its own workaround (loft through placed copies) is only ~1e-4 exact.
- Measured tube volumes for the intended sweep (this triangle, 3 turns, lead 8; the rigid
  helical value would be Theta*rbar*A = 6*pi*34 = 640.885):
  build123d sweep(binormal=Axis.Z) -> 991.083, smlibpy sweep -> 998.020. Neither matches the
  rigid-helical value and the two kernels disagree with each other by ~0.7%.
Since expected.json is shared, both kernels build the demoted stacked-ring geometry, where
every surface is a plane, a cone or a cylinder - exact in both kernels.

## Volume (Pappus, hand-derived)
Effective removed profile per groove: triangle apex (10, zc), base corners (12, zc +- 1):
A' = 1/2 * 2 * 2 = 2, centroid radius rbar' = (10 + 12 + 12)/3 = 34/3 (triangle centroid).
Per groove V_g = 2*pi*A'*rbar' = 136*pi/3; total removed = 5 * 136*pi/3 = 680*pi/3.

V = pi*12^2*24 - 680*pi/3 = (10368 - 680)/3 * pi = 9688*pi/3 = 10145.249875992638 mm^3

## 质心手算

质心：轴对称且槽位关于 z=0 对称 → (0,0,0)。
