import tkinter as tk
import math
import copy
from PIL import Image
from PIL import ImageTk
from english2tikz.utils import *
from english2tikz.latex import text_to_latex_image_path
from english2tikz.gui.object_utils import *
from english2tikz.gui.image_utils import *


"""
The LaTeX equations are smaller than expected.
"""
line_width_ratio = 2.5
latex_scale_ratio = 0.42
font_size = 40


def create_text(canvas, x, y, obj, scale, cs_scale,
                text_color, text_width, angle=0):
  if need_latex(obj["text"]):
    try:
      return canvas.create_image(
          x, y,
          image=get_image_from_path(
              text_to_latex_image_path(obj["text"], text_color, text_width),
              scale * latex_scale_ratio, obj["id"], angle))
    except tk.TclError:
      return canvas.create_image(
          x, y,
          image=get_image_from_path(
              text_to_latex_image_path(obj["text"], text_color, text_width),
              scale * latex_scale_ratio, obj["id"], angle, recreate=True))
  return canvas.create_text(
      x, y, text=obj["text"],
      fill=color_to_tk(text_color),
      font=("Times New Roman", int(font_size * scale), "normal"),
      width=dist_to_num(text_width) * scale * cs_scale
      if text_width is not None else None,
      angle=angle % 360)


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

  def _precompute_text_size(canvas, obj, scale, cs_scale, inner_sep):
    text_width = get_default(obj, "text.width")
    tmptext = create_text(canvas, 0, 0, obj, scale,
                          cs_scale, "black", text_width)
    x0, y0, x1, y1 = canvas.bbox(tmptext)
    canvas.delete(tmptext)
    width = (x1 - x0) / cs_scale + inner_sep * 2 * scale
    height = (y1 - y0) / cs_scale + inner_sep * 2 * scale
    return width, height

  def _compute_object_size(canvas, obj, cs_scale):
    circle = "circle" in obj
    ellipse = "ellipse" in obj
    text = get_default(obj, "text")
    inner_sep = dist_to_num(get_default(obj, "inner.sep", 0.1))
    scale = float(get_default(obj, "scale", 1))
    if text:
      width, height = BoxDrawer._precompute_text_size(
          canvas, obj, scale, cs_scale, inner_sep)
    else:
      width = inner_sep * 2 * scale
      height = inner_sep * 2 * scale

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

    return width, height

  def _draw(canvas, obj, env, position=None, slope=0):
    id_ = get_default(obj, "id")
    assert id_ is not None
    selected = env["selection"].selected(obj)
    finding = env["finding"]
    cs = env["coordinate system"]
    cs_scale = cs._scale

    angle = dist_to_num(get_default(obj, "rotate", 0)) + slope
    scale = float(get_default(obj, "scale", 1))
    circle = "circle" in obj
    ellipse = "ellipse" in obj
    fill = get_default(obj, "fill", "")
    line_width = get_default(obj, "line.width")
    if line_width is not None:
      line_width = dist_to_num(line_width) * line_width_ratio
    dash = 2 if "dashed" in obj else None
    if line_width is not None and dash is not None:
      dash = int(dash * line_width)
    rounded_corners = get_rounded_corners(obj, 0.2)
    draw = draw_border(obj)
    color = get_draw_color(obj)
    text_color = get_text_color(obj)
    text = get_default(obj, "text")
    text_width = get_default(obj, "text.width")
    width, height = BoxDrawer._compute_object_size(canvas, obj, cs_scale)
    direction = get_direction_of(obj)
    bounding_boxes = env["bounding box"]

    anchor = get_default(obj, "anchor")
    if anchor is None and direction is not None:
      anchor = direction_to_anchor(flipped(direction))
    anchor = anchor if anchor is not None else "center"

    x, y = get_original_pos(obj, bounding_boxes, position)
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

    anchorx, anchory = BoundingBox._get_anchor_pos(
        (x, y, width, height), anchor)
    bb = BoundingBox(x, y, width, height, shape=get_shape(obj),
                     angle=none_or(angle, 0), center=(anchorx, anchory),
                     obj=obj)
    bounding_boxes[obj["id"]] = bb
    centerx, centery = bb.get_anchor_pos("center")

    x0, y0 = cs.map_point(x, y)
    x1, y1 = cs.map_point(x + width, y + height)
    anchor_screen_x, anchor_screen_y = cs.map_point(anchorx, anchory)
    center_screen_x, center_screen_y = cs.map_point(centerx, centery)
    draw_fill_style = {
        "fill": color_to_tk(fill),
        "outline": color_to_tk(color),
        "width": line_width,
        "dash": dash,
    }
    select_buff = 5
    select_style = {
        "fill": "",
        "outline": "red",
        "dash": 2,
    }
    rotate_options = {
        "rotate_center": (anchor_screen_x, anchor_screen_y),
        "angle": angle,
    }
    rotate_draw_fill_style = {
        **draw_fill_style,
        **rotate_options,
    }
    rotate_select_style = {
        **select_style,
        **rotate_options,
    }

    if circle:
      if fill or draw:
        radius = width / 2 * cs_scale
        rx0, ry0 = center_screen_x - radius, center_screen_y - radius
        rx1, ry1 = center_screen_x + radius, center_screen_y + radius
        canvas.create_oval((rx0, ry0, rx1, ry1), **draw_fill_style)
      if selected:
        canvas.create_oval((rx0 - select_buff, ry0 - select_buff,
                            rx1 + select_buff, ry1 + select_buff),
                           **select_style)
    elif ellipse:
      if angle != 0:
        if fill or draw:
          BoxDrawer.rotated_oval(canvas, x0, y0, x1, y1,
                                 **rotate_draw_fill_style)
        if selected:
          BoxDrawer.rotated_oval(canvas, x0 - select_buff, y0 + select_buff,
                                 x1 + select_buff, y1 - select_buff,
                                 **rotate_select_style)
      else:
        if fill or draw:
          canvas.create_oval((x0, y0, x1, y1), **draw_fill_style)
        if selected:
          canvas.create_oval(x0 - select_buff, y0 + select_buff,
                             x1 + select_buff, y1 - select_buff,
                             **select_style)
    elif rounded_corners:
      if fill or draw:
        BoxDrawer.round_rectangle(canvas, x0, y0, x1, y1,
                                  radius=rounded_corners*cs._scale,
                                  **rotate_draw_fill_style)
      if selected:
        BoxDrawer.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5,
                                  radius=rounded_corners * cs._scale,
                                  **rotate_select_style)
    else:
      if angle != 0:
        if fill or draw:
          canvas.create_polygon(
              BoxDrawer.rotate_rect(x0, y0, x1, y1, anchor_screen_x,
                                    anchor_screen_y, angle),
              **draw_fill_style)
        if selected:
          canvas.create_polygon(
              BoxDrawer.rotate_rect(x0 - select_buff, y0 + select_buff,
                                    x1 + select_buff, y1 - select_buff,
                                    anchor_screen_x, anchor_screen_y, angle),
              **select_style)
      else:
        if fill or draw:
          canvas.create_rectangle((x0, y0, x1, y1), **draw_fill_style)
        if selected:
          canvas.create_rectangle(x0 - select_buff, y0 + select_buff,
                                  x1 + select_buff, y1 - select_buff,
                                  **select_style)

    if text:
      create_text(canvas, center_screen_x, center_screen_y,
                  obj, scale, cs_scale, text_color, text_width, angle)

    if selected:
      canvas.create_oval(anchor_screen_x - 3, anchor_screen_y - 3,
                         anchor_screen_x + 3, anchor_screen_y + 3,
                         fill="#77ff77", outline="green")

    if finding is not None:
      candidate_code = finding.get_chopped_code(obj)
      if candidate_code is not None:
        label_pos = cs.map_point(*bb.get_anchor_pos("north.west"))
        ftext = canvas.create_text(
            label_pos, anchor="nw", text=candidate_code, fill="black")
        fback = canvas.create_rectangle(
            canvas.bbox(ftext), fill="yellow", outline="blue")
        canvas.tag_lower(fback, ftext)

  def rotate_rect(x0, y0, x1, y1, centerx, centery, angle):
    rx0, ry0 = rotate(x0, y0, centerx, centery, angle)
    rx1, ry1 = rotate(x0, y1, centerx, centery, angle)
    rx2, ry2 = rotate(x1, y1, centerx, centery, angle)
    rx3, ry3 = rotate(x1, y0, centerx, centery, angle)
    return rx0, ry0, rx1, ry1, rx2, ry2, rx3, ry3

  def round_rectangle(canvas, x1, y1, x2, y2, radius=25, angle=0,
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

    if angle != 0 and rotate_center is not None:
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
    line_width = get_default(obj, "line.width")
    if line_width is not None:
      line_width = dist_to_num(line_width) * line_width_ratio
    arrow = "stealth" in obj or "arrow" in obj
    rarrow = "reversed.stealth" in obj or "reversed.arrow" in obj
    darrow = "double.stealth" in obj or "double.arrow" in obj
    if arrow:
      arrow = tk.LAST
    elif rarrow:
      arrow = tk.FIRST
    elif darrow:
      arrow = tk.BOTH
    else:
      arrow = None
    starting_pos = None
    current_pos = None
    current_pos_clip = None
    position_number = 0
    to_draw = None
    first_segment = None
    cs = env["coordinate system"]
    selection = env["selection"]
    finding = env["finding"]
    bounding_boxes = env["bounding box"]
    is_selected = selection.selected(obj)
    for index, item in enumerate(obj["items"]):
      segment_id = f"segment_{id(obj)}_{index}"
      new_pos = None
      new_pos_clip = None
      if is_type(item, "nodename"):
        name = item["name"]
        anchor = get_default(item, "anchor")
        xshift = dist_to_num(get_default(item, "xshift", 0))
        yshift = dist_to_num(get_default(item, "yshift", 0))
        if anchor is None:
          """
          anchor = None or anchor = "center" is different here, and only here:
          1. if the line is clipped by the bounding box of the node
          2. if the xshift and yshift take affect
          """
          new_pos_clip = bounding_boxes[name]
          anchor = "center"
          xshift, yshift = 0, 0
        x, y = bounding_boxes[name].get_anchor_pos(anchor)
        new_pos = (x + xshift, y + yshift)
      elif is_type(item, "point"):
        bounding_boxes[item["id"]] = BoundingBox(*current_pos, 0, 0)
      elif is_type(item, "coordinate"):
        dx = dist_to_num(get_default(item, "x", 0))
        dy = dist_to_num(get_default(item, "y", 0))
        if get_default(item, "relative", False):
          if current_pos is None:
            raise Exception("Current position is None")
          x, y = current_pos
          new_pos = (x + dx, y + dy)
        else:
          new_pos = (dx, dy)
      elif is_type(item, "intersection"):
        name1, name2 = item["name1"], item["name2"]
        anchor1 = get_default(item, "anchor1", "center")
        anchor2 = get_default(item, "anchor2", "center")
        x, _ = bounding_boxes[name1].get_anchor_pos(anchor1)
        _, y = bounding_boxes[name2].get_anchor_pos(anchor2)
        new_pos = (x, y)
      elif is_type(item, "cycle"):
        assert starting_pos is not None, "Starting position not set yet"
        new_pos = starting_pos
      elif is_type(item, "line"):
        assert to_draw is None, "Expected position, got line"
        to_draw = item
      elif is_type(item, "rectangle"):
        assert to_draw is None, "Expected position, got rectangle"
        to_draw = item
      else:
        raise Exception(f"Unsupported path item type {item['type']}")

      if new_pos is not None and to_draw is not None:
        assert current_pos is not None, "No starting position for line"
        citem = PathDrawer._draw_item(canvas, to_draw, *current_pos, *new_pos,
                                      current_pos_clip, new_pos_clip,
                                      is_selected, arrow, obj, segment_id, env)
        if first_segment is None:
          first_segment = citem
        to_draw = None

      if new_pos is not None:
        if is_selected:
          x, y = cs.map_point(*new_pos)
          if selection.selected_position(index):
            radius = 7
            canvas.create_oval(x-radius, y-radius, x+radius,
                               y+radius, outline="black", fill="yellow")
            canvas.create_text(x, y, text=str(position_number), fill="blue")
          else:
            radius = none_or(line_width, 1)+5
            canvas.create_oval(x-radius, y-radius, x+radius,
                               y+radius, outline="red", dash=2)
        if starting_pos is None:
          starting_pos = new_pos
        current_pos = new_pos
        current_pos_clip = new_pos_clip
        position_number += 1
        fill_polygon.append(new_pos)
        new_pos = None

    assert to_draw is None, f"Undrawn item {to_draw}"

    if fill and len(fill_polygon) > 2:
      fill_polygon = [e for x, y in fill_polygon for e in cs.map_point(x, y)]
      p = canvas.create_polygon(fill_polygon, fill=color_to_tk(obj["fill"]),
                                outline="")
      canvas.tag_lower(p, first_segment)

    if finding is not None:
      candidate_code = finding.get_chopped_code(obj)
      if candidate_code is not None:
        x0, y0 = cs.map_point(*starting_pos)
        ftext = canvas.create_text(
            x0, y0, anchor="nw", text=candidate_code, fill="black")
        fback = canvas.create_rectangle(
            canvas.bbox(ftext), fill="yellow", outline="blue")
        canvas.tag_lower(fback, ftext)

  def _draw_item(canvas, item, x0, y0, x1, y1, current_pos_clip, new_pos_clip,
                 is_selected, arrow, path, segment_id, env):
    line_width = get_default(path, "line.width")
    if line_width is not None:
      line_width = dist_to_num(line_width) * line_width_ratio
    dash = 2 if "dashed" in path else None
    if line_width is not None and dash is not None:
      dash = int(dash * line_width)
    color = get_default(path, "color", "black")
    draw = "draw" in path
    fill = get_default(path, "fill", "")
    cs = env["coordinate system"]
    bounding_boxes = env["bounding box"]
    ret = None

    if is_type(item, "line"):
      line_style = {
          "fill": color,
          "width": line_width,
          "arrow": arrow,
          "dash": dash,
      }
      select_style = {
          "fill": "red",
          "width": int(none_or(line_width, 1)) + 4,
          "dash": int(none_or(line_width, 1)) + 4,
      }

      if "in" in item and current_pos_clip:
        diagnal = current_pos_clip.diameter()
        start_point = current_pos_clip.get_point_at_direction(
            x0 + dx * diagnal / dist * 3,
            y0 + dy * diagnal / dist * 3)
        assert start_point is not None
        x0, y0 = start_point

      if "out" in item and new_pos_clip:
        diagnal = new_pos_clip.diameter()
        end_point = new_pos_clip.get_point_at_direction(
            x1 + dx * diagnal / dist * 3,
            y1 + dy * diagnal / dist * 3)
        assert end_point is not None
        x1, y1 = end_point

      if "in" not in item and current_pos_clip:
        cliped_pos = current_pos_clip.get_point_at_direction(x1, y1)
        if cliped_pos is None:
          return ret
        x0, y0 = cliped_pos

      if "out" not in item and new_pos_clip:
        cliped_pos = new_pos_clip.get_point_at_direction(x0, y0)
        if cliped_pos is None:
          return ret
        x1, y1 = cliped_pos

      straight = "in" not in item and "out" not in item
      if straight:
        bounding_boxes[segment_id] = BoundingBox.from_rect(
            x0, y0, x1, y1, shape="line", obj=path)

        x0p, y0p = cs.map_point(x0, y0)
        x1p, y1p = cs.map_point(x1, y1)
        line_segments = (x0p, y0p, x1p, y1p)
      else:
        points = [[x0, y0]]
        dist = math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))
        steps = max(int(dist / 0.01) + 1, 20)

        if "out" in item:
          out_degree = int(item["out"])
          dy = math.sin(out_degree / 180 * math.pi) * dist / 3
          dx = math.cos(out_degree / 180 * math.pi) * dist / 3
          points[0] = [x0, y0]
          points.append([x0 + dx, y0 + dy])

        if "in" in item:
          in_degree = int(item["in"])
          dy = math.sin(in_degree / 180 * math.pi) * dist / 3
          dx = math.cos(in_degree / 180 * math.pi) * dist / 3
          points.append([x1 + dx, y1 + dy])
        points.append([x1, y1])

        curve = Bezier.generate_line_segments(*points, steps=steps)

        """
        Don't know why still need to clip curve. Maybe forgot to delete
        the code.
        """
        """
        if current_pos_clip:
          curve = current_pos_clip.clip_curve(curve)
          if curve is None:
            return

        if new_pos_clip:
          curve = list(
              reversed(new_pos_clip.clip_curve(list(reversed(curve)))))
          if curve is None:
            return
        """

        bounding_boxes[segment_id] = BoundingBox(
            0, 0, 0, 0, shape="curve", points=curve, obj=path)
        screen_curve = [cs.map_point(x, y) for x, y in curve]
        line_segments = [e for x, y in screen_curve for e in (x, y)]

      if is_selected:
        canvas.create_line(line_segments, **select_style)
      if draw:
        ret = canvas.create_line(line_segments, **line_style)

      if "annotates" in item:
        for annotate in item["annotates"]:
          t = get_position_in_line(annotate)
          if straight:
            x = x0 * t + x1 * (1 - t)
            y = y0 * t + y1 * (1 - t)
          else:
            x, y = curve[int((len(curve)-1) * (1-t))]

          angle = None
          if "sloped" in annotate:
            if straight:
              ax0, ay0, ax1, ay1 = x0, y0, x1, y1
            else:
              if t == 0:
                ax0, ay0 = curve[len(curve)-2]
                ax1, ay1 = x, y
              else:
                ax0, ay0 = x, y
                ax1, ay1 = curve[int((len(curve)-1) * (1-t))+1]

            angle = get_angle(ax0, ay0, ax1, ay1) % 360
            if angle < 270 and angle > 90:
              angle = (angle + 180) % 360

          BoxDrawer._draw(canvas, annotate, env,
                          position=(x, y), slope=angle)

    elif is_type(item, "rectangle"):
      line_style = {
          "fill": color_to_tk(fill),
          "outline": color_to_tk(color),
          "width": line_width,
          "dash": dash,
      }
      select_style = {
          "fill": "",
          "outline": "red",
          "dash": 2,
      }
      x0, x1 = min(x0, x1), max(x0, x1)
      y0, y1 = min(y0, y1), max(y0, y1)

      bounding_boxes[segment_id] = BoundingBox.from_rect(
          x0, y0, x1, y1, shape="rectangle", obj=path)

      x0p, y0p = cs.map_point(x0, y0)
      x1p, y1p = cs.map_point(x1, y1)

      if is_selected:
        canvas.create_rectangle((x0p-5, y0p+5, x1p+5, y1p-5), **select_style)
      if draw:
        ret = canvas.create_rectangle((x0p, y0p, x1p, y1p), **line_style)
    else:
      raise Exception(f"Unknown type {item['type']}")
    return ret
