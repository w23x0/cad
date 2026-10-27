from build123d import Box, Cylinder, Pos

P = Box(80, 40, 10) - Pos(0, 0, 0) * Cylinder(10, 30)
rim = [e for e in P.edges() if e.geom_type.name == "CIRCLE" and abs(e.center().Z - 5) < 1e-9]
result = P.fillet(2, rim)
