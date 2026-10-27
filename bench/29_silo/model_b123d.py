from build123d import Cone, Cylinder, Keep, Plane, Pos, Sphere, split

# Probe: both kernels Cone(bottom_r, top_r, h) centered -> big end up = Cone(8, 20, 12) shifted down 6.
result = Pos(0, 0, -6) * Cone(8, 20, 12)          # hopper, z -12..0
result += Pos(0, 0, 15) * Cylinder(20, 30)        # shell, z 0..30
# Dome: move the sphere to (0,0,30) BEFORE splitting (unmoved sphere + z=30 plane
# gives a silent empty shell here; see 21_dome for the split pattern).
result += split(Pos(0, 0, 30) * Sphere(20), bisect_by=Plane.XY.offset(30), keep=Keep.TOP)
