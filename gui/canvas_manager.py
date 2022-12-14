import traceback
from english2tikz.utils import *
from english2tikz.errors import *
from english2tikz.gui.drawers import *


class CanvasManager(object):
  def __init__(self, root, canvas, screen_width, screen_height, editor):
    self._canvas = canvas
    self._root = root
    self._end = False
    self._drawers = []
    self._register_fundamental_drawers()
    self._show_axes = True
    self._show_grid = True
    self._show_attributes = True
    self._image_references = {}
    self._start_time = now()
    self._pointer_objects = []
    self._editor = editor
    self._preview = None
    root.after(100, self._draw_animated)
    root.after(1, self.draw)

  def _pointer(self):
    return self._editor._pointer

  def _command_line(self):
    return self._editor._command_line

  def _error_msg(self):
    return self._editor._error_msg

  def _cs(self):
    return self._pointer()._cs

  def _marks(self):
    return self._editor._marks

  def _visual(self):
    return self._editor._visual

  def _editing_text(self):
    return self._editor._editing_text

  def _editing_text_pos(self):
    return self._editor._editing_text_pos

  def _selection(self):
    return self._editor._selection

  def _register_fundamental_drawers(self):
    self.register_drawer(BoxDrawer())
    self.register_drawer(PathDrawer())

  def register_drawer(self, drawer):
    assert isinstance(drawer, Drawer)
    self._drawers.append(drawer)

  def draw(self):
    if self._end:
      return

    self._canvas.delete("all")

    if self._preview is not None:
      self._draw_preview()
      return
    if self._show_grid:
      self._draw_grid(self._canvas)
    if self._show_axes:
      self._draw_axes(self._canvas)
    self._draw_picture(self._canvas,
                       self._editor._context._picture,
                       {}, [])
    self._draw_visual(self._canvas)
    self._draw_marks(self._canvas)
    self._draw_attributes(self._canvas)
    if self._editor._has_suggest():
      self._editor._suggest._propose_suggestions()
      for candidate in self._editor._suggest._new_suggestions:
        self._draw_picture(self._canvas,
                           candidate._content,
                           self._bounding_boxes,
                           self._point_collection,
                           no_new_bound_box=True)
      self._draw_picture(self._canvas,
                         self._editor._suggest.suggestion()._content,
                         self._bounding_boxes,
                         self._point_collection,
                         hint=self._editor._suggest._hint,
                         no_new_bound_box=True)
    if self._editing_text() is not None:
      self._draw_editing_text(self._canvas)
    else:
      self._draw_pointer_indicator(self._canvas)
    self._draw_command(self._canvas)

  def _draw_preview(self):
    img = Image.open(self._preview)
    img = img.convert("RGBA")
    w, h = img.size
    if w >= self._cs()._view_width:
      w, h = self._cs()._view_width, h / w * self._cs()._view_width
    if h >= self._cs()._view_height:
      w, h = w / h * self._cs()._view_height, self._cs()._view_height
    w, h = int(0.95 * w), int(0.95 * h)
    x0 = self._cs()._view_width / 2
    y0 = self._cs()._view_height / 2
    img = img.resize((w, h))
    image = ImageTk.PhotoImage(img)
    self._image_references["view"] = image
    self._canvas.create_image(x0, y0, image=image)

  def _draw_animated(self):
    if self._end:
      return
    for obj in self._pointer_objects:
      self._canvas.delete(obj)
    if self._editing_text() is None and self._preview is None:
      self._pointer_objects = self._draw_pointer(self._canvas)
    else:
      self._pointer_objects = []
    self._root.after(100, self._draw_animated)

  def _draw_grid(self, c):
    upper, lower, left, right = self._pointer().boundary_grids()
    step = round(1 / self._pointer().grid_size())
    for i in range(lower, upper+1):
      x, y = self._cs().map_point(0, self._pointer().grid_size() * i)
      c.create_line(self._cs().horizontal_line(y),
                    fill="gray", dash=2)
      draw_text = i == self._pointer().iy() or i % step == 0
      color = "red" if i == self._pointer().iy() else "gray"
      if draw_text:
        text = "%g" % (i * self._pointer().grid_size())
        c.create_text(5, y, text=text, anchor="sw", fill=color)
        c.create_text(self._cs().right_boundary()-3, y,
                      text=text, anchor="se", fill=color)
    for i in range(left, right+1):
      x, y = self._cs().map_point(
          self._pointer().grid_size() * i, 0)
      c.create_line(self._cs().vertical_line(x),
                    fill="gray", dash=2)
      draw_text = i == self._pointer().ix() or i % step == 0
      color = "red" if i == self._pointer().ix() else "gray"
      if draw_text:
        text = "%g" % (i * self._pointer().grid_size())
        c.create_text(x, 0, text=text, anchor="nw", fill=color)
        c.create_text(x, self._cs().bottom_boundary(),
                      text=text, anchor="sw", fill=color)

  def _draw_axes(self, c):
    c.create_line(self._cs().center_horizontal_line(),
                  fill="#888888", width=1.5)
    c.create_line(self._cs().center_vertical_line(),
                  fill="#888888", width=1.5)

  def _draw_picture(self, c, picture, bounding_box,
                    point_collection=[], hint={},
                    no_new_bound_box=False):
    env = {
        "bounding box": bounding_box,
        "point collection": point_collection,
        "coordinate system": self._cs(),
        "selection": self._selection(),
        "image references": self._image_references,
        "finding": self._editor._finding,
    }
    try:
      for obj in picture:
        self._draw_obj(c, obj, env, hint, no_new_bound_box)
    except Exception as e:
      traceback.print_exc()
      self._editor._error_msg = f"Error in drawing {obj}: {e}"
    self._bounding_boxes = env["bounding box"]
    self._point_collection = env["point collection"]
    self._pointer().find_closest(self._point_collection)

  def _draw_obj(self, c, obj, env, hint={}, no_new_bound_box=False):
    for drawer in self._drawers:
      if not drawer.match(obj):
        continue
      drawer.draw(c, obj, env, hint, no_new_bound_box)
      return
    raise ConfigurationError(f"Cannot find drawer for obj {obj}")

  def _draw_visual(self, c):
    if not self._visual().active():
      return
    c.create_rectangle(self._visual().ordered_vrect(),
                       outline="red", width=4, dash=8)

  def _get_mark_pos(self, i):
    return self._marks().get_pos(i, self._bounding_boxes)

  def _draw_marks(self, c):
    for i, mark in enumerate(self._marks().marks()):
      coord = self._get_mark_pos(i)
      if coord is None:
        """
        When a mark is deleted, it may cause marks with relative positions
        to be invalid. So it is possible to have exception here, and in
        this case, we simply remove all the following marks.
        """
        self._marks().chop(i)
        return
      x, y = self._cs().map_point(*coord)
      radius = 10
      if is_type(mark, "coordinate"):
        if mark.get("relative", False):
          fill, outline = "#ff7777", "red"
        else:
          fill, outline = "#77ff77", "green"
      elif is_type(mark, "nodename"):
        if "xshift" in mark or "yshift" in mark:
          fill, outline = "#7777ff", "blue"
        else:
          fill, outline = "#ffff77", "orange"
      elif is_type(mark, "intersection"):
        fill, outline = "white", "black"
      elif is_type(mark, "arc"):
        fill, outline = "#444444", "black"
      elif is_type(mark, "cycle"):
        fill, outline, radius = "red", "black", 12
      c.create_oval(x-radius, y-radius, x+radius, y + radius,
                    fill=fill, outline=outline)
      c.create_text(x, y, text=str(i), fill="black")

  def _draw_editing_text(self, c):
    x, y = self._cs().map_point(*self._editing_text_pos())
    t = c.create_text(x, y, text=self._editing_text().view(),
                      fill="black", font=("Courier", 20, "normal"))
    bg = c.create_rectangle(c.bbox(t), fill="white", outline="blue")
    c.tag_lower(bg, t)

  def _elapsed(self):
    return now() - self._start_time

  def _draw_pointer_indicator(self, c):
    x, y = self._pointer().vpos()
    c.create_line(self._cs().horizontal_line(y),
                  fill="red", width=1)
    c.create_line(self._cs().vertical_line(x),
                  fill="red", width=1)

  def _draw_pointer(self, c):
    ret = []
    x, y = self._pointer().vpos()
    angle = int((self._elapsed() / 5)) % 360
    rad = angle / 180 * math.pi
    dx1, dy1 = 10 * math.cos(rad), 10 * math.sin(rad)
    dx2, dy2 = -10 * math.sin(rad), 10 * math.cos(rad)
    ret.append(c.create_line((x+dx1, y+dy1, x-dx1, y-dy1),
                             fill="red", width=2))
    ret.append(c.create_line((x+dx2, y+dy2, x-dx2, y-dy2),
                             fill="red", width=2))
    if self._pointer().has_closest():
      x1, y1 = self._pointer().closest_vpos()
      ret.append(c.create_line(x, y, x1, y1, fill="blue",
                               dash=4, width=1.5,
                               dashoffset=int(self._elapsed()/100)%8))
      radius = int(self._elapsed()/100) % 5
      ret.append(c.create_oval(x1-radius, y1-radius, x1+radius, y1+radius,
                               fill="blue", outline="red"))
    return ret

  def _draw_attributes(self, c):
    if not self._show_attributes:
      return

    to_draw = self._selection().get_selected_objects_common_description()
    keys = sorted(list(to_draw.keys()))

    y = 5
    for key in keys:
      value = to_draw[key]
      if isinstance(value, str):
        t = c.create_text(15, y, anchor="nw", text=key, fill="blue",
                          font=("Courier", 15, "normal"))
        t = c.create_text(120, y, anchor="nw", text=str(value),
                          fill="#000077", font=("Courier", 15, "normal"))
        _, _, _, y = c.bbox(t)
      elif isinstance(value, dict):
        t = c.create_text(15, y, anchor="nw", text=key, fill="blue",
                          font=("Courier", 15, "normal"))
        for k, v in value.items():
          t = c.create_text(120, y, anchor="nw", text=k,
                            fill="#000077", font=("Courier", 15, "normal"))
          t = c.create_text(200, y, anchor="nw", text=v,
                            fill="#007700", font=("Courier", 15, "normal"))
          _, _, _, y = c.bbox(t)
      elif value is True:
        t = c.create_text(15, y, anchor="nw", text=key, fill="blue",
                          font=("Courier", 15, "normal"))
        _, _, _, y = c.bbox(t)

  def _draw_command(self, c):
    if self._command_line().active():
      c.create_rectangle((3, self._cs().bottom_boundary()-28,
                          self._cs().right_boundary(),
                          self._cs().bottom_boundary()),
                         fill="white", outline="black")
      c.create_text(5, self._cs().bottom_boundary(),
                    text=":" + self._command_line().view(),
                    anchor="sw", fill="black", font=("Courier", 20, "normal"))
    elif self._error_msg() is not None:
      c.create_rectangle((3, self._cs().bottom_boundary()-15,
                          self._cs().right_boundary(),
                          self._cs().bottom_boundary()),
                         fill="white", outline="black")
      c.create_text(5, self._cs().bottom_boundary(),
                    text=self._error_msg(), anchor="sw", fill="red")

  def find_all_in_screen(self):
    sel = self._cs().view_range()
    selected_ids, selected_paths = [], []

    for id_, bb in self._bounding_boxes.items():
      if bb.intersect_rect(sel):
        if id_.startswith("segment_"):
          append_if_not_in(selected_paths, bb._obj)
        else:
          append_if_not_in(selected_ids, id_)

    return selected_ids, selected_paths

  def preview(self, path):
    self._preview = path
