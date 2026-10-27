from build123d import Box, Cylinder, Pos, Sphere

result = Box(40, 40, 30) - Pos(6, -5, 1) * Sphere(8) - Pos(-10, 8, 0) * Cylinder(4, 40)
