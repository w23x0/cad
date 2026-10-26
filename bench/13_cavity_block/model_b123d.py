from build123d import Box, Pos, Sphere, Torus

result = Box(40, 40, 30)
result -= Pos(-10, 0, 0) * Sphere(9)
result -= Pos(10, 0, 0) * Torus(6, 2)
