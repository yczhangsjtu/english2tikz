import tkinter as tk
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
    BoxDrawer._draw(canvas, obj, env)

  def _draw(canvas, obj, env, position=None):
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
      if position is not None:
        x, y = position
      else:
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
    elif "above" in obj:
      anchor = "south"
    elif "left" in obj:
      anchor = "east"
    elif "right" in obj:
      anchor = "west"
    elif "below" in obj:
      anchor = "north"
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
    elif "color" in obj:
      text_color = obj["color"]
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
    anchorx, anchory = get_anchor_pos((x, y, width, height), anchor)
    r = None
    if fill or draw:
      if rounded_corners:
        r = BoxDrawer.round_rectangle(canvas, x0, y0, x1, y1, radius=rounded_corners*cs["scale"], fill=fill, outline=color, width=line_width)
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
        BoxDrawer.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5, radius=rounded_corners*cs["scale"], fill="", outline="red", dash=2)
      else:
        canvas.create_rectangle(x0 - 5, y0 + 5, x1 + 5, y1 - 5, outline="red", dash=2, fill="")
      x, y = map_point(anchorx, anchory, cs)
      canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#77ff77", outline="green")

  def round_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
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


class PathDrawer(Drawer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "path"

  def draw(self, canvas, obj, env):
    draw = "draw" in obj
    arrow = "stealth" in obj or "arrow" in obj
    rarrow = "reversed.stealth" in obj or "reversed.arrow" in obj
    darrow = "double.stealth" in obj or "double.arrow" in obj
    current_pos = None
    current_pos_clip = None
    to_draw = None
    cs = env["coordinate system"]
    for item in obj["items"]:
      new_pos = None
      new_pos_clip = None
      if item["type"] == "nodename":
        name = item["name"]
        anchor = "center"
        if "anchor" in item:
          anchor = item["anchor"]
        new_pos = get_anchor_pos(env["bounding box"][name], anchor)
        if anchor == "center":
          new_pos_clip = env["bounding box"][name]
      elif item["type"] == "coordinate":
        if "relative" in item:
          new_pos = (dist_to_num(item["x"]), dist_to_num(item["y"]))
        else:
          if current_pos is None:
            raise Exception("Current position is None")
          x, y = current_pos
          new_pos = (x + dist_to_num(item["x"]), y + dist_to_num(item["y"]))
      elif item["type"] == "line":
        if to_draw is not None:
          raise Exception(f"Expected position, got line")
        to_draw = item
      else:
        raise Exception(f"Unsupported path item type {item['type']}")

      if new_pos is not None and to_draw is not None:
        if to_draw["type"] == "line":
          if current_pos is None:
            raise Exception("No starting position for line")
          if draw:
            x0, y0 = current_pos
            x1, y1 = new_pos

            if current_pos_clip:
              x0, y0 = clip_line(x0, y0, x1, y1, current_pos_clip)

            if new_pos_clip:
              x1, y1 = clip_line(x1, y1, x0, y0, new_pos_clip)

            x0p, y0p = map_point(x0, y0, cs)
            x1p, y1p = map_point(x1, y1, cs)

            if "line.width" in obj:
              width = obj["line.width"]
            else:
              width = None
            if "color" in obj:
              color = obj["color"]
            else:
              color = "black"

            if arrow:
              arrow = tk.LAST
            elif rarrow:
              arrow = tk.FIRST
            elif darrow:
              arrow = tk.BOTH
            else:
              arrow = None
            canvas.create_line((x0p, y0p, x1p, y1p), fill=color, width=width,
                               arrow=arrow)
            if "annotates" in to_draw:
              for annotate in to_draw["annotates"]:
                if "start" in annotate:
                  t = 1
                elif "near.start" in annotate:
                  t = 0.9
                elif "midway" in annotate:
                  t = 0.5
                elif "near.end" in annotate:
                  t = 0.1
                elif "end" in annotate:
                  t = 0
                else:
                  t = 0.5
                x = x0 * t + x1 * (1 - t)
                y = y0 * t + y1 * (1 - t)
                BoxDrawer._draw(canvas, annotate, env, position=(x, y))

        to_draw = None

      if new_pos is not None:
        current_pos = new_pos
        current_pos_clip = new_pos_clip
        new_pos = None

    if to_draw is not None:
      raise Exception(f"Undrawn item {to_draw}")
