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
