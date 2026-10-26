from build123d import Box, Cone, Pos

result = Box(80, 40, 10) - Pos(0, 0, 5) * Cone(4, 9, 10)
