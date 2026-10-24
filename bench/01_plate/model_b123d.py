from build123d import Box, Cylinder, Pos

result = Box(80, 60, 10)
for x, y in [(-30, -20), (30, -20), (-30, 20), (30, 20)]:
    result -= Pos(x, y, 0) * Cylinder(4, 12)
result -= Pos(0, 0, 3) * Box(30, 20, 4)
