from build123d import Cylinder, Polyline, Pos, extrude, make_face

profile = Polyline(
    (0, 0), (60, 0), (60, 10), (10, 10), (10, 50), (0, 50), close=True
)
result = extrude(make_face(profile), 40)
result -= Pos(30, 5, 20) * Cylinder(4, 60)
result -= Pos(5, 30, 20) * Cylinder(4, 60)
