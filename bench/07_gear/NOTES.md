# 07 gear

Simplified spur gear: root disk + 12 straight-flank trapezoidal teeth (polar pattern) +
centre bore. No involute on purpose: an involute needs a spline approximation whose control
points are not equivalent across kernels; straight lines and circular arcs are exact in both,
which is what both models use (circles + lines + booleans only).

## Design
- N = 12, r_root = 20, r_tip = 26, tooth half-width 10 deg at the root tapering to 6 deg at
  the tip (straight flanks in the transverse plane), height h = 10 (z -5..5), bore r = 6.
- Overlap check: full width at tip 12 deg * 12 = 144 < 360 (at root 240 < 360).
- Each tooth blank extends inward to r = 18 (the flank lines are intersected with that
  circle) so the tooth overlaps the root disk transversally - no coincident-face fuse. The
  visible flank endpoints stay (20, +-10 deg) and (26, +-6 deg); the part inside the root
  disk is absorbed by the fuse. Even the extended teeth (23.9 deg full width at r = 18)
  stay clear of each other.
- bbox 52 x 52 x 10.

## Volume (hand-derived, surveyor/Green formula)
One tooth outside the root circle is bounded by the root arc r1 = 20 (half-width t1),
a straight flank, the tip arc r2 = 26 (half-width t2) and the mirrored flank. With
A = 1/2 * contour integral of (x dy - y dx) (arc contributes r^2 * dtheta, a chord P->Q
contributes the cross product x_P*y_Q - y_P*x_Q):

    A_tooth = r1*r2*sin(t1 - t2) + t2*r2^2 - t1*r1^2
            = 520*sin(4 deg) + 676*pi/30 - 400*pi/18 = 37.25075072806197 mm^2

Sanity: for radial flanks (t1 = t2) this reduces to t*(r2^2 - r1^2), the annular sector area.

    V = (pi*r1^2 + N*A_tooth)*h - pi*r_bore^2*h
      = 3640*pi + 120*A_tooth = 11032*pi/3 + 62400*sin(4 deg) = 15905.487346434285 mm^3

## 质心手算

质心：轴对称且 z 对称（Cylinder 与 both=True 挤出均居中）→ (0,0,0)。
