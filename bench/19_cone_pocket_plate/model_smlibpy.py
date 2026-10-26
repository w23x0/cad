from smlibpy import Box, Cone, Pos

result = Box(80, 40, 10) - Cone(4, 9, 10).moved(Pos(0, 0, 5))
