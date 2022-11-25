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


def none_or(a, default):
  if a is None:
    return default
  return a


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


latex_hints = [
    "$", "\\textbf{", "\\begin{", "\\emph{"
]


def need_latex(text):
  for hint in latex_hints:
    if text.find(hint) >= 0:
      return True
  return False


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
