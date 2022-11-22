import tkinter as tk
import math
from PIL import Image
from PIL import ImageTk
from english2tikz.utils import *
from english2tikz.latex import text_to_latex_image_path


line_width_ratio = 2.5


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

  def _draw(canvas, obj, env, position=None, slope=None):
    assert "id" in obj
    selection = env["selection"]
    finding = env["finding"]
    tmptext = None
    """
    The LaTeX equations are smaller than expected.
    """
    latex_scale_ratio = 0.42

    if "scale" in obj:
      scale = float(obj["scale"])
    else:
      scale = 1

    cs_scale = env["coordinate system"]["scale"]
    angle = get_default(obj, "rotate")

    if slope is not None or angle is not None:
      angle = none_or(slope, 0) + dist_to_num(none_or(angle, 0))

    circle = "circle" in obj
    ellipse = "ellipse" in obj

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

    if "text" in obj:
      text_width = get_default(obj, "text.width")
      if need_latex(obj["text"]):
        path = text_to_latex_image_path(obj["text"], text_color, text_width)
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
        tmptext = canvas.create_text(
            0, 0, text=obj["text"],
            font=default_font(font_size),
            width=dist_to_num(text_width) * scale * cs_scale
            if text_width is not None else None)
      x0, y0, x1, y1 = canvas.bbox(tmptext)

      if "inner.sep" in obj:
        inner_sep = dist_to_num(obj["inner.sep"])
      else:
        inner_sep = 0.1

      width = (x1 - x0) / cs_scale + inner_sep * 2 * scale
      height = (y1 - y0) / cs_scale + inner_sep * 2 * scale

      if circle:
        radius = math.sqrt(width*width+height*height)/2
        width, height = radius*2, radius*2
      elif ellipse:
        width *= 1.414
        height *= 1.414

    width = max(dist_to_num(get_default(obj, "width", 0)) * scale, width)
    height = max(dist_to_num(get_default(obj, "height", 0)) * scale, height)

    if circle:
      width = max(width, height)
      height = width

    anchor = get_default(obj, "anchor", "center")

    if "at" not in obj:
      if position is not None:
        x, y = position
      else:
        x, y = 0, 0
      if get_direction_of(obj) is not None:
        direction = get_direction_of(obj)
        anchor = direction_to_anchor(flipped(direction))
        at = get_default_of_type(obj, direction, str)
        if at is not None:
          at_bounding_box = env["bounding box"][at]
          at_anchor = direction_to_anchor(direction)
          x, y = at_bounding_box.get_anchor_pos(at_anchor)
          dx, dy = direction_to_num(direction)
          dist = get_default(obj, "distance", 1)
          if isinstance(dist, str) and dist.find("and") >= 0:
            disty, distx = dist_to_num(*dist.split(".and."))
          else:
            distx = dist_to_num(dist)
            disty = distx
          x += distx * dx
          y += disty * dy
    elif isinstance(obj["at"], str):
      at_bounding_box = env["bounding box"][obj["at"]]
      x, y = at_bounding_box.get_anchor_pos(
          get_default(obj, "at.anchor", "center"))
    elif obj["at"]["type"] == "coordinate":
      x = dist_to_num(obj["at"]["x"]) if "x" in obj["at"] else 0
      y = dist_to_num(obj["at"]["y"]) if "y" in obj["at"] else 0
    elif obj["at"]["type"] == "intersection":
      x, _ = env["bounding box"][obj["at"]["name1"]].get_anchor_pos(
          get_default(obj["at"], "anchor1", "center"))
      _, y = env["bounding box"][obj["at"]["name2"]].get_anchor_pos(
          get_default(obj["at"], "anchor2", "center"))
    else:
      raise Exception(f"Unsupported at {obj['at']}")

    # Move anchor to the specified location, then compute the
    # coordinate of the left-up corner
    x, y = shift_by_anchor(x, y, anchor, width, height)

    if "xshift" in obj or "yshift" in obj:
      dx, dy = dist_to_num(get_default(obj, "xshift", 0),
                           get_default(obj, "yshift", 0))
      if slope is not None:
        dx, dy = rotate(dx, dy, 0, 0, slope % 360)
      x += dx
      y += dy

    if circle:
      shape = "circle"
    elif ellipse:
      shape = "ellipse"
    else:
      shape = "rectangle"

    bb = BoundingBox(
        x, y, width, height,
        shape=shape,
        angle=none_or(angle, 0),
        center=BoundingBox._get_anchor_pos((x, y, width, height), anchor),
        obj=obj)
    env["bounding box"][obj["id"]] = bb

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

    x0, y0 = map_point(x, y, cs)
    x1, y1 = map_point(x + width, y + height, cs)
    anchorx, anchory = BoundingBox._get_anchor_pos(
        (x, y, width, height), anchor)
    anchor_screen_x, anchor_screen_y = map_point(anchorx, anchory, cs)
    if angle is None:
      r = None
      if fill or draw:
        if circle or ellipse:
          r = canvas.create_oval((x0, y0, x1, y1),
                                 fill=color_to_tk(fill),
                                 outline=color_to_tk(color),
                                 width=line_width * line_width_ratio
                                 if line_width is not None else None,
                                 dash=dash)
        elif rounded_corners:
          r = BoxDrawer.round_rectangle(canvas, x0, y0, x1, y1,
                                        radius=rounded_corners*cs["scale"],
                                        fill=color_to_tk(fill),
                                        outline=color_to_tk(color),
                                        width=line_width * line_width_ratio
                                        if line_width is not None else None,
                                        dash=dash)
        else:
          r = canvas.create_rectangle((x0, y0, x1, y1),
                                      fill=color_to_tk(fill),
                                      outline=color_to_tk(color),
                                      width=line_width * line_width_ratio
                                      if line_width is not None else None,
                                      dash=dash)
      if "text" in obj and obj["text"]:
        text_width = get_default(obj, "text.width")
        center_x, center_y = BoundingBox._get_anchor_pos(
            (x, y, width, height), "center")
        x, y = map_point(center_x, center_y, cs)
        if need_latex(obj["text"]):
          if tmptext is None:
            path = text_to_latex_image_path(
                obj["text"], text_color, text_width)
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
            canvas.create_text(
                x, y, text=obj["text"],
                fill=color_to_tk(text_color),
                font=default_font(font_size),
                width=dist_to_num(text_width) * scale * cs_scale
                if text_width is not None else None)
          else:
            canvas.move(tmptext, x, y)
            canvas.itemconfig(tmptext, fill=color_to_tk(text_color))
            if r:
              canvas.tag_lower(r, tmptext)
      if selection.selected(obj):
        if circle or ellipse:
          canvas.create_oval(x0 - 5, y0 + 5, x1 + 5, y1 - 5,
                             fill="", outline="red", dash=2)
        elif rounded_corners:
          BoxDrawer.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5,
                                    radius=rounded_corners * cs["scale"],
                                    fill="", outline="red", dash=2)
        else:
          canvas.create_rectangle(
              x0 - 5, y0 + 5, x1 + 5, y1 - 5, outline="red", dash=2, fill="")

    else:
      r = None
      if fill or draw:
        if circle:
          centerx, centery = (x0 + x1) / 2, (y0 + y1) / 2
          radius = max(abs(x1 - x0), abs(y1 - y0)) / 2
          newx, newy = rotate(centerx, centery,
                              anchor_screen_x,
                              anchor_screen_y,
                              angle)
          rx0, ry0 = newx - radius, newy - radius
          rx1, ry1 = newx + radius, newy + radius
          r = canvas.create_oval((rx0, ry0, rx1, ry1),
                                 fill=color_to_tk(fill),
                                 outline=color_to_tk(color),
                                 width=line_width * line_width_ratio)
        elif ellipse:
          r = BoxDrawer.rotated_oval(canvas, x0, y0, x1, y1,
                                     angle=angle,
                                     rotate_center=(anchor_screen_x,
                                                    anchor_screen_y),
                                     fill=color_to_tk(fill),
                                     outline=color_to_tk(color),
                                     width=line_width * line_width_ratio)
        elif rounded_corners:
          r = BoxDrawer.round_rectangle(canvas, x0, y0, x1, y1,
                                        radius=rounded_corners*cs["scale"],
                                        fill=color_to_tk(fill),
                                        outline=color_to_tk(color),
                                        width=line_width * line_width_ratio,
                                        angle=angle,
                                        rotate_center=(anchor_screen_x,
                                                       anchor_screen_y))
        else:
          rx0, ry0 = rotate(x0, y0, anchor_screen_x, anchor_screen_y, angle)
          rx1, ry1 = rotate(x0, y1, anchor_screen_x, anchor_screen_y, angle)
          rx2, ry2 = rotate(x1, y1, anchor_screen_x, anchor_screen_y, angle)
          rx3, ry3 = rotate(x1, y0, anchor_screen_x, anchor_screen_y, angle)
          r = canvas.create_polygon((rx0, ry0, rx1, ry1, rx2, ry2, rx3, ry3),
                                    fill=color_to_tk(fill),
                                    outline=color_to_tk(color),
                                    width=line_width * line_width_ratio
                                    if line_width is not None else None)

      if "text" in obj and obj["text"]:
        text_width = get_default(obj, "text.width")
        center_x, center_y = BoundingBox._get_anchor_pos(
            (x, y, width, height), "center")
        anchor_x, anchor_y = BoundingBox._get_anchor_pos(
            (x, y, width, height), anchor)
        rotated_x, rotated_y = rotate(
            center_x, center_y, anchor_x, anchor_y, 360-angle)

        x, y = map_point(rotated_x, rotated_y, cs)
        if need_latex(obj["text"]):
          if tmptext is not None:
            canvas.delete(tmptext)
          path = text_to_latex_image_path(obj["text"], text_color, text_width)
          if (path, scale, angle, obj["id"]) not in env["image references"]:
            img = Image.open(path)
            img = img.convert("RGBA")
            w, h = img.size
            img = img.resize((int(w * scale * latex_scale_ratio),
                              int(h * scale * latex_scale_ratio)))
            if angle != 0:
              img = img.rotate(angle % 360, expand=True)
            image = ImageTk.PhotoImage(img)
            env["image references"][(path, scale, angle, obj["id"])] = image
          else:
            image = env["image references"][(path, scale, angle, obj["id"])]
          canvas.create_image(x, y, image=image)
        else:
          if tmptext is None:
            canvas.create_text(
                x, y, text=obj["text"],
                fill=color_to_tk(text_color),
                font=("Times New Roman", font_size, "normal"),
                width=dist_to_num(text_width) * scale * cs_scale
                if text_width is not None else None,
                angle=angle % 360)
          else:
            canvas.move(tmptext, x, y)
            canvas.itemconfig(tmptext, fill=color_to_tk(
                text_color), angle=angle % 360)
            if r:
              canvas.tag_lower(r, tmptext)

      if selection.selected(obj):
        if circle:
          centerx, centery = (x0 + x1) / 2, (y0 + y1) / 2
          radius = max(abs(x1 - x0), abs(y1 - y0)) / 2
          newx, newy = rotate(centerx, centery,
                              anchor_screen_x,
                              anchor_screen_y,
                              angle)
          rx0, ry0 = newx - radius, newy - radius
          rx1, ry1 = newx + radius, newy + radius
          r = canvas.create_oval((rx0 - 5, ry0 - 5, rx1 + 5, ry1 + 5),
                                 fill="", outline="red", dash=2)
        elif ellipse:
          r = BoxDrawer.rotated_oval(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5,
                                     angle=angle,
                                     rotate_center=(anchor_screen_x,
                                                    anchor_screen_y),
                                     fill="", outline="red", dash=2)
        elif rounded_corners:
          BoxDrawer.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5,
                                    radius=rounded_corners*cs["scale"],
                                    angle=angle,
                                    rotate_center=(anchor_screen_x,
                                                   anchor_screen_y),
                                    fill="", outline="red", dash=2)
        else:
          rx0, ry0 = rotate(x0 - 5, y0 + 5, anchor_screen_x,
                            anchor_screen_y, angle)
          rx1, ry1 = rotate(x0 - 5, y1 - 5, anchor_screen_x,
                            anchor_screen_y, angle)
          rx2, ry2 = rotate(x1 + 5, y1 - 5, anchor_screen_x,
                            anchor_screen_y, angle)
          rx3, ry3 = rotate(x1 + 5, y0 + 5, anchor_screen_x,
                            anchor_screen_y, angle)
          canvas.create_polygon((rx0, ry0, rx1, ry1, rx2, ry2, rx3, ry3),
                                outline="red", dash=2, fill="")

    if selection.selected(obj):
      canvas.create_oval(anchor_screen_x - 3, anchor_screen_y - 3,
                         anchor_screen_x + 3, anchor_screen_y + 3,
                         fill="#77ff77", outline="green")

    if finding is not None:
      candidate_code = finding.get_chopped_code(obj)
      if candidate_code is not None:
        label_pos = map_point(*bb.get_anchor_pos("north.west"), cs)
        ftext = canvas.create_text(
            label_pos, anchor="nw", text=candidate_code, fill="black")
        fback = canvas.create_rectangle(
            canvas.bbox(ftext), fill="yellow", outline="blue")
        canvas.tag_lower(fback, ftext)

  def round_rectangle(canvas, x1, y1, x2, y2, radius=25, angle=None,
                      rotate_center=None, **kwargs):
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

  def rotated_oval(canvas, x1, y1, x2, y2, angle=None,
                   rotate_center=None, **kwargs):
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    centerx, centery = (x1 + x2) / 2, (y1 + y2) / 2
    radiusx, radiusy = (x2 - x1) / 2, (y2 - y1) / 2
    steps = max(int((radiusx + radiusy) / 0.02), 50)
    points = [(math.cos(i*math.pi*2/steps) * radiusx + centerx,
               math.sin(i*math.pi*2/steps) * radiusy + centery)
              for i in range(steps)]

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
    fill = "fill" in obj
    fill_polygon = []
    arrow = "stealth" in obj or "arrow" in obj
    rarrow = "reversed.stealth" in obj or "reversed.arrow" in obj
    darrow = "double.stealth" in obj or "double.arrow" in obj
    starting_pos = None
    current_pos = None
    current_pos_clip = None
    position_number = 0
    to_draw = None
    first_segment = None
    cs = env["coordinate system"]
    selection = env["selection"]
    finding = env["finding"]
    is_selected = selection.selected(obj)
    for index, item in enumerate(obj["items"]):
      segment_id = f"segment_{id(obj)}_{index}"
      new_pos = None
      new_pos_clip = None
      if item["type"] == "nodename":
        name = item["name"]
        anchor = get_default(item, "anchor")
        new_pos = env["bounding box"][name].get_anchor_pos(
            none_or(anchor, "center"))
        if anchor is None:
          new_pos_clip = env["bounding box"][name]
        elif "xshift" in item or "yshift" in item:
          x, y = new_pos
          if "xshift" in item:
            x += dist_to_num(item["xshift"])
          if "yshift" in item:
            y += dist_to_num(item["yshift"])
          new_pos = (x, y)
      elif item["type"] == "point":
        id_ = item["id"]
        x, y = current_pos
        env["bounding box"][id_] = BoundingBox(x, y, 0, 0)
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
        anchor1 = get_default(item, "anchor1", "center")
        anchor2 = get_default(item, "anchor2", "center")
        x, _ = env["bounding box"][name1].get_anchor_pos(anchor1)
        _, y = env["bounding box"][name2].get_anchor_pos(anchor2)
        new_pos = (x, y)
      elif item["type"] == "cycle":
        if starting_pos is None:
          raise Exception("Starting position not set yet")
        new_pos = starting_pos
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

          x0, y0 = current_pos
          x1, y1 = new_pos

          straight = "in" not in to_draw and "out" not in to_draw

          if straight:
            if current_pos_clip:
              cliped_pos = current_pos_clip.get_point_at_direction(x1, y1)
              if cliped_pos is None:
                to_draw = None
                if new_pos is not None:
                  current_pos = new_pos
                  current_pos_clip = new_pos_clip
                  new_pos = None
                continue
              x0, y0 = cliped_pos

            if new_pos_clip:
              cliped_pos = new_pos_clip.get_point_at_direction(x0, y0)
              if cliped_pos is None:
                to_draw = None
                if new_pos is not None:
                  current_pos = new_pos
                  current_pos_clip = new_pos_clip
                  new_pos = None
                continue
              x1, y1 = cliped_pos

            env["bounding box"][segment_id] = BoundingBox.from_rect(
                x0, y0, x1, y1, shape="line", obj=obj)

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
                                 width=(width+4) * line_width_ratio
                                 if width is not None
                                 else 4 * line_width_ratio)
            if draw:
              h = canvas.create_line((x0p, y0p, x1p, y1p),
                                     fill=color_to_tk(color),
                                     width=width * line_width_ratio
                                     if width is not None else None,
                                     arrow=arrow, dash=dashed)
              if first_segment is None:
                first_segment = h

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
                  angle = get_angle(x0, y0, x1, y1) % 360
                  if angle < 270 and angle > 90:
                    angle = (angle + 180) % 360
                BoxDrawer._draw(canvas, annotate, env,
                                position=(x, y), slope=angle)
          else:
            points = [[x0, y0]]
            dist = math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))

            if "out" in to_draw:
              out_degree = int(to_draw["out"])
              dy = math.sin(out_degree / 180 * math.pi) * dist / 3
              dx = math.cos(out_degree / 180 * math.pi) * dist / 3
              if current_pos_clip:
                diagnal = current_pos_clip.diameter()
                start_point = current_pos_clip.get_point_at_direction(
                    x0 + dx * diagnal / dist * 3,
                    y0 + dy * diagnal / dist * 3)
                assert start_point is not None
                x0, y0 = start_point
                points[0] = [x0, y0]
              points.append([x0 + dx, y0 + dy])

            if "in" in to_draw:
              in_degree = int(to_draw["in"])
              dy = math.sin(in_degree / 180 * math.pi) * dist / 3
              dx = math.cos(in_degree / 180 * math.pi) * dist / 3
              if new_pos_clip:
                diagnal = new_pos_clip.diameter()
                end_point = new_pos_clip.get_point_at_direction(
                    x1 + dx * diagnal / dist * 3,
                    y1 + dy * diagnal / dist * 3)
                assert end_point is not None
                x1, y1 = end_point
              points.append([x1 + dx, y1 + dy])
            points.append([x1, y1])

            dist = math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))
            steps = max(int(dist / 0.01) + 1, 20)
            curve = Bezier.generate_line_segments(*points, steps=steps)

            if current_pos_clip:
              curve = current_pos_clip.clip_curve(curve)
              if curve is None:
                to_draw = None
                if new_pos is not None:
                  current_pos = new_pos
                  current_pos_clip = new_pos_clip
                  new_pos = None
                continue

            if new_pos_clip:
              curve = list(
                  reversed(new_pos_clip.clip_curve(list(reversed(curve)))))
              if curve is None:
                to_draw = None
                if new_pos is not None:
                  current_pos = new_pos
                  current_pos_clip = new_pos_clip
                  new_pos = None
                continue

            env["bounding box"][segment_id] = BoundingBox(
                0, 0, 0, 0, shape="curve", points=curve, obj=obj)
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
              canvas.create_line(*[e for x, y in screen_curve
                                   for e in (x, y)],
                                 fill="red", dash=6,
                                 width=(width+4) * line_width_ratio
                                 if width is not None
                                 else 4 * line_width_ratio)
            if draw:
              h = canvas.create_line(*[e for x, y in screen_curve
                                       for e in (x, y)],
                                     fill=color_to_tk(color),
                                     width=width * line_width_ratio
                                     if width is not None else None,
                                     arrow=arrow, dash=dashed)
              if first_segment is None:
                first_segment = h

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
                  angle = get_angle(x0, y0, x1, y1) % 360
                  if angle < 270 and angle > 90:
                    angle = (angle + 180) % 360
                BoxDrawer._draw(canvas, annotate, env,
                                position=(x, y), slope=angle)
        elif to_draw["type"] == "rectangle":
          if current_pos is None:
            raise Exception("No starting position for rectangle")
          x0, y0 = current_pos
          x1, y1 = new_pos

          x0, x1 = min(x0, x1), max(x0, x1)
          y0, y1 = min(y0, y1), max(y0, y1)

          env["bounding box"][segment_id] = BoundingBox.from_rect(
              x0, y0, x1, y1, shape="rectangle", obj=obj)

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
            canvas.create_rectangle(
                (x0p-5, y0p+5, x1p+5, y1p-5), fill="", outline="red", dash=4)
          if draw:
            h = canvas.create_rectangle((x0p, y0p, x1p, y1p),
                                        fill=color_to_tk(fill),
                                        outline=color_to_tk(color),
                                        width=width * line_width_ratio
                                        if width is not None else None,
                                        dash=dashed)
            if first_segment is None:
              first_segment = h

        to_draw = None

      if new_pos is not None:
        if is_selected:
          x, y = new_pos
          x, y = map_point(x, y, cs)
          if "line.width" in obj:
            width = 5 + float(obj["line.width"])
          else:
            width = 5
          if selection.selected_position(index):
            canvas.create_oval(x-width-2, y-width-2, x+width+2,
                               y+width+2, outline="black", fill="yellow")
            canvas.create_text(x, y, text=str(position_number), fill="blue")
          else:
            canvas.create_oval(x-width, y-width, x+width,
                               y+width, outline="red", dash=2)
        if current_pos is None:
          starting_pos = new_pos
        current_pos = new_pos
        fill_polygon.append(new_pos)
        current_pos_clip = new_pos_clip
        position_number += 1
        new_pos = None

    if to_draw is not None:
      raise Exception(f"Undrawn item {to_draw}")

    if fill and len(fill_polygon) > 2:
      fill_polygon = [e for x, y in fill_polygon for e in map_point(x, y, cs)]
      p = canvas.create_polygon(fill_polygon, fill=color_to_tk(obj["fill"]),
                                outline="")
      canvas.tag_lower(p, first_segment)

    if finding is not None:
      candidate_code = finding.get_chopped_code(obj)
      if candidate_code is not None:
        x0, y0 = map_point(*starting_pos, cs)
        ftext = canvas.create_text(
            x0, y0, anchor="nw", text=candidate_code, fill="black")
        fback = canvas.create_rectangle(
            canvas.bbox(ftext), fill="yellow", outline="blue")
        canvas.tag_lower(fback, ftext)
