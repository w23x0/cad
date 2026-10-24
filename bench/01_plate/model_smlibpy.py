from smlibpy import Box, Cylinder, Location, Locations

result = Box(80, 60, 10)
result -= Locations((-30, -20, 0), (30, -20, 0), (-30, 20, 0), (30, 20, 0)) * Cylinder(4, 12)
result -= Location((0, 0, 3)) * Box(30, 20, 4)
