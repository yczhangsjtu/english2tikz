import math


colors = [
  "red", "blue", "white", "black", "yellow", "orange", "green"
]


anchor_list = [
  "north.west", "north", "north.east",
  "west", "center", "east",
  "south.west", "south", "south.east",
]


short_anchor_dict = {
  "nw": "north.west",
  "n": "north",
  "ne": "north.east",
  "w": "west",
  "c": "center",
  "e": "east",
  "sw": "south.west",
  "s": "south",
  "se": "south.east",
}


counter = 0


def getid():
  global counter
  ret = f"id{counter}"
  counter += 1
  return ret


def dump_options(o):
  return ", ".join([key if isinstance(value, bool) and value
                    else f"{key}={value}"
                    for key, value in o.items()])


def unindent(code):
  lines = code.split("\n")
  indent_size = 0
  for line in lines:
    if line.strip() == "":
      continue
    indent_size = len(line) - len(line.lstrip())
    break
  if indent_size == 0:
    return code
  for i, line in enumerate(lines):
    if line.strip() != "":
      if len(line) < indent_size or line[:indent_size] != " " * indent_size:
        raise Exception(f"code does not have sufficient indentation on line {i}:\n{code}")
      lines[i] = lines[i][indent_size:]
  return "\n".join(lines)


def _dist_to_num(dist):
  if isinstance(dist, str):
    if dist.endswith("cm"):
      return float(dist[:-2])
    return float(dist)
  return float(dist)

def dist_to_num(*dists):
  if len(dists) == 0:
    return None
  if len(dists) == 1:
    return _dist_to_num(dists[0])
  return [_dist_to_num(dist) for dist in dists]


def _num_to_dist(num):
  if num == 0:
    return "0"
  if num < 0.001 and num > -0.001:
    return "0"
  return f"{num:g}cm"

def num_to_dist(*nums):
  if len(nums) == 0:
    return None
  if len(nums) == 1:
    return _num_to_dist(nums[0])
  return [_num_to_dist(num) for num in nums]


def shift_by_anchor(x, y, anchor, width, height):
  anchor_x, anchor_y = get_anchor_pos((x, y, width, height), anchor)
  return 2 * x - anchor_x, 2 * y - anchor_y


def get_anchor_pos(bb, anchor):
  x, y, w, h = bb
  if anchor == "center":
    return x + w/2, y + h/2
  elif anchor == "west":
    return x, y + h/2
  elif anchor == "east":
    return x + w, y + h/2
  elif anchor == "south":
    return x + w/2, y
  elif anchor == "north":
    return x + w/2, y + h
  elif anchor == "north.east":
    return x + w, y + h
  elif anchor == "north.west":
    return x, y + h
  elif anchor == "south.east":
    return x + w, y
  elif anchor == "south.west":
    return x, y
  else:
    raise Exception(f"Unsupported anchor: {anchor}")


def map_point(x, y, cs):
  return cs["center_x"] + x * cs["scale"], cs["center_y"] - y * cs["scale"]


def reverse_map_point(x, y, cs):
  return (x - cs["center_x"]) / cs["scale"], (cs["center_y"] - y) / cs["scale"]


def intersect(rect1, rect2):
  x0, y0, x1, y1 = rect1
  x2, y2, x3, y3 = rect2
  return intersect_interval((x0, x1), (x2, x3)) and intersect_interval((y0, y1), (y2, y3))


def intersect_interval(interval1, interval2):
  x0, x1 = interval1
  x2, x3 = interval2
  x0, x1 = min(x0, x1), max(x0, x1)
  x2, x3 = min(x2, x3), max(x2, x3)
  return (x3 >= x0 and x3 <= x1) or (x1 >= x2 and x1 <= x3)


def rect_line_intersect(rect, line):
  x0, y0, x1, y1 = rect
  x2, y2, x3, y3 = line
  return point_in_rect(x2, y2, rect) or \
         point_in_rect(x3, y3, rect) or \
         line_line_intersect((x0, y0, x1, y0), line) or \
         line_line_intersect((x0, y0, x0, y1), line) or \
         line_line_intersect((x1, y1, x0, y1), line) or \
         line_line_intersect((x1, y1, x0, y1), line)


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


def color_to_tk(color):
  if color is None:
    return None
  if color == "":
    return ""
  if "!" in color:
    components = color.split("!")
    key_values = {}
    key_values[components[0]] = 1
    for i in range(1, len(components), 2):
      for key in key_values:
        key_values[key] = key_values[key] * int(components[i]) / 100
      if i + 1 < len(components):
        key_values[components[i+1]] = (100-int(components[i])) / 100
    cleaned_dict, s = {}, 0
    for key, value in key_values.items():
      if key != "white" and value > 0:
        cleaned_dict[key] = value
        s += value
    if s < 1:
      cleaned_dict["white"] = 1-s
    elif s > 1:
      raise Exception(f"Got s > 1 for color {color}")
    r0, g0, b0 = 0, 0, 0
    for key, weight in cleaned_dict.items():
      r, g, b = color_name_to_rgb(key)
      r0 += r * weight
      g0 += g * weight
      b0 += b * weight
    r0 = min(max(int(r0), 0), 255)
    g0 = min(max(int(g0), 0), 255)
    b0 = min(max(int(b0), 0), 255)
    return f"#{r0:02x}{g0:02x}{b0:02x}"
  return color


def color_name_to_rgb(name):
  if name == "red":
    return 255, 0, 0
  if name == "green":
    return 0, 255, 0
  if name == "blue":
    return 0, 0, 255
  if name == "black":
    return 0, 0, 0
  if name == "white":
    return 255, 255, 255
  if name == "cyan":
    return 0, 255, 255
  if name == "yellow":
    return 255, 255, 0
  if name == "purple":
    return 255, 0, 255
  raise Exception(f"Unrecognized color {name}")


def shift_anchor(anchor, direction):
  x, y = anchor_to_num(anchor)
  dx, dy = direction_to_num(direction)
  x = min(max(x + dx, -1), 1)
  y = min(max(y + dy, -1), 1)
  return num_to_anchor(x, y)


def anchor_to_num(anchor):
  return {
    "center": (0, 0),
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
    "north.east": (1, 1),
    "north.west": (-1, 1),
    "south.east": (1, -1),
    "south.west": (-1, -1),
  }[anchor]


def direction_to_num(direction):
  return {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
  }[direction]


def num_to_anchor(x, y):
  return [["south.west", "south", "south.east"],
          ["west", "center", "east"],
          ["north.west", "north", "north.east"]][y+1][x+1]


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
  dx, dy = x0 - x, y0 - y
  dx, dy = a * dx + b * dy, c * dx + d * dy
  return x0 + dx, y0 + dy


def get_angle(x0, y0, x1, y1):
  dist = math.sqrt((x1-x0)*(x1-x0)+(y1-y0)*(y1-y0))
  angle = int(math.asin((y1-y0)/dist) / math.pi * 180)
  if x1 < x0:
    angle = 180 - angle
  if angle < 0:
    angle += 360
  return angle


def need_latex(text):
  return "$" in text or text.find("\\textbf{") >= 0


def satisfy_filters(obj, filters):
  for key, value in filters:
    satisfied = False
    for k, v in obj.items():
      if value is not None:
        if not isinstance(v, str) or v.find(value) < 0:
          continue
      if key is not None and k.find(key) < 0:
        continue
      satisfied = True
      break
    if not satisfied:
      return False
  return True


def get_default(dic, key, default=None):
  if key in dic:
    return dic[key]
  return default


def get_default_of_type(dic, key, type_, default=None):
  ret = get_default(dic, key, default)
  if isinstance(ret, type_):
    return ret
  return default


def del_if_has(dic, key):
  if key in dic:
    del dic[key]


def bound_by(x, a, b):
  return max(min(x, b), a)


def is_bound_by(x, a, b):
  return x <= max(a, b) and x >= min(a, b)


def order(a, b):
  return min(a, b), max(a, b)


def create_coordinate(x, y):
  return {
    "type": "coordinate",
    "x": num_to_dist(x),
    "y": num_to_dist(y),
  }


def get_type_if_dict(dic):
  if not isinstance(dic, dict):
    return None
  if "type" not in dic:
    return None
  return dic["type"]


def is_type(dic, type_):
  return get_type_if_dict(dic) == type_


def set_or_del(dic, key, value, empty):
  if value == empty:
    del_if_has(dic, key)
  else:
    dic[key] = value


def append_if_not_in(l, e):
  if e not in l:
    l.append(e)


def remove_if_in(l, e):
  return [a for a in l if a != e]


"""
Modified from
https://git.sr.ht/~torresjrjr/Bezier.py/tree/bc87b14eaa226f8fb68d2925fb4f37c3344418c1/item/Bezier.py
Modified to avoid using numpy
Bezier, a module for creating Bezier curves.
Version 1.1, from < BezierCurveFunction-v1.ipynb > on 2019-05-02
"""

class Bezier():
  def TwoPoints(t, P1, P2):
    assert len(P1) == 2
    assert len(P2) == 2
    assert isinstance(P1[0], float) or isinstance(P1[0], int)
    assert isinstance(P1[1], float) or isinstance(P1[1], int)
    """
    Returns a point between P1 and P2, parametised by t.
    """

    Q1 = [(1 - t) * e1 + t * e2 for e1, e2 in zip(P1, P2)]
    assert len(Q1) == 2
    assert isinstance(Q1[0], float) or isinstance(Q1[0], int)
    return Q1

  def Points(t, *points):
    """
    Returns a list of points interpolated by the Bezier process
    """
    newpoints = []
    for i in range(0, len(points) - 1):
      point = Bezier.TwoPoints(t, points[i], points[i + 1])
      assert isinstance(point, list)
      assert len(point) == 2
      assert isinstance(point[0], float) or isinstance(point[0], int)
      assert isinstance(point[1], float) or isinstance(point[1], int)
      newpoints.append(point)
    assert isinstance(newpoints, list)
    assert isinstance(newpoints[0], list)
    assert isinstance(newpoints[0][0], float) or isinstance(newpoints[0][1], int)
    return newpoints

  def Point(t, *points):
    """
    Returns a point interpolated by the Bezier process
    """
    newpoints = points
    while len(newpoints) > 1:
      newpoints = Bezier.Points(t, *newpoints)
    assert len(newpoints) == 1
    assert isinstance(newpoints[0], list)
    assert len(newpoints[0]) == 2
    assert isinstance(newpoints[0][0], float) or isinstance(newpoints[0][0], int)
    return newpoints[0]

  def Curve(t_values, *points):
    """
    Returns a point interpolated by the Bezier process
    """
    return [Bezier.Point(t, *points) for t in t_values]

  def generate_line_segments(*points, steps=100):
    t_values = [i/steps for i in range(steps+1)]
    curve = Bezier.Curve(t_values, *points)
    return [(x, y) for x, y in curve]
