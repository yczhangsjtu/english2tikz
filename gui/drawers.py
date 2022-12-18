import tkinter as tk
import math
import copy
from PIL import Image
from PIL import ImageTk
from english2tikz.utils import *
from english2tikz.errors import *
from english2tikz.latex import text_to_latex_image_path
from english2tikz.gui.object_utils import *
from english2tikz.gui.image_utils import *
from english2tikz.gui.bezier import *
from english2tikz.gui.bounding_box import *
from english2tikz.gui.geometry import *


"""
The LaTeX equations are smaller than expected.
"""
line_width_ratio = 2.5
latex_scale_ratio = 0.42
font_size = 40


def draw_text(canvas, x, y, obj, scale, cs_scale,
              text_color, text_width, angle=0, temp=False):
  should_compile = False
  if need_latex(obj["text"]):
    should_compile = True
    image_path, ready = text_to_latex_image_path(obj["text"],
                                                 text_color,
                                                 text_width)
    if ready:
      try:
        return canvas.create_image(
            x, y,
            image=get_image_from_path(
                image_path,
                scale * latex_scale_ratio, obj["id"],
                angle))
      except tk.TclError:
        return canvas.create_image(
            x, y,
            image=get_image_from_path(
                image_path,
                scale * latex_scale_ratio, obj["id"],
                angle, recreate=True))
  ret = canvas.create_text(
      x, y, text=obj["text"],
      fill=color_to_tk(text_color),
      font=("Times New Roman", int(font_size * scale), "normal"),
      width=dist_to_num(text_width) * scale * cs_scale
      if text_width is not None else None,
      angle=angle % 360)
  if not temp and should_compile:
    canvas.create_oval(x - 10, y - 10, x + 10, y + 10,
                       fill="white", outline="black")
    canvas.create_line(x, y, x, y - 8, fill="black")
    canvas.create_line(x, y, x + 4, y - 4 * 1.732, fill="black")
  return ret


class Drawer(object):
  def match(self, obj):
    raise ConfigurationError(
        "Cannot invoke match method from base class Drawer")

  def draw(self, canvas, obj, env, hint={}):
    raise ConfigurationError(
        "Cannot invoke draw method from base class Drawer")


class BoxDrawer(Drawer):
  def match(self, obj):
    return "type" in obj and obj["type"] in ["box", "text"]

  def draw(self, canvas, obj, env, hint={}, no_new_bound_box=False):
    BoxDrawer._draw(canvas, obj, env,
                    hint=hint, no_new_bound_box=no_new_bound_box)

  def _precompute_text_size(canvas, obj, scale, cs_scale, inner_sep):
    text_width = obj.get("text.width")
    tmptext = draw_text(canvas, 0, 0, obj, scale,
                        cs_scale, "black", text_width,
                        temp=True)
    x0, y0, x1, y1 = canvas.bbox(tmptext)
    canvas.delete(tmptext)
    width = (x1 - x0) / cs_scale + inner_sep * 2 * scale
    height = (y1 - y0) / cs_scale + inner_sep * 2 * scale
    return width, height

  def _compute_object_size(canvas, obj, cs_scale):
    circle = "circle" in obj
    ellipse = "ellipse" in obj
    text = obj.get("text")
    inner_sep = dist_to_num(obj.get("inner.sep", 0.1))
    scale = float(obj.get("scale", 1))
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

    width = max(dist_to_num(obj.get("width", 0)) * scale, width)
    height = max(dist_to_num(obj.get("height", 0)) * scale, height)

    if circle:
      width = max(width, height)
      height = width

    return width, height

  def _draw(canvas, obj, env, position=None, slope=0, hint={},
            no_new_bound_box=False):
    id_ = obj.get("id")
    assert id_ is not None
    selected = env["selection"].selected(obj)
    selected_anchor = env["selection"].selected_node_anchor(id_)
    finding = env["finding"]
    cs = env["coordinate system"]
    cs_scale = cs._scale

    angle = dist_to_num(obj.get("rotate", 0)) + slope
    scale = float(obj.get("scale", 1))
    circle = "circle" in obj
    ellipse = "ellipse" in obj
    fill = obj.get("fill", "")
    line_width = obj.get("line.width")
    if line_width is not None:
      line_width = dist_to_num(line_width) * line_width_ratio
    dash = 2 if "dashed" in obj else None
    if line_width is not None and dash is not None:
      dash = int(dash * line_width)
    rounded_corners = get_rounded_corners(obj, 0.2)
    draw = draw_border(obj)
    color = get_draw_color(obj)
    text_color = get_text_color(obj)
    text = obj.get("text")
    text_width = obj.get("text.width")
    width, height = BoxDrawer._compute_object_size(canvas, obj, cs_scale)
    direction = get_direction_of(obj)
    bounding_boxes = env["bounding box"]

    anchor = obj.get("anchor")
    if anchor is None and direction is not None:
      anchor = direction_to_anchor(flipped(direction))
    anchor = anchor if anchor is not None else "center"

    x, y = get_original_pos(obj, bounding_boxes, position)
    # Move anchor to the specified location, then compute the
    # coordinate of the left-up corner
    x, y = shift_by_anchor(x, y, anchor, width, height)

    if "xshift" in obj or "yshift" in obj:
      dx, dy = dist_to_num(obj.get("xshift", 0),
                           obj.get("yshift", 0))
      if slope is not None:
        dx, dy = rotate(dx, dy, 0, 0, slope % 360)
      x += dx
      y += dy

    anchorx, anchory = BoundingBox._get_anchor_pos(
        (x, y, width, height), anchor)
    bb = BoundingBox(x, y, width, height, shape=get_shape(obj),
                     angle=none_or(angle, 0), center=(anchorx, anchory),
                     obj=obj)
    if not no_new_bound_box:
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
      radius = width / 2 * cs_scale
      rx0, ry0 = center_screen_x - radius, center_screen_y - radius
      rx1, ry1 = center_screen_x + radius, center_screen_y + radius
      if (fill or draw) and "hidden" not in obj:
        canvas.create_oval((rx0, ry0, rx1, ry1), **draw_fill_style)
      if selected:
        canvas.create_oval((rx0 - select_buff, ry0 - select_buff,
                            rx1 + select_buff, ry1 + select_buff),
                           **select_style)
    elif ellipse:
      if angle != 0:
        if (fill or draw) and "hidden" not in obj:
          BoxDrawer.rotated_oval(canvas, x0, y0, x1, y1,
                                 **rotate_draw_fill_style)
        if selected:
          BoxDrawer.rotated_oval(canvas, x0 - select_buff, y0 + select_buff,
                                 x1 + select_buff, y1 - select_buff,
                                 **rotate_select_style)
      else:
        if (fill or draw) and "hidden" not in obj:
          canvas.create_oval((x0, y0, x1, y1), **draw_fill_style)
        if selected:
          canvas.create_oval(x0 - select_buff, y0 + select_buff,
                             x1 + select_buff, y1 - select_buff,
                             **select_style)
    elif rounded_corners:
      if (fill or draw) and "hidden" not in obj:
        BoxDrawer.round_rectangle(canvas, x0, y0, x1, y1,
                                  radius=rounded_corners*cs._scale,
                                  **rotate_draw_fill_style)
      if selected:
        BoxDrawer.round_rectangle(canvas, x0 - 5, y0 + 5, x1 + 5, y1 - 5,
                                  radius=rounded_corners * cs._scale,
                                  **rotate_select_style)
    else:
      if angle != 0:
        if (fill or draw) and "hidden" not in obj:
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
        if (fill or draw) and "hidden" not in obj:
          canvas.create_rectangle((x0, y0, x1, y1), **draw_fill_style)
        if selected:
          canvas.create_rectangle(x0 - select_buff, y0 + select_buff,
                                  x1 + select_buff, y1 - select_buff,
                                  **select_style)

    if text and "hidden" not in obj:
      draw_text(canvas, center_screen_x, center_screen_y,
                obj, scale, cs_scale, text_color, text_width, angle)

    if selected:
      canvas.create_oval(anchor_screen_x - 3, anchor_screen_y - 3,
                         anchor_screen_x + 3, anchor_screen_y + 3,
                         fill="#77ff77", outline="green")
      if selected_anchor is not None:
        selected_anchor_x, selected_anchor_y = cs.map_point(
          *bb.get_anchor_pos(selected_anchor))
        canvas.create_oval(selected_anchor_x - 5, selected_anchor_y - 5,
                           selected_anchor_x + 5, selected_anchor_y + 5,
                           fill="#ff7733", outline="green")
      
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

  def draw(self, canvas, obj, env, hint={}, no_new_bound_box=False):
    draw = "draw" in obj and "hidden" not in obj
    fill = "fill" in obj
    fill_polygon = []
    line_width = obj.get("line.width")
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
    to_draw = None
    cs = env["coordinate system"]
    selection = env["selection"]
    finding = env["finding"]
    bounding_boxes = env["bounding box"]
    is_selected = selection.selected(obj)
    hint_positions, hint_directions = [], []
    hint["last_path"] = {
        "positions": hint_positions,
        "directions": hint_directions,
    }
    positions, draws = generate_path_positions_and_draws(obj, bounding_boxes)

    if len(positions) > 0:
      hint_positions.append(positions[0][0])
      hint_directions.append(None)

    fill_polygon = []
    first_item = None
    polygon_pos_index = 0
    for draw_index, draw_item in enumerate(draws):
      start_index, to_index, to_draw, index = draw_item
      while polygon_pos_index <= start_index:
        fill_polygon.append(positions[polygon_pos_index][0])
        polygon_pos_index += 1
      start_pos = positions[start_index]
      end_pos = positions[to_index]
      segment_id = f"segment_{id(obj)}_{index}"
      is_first = draw_index == 0
      is_last = draw_index == len(draws) - 1
      
      citem = PathDrawer._draw_item(canvas, to_draw, start_pos, end_pos,
                            is_selected, arrow if is_last else None,
                            obj, segment_id, env,
                            hint, no_new_bound_box, fill_polygon)
      if is_first:
        first_item = citem

    if fill:
      fill_polygon = [e for x, y in fill_polygon for e in cs.map_point(x, y)]
      polygon = canvas.create_polygon(fill_polygon, fill=color_to_tk(obj["fill"]), outline="")
      if first_item is not None:
        canvas.tag_lower(polygon, first_item)
    
    if is_selected:
      for pos_index, position in enumerate(positions):
        pos, _, _, index = position
        x, y = cs.map_point(*pos)
        if selection.selected_position(index):
          radius = 7
          canvas.create_oval(x-radius, y-radius, x+radius,
                              y+radius, outline="black", fill="yellow")
          canvas.create_text(x, y, text=str(pos_index), fill="blue")
        else:
          radius = none_or(line_width, 1)+5
          canvas.create_oval(x-radius, y-radius, x+radius,
                             y+radius, outline="red", dash=2)

    if finding is not None and len(positions) > 0:
      candidate_code = finding.get_chopped_code(obj)
      if candidate_code is not None:
        x0, y0 = cs.map_point(*positions[0][0])
        ftext = canvas.create_text(
            x0, y0, anchor="nw", text=candidate_code, fill="black")
        fback = canvas.create_rectangle(
            canvas.bbox(ftext), fill="yellow", outline="blue")
        canvas.tag_lower(fback, ftext)

  def _draw_item(canvas, item, start_pos, end_pos,
                 is_selected, arrow, path, segment_id, env, hint={},
                 no_new_bound_box=False, fill_polygon=[]):
    start_pos, current_pos_clip, _, _ = start_pos
    end_pos, new_pos_clip, _, _ = end_pos
    x0, y0 = start_pos
    x1, y1 = end_pos
    hint_directions = hint["last_path"]["directions"]
    hint_positions = hint["last_path"]["positions"]
    line_width = path.get("line.width")
    if line_width is not None:
      line_width = dist_to_num(line_width) * line_width_ratio
    dash = 2 if "dashed" in path else None
    if line_width is not None and dash is not None:
      dash = int(dash * line_width)
    color = path.get("color", "black")
    draw = "draw" in path and "hidden" not in path
    fill = path.get("fill", "")
    cs = env["coordinate system"]
    bounding_boxes = env["bounding box"]
    ret = None

    if is_type(item, "line"):
      line_style = {
          "fill": color_to_tk(color),
          "width": line_width,
          "arrow": arrow,
          "dash": dash,
      }
      select_style = {
          "fill": "red",
          "width": int(none_or(line_width, 1)) + 4,
          "dash": int(none_or(line_width, 1)) + 4,
      }
      dist = math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))
      hint_positions.append((x1, y1))

      if "out" in item:
        out_degree = int(item["out"])
        outdy = math.sin(out_degree / 180 * math.pi) * dist / 3
        outdx = math.cos(out_degree / 180 * math.pi) * dist / 3
        if current_pos_clip:
          diagnal = current_pos_clip.diameter()
          start_point = current_pos_clip.get_point_at_direction(
              x0 + outdx * diagnal / dist * 3,
              y0 + outdy * diagnal / dist * 3)
          assert start_point is not None
          x0, y0 = start_point

      if "in" in item:
        in_degree = int(item["in"])
        indy = math.sin(in_degree / 180 * math.pi) * dist / 3
        indx = math.cos(in_degree / 180 * math.pi) * dist / 3
        if new_pos_clip:
          diagnal = new_pos_clip.diameter()
          end_point = new_pos_clip.get_point_at_direction(
              x1 + indx * diagnal / dist * 3,
              y1 + indy * diagnal / dist * 3)
          assert end_point is not None
          x1, y1 = end_point

      if "out" not in item and current_pos_clip:
        cliped_pos = current_pos_clip.get_point_at_direction(x1, y1)
        if cliped_pos is None:
          return ret
        x0, y0 = cliped_pos

      if "in" not in item and new_pos_clip:
        cliped_pos = new_pos_clip.get_point_at_direction(x0, y0)
        if cliped_pos is None:
          return ret
        x1, y1 = cliped_pos

      straight = "in" not in item and "out" not in item
      if straight:
        fill_polygon.append((x1, y1))
        if not no_new_bound_box:
          bounding_boxes[segment_id] = BoundingBox.from_rect(
              x0, y0, x1, y1, shape="line", obj=path)
        hint_directions.append(none_or(get_angle(x0, y0, x1, y1), 0) % 360)
        x0p, y0p = cs.map_point(x0, y0)
        x1p, y1p = cs.map_point(x1, y1)
        line_segments = (x0p, y0p, x1p, y1p)
      else:
        points = [[x0, y0]]

        if "out" in item:
          points.append([x0 + outdx, y0 + outdy])

        if "in" in item:
          points.append([x1 + indx, y1 + indy])
          hint_directions.append((int(item["in"]) + 180) % 360)
        else:
          hint_directions.append(none_or(get_angle(x0+outdx, y0+outdy,
                                                   x1, y1), 0) % 360)
        points.append([x1, y1])

        curve = Bezier.generate_line_segments(
            *points, steps=max(int(dist / 0.01) + 1, 20))

        fill_polygon += curve
        if not no_new_bound_box:
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

          angle = 0
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

            angle = none_or(get_angle(ax0, ay0, ax1, ay1), 0) % 360
            if angle < 270 and angle > 90:
              angle = (angle + 180) % 360

          BoxDrawer._draw(canvas, annotate, env,
                          position=(x, y), slope=angle, hint=hint,
                          no_new_bound_box=no_new_bound_box)

    elif is_type(item, "rectangle"):
      fill_polygon.append((x1, y1))
      hint_directions.append((x1, y1))
      hint_positions.append(None)
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

      if not no_new_bound_box:
        bounding_boxes[segment_id] = BoundingBox.from_rect(
            x0, y0, x1, y1, shape="rectangle", obj=path)

      x0p, y0p = cs.map_point(x0, y0)
      x1p, y1p = cs.map_point(x1, y1)

      if is_selected:
        canvas.create_rectangle((x0p-5, y0p+5, x1p+5, y1p-5), **select_style)
      if draw:
        ret = canvas.create_rectangle((x0p, y0p, x1p, y1p), **line_style)
    elif is_type(item, "arc"):
      line_style = {
          "outline": color_to_tk(color),
          "width": line_width,
          "arrow": arrow,
          "dash": dash,
      }
      select_style = {
          "outline": "red",
          "width": int(none_or(line_width, 1)) + 4,
          "dash": int(none_or(line_width, 1)) + 4,
      }
      start = int(item["start"])
      end = int(item["end"])
      radius = dist_to_num(item["radius"])
      hint_directions.append((end + 90) % 360 if end > start else
                             (end + 270) % 360)
      hint_positions.append((x1, y1))
      curve = create_arc_curve(x0, y0, start, end, radius)
      fill_polygon += curve
      if not no_new_bound_box:
        bounding_boxes[segment_id] = BoundingBox(
            0, 0, 0, 0, shape="curve", points=curve, obj=path)
      dx1, dy1 = math.cos(start*math.pi/180), math.sin(start*math.pi/180)
      dx2, dy2 = math.cos(end*math.pi/180), math.sin(end*math.pi/180)
      centerx, centery = x0 - dx1 * radius, y0 - dy1 * radius
      screenx0, screeny0 = cs.map_point(centerx - radius, centery - radius)
      screenx1, screeny1 = cs.map_point(centerx + radius, centery + radius)
      start, end = order(start, end)
      extent = end - start
      if extent < 0:
        extent += 360
      if is_selected:
        canvas.create_arc(screenx0, screeny0, screenx1, screeny1, start=start,
                          extent=extent, style=tk.ARC, **select_style)
      if draw:
        canvas.create_arc(screenx0, screeny0, screenx1, screeny1, start=start,
                          extent=extent, style=tk.ARC, **line_style)

      if "annotates" in item:
        for annotate in item["annotates"]:
          t = get_position_in_line(annotate)
          start = int(item["start"])
          end = int(item["end"])
          deg = int((end - start) * t + start)
          x = centerx + math.cos(deg/180*math.pi) * radius
          y = centery + math.sin(deg/180*math.pi) * radius

          angle = 0
          if "sloped" in annotate:
            angle = (deg + 360 + 270) % 360
            if angle < 270 and angle > 90:
              angle = (angle + 180) % 360

          BoxDrawer._draw(canvas, annotate, env, position=(x, y),
                          slope=angle, hint=hint,
                          no_new_bound_box=no_new_bound_box)
    else:
      raise ValueError(f"Unknown type {item['type']}")
    return ret
