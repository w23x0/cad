from build123d import Box, Cylinder, chamfer

P = Box(80, 40, 10) - Cylinder(10, 30)
rim = [e for e in P.edges() if e.geom_type.name == "CIRCLE" and abs(e.center().Z - 5) < 1e-9]
result = chamfer(rim, 2)
