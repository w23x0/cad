from smlibpy import Box, Pos, Sphere

result = Box(100, 60, 10)
result -= Sphere(8).moved(Pos(-30, 0, 5))
result -= Sphere(6).moved(Pos(0, -12, 5))
result -= Sphere(5).moved(Pos(10, 14, 5))
