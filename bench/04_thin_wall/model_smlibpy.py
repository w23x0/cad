from smlibpy import Box, Cylinder, Pos, Rot

outer = Box(90, 60, 40).moved(Pos(0, 0, 20))
result = outer - Box(86, 56, 38).moved(Pos(0, 0, 21))
result += Box(86, 2, 38).moved(Pos(0, 0, 21))
hole = Cylinder(5, 30).moved(Rot(90, 0, 0)).moved(Pos(30, 30, 12))
result -= hole
