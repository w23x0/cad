from smlibpy import Box, Pos, Sphere, Torus

result = Box(40, 40, 30)
result -= Sphere(9).moved(Pos(-10, 0, 0))
result -= Torus(6, 2).moved(Pos(10, 0, 0))
