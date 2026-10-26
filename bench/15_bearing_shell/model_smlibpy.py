from smlibpy import Box, Cylinder, Plane, Pos

B = Box(60, 40, 20) - Cylinder(6, 60).moved(Pos(0, 0, 0))
result = B.split(Plane.XZ, keep="above")
