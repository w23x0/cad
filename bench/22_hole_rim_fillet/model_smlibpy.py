from smlibpy import Box, Cylinder, Pos

P = Box(80, 40, 10) - Cylinder(10, 30).moved(Pos(0, 0, 0))
rim = [e for e in P.edges() if e.geom_type == "circle" and abs(e.center().z - 5) < 1e-9]
result = P.fillet(rim, 2)
