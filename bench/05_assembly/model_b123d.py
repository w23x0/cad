from build123d import Box, Cylinder, Pos

plate = Pos(0, 0, 4) * Box(80, 50, 8)
shaft = Pos(20, 0, 29) * Cylinder(8, 40)
collar = Pos(20, 0, 35) * (Cylinder(12, 10) - Cylinder(8.2, 12))
boss = Pos(-25, 15, 14) * Box(12, 12, 10)
result = plate + shaft + collar + boss
