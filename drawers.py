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
    assert "id" in obj
    tmptext = None
    draw = ("draw" in obj and obj["draw"]) or obj["type"] == "box"
    if "width" in obj and "height" in obj:
      width, height = dist_to_num(obj["width"]), dist_to_num(obj["height"])
    elif "text" in obj:
      tmptext = canvas.create_text(0, 0, text=obj["text"])
      x0, y0, x1, y1 = canvas.bbox(tmptext)
      if "inner.sep" in obj:
        inner_sep = dist_to_num(obj["inner.sep"])
      else:
        inner_sep = 0.1
      if "width" in obj:
        width = dist_to_num(obj["width"])
      else:
        width = (x1 - x0) / env["coordinate system"]["scale"] + inner_sep * 2
      if "height" in obj:
        height = dist_to_num(obj["height"])
      else:
        height = (y1 - y0) / env["coordinate system"]["scale"] + inner_sep * 2
    else:
      if "width" in obj:
        width = dist_to_num(obj["width"])
      else:
        width = 1
      if "height" in obj:
        height = dist_to_num(obj["height"])
      else:
        height = 1

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
      x = dist_to_num(obj["at"]["x"]) if "x" in obj["at"] else 0
      y = dist_to_num(obj["at"]["y"]) if "y" in obj["at"] else 0
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

    if draw:
      if "color" in obj:
        color = color_to_tk(obj["color"])
      else:
        color = "black"
    else:
      color = ""

    if "text.color" in obj:
      text_color = color_to_tk(obj["text.color"])
    elif len(color) > 0:
      text_color = color
    else:
      text_color = "black"

    if "fill" in obj:
      fill = color_to_tk(obj["fill"])
    else:
      fill = ""

    if "line.width" in obj:
      line_width = obj["line.width"]
    else:
      line_width = None
    if "rounded.corners" in obj:
      if isinstance(obj["rounded.corners"], bool):
        rounded_corners = 0.2
      else:
        rounded_corners = dist_to_num(obj["rounded.corners"])
    else:
      rounded_corners = None
    cs = env["coordinate system"]
    x0, y0 = map_point(x, y, cs)
    x1, y1 = map_point(x + width, y + height, cs)
    r = None
    if fill or draw:
      if rounded_corners:
        r = self.round_rectangle(canvas, x0, y0, x1, y1, radius=rounded_corners*cs["scale"], fill=fill, outline=color, width=line_width)
      else:
        r = canvas.create_rectangle((x0, y0, x1, y1), fill=fill, outline=color, width=line_width)
    if "text" in obj and obj["text"]:
      center_x, center_y = get_anchor_pos((x, y, width, height), "center")
      x, y = map_point(center_x, center_y, cs)
      if tmptext is None:
        canvas.create_text(x, y, text=obj["text"], fill=text_color)
      else:
        canvas.move(tmptext, x, y)
        canvas.itemconfig(tmptext, fill=text_color)
        if r:
          canvas.tag_lower(r, tmptext)
    if obj["id"] in env["selected ids"]:
      if rounded_corners:
        self.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5, radius=rounded_corners*cs["scale"], fill="", outline="red", dash=2)
      else:
        canvas.create_rectangle(x0 - 5, y0 + 5, x1 + 5, y1 - 5, outline="red", dash=2, fill="")

  def round_rectangle(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    points = [x1+radius, y1,
              x1+radius, y1,
              x2-radius, y1,
              x2-radius, y1,
              x2, y1,
              x2, y1+radius,
              x2, y1+radius,
              x2, y2-radius,
              x2, y2-radius,
              x2, y2,
              x2-radius, y2,
              x2-radius, y2,
              x1+radius, y2,
              x1+radius, y2,
              x1, y2,
              x1, y2-radius,
              x1, y2-radius,
              x1, y1+radius,
              x1, y1+radius,
              x1, y1]

    return canvas.create_polygon(points, **kwargs, smooth=True)
