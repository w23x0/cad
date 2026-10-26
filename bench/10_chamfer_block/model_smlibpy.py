from smlibpy import Box, Z

B = Box(60, 40, 20)
result = B.chamfer(B.edges().parallel_to(Z), 4)
