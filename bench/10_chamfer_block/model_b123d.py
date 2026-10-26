from build123d import Axis, Box, chamfer

result = chamfer(Box(60, 40, 20).edges().filter_by(Axis.Z), 4)
