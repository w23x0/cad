from smlibpy import Cylinder, PolarLocations

result = Cylinder(30, 10) - Cylinder(10, 12)
result -= PolarLocations(23, 6) * Cylinder(3, 12)
