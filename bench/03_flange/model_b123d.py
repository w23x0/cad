from build123d import Cylinder, Pos, Rot

result = Cylinder(30, 10) - Cylinder(10, 12)
for i in range(6):
    result -= Rot(0, 0, i * 60) * Pos(23, 0, 0) * Cylinder(3, 12)
