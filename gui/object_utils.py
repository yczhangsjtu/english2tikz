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
    raise Exception(f"Unsupported at {at}")


def get_rounded_corners(obj, default):
  rounded_corners = get_default(obj, "rounded.corners")
  if rounded_corners is True:
    return default
  if rounded_corners is not None:
    return dist_to_num(rounded_corners)
  return None