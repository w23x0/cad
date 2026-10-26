from smlibpy import Cone, Cylinder, PolarLocations, Pos, Sphere, Torus

result = Cylinder(20, 8).moved(Pos(0, 0, 4))
result += Cone(12, 9, 12).moved(Pos(0, 0, 14))
result += Sphere(8).moved(Pos(0, 0, 20))
result += Torus(10, 2).moved(Pos(34, 0, 2))
result -= PolarLocations(15, 4) * Cylinder(2, 10).moved(Pos(0, 0, 4))
