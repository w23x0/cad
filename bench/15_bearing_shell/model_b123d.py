from build123d import Box, Cylinder, Keep, Plane, Pos, split

B = Box(60, 40, 20) - Pos(0, 0, 0) * Cylinder(6, 60)
result = split(B, bisect_by=Plane.XZ, keep=Keep.TOP)
