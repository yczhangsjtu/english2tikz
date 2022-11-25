import math


def create_arc_curve(x0, y0, start, end, radius):
  length = (abs(end - start) / 360) * 2 * math.pi * radius
  steps = max(int(length / 0.1), 10)
  dx1, dy1 = math.cos(start*math.pi/180), math.sin(start*math.pi/180)
  dx2, dy2 = math.cos(end*math.pi/180), math.sin(end*math.pi/180)
  centerx, centery = x0 - dx1 * radius, y0 - dy1 * radius
  return [(centerx+math.cos((t/steps*(end-start)+start)*math.pi/180) * radius,
           centery+math.sin((t/steps*(end-start)+start)*math.pi/180) * radius)
          for t in range(steps+1)]
