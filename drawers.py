from .utils import *


class Drawer(object):
  def match(self, obj):
    raise Exception("Cannot invoke match method from base class Drawer")

  def draw(self, canvas, obj, env):
    raise Exception("Cannot invoke draw method from base class Drawer")


class BoxDrawer(Drawer):
  def match(self, obj):
    return "type" in obj and obj["type"] in ["box", "text"]

  def draw(self, canvas, obj, env):
    assert "width" in obj
    assert "height" in obj
    assert "id" in obj
    draw = ("draw" in obj and obj["draw"]) or obj["type"] == "box"
    width, height = dist_to_num(obj["width"]), dist_to_num(obj["height"])
    if "at" not in obj:
      x, y = 0, 0
    elif isinstance(obj["at"], str):
      at_bounding_box = env["bounding box"][obj["at"]]
      if "at.anchor" in obj:
        anchor = obj["at.anchor"]
      else:
        anchor = "center"
      x, y = get_anchor_pos(at_bounding_box, anchor)
    elif obj["at"]["type"] == "coordinate":
      x = obj["at"]["x"] if "x" in obj["at"] else 0
      y = obj["at"]["y"] if "y" in obj["at"] else 0
    else:
      raise Exception(f"Unsupported at {obj['at']}")
    anchor = "center"
    if "anchor" in obj:
      anchor = obj["anchor"]
    x, y = shift_by_anchor(x, y, anchor, width, height)
    if "xshift" in obj:
      x += dist_to_num(obj["xshift"])
    if "yshift" in obj:
      y += dist_to_num(obj["yshift"])
    env["bounding box"][obj["id"]] = (x, y, width, height)
    cs = env["coordinate system"]
    x0, y0 = map_point(x, y, cs)
    x1, y1 = map_point(x + width, y + height, cs)
    canvas.create_rectangle((x0, y0, x1, y1))
    if "text" in obj and obj["text"]:
      center_x, center_y = get_anchor_pos((x, y, width, height), "center")
      x, y = map_point(center_x, center_y, cs)
      canvas.create_text(x, y, text=obj["text"])
