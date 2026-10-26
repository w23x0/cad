from build123d import CenterArc, Circle, Pos, Rot, sweep

arc = CenterArc((0, 0), 20, 0, 270)
# F-9: build123d needs the profile at the path start, perpendicular to the
# start tangent (+Y here, so the section lies in XZ) - otherwise it silently
# returns an empty shell.
result = sweep(Pos(20, 0, 0) * Rot(90, 0, 0) * Circle(5), arc)
