from smlibpy import Box, X

B = Box(80, 40, 10)
edges = [e for e in B.edges().parallel_to(X) if abs(e.center().z) == 5]
result = B.fillet(edges, 4)
