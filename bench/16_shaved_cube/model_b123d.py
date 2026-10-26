from build123d import Box, Cylinder, Keep, Plane, Pos, split

B = Box(40, 40, 40)
B = split(B, bisect_by=Plane(origin=(30, 0, 0), z_dir=(1, 0, 1)), keep=Keep.BOTTOM)
result = B - Pos(0, 0, 0) * Cylinder(5, 60)
