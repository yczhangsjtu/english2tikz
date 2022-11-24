import math
from english2tikz.utils import *


def draw_border(obj):
  return get_default(obj, "draw", False) or is_type(obj, "box")


def get_draw_color(obj):
  return get_default(obj, "color", "black") if draw_border(obj) else ""


def get_text_color(obj):
  text_color = get_default(obj, "text.color")
  text_color = get_default(obj, "color") if text_color is None else text_color
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
    dist = get_default(obj, "distance", 1)
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
        get_default(obj, "at.anchor", "center"))
  elif at["type"] == "coordinate":
    return dist_to_num(get_default(at, "x", 0), get_default(at, "y", 0))
  elif at["type"] == "intersection":
    x, _ = bounding_boxes[at["name1"]].get_anchor_pos(
        get_default(at, "anchor1", "center"))
    _, y = bounding_boxes[at["name2"]].get_anchor_pos(
        get_default(at, "anchor2", "center"))
    return x, y
  else:
    raise ValueError(f"Unsupported at {at}")


def get_rounded_corners(obj, default):
  rounded_corners = get_default(obj, "rounded.corners")
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
