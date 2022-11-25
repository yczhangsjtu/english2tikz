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


def euclidean_dist(a, b):
  x0, y0 = a
  x1, y1 = b
  return math.sqrt((x0 - x1) * (x0 - x1) + (y0 - y1) * (y0 - y1))


def point_line_dist(x, y, line):
  x1, y1, x2, y2 = line
  # Copied from
  # https://stackoverflow.com/questions/849211/shortest-distance-between-a-point-and-a-line-segment
  A = x - x1
  B = y - y1
  C = x2 - x1
  D = y2 - y1

  dot = A * C + B * D
  len_sq = C * C + D * D
  param = -1
  if len_sq != 0:  # in case of 0 length line
    param = dot / len_sq

  if param < 0:
    xx = x1
    yy = y1
  elif param > 1:
    xx = x2
    yy = y2
  else:
    xx = x1 + param * C
    yy = y1 + param * D

  dx = x - xx
  dy = y - yy
  return math.sqrt(dx * dx + dy * dy)


def intersect(rect1, rect2):
  x0, y0, x1, y1 = rect1
  x2, y2, x3, y3 = rect2
  return both(intersect_interval((x0, x1), (x2, x3)),
              intersect_interval((y0, y1), (y2, y3)))


def intersect_interval(interval1, interval2):
  x0, x1 = interval1
  x2, x3 = interval2
  x0, x1 = min(x0, x1), max(x0, x1)
  x2, x3 = min(x2, x3), max(x2, x3)
  return (x3 >= x0 and x3 <= x1) or (x1 >= x2 and x1 <= x3)


def rect_line_intersect(rect, line):
  x0, y0, x1, y1 = rect
  x2, y2, x3, y3 = line
  return (point_in_rect(x2, y2, rect) or
          point_in_rect(x3, y3, rect) or
          line_line_intersect((x0, y0, x1, y0), line) or
          line_line_intersect((x0, y0, x0, y1), line) or
          line_line_intersect((x1, y1, x0, y1), line) or
          line_line_intersect((x1, y1, x0, y1), line))


def point_in_rect(x, y, rect, strict=False):
  x0, y0, x1, y1 = rect
  x0, x1 = min(x0, x1), max(x0, x1)
  y0, y1 = min(y0, y1), max(y0, y1)
  if strict:
    return x > x0 and x < x1 and y > y0 and y < y1
  return x >= x0 and x <= x1 and y >= y0 and y <= y1


def line_line_intersect(line1, line2):
  # https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection
  x0, y0, x1, y1 = line1
  x2, y2, x3, y3 = line2
  t1 = (x0 - x2) * (y2 - y3) - (y0 - y2) * (x2 - x3)
  dn = (x0 - x1) * (y2 - y3) - (y0 - y1) * (x2 - x3)
  u1 = (x0 - x2) * (y0 - y1) - (y0 - y2) * (x0 - x1)
  if dn == 0:
    return False

  t, u = t1 / dn, u1 / dn
  return t >= 0 and t <= 1 and u >= 0 and u <= 1
