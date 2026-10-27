from build123d import Box, Pos

base = Box(80, 40, 10) + Pos(0, 0, 10) * Box(20, 20, 10)  # boss contact-fused onto top face
result = base + Pos(0, 0, 21) * Box(30, 30, 6)  # cover floating 3 mm above, disjoint
