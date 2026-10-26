from build123d import Plane, Pos, Rectangle, extrude

result = extrude(Pos(0, 0, 0) * Rectangle(40, 30), 20, taper=10)
