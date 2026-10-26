from build123d import Box, Cylinder, Pos, Rot

outer = Pos(0, 0, 20) * Box(90, 60, 40)
result = outer - Pos(0, 0, 21) * Box(86, 56, 38)
result += Pos(0, 0, 21) * Box(86, 2, 38)
result -= Pos(30, 30, 12) * Rot(90, 0, 0) * Cylinder(5, 30)
