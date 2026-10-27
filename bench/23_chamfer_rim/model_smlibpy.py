from smlibpy import Box, Cylinder

P = Box(80, 40, 10) - Cylinder(10, 30)
rim = [e for e in P.edges() if e.geom_type == "circle" and abs(e.center().z - 5) < 1e-9]
result = P.chamfer(rim, 2)
