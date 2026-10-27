from smlibpy import Box, Cylinder, Pos, Sphere

result = Box(40, 40, 30) - Sphere(8).moved(Pos(6, -5, 1)) - Cylinder(4, 40).moved(Pos(-10, 8, 0))
