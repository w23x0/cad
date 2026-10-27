from smlibpy import Box, Pos

base = Box(80, 40, 10) + Box(20, 20, 10).moved(Pos(0, 0, 10))  # boss contact-fused onto top face
result = base + Box(30, 30, 6).moved(Pos(0, 0, 21))  # cover floating 3 mm above, disjoint
