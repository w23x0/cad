from build123d import Box, Pos, Sphere

result = Box(100, 60, 10)
result -= Pos(-30, 0, 5) * Sphere(8)
result -= Pos(0, -12, 5) * Sphere(6)
result -= Pos(10, 14, 5) * Sphere(5)
