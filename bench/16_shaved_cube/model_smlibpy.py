from smlibpy import Box, Cylinder, Plane, Pos

B = Box(40, 40, 40)
B = B.split(Plane(origin=(30, 0, 0), z_dir=(1, 0, 1)), keep="below")
result = B - Cylinder(5, 60).moved(Pos(0, 0, 0))
