from build123d import Circle, Pos, extrude

result = extrude(Pos(0, 0, 0) * (Circle(10) - Circle(5)), 10, taper=5)
