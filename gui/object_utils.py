import math
from english2tikz.utils import *
from english2tikz.gui.bounding_box import *


def draw_border(obj):
  return obj.get("draw", False) or is_type(obj, "box")


def get_draw_color(obj):
  return obj.get("color", "black") if draw_border(obj) else ""


def get_text_color(obj):
  text_color = obj.get("text.color")
  text_color = obj.get("color") if text_color is None else text_color
  text_color = "black" if text_color is None else text_color
  return text_color


def get_shape(obj):
  if "circle" in obj:
    return "circle"
  if "ellipse" in obj:
    return "ellipse"
  return "rectangle"


def get_original_pos(obj, bounding_boxes, position=None):
  if "at" not in obj:
    x, y = position if position is not None else (0, 0)
    direction = get_direction_of(obj)
    if direction is None:
      return x, y
    at = get_default_of_type(obj, direction, str)
    if at is None:
      return x, y
    at_bounding_box = bounding_boxes[at]
    x, y = at_bounding_box.get_anchor_pos(direction_to_anchor(direction))
    dx, dy = direction_to_num(direction)
    dist = obj.get("distance", 1)
    if isinstance(dist, str) and dist.find("and") >= 0:
      disty, distx = dist_to_num(*dist.split(".and."))
    else:
      distx = dist_to_num(dist)
      disty = distx
    return x + distx * dx, y + disty * dy

  at = obj["at"]
  if isinstance(at, str):
    at_bounding_box = bounding_boxes[at]
    return at_bounding_box.get_anchor_pos(
        obj.get("at.anchor", "center"))
  elif at["type"] == "coordinate":
    return dist_to_num(at.get("x", 0), at.get("y", 0))
  elif at["type"] == "intersection":
    x, _ = bounding_boxes[at["name1"]].get_anchor_pos(
        at.get("anchor1", "center"))
    _, y = bounding_boxes[at["name2"]].get_anchor_pos(
        at.get("anchor2", "center"))
    return x, y
  else:
    raise ValueError(f"Unsupported at {at}")


def get_rounded_corners(obj, default):
  rounded_corners = obj.get("rounded.corners")
  if rounded_corners is True:
    return default
  if rounded_corners is not None:
    return dist_to_num(rounded_corners)
  return None


def get_position_in_line(obj):
  if "at.start" in obj:
    return 1
  if "near.start" in obj:
    return 0.8
  if "midway" in obj:
    return 0.5
  if "near.end" in obj:
    return 0.2
  if "at.end" in obj:
    return 0
  return 0.5


def compute_arc_to_extend_path(path, x, y, hint):
  if "last_path" not in hint:
    return None, None, None
  last_path_hint = hint["last_path"]
  hint_directions = last_path_hint["directions"]
  hint_positions = last_path_hint["positions"]
  assert len(hint_positions) == len(hint_directions), "Mismatched hint sizes"
  if len(hint_positions) == 0 or hint_directions[-1] is None:
    return None, None, None
  x0, y0 = hint_positions[-1]
  deg = hint_directions[-1]
  dx0, dy0 = math.sin(deg/180*math.pi), -math.cos(deg/180*math.pi)
  xm, ym = (x + x0) / 2, (y + y0) / 2
  dxm, dym = y - y0, x0 - x
  if abs(dx0 * dym - dy0 * dxm) < 0.01:
    return None, None, None
  u = (dym * xm - dxm * ym + y0 * dxm - x0 * dym) / (dx0 * dym - dy0 * dxm)
  radius = abs(u)
  if radius > 20 or radius < 0.1:
    return None, None, None
  centerx, centery = x0 + u * dx0, y0 + u * dy0
  if u > 0:
    start = (deg + 90) % 360
  else:
    start = (deg + 270) % 360
  if x == centerx:
    if y > centery:
      end = 90
    else:
      end = -90
  else:
    end = int(math.atan((y - centery) / (x - centerx)) * 180 / math.pi)
    if x < centerx:
      end = (end + 180) % 360
  if u > 0 and end > start:
    end -= 360
  elif u < 0 and end < start:
    end += 360
  if abs(end - start) < 3:
    return None, None, None
  return start, end, radius


def create_nodename(name, anchor=None):
  ret = {
      "type": "nodename",
      "name": name
  }
  if anchor is not None:
    ret["anchor"] = anchor
  return ret


def create_coordinate(x, y, relative=False):
  ret = {
      "type": "coordinate",
      "x": num_to_dist(none_or(x, 0)),
      "y": num_to_dist(none_or(y, 0)),
  }
  if relative:
    ret["relative"] = True
  return ret


def create_arc(start, end, radius):
  return {
      "type": "arc",
      "start": str(start),
      "end": str(end),
      "radius": num_to_dist(radius),
  }


def create_line():
  return {"type": "line"}


def create_rectangle():
  return {"type": "rectangle"}


def create_path(items, arrow=None):
  ret = {"type": "path", "draw": True, "items": items}
  if arrow is not None:
    if arrow in arrow_types:
      ret[arrow] = True
    elif arrow in arrow_symbols:
      ret[arrow_symbols[arrow]] = True
    else:
      raise ValueError(f"Invalid arrow type: {arrow}")
  return ret


def create_text(text, x=None, y=None):
  ret = {"type": "text", "text": text}
  if x is not None or y is not None:
    ret["at"] = create_coordinate(x, y)
  return ret


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
          return dist_to_num(item.get("x", 0), item.get("y", 0))
  return None


def get_top_left_corner(data, bounding_boxes):
  x0, y0, x1, y1 = get_bounding_box(data, bounding_boxes)
  return x0, y0


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
