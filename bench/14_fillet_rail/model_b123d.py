from build123d import Axis, Box, fillet

B = Box(80, 40, 10)
edges = [e for e in B.edges().filter_by(Axis.X) if abs(e.center().Z) == 5]
result = fillet(edges, 4)
