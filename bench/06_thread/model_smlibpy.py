from smlibpy import Cylinder, Plane, Polygon, Z, revolve

# Cylinder minus 5 stacked annular V-grooves.
# Cutter triangle on Plane.front (= XZ: local x = radius, local y = height):
# apex (10, zc), base (13, zc +- 1.5) - base 1 mm outside the surface for a transversal cut.
result = Cylinder(12, 24)
for zc in (-8, -4, 0, 4, 8):
    tri = Polygon((13, zc - 1.5), (13, zc + 1.5), (10, zc)).on(Plane.front)
    result -= revolve(tri, Z)
