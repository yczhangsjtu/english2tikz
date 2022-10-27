import tkinter as tk
import math
from PIL import Image
from PIL import ImageTk
from .utils import *
from .latex import text_to_latex_image_path


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

  def _draw(canvas, obj, env, position=None, angle=None):
    assert "id" in obj
    tmptext = None
    """
    The LaTeX equations are smaller than expected.
    """
    latex_scale_ratio = 1.5

    if "scale" in obj:
      scale = float(obj["scale"])
    else:
      scale = 1

    if "rotate" in obj:
      if angle is None:
        angle = int(obj["rotate"])
      else:
        angle = (int(obj["rotate"]) + angle) % 360

    font_size = 40
    if scale != 1:
      font_size = int(font_size * scale)

    draw = ("draw" in obj and obj["draw"]) or obj["type"] == "box"
    color = get_default(obj, "color", "black") if draw else ""

    if "text.color" in obj:
      text_color = obj["text.color"]
    elif len(color) > 0:
      text_color = color
    elif "color" in obj:
      text_color = obj["color"]
    else:
      text_color = "black"

    if "width" in obj and "height" in obj:
      width, height = dist_to_num(obj["width"]) * scale, dist_to_num(obj["height"]) * scale
    elif "text" in obj:
      if need_latex(obj["text"]):
        path = text_to_latex_image_path(obj["text"], text_color)
        if (path, scale, obj["id"]) not in env["image references"]:
          img = Image.open(path)
          img = img.convert("RGBA")
          w, h = img.size
          img = img.resize((int(w * scale * latex_scale_ratio),
                            int(h * scale * latex_scale_ratio)))
          image = ImageTk.PhotoImage(img)
          env["image references"][(path, scale, obj["id"])] = image
        else:
          image = env["image references"][(path, scale, obj["id"])]
        tmptext = canvas.create_image(0, 0, image=image)
      else:
        tmptext = canvas.create_text(0, 0, text=obj["text"],
                                     font=("Times New Roman", font_size, "normal"))
      x0, y0, x1, y1 = canvas.bbox(tmptext)
      if "inner.sep" in obj:
        inner_sep = dist_to_num(obj["inner.sep"])
      else:
        inner_sep = 0.1
      if "width" in obj:
        width = dist_to_num(obj["width"]) * scale
      else:
        width = (x1 - x0) / env["coordinate system"]["scale"] + inner_sep * 2 * scale
      if "height" in obj:
        height = dist_to_num(obj["height"]) * scale
      else:
        height = (y1 - y0) / env["coordinate system"]["scale"] + inner_sep * 2 * scale
    else:
      if "width" in obj:
        width = dist_to_num(obj["width"]) * scale
      else:
        width = scale
      if "height" in obj:
        height = dist_to_num(obj["height"]) * scale
      else:
        height = scale

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


    if "fill" in obj:
      fill = obj["fill"]
    else:
      fill = ""

    if "line.width" in obj:
      line_width = obj["line.width"]
    else:
      line_width = None
    if "dashed" in obj:
      dash = 2
    else:
      dash = None
    if "rounded.corners" in obj:
      if isinstance(obj["rounded.corners"], bool):
        rounded_corners = 0.2
      else:
        rounded_corners = dist_to_num(obj["rounded.corners"])
    else:
      rounded_corners = None
    cs = env["coordinate system"]
    
    if angle is None:
      x0, y0 = map_point(x, y, cs)
      x1, y1 = map_point(x + width, y + height, cs)
      anchorx, anchory = get_anchor_pos((x, y, width, height), anchor)
      r = None
      if fill or draw:
        if rounded_corners:
          r = BoxDrawer.round_rectangle(canvas, x0, y0, x1, y1,
                                        radius=rounded_corners*cs["scale"],
                                        fill=color_to_tk(fill),
                                        outline=color_to_tk(color),
                                        width=line_width,
                                        dash=dash)
        else:
          r = canvas.create_rectangle((x0, y0, x1, y1),
                                      fill=color_to_tk(fill),
                                      outline=color_to_tk(color),
                                      width=line_width,
                                      dash=dash)
      if "text" in obj and obj["text"]:
        center_x, center_y = get_anchor_pos((x, y, width, height), "center")
        x, y = map_point(center_x, center_y, cs)
        if need_latex(obj["text"]):
          if tmptext is None:
            path = text_to_latex_image_path(obj["text"], text_color)
            if (path, scale, obj["id"]) not in env["image references"]:
              img = Image.open(path)
              img = img.convert("RGBA")
              w, h = img.size
              img = img.resize((int(w * scale * latex_scale_ratio),
                                int(h * scale * latex_scale_ratio)))
              image = ImageTk.PhotoImage(img)
              env["image references"][(path, scale, obj["id"])] = image
            else:
              image = env["image references"][(path, scale, obj["id"])]
            canvas.create_image(x, y, image=image)
          else:
            canvas.move(tmptext, x, y)
            canvas.itemconfig(tmptext)
            if r:
              canvas.tag_lower(r, tmptext)
        else:
          if tmptext is None:
            canvas.create_text(x, y, text=obj["text"], fill=color_to_tk(text_color),
                               font=("Times New Roman", font_size, "normal"))
          else:
            canvas.move(tmptext, x, y)
            canvas.itemconfig(tmptext, fill=color_to_tk(text_color))
            if r:
              canvas.tag_lower(r, tmptext)
      if obj["id"] in env["selected ids"]:
        if rounded_corners:
          BoxDrawer.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5, radius=rounded_corners*cs["scale"], fill="", outline="red", dash=2)
        else:
          canvas.create_rectangle(x0 - 5, y0 + 5, x1 + 5, y1 - 5, outline="red", dash=2, fill="")
        x, y = map_point(anchorx, anchory, cs)
        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#77ff77", outline="green")

      if env["finding prefix"] is not None:
        candidate_code = env["get_candidate_code"](obj)
        if candidate_code is not None:
          ftext = canvas.create_text(x0, y0, anchor="nw", text=candidate_code, fill="black")
          fback = canvas.create_rectangle(canvas.bbox(ftext), fill="yellow", outline="blue")
          canvas.tag_lower(fback, ftext)
    else:
      x0, y0 = map_point(x, y, cs)
      x1, y1 = map_point(x + width, y + height, cs)
      anchorx, anchory = get_anchor_pos((x, y, width, height), anchor)
      anchor_screen_x, anchor_screen_y = map_point(anchorx, anchory, cs)
      r = None
      if fill or draw:
        if rounded_corners:
          r = BoxDrawer.round_rectangle(canvas, x0, y0, x1, y1,
                                        radius=rounded_corners*cs["scale"],
                                        fill=color_to_tk(fill),
                                        outline=color_to_tk(color),
                                        width=line_width, angle=angle,
                                        rotate_center=(anchor_screen_x, anchor_screen_y))
        else:
          rx0, ry0 = rotate(x0, y0, anchor_screen_x, anchor_screen_y, angle)
          rx1, ry1 = rotate(x0, y1, anchor_screen_x, anchor_screen_y, angle)
          rx2, ry2 = rotate(x1, y1, anchor_screen_x, anchor_screen_y, angle)
          rx3, ry3 = rotate(x1, y0, anchor_screen_x, anchor_screen_y, angle)
          r = canvas.create_polygon((rx0, ry0, rx1, ry1, rx2, ry2, rx3, ry3),
                                    fill=color_to_tk(fill),
                                    outline=color_to_tk(color), width=line_width)

      if "text" in obj and obj["text"]:
        center_x, center_y = get_anchor_pos((x, y, width, height), "center")
        anchor_x, anchor_y = get_anchor_pos((x, y, width, height), anchor)
        rotated_x, rotated_y = rotate(center_x, center_y, anchor_x, anchor_y, 360-angle)

        x, y = map_point(rotated_x, rotated_y, cs)
        if need_latex(obj["text"]):
          if tmptext is not None:
            canvas.delete(tmptext)
          path = text_to_latex_image_path(obj["text"], text_color)
          if (path, scale, angle, obj["id"]) not in env["image references"]:
            img = Image.open(path)
            img = img.convert("RGBA")
            w, h = img.size
            img = img.resize((int(w * scale * latex_scale_ratio),
                              int(h * scale * latex_scale_ratio)))
            if angle != 0:
              img = img.rotate((180+angle)%360, expand=True)
            image = ImageTk.PhotoImage(img)
            env["image references"][(path, scale, angle, obj["id"])] = image
          else:
            image = env["image references"][(path, scale, angle, obj["id"])]
          canvas.create_image(x, y, image=image)
        else:
          if tmptext is None:
            canvas.create_text(x, y, text=obj["text"], fill=color_to_tk(text_color),
                               font=("Times New Roman", font_size, "normal"),
                               angle=(180+angle)%360)
          else:
            canvas.move(tmptext, x, y)
            canvas.itemconfig(tmptext, fill=color_to_tk(text_color), angle=(180+angle)%360)
            if r:
              canvas.tag_lower(r, tmptext)

      if obj["id"] in env["selected ids"]:
        if rounded_corners:
          BoxDrawer.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5,
                                    radius=rounded_corners*cs["scale"], angle=angle,
                                    rotate_center=(anchor_screen_x, anchor_screen_y),
                                    fill="", outline="red", dash=2)
        else:
          rx0, ry0 = rotate(x0 - 5, y0 + 5, anchor_screen_x, anchor_screen_y, angle)
          rx1, ry1 = rotate(x0 - 5, y1 - 5, anchor_screen_x, anchor_screen_y, angle)
          rx2, ry2 = rotate(x1 + 5, y1 - 5, anchor_screen_x, anchor_screen_y, angle)
          rx3, ry3 = rotate(x1 + 5, y0 + 5, anchor_screen_x, anchor_screen_y, angle)
          canvas.create_polygon((rx0, ry0, rx1, ry1, rx2, ry2, rx3, ry3),
                                outline="red", dash=2, fill="")

        x, y = map_point(anchorx, anchory, cs)
        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#77ff77", outline="green")

      if env["finding prefix"] is not None:
        candidate_code = env["get_candidate_code"](obj)
        if candidate_code is not None:
          ftext = canvas.create_text(x0, y0, anchor="nw", text=candidate_code, fill="black")
          fback = canvas.create_rectangle(canvas.bbox(ftext), fill="yellow", outline="blue")
          canvas.tag_lower(fback, ftext)

  def round_rectangle(canvas, x1, y1, x2, y2, radius=25, angle=None, rotate_center=None, **kwargs):
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    points = [(x1+radius, y1),
              (x1+radius, y1),
              (x2-radius, y1),
              (x2-radius, y1),
              (x2, y1),
              (x2, y1+radius),
              (x2, y1+radius),
              (x2, y2-radius),
              (x2, y2-radius),
              (x2, y2),
              (x2-radius, y2),
              (x2-radius, y2),
              (x1+radius, y2),
              (x1+radius, y2),
              (x1, y2),
              (x1, y2-radius),
              (x1, y2-radius),
              (x1, y1+radius),
              (x1, y1+radius),
              (x1, y1)]

    if angle is not None and rotate_center is not None:
      x0, y0 = rotate_center
      points = [rotate(x, y, x0, y0, angle) for x, y in points]
      points = [e for x, y in points for e in (x, y)]
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
    position_number = 0
    to_draw = None
    cs = env["coordinate system"]
    is_selected = obj in env["selected paths"]
    for index, item in enumerate(obj["items"]):
      new_pos = None
      new_pos_clip = None
      if item["type"] == "nodename":
        name = item["name"]
        anchor = "center"
        if "anchor" in item:
          anchor = item["anchor"]
        new_pos = get_anchor_pos(env["bounding box"][name], anchor)
        if "xshift" in item or "yshift" in item:
          x, y = new_pos
          if "xshift" in item:
            x += dist_to_num(item["xshift"])
          if "yshift" in item:
            y += dist_to_num(item["yshift"])
          new_pos = (x, y)
        elif anchor == "center":
          new_pos_clip = env["bounding box"][name]
      elif item["type"] == "point":
        id_ = item["id"]
        x, y = current_pos
        env["bounding box"][id_] = (x, y, 0, 0)
      elif item["type"] == "coordinate":
        if "relative" in item and item["relative"]:
          if current_pos is None:
            raise Exception("Current position is None")
          x, y = current_pos
          new_pos = (x + dist_to_num(item["x"]), y + dist_to_num(item["y"]))
        else:
          new_pos = (dist_to_num(item["x"]), dist_to_num(item["y"]))
      elif item["type"] == "intersection":
        name1, name2 = item["name1"], item["name2"]
        anchor1, anchor2 = "center", "center"
        if "anchor1" in item:
          anchor1 = item["anchor1"]
        if "anchor2" in item:
          anchor2 = item["anchor2"]
        x, _ = get_anchor_pos(env["bounding box"][name1], anchor1)
        _, y = get_anchor_pos(env["bounding box"][name2], anchor2)
        new_pos = (x, y)
      elif item["type"] == "line":
        if to_draw is not None:
          raise Exception(f"Expected position, got line")
        to_draw = item
      elif item["type"] == "rectangle":
        if to_draw is not None:
          raise Exception(f"Expected position, got rectangle")
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

            straight = "in" not in to_draw and "out" not in to_draw

            if straight:
              if current_pos_clip:
                cliped_pos = clip_line(x0, y0, x1, y1, current_pos_clip)
                if cliped_pos is None:
                  to_draw = None
                  if new_pos is not None:
                    current_pos = new_pos
                    current_pos_clip = new_pos_clip
                    new_pos = None
                  continue
                x0, y0 = cliped_pos

              if new_pos_clip:
                cliped_pos = clip_line(x1, y1, x0, y0, new_pos_clip)
                if cliped_pos is None:
                  to_draw = None
                  if new_pos is not None:
                    current_pos = new_pos
                    current_pos_clip = new_pos_clip
                    new_pos = None
                  continue
                x1, y1 = cliped_pos

              env["segments"].append(("line", (x0, y0, x1, y1), obj))

              x0p, y0p = map_point(x0, y0, cs)
              x1p, y1p = map_point(x1, y1, cs)

              if "line.width" in obj:
                width = float(obj["line.width"])
              else:
                width = None
              if "color" in obj:
                color = obj["color"]
              else:
                color = "black"
              dashed = 2 if "dashed" in obj else None

              if arrow:
                arrow = tk.LAST
              elif rarrow:
                arrow = tk.FIRST
              elif darrow:
                arrow = tk.BOTH
              else:
                arrow = None

              if is_selected:
                canvas.create_line((x0p, y0p, x1p, y1p), fill="red", dash=6,
                                   width=width+4 if width is not None else 4)
              canvas.create_line((x0p, y0p, x1p, y1p), fill=color_to_tk(color),
                                 width=width, arrow=arrow, dash=dashed)

              if "annotates" in to_draw:
                for annotate in to_draw["annotates"]:
                  if "at.start" in annotate:
                    t = 1
                  elif "near.start" in annotate:
                    t = 0.8
                  elif "midway" in annotate:
                    t = 0.5
                  elif "near.end" in annotate:
                    t = 0.2
                  elif "at.end" in annotate:
                    t = 0
                  else:
                    t = 0.5
                  x = x0 * t + x1 * (1 - t)
                  y = y0 * t + y1 * (1 - t)
                  angle = None
                  if "sloped" in annotate:
                    angle = (get_angle(x0, y0, x1, y1) + 180) % 360
                    if angle > 270 or angle < 90:
                      angle = (angle + 180) % 360
                  BoxDrawer._draw(canvas, annotate, env, position=(x, y), angle=angle)
            else:
              points = [[x0, y0]]
              dist = math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))

              if "out" in to_draw:
                out_degree = to_draw["out"]
                dy = math.sin(out_degree / 180 * math.pi) * dist / 3
                dx = math.cos(out_degree / 180 * math.pi) * dist / 3
                if current_pos_clip:
                  cx, cy, cw, ch = current_pos_clip
                  diagnal = math.sqrt(cw*cw + ch*ch)
                  start_point = clip_line(x0, y0,
                      x0 + dx * diagnal / dist * 3,
                      y0 + dy * diagnal / dist * 3, current_pos_clip)
                  assert start_point is not None
                  x0, y0 = start_point
                  points[0] = [x0, y0]
                points.append([x0 + dx, y0 + dy])

              if "in" in to_draw:
                in_degree = to_draw["in"]
                dy = math.sin(in_degree / 180 * math.pi) * dist / 3
                dx = math.cos(in_degree / 180 * math.pi) * dist / 3
                if new_pos_clip:
                  cx, cy, cw, ch = current_pos_clip
                  diagnal = math.sqrt(cw*cw + ch*ch)
                  end_point = clip_line(x1, y1,
                      x1 + dx * diagnal / dist * 3,
                      y1 + dy * diagnal / dist * 3, new_pos_clip)
                  assert end_point is not None
                  x1, y1 = end_point
                points.append([x1 + dx, y1 + dy])
              points.append([x1, y1])

              dist = math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))
              steps = max(int(dist / 0.01) + 1, 20)
              curve = Bezier.generate_line_segments(*points, steps=steps)

              if current_pos_clip:
                curve = clip_curve(curve, current_pos_clip)
                if curve is None:
                  to_draw = None
                  if new_pos is not None:
                    current_pos = new_pos
                    current_pos_clip = new_pos_clip
                    new_pos = None
                  continue

              if new_pos_clip:
                curve = list(reversed(clip_curve(list(reversed(curve)), new_pos_clip)))
                if curve is None:
                  to_draw = None
                  if new_pos is not None:
                    current_pos = new_pos
                    current_pos_clip = new_pos_clip
                    new_pos = None
                  continue

              env["segments"].append(("curve", curve, obj))
              screen_curve = [map_point(x, y, cs) for x, y in curve]

              if "line.width" in obj:
                width = float(obj["line.width"])
              else:
                width = None
              if "color" in obj:
                color = obj["color"]
              else:
                color = "black"
              dashed = 2 if "dashed" in obj else None

              if arrow:
                arrow = tk.LAST
              elif rarrow:
                arrow = tk.FIRST
              elif darrow:
                arrow = tk.BOTH
              else:
                arrow = None

              if is_selected:
                canvas.create_line(*[e for x, y in screen_curve for e in (x, y)],
                                   fill="red", dash=6,
                                   width=width+4 if width is not None else 4)
              canvas.create_line(*[e for x, y in screen_curve for e in (x, y)],
                                 fill=color_to_tk(color), width=width,
                                 arrow=arrow, dash=dashed)

              if "annotates" in to_draw:
                for annotate in to_draw["annotates"]:
                  if "at.start" in annotate:
                    t = 1
                  elif "near.start" in annotate:
                    t = 0.8
                  elif "midway" in annotate:
                    t = 0.5
                  elif "near.end" in annotate:
                    t = 0.2
                  elif "at.end" in annotate:
                    t = 0
                  else:
                    t = 0.5
                  x, y = curve[int((len(curve)-1) * (1-t))]
                  angle = None
                  if "sloped" in annotate:
                    if t == 0:
                      x0, y0 = curve[len(curve)-2]
                      x1, y1 = x, y
                    else:
                      x0, y0 = x, y
                      x1, y1 = curve[int((len(curve)-1) * (1-t))+1]
                    angle = (get_angle(x0, y0, x1, y1) + 180) % 360
                    if angle > 270 or angle < 90:
                      angle = (angle + 180) % 360
                  BoxDrawer._draw(canvas, annotate, env, position=(x, y), angle=angle)
        elif to_draw["type"] == "rectangle":
          if current_pos is None:
            raise Exception("No starting position for rectangle")
          if draw:
            x0, y0 = current_pos
            x1, y1 = new_pos

            x0, x1 = min(x0, x1), max(x0, x1)
            y0, y1 = min(y0, y1), max(y0, y1)

            env["segments"].append(("rectangle", (x0, y0, x1, y1), obj))

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
            if "fill" in obj:
              fill = obj["fill"]
            else:
              fill = ""
            dashed = 2 if "dashed" in obj else None

            if is_selected:
              canvas.create_rectangle((x0p-5, y0p+5, x1p+5, y1p-5), fill="", outline="red", dash=4)
            canvas.create_rectangle((x0p, y0p, x1p, y1p), fill=color_to_tk(fill),
                                    outline=color_to_tk(color), width=width, dash=dashed)

        to_draw = None

      if new_pos is not None:
        if is_selected:
          x, y = new_pos
          x, y = map_point(x, y, cs)
          if "line.width" in obj:
            width = 5 + float(obj["line.width"])
          else:
            width = 5
          if index == env["selected path position"]:
            canvas.create_oval(x-width-2, y-width-2, x+width+2, y+width+2, outline="black", fill="yellow")
            canvas.create_text(x, y, text=str(position_number), fill="blue")
          else:
            canvas.create_oval(x-width, y-width, x+width, y+width, outline="red", dash=2)
        if current_pos is None:
          starting_pos = new_pos
        current_pos = new_pos
        current_pos_clip = new_pos_clip
        position_number += 1
        new_pos = None

    if to_draw is not None:
      raise Exception(f"Undrawn item {to_draw}")

    if env["finding prefix"] is not None:
      candidate_code = env["get_candidate_code"](obj)
      if candidate_code is not None:
        x0, y0 = map_point(*starting_pos, cs)
        ftext = canvas.create_text(x0, y0, anchor="nw", text=candidate_code, fill="black")
        fback = canvas.create_rectangle(canvas.bbox(ftext), fill="yellow", outline="blue")
        canvas.tag_lower(fback, ftext)
