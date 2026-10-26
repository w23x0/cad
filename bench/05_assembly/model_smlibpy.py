from smlibpy import Box, Cylinder, Pos

plate = Box(80, 50, 8).moved(Pos(0, 0, 4))
shaft = Cylinder(8, 40).moved(Pos(20, 0, 29))
collar = (Cylinder(12, 10) - Cylinder(8.2, 12)).moved(Pos(20, 0, 35))
boss = Box(12, 12, 10).moved(Pos(-25, 15, 14))
result = plate + shaft + collar + boss
