from build123d import Keep, Plane, Sphere, split

result = split(Sphere(15), bisect_by=Plane.XY.offset(5), keep=Keep.BOTTOM)
