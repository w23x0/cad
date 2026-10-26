from build123d import Cone, Cylinder, PolarLocations, Pos, Sphere, Torus

result = Pos(0, 0, 4) * Cylinder(20, 8)
result += Pos(0, 0, 14) * Cone(12, 9, 12)
result += Pos(0, 0, 20) * Sphere(8)
result += Pos(34, 0, 2) * Torus(10, 2)
result -= Pos(0, 0, 4) * (PolarLocations(15, 4) * Cylinder(2, 10))
