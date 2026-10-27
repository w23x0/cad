from smlibpy import Cone, Cylinder, Plane, Pos, Sphere

# Probe: Cone(bottom_r, top_r, h) -> big end up = Cone(8, 20, 12) shifted down 6.
result = Cone(8, 20, 12).moved(Pos(0, 0, -6))     # hopper, z -12..0
result += Cylinder(20, 30).moved(Pos(0, 0, 15))   # shell, z 0..30
# Dome: move the sphere to (0,0,30) BEFORE splitting (unmoved sphere + z=30 plane
# raises ModelingError "nothing lies above"; see 21_dome for the split pattern).
result += Sphere(20).moved(Pos(0, 0, 30)).split(Plane.XY.offset(30), keep="above")
