import math
import re
from datetime import datetime
from english2tikz.errors import *


mutually_exclusive = [
    set([
        "above", "below", "left", "right",
        "below.left", "below.right",
        "above.left", "above.right"]),
    set([
        "midway", "pos",
        "near.end", "near.start",
        "very.near.end", "very.near.start",
        "at.end", "at.start"]),
    set([
        "stealth", "arrow",
        "reversed.stealth", "reversed.arrow",
        "double.stealth", "double.arrow"]),
    set(["circle", "ellipse"]),
]


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


arrow_types = [
    "arrow",
    "reversed.arrow",
    "double.arrow",
    "stealth",
    "reversed.stealth",
    "double.stealth",
]


arrow_symbols = {
    "->": "stealth",
    "<-": "reversed.stealth",
    "<->": "double.stealth",
}


directions = ["left", "right", "up", "down",
              "below", "above",
              "below.left", "below.right",
              "above.left", "above.right"]


counter = 0


def now():
  return int(datetime.now().timestamp() * 1000)


def mutex(a, b, c):
  return b if a else c


def none_or(a, default):
  if a is None:
    return default
  return a


def index_two_lists(a, b, i):
  if i >= 0 and i < len(a):
    return a[i]
  if i >= len(a) and i < len(a) + len(b):
    return b[i-len(a)]
  raise IndexError(f"Expected [0, {len(a)+len(b)}), got {i}")


def add_to_key(item, key, delta):
  item[key] = num_to_dist(dist_to_num(item.get(key, 0)) + delta)


def default_font(font_size):
  return ("Times New Roman", font_size, "normal")


def is_str(s):
  marks = ['"', "'"]
  for mark in marks:
    if s.startswith(mark) and s.endswith(mark):
      return True
  return False


def is_long_str(s):
  marks = ['"""', "'''"]
  for mark in marks:
    if s.startswith(mark) and s.endswith(mark):
      return True
  return False


def both(a, b):
  return a and b


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
        raise UserInputError(
            f"code does not have sufficient indentation on line {i}:\n{code}")
      lines[i] = lines[i][indent_size:]
  return "\n".join(lines)


def common_part(dics):
  keys = list(dics[0].keys())
  for dic in dics[1:]:
    keys = [key for key in keys
            if key in dic and
            dic[key] == dics[0][key]]
  return {key: dics[0][key] for key in keys}


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
  if isinstance(num, str):
    if num.endswith("cm"):
      return num
    if num == "0":
      return num
    return f"{num}cm"
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


def shift_dist(obj, key, delta, round_by=None, empty_val=None):
  if delta == 0:
    return
  val = dist_to_num(obj.get(key, 0)) + delta
  if round_by is not None:
    val = round(val / round_by) * round_by
  val = num_to_dist(val)
  set_or_del(obj, key, val, empty_val)


def shift_object(obj, dx, dy, round_by=None):
  if is_type(obj, "path"):
    shift_path(obj, dx, dy, round_by)
    return
  at = obj.get("at")
  if is_type(at, "coordinate"):
    shift_dist(at, "x", dx, round_by=round_by)
    shift_dist(at, "y", dy, round_by=round_by)
  elif obj.get("in_path", False):
    shift_dist(obj, "xshift", dx, round_by=round_by, empty_val="0")
    shift_dist(obj, "yshift", dy, round_by=round_by, empty_val="0")
  elif isinstance(at, str):
    shift_dist(obj, "xshift", dx, round_by=round_by, empty_val="0")
    shift_dist(obj, "yshift", dy, round_by=round_by, empty_val="0")
  elif is_type(at, "intersection"):
    shift_dist(obj, "xshift", dx, round_by=round_by, empty_val="0")
    shift_dist(obj, "yshift", dy, round_by=round_by, empty_val="0")
  elif get_direction_of(obj) is not None:
    shift_dist(obj, "xshift", dx, round_by=round_by, empty_val="0")
    shift_dist(obj, "yshift", dy, round_by=round_by, empty_val="0")
  else:
    obj["at"] = {
        "type": "coordinate",
        "x": dx,
        "y": dy,
    }


def shift_path(path, dx, dy, round_by=None):
  for item in path["items"]:
    if is_type(item, "nodename") and item.get("anchor") is None:
      raise ErrorMessage("Cannot shift path containing "
                         "nodename without anchor")
  for item in path["items"]:
    if is_type(item, "coordinate") and not item.get("relative", False):
      shift_path_position(item, dx, dy, round_by)
    elif is_type(item, "nodename"):
      if item.get("anchor") is not None:
        shift_path_position(item, dx, dy, round_by)


def shift_path_position(item, dx, dy, round_by=None):
  if is_type(item, "coordinate"):
    shift_dist(item, "x", dx, round_by)
    shift_dist(item, "y", dy, round_by)
    return
  if is_type(item, "nodename"):
    shift_dist(item, "xshift", dx, round_by, empty_val="0")
    shift_dist(item, "yshift", dy, round_by, empty_val="0")


def related_to(obj, id_):
  if "id" in obj and obj["id"] == id_:
    return True
  if "at" in obj and obj["at"] == id_:
    return True
  if "items" in obj:
    for item in obj["items"]:
      if is_type(item, "nodename"):
        if item["name"] == id_:
          return True
      elif is_type(item, "intersection"):
        if item["name1"] == id_ or item["name2"] == id_:
          return True
  return False


def smart_key_value(key, value):
  """
  Implement acronyms and aliases.
  """
  if isinstance(value, list) and len(value) == 1:
    value = value[0]
  if is_color(key) and value is True:
    """
    set blue <=> set color=blue
    """
    return [("color", key)]
  if key in anchor_list and value is True:
    return [("anchor", key)]
  if key in short_anchor_dict and value is True:
    return [("anchor", short_anchor_dict[key])]
  if key == "at" and value in anchor_list:
    return [("at.anchor", value)]
  if key == "at" and value in short_anchor_dict:
    return [("at.anchor", short_anchor_dict[value])]
  if key == "at":
    raise UserInputError("Does not support setting node "
                         "position (except anchor)")
  if key == "rc":
    key = "rounded.corners"
  if value == "False" or value == "None":
    return [(key, None)]
  if key in ["width", "height", "xshift", "yshift"]:
    value = num_to_dist(value)
  if key in ["out", "in"] and value in directions:
    return [(key, direction_to_angle(value))]
  if key in ["rectangle", "line"]:
    return [("type", key)]
  if key == "->":
    return [("stealth", True)]
  if key == "<-":
    return [("reversed.stealth", True)]
  if key == "<->":
    return [("double.stealth", True)]
  ret = [(key, value)]
  for s in mutually_exclusive:
    if key in s:
      ret = ret + [(k, False) for k in s if k != key]
  return ret


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
      raise ValueError(f"Got s > 1 for color {color}")
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
  if name == "orange":
    return 255, 165, 0
  raise ValueError(f"Unrecognized color {name}")


def flipped(direction):
  if direction == "left":
    return "right"
  if direction == "right":
    return "left"
  if direction == "up":
    return "down"
  if direction == "down":
    return "up"
  if direction == "below":
    return "above"
  if direction == "above":
    return "below"
  if direction == "below.left":
    return "above.right"
  if direction == "below.right":
    return "above.left"
  if direction == "above.left":
    return "below.right"
  if direction == "above.right":
    return "below.left"
  raise ValueError(f"Unrecognized direction {direction}")


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
      "above": (0, 1),
      "below": (0, -1),
      "left": (-1, 0),
      "right": (1, 0),
      "above.left": (-1, 1),
      "below.left": (-1, -1),
      "above.right": (1, 1),
      "below.right": (1, -1),
  }[direction]


def direction_to_angle(direction):
  return {
      "up": 90,
      "down": 270,
      "left": 180,
      "right": 0,
  }[direction]


def direction_to_anchor(direction):
  x, y = direction_to_num(direction)
  return num_to_anchor(x, y)


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


latex_hints = [
    "$", "\\textbf{", "\\begin{", "\\emph{"
]


def need_latex(text):
  for hint in latex_hints:
    if text.find(hint) >= 0:
      return True
  return False


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


def get_direction_of(obj):
  for direction in directions:
    if obj.get(direction) is not None:
      return direction
  return None


def get_default_of_type(dic, key, type_, default=None):
  ret = dic.get(key, default)
  if isinstance(ret, type_):
    return ret
  return default


def bound_by(x, a, b):
  return max(min(x, b), a)


def is_bound_by(x, a, b):
  return x <= max(a, b) and x >= min(a, b)


def order(a, b):
  return min(a, b), max(a, b)


def get_type_if_dict(dic):
  if not isinstance(dic, dict):
    return None
  return dic.get("type")


def is_type(dic, type_):
  return get_type_if_dict(dic) == type_


def set_or_del(dic, key, value, empty):
  if value == empty:
    dic.pop(key, None)
  else:
    dic[key] = value


def append_if_not_in(ls, e):
  if e not in ls:
    ls.append(e)


def remove_if_in(ls, e):
  return [a for a in ls if a != e]


def toggle_element(ls, e):
  if e not in ls:
    ls.append(e)
    return ls
  else:
    return [a for a in ls if a != e]


def is_color(name):
  if name is None:
    return False
  if name == "":
    return False
  for item in name.split("!"):
    if item not in colors and not re.match(r"\d+$", item):
      return False
  return True


def clear_dict(d):
  keys = [key for key in d.keys()]
  for key in keys:
    del d[key]


def get_first_absolute_coordinate(data):
  for obj in data:
    at = obj.get("at")
    if is_type(at, "coordinate"):
      if at.get("relative", False):
        raise ValueError("An object cannot have relative coordinate")
      return dist_to_num(at.get("x", 0), at.get("y", 0))
    if "id" in obj and at is None:
      return 0, 0
    items = obj.get("items")
    if items is not None:
      for item in items:
        if both(is_type(item, "coordinate"),
                not item.get("relative", False)):
          return dist_to_num(item.get("x", 0),
                             item.get("y", 0))
  return None


def get_top_left_corner(data, bounding_boxes):
  x0, y0, x1, y1 = get_bounding_box(data, bounding_boxes)
  return x0, y0


def enlarge_bound_box(x0, y0, x1, y1, x, y):
  if x0 is None or x < x0:
    x0 = x
  if y0 is None or y < y0:
    y0 = y
  if x1 is None or x > x1:
    x1 = x
  if y1 is None or y > y1:
    y1 = y
  return x0, y0, x1, y1


def get_bounding_box(data, bounding_boxes):
  x0, y0, x1, y1 = None, None, None, None
  for obj in data:
    id_ = obj.get("id")
    if id_ is not None:
      id_ = obj.get("id")
      bb = bounding_boxes[id_]
      x2, y2, x3, y3 = bb.get_bound()
      x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x2, y2)
      x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x3, y3)
    else:
      for id_, bb in bounding_boxes.items():
        if obj == bb._obj:
          x2, y2, x3, y3 = bb.get_bound()
          x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x2, y2)
          x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x3, y3)
    if "items" in obj:
      for item in obj["items"]:
        if "annotates" in item:
          for annotate in item["annotates"]:
            id_ = annotate.get("id")
            if id_ is not None:
              bb = bounding_boxes[id_]
              x2, y2, x3, y3 = bb.get_bound()
              x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x2, y2)
              x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x3, y3)
  if x0 is None:
    return 0, 0, 0, 0
  return x0, y0, x1, y1


def get_path_position_items(path):
  return [(i, item) for (i, item) in enumerate(path["items"])
          if item["type"] in ["nodename", "coordinate", "intersection"]]


def get_path_segment_items(path):
  return [(i, item) for (i, item) in enumerate(path["items"])
          if item["type"] in ["line", "rectangle"]]


def count_path_position_items(path):
  return len(get_path_position_items(path))


def count_path_segment_items(path):
  return len(get_path_segment_items(path))


def previous_line(items, position):
  for pos in reversed(range(0, position+1)):
    if is_type(items[pos], "line") or is_type(items[pos], "arc"):
      return items[pos]
  return None


def next_line(items, position):
  for pos in range(position, len(items)):
    if items[pos].get("type") in ["line", "rectangle", "arc"]:
      return items[pos]
  return None


def create_arc_curve(x0, y0, start, end, radius):
  length = (abs(end - start) / 360) * 2 * math.pi * radius
  steps = max(int(length / 0.1), 10)
  dx1, dy1 = math.cos(start*math.pi/180), math.sin(start*math.pi/180)
  dx2, dy2 = math.cos(end*math.pi/180), math.sin(end*math.pi/180)
  centerx, centery = x0 - dx1 * radius, y0 - dy1 * radius
  return [(centerx+math.cos((t/steps*(end-start)+start)*math.pi/180) * radius,
           centery+math.sin((t/steps*(end-start)+start)*math.pi/180) * radius)
          for t in range(steps+1)]
