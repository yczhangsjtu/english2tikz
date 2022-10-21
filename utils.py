colors = [
  "red", "blue", "white", "black", "yellow", "orange", "green"
]


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


def dist_to_num(dist):
  if isinstance(dist, str):
    if dist.endswith("cm"):
      return float(dist[:-2])
    return float(dist)
  return float(dist)


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


def color_to_tk(color):
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
