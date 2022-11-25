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


def clip_line(x0, y0, x1, y1, clip):
  x, y, w, h = clip
  assert x0 >= x and x0 <= x+w and y0 >= y and y0 <= y+w
  if x1 >= x and x1 <= x+w and y1 >= y and y1 <= y+h:
    return None
  while (x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0) > 0.001:
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    if xm >= x and xm <= x+w and ym >= y and ym <= y+h:
      x0, y0 = xm, ym
    else:
      x1, y1 = xm, ym
  return x1, y1


def clip_curve(curve, clip):
  x, y, w, h = clip
  for i in range(len(curve)):
    if not point_in_rect(*curve[i], (x, y, x+w, y+h), strict=True):
      return curve[i:]
  return None


def rotate(x, y, x0, y0, angle):
  rad = angle / 180 * math.pi
  a, b, c, d = math.cos(rad), math.sin(rad), -math.sin(rad), math.cos(rad)
  dx, dy = x - x0, y - y0
  dx, dy = a * dx + b * dy, c * dx + d * dy
  return x0 + dx, y0 + dy


def get_angle(x0, y0, x1, y1):
  dist = math.sqrt((x1-x0)*(x1-x0)+(y1-y0)*(y1-y0))
  if dist < 0.0001:
    return None
  angle = int(math.asin((y1-y0)/dist) / math.pi * 180)
  if x1 < x0:
    angle = 180 - angle
  if angle < 0:
    angle += 360
  return angle
