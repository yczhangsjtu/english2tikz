import tkinter as tk
import string
import copy
import re
from english2tikz.describe_it import DescribeIt
from english2tikz.drawers import *
from english2tikz.utils import *

screen_width, screen_height = 1200, 750

class CanvasManager(object):
  def __init__(self, root, canvas):
    self._canvas = canvas
    self._root = root
    self._context = DescribeIt()
    self._drawers = []
    self._register_fundamental_drawers()
    self._centerx = screen_width / 2
    self._centery = screen_height / 2
    self._pointerx = 0
    self._pointery = 0
    self._scale = 100
    self._command_line = None
    self._error_msg = None
    self._grid_size_index = 0
    self._grid_sizes = [1, 0.5, 0.2, 0.1, 0.05]
    self._show_axes = True
    self._show_grid = True
    self._obj_to_edit_text = None
    self._editing_text = None
    self._history = [self._context._picture]
    self._history_index = 0
    self._visual_start = None
    self._bounding_boxes = {}
    self._selected_ids = []
    root.bind("<Key>", self.handle_key)
    self.draw()

  def _register_fundamental_drawers(self):
    self.register_drawer(BoxDrawer())

  def register_drawer(self, drawer):
    assert isinstance(drawer, Drawer)
    self._drawers.append(drawer)

  def _parse(self, code):
    self._history = self._history[:self._history_index+1]
    self._history[self._history_index] = copy.deepcopy(self._history[self._history_index])
    self._context.parse(code)
    self._history.append(self._context._picture)
    self._history_index = len(self._history) - 1

  def _undo(self):
    if self._history_index == 0:
      self._error_msg = "Already the oldest"
      return

    self._history_index -= 1
    self._context._picture = self._history[self._history_index]

  def _redo(self):
    if self._history_index >= len(self._history) - 1:
      self._error_msg = "Already at newest change"
      return
    self._history_index += 1
    self._context._picture = self._history[self._history_index]

  def _grid_size(self):
    return self._grid_sizes[self._grid_size_index]

  def handle_key(self, event):
    if self._command_line is not None:
      if event.char:
        self._command_line += event.char
      elif event.keysym == "Return":
        self._process_command(self._command_line)
        self._command_line = None
      elif event.keysym == "BackSpace":
        if len(self._command_line) > 0:
          self._command_line = self._command_line[:-1]
        else:
          self._command_line = None
      elif event.state == 4 and event.keysym in string.ascii_lowercase:
        """
        Ctrl + letter
        """
        if event.keysym == "c":
          self._command_line = None
      else:
        print(dir(event))
        print(event.state, event.keysym)
    else:
      if self._editing_text is not None:
        if event.char:
          self._editing_text += event.char
        elif event.keysym == "Return":
          self._editing_text += "\n"
        elif event.keysym == "BackSpace":
          if len(self._editing_text) > 0:
            self._editing_text = self._editing_text[:-1]
        elif event.state == 4 and event.keysym in string.ascii_lowercase:
          """
          Ctrl + letter
          """
          if event.keysym == "c":
            if self._obj_to_edit_text is None:
              if len(self._editing_text) > 0:
                x = self._pointerx * self._grid_size()
                y = self._pointery * self._grid_size()
                if x != 0:
                  x = f"{x}cm"
                if y != 0:
                  y = f"{y}cm"
                self._parse(f"""there.is.text "{self._editing_text}" at.x.{x}.y.{y}
                                with.text.align=left""")
            else:
              self._obj_to_edit_text["text"] = self._editing_text
            self._editing_text = None
        else:
          print(dir(event))
          print(event.state, event.keysym)
      elif event.char:
        if event.char == ":":
          self._command_line = ""
          self._error_msg = None
        elif event.char == "j":
          self._move_pointer(0, -1)
        elif event.char == "k":
          self._move_pointer(0, 1)
        elif event.char == "h":
          self._move_pointer(-1, 0)
        elif event.char == "l":
          self._move_pointer(1, 0)
        elif event.char == "L":
          upper, lower, left, right = self._boundary_grids()
          self._pointery = lower
          self._move_pointer_into_screen()
        elif event.char == "H":
          upper, lower, left, right = self._boundary_grids()
          self._pointery = upper
          self._move_pointer_into_screen()
        elif event.char == "M":
          upper, lower, left, right = self._boundary_grids()
          self._pointery = int((upper + lower)/2)
          self._move_pointer_into_screen()
        elif event.char == "0":
          upper, lower, left, right = self._boundary_grids()
          self._pointerx = left
          self._move_pointer_into_screen()
        elif event.char == "$":
          upper, lower, left, right = self._boundary_grids()
          self._pointerx = right
          self._move_pointer_into_screen()
        elif event.char == "G":
          self._pointerx = 0
          self._pointery = 0
          self._centerx = screen_width / 2
          self._centery = screen_height / 2
        elif event.char == "i":
          if len(self._selected_ids) > 1:
            self._error_msg = "Cannot edit more than one objects"
          elif len(self._selected_ids) == 1:
            self._obj_to_edit_text = self._find_object_by_id(self._selected_ids[0])
            if "text" in self._obj_to_edit_text:
              self._editing_text = self._obj_to_edit_text["text"]
            else:
              self._error_msg = "The selected object does not support text."
          else:
            self._editing_text = ""
        elif event.char == "u":
          self._undo()
        elif event.char == "v":
          if self._visual_start is not None:
            self._select_targets(False)
            self._visual_start = None
          else:
            x, y = self._get_pointer_pos()
            self._visual_start = (x, y)
      elif event.keysym == "Return":
        self._error_msg = None
        if self._visual_start is not None:
          self._select_targets()
          self._visual_start = None
      elif event.state == 4 and event.keysym in string.ascii_lowercase:
        if event.keysym == "r":
          self._redo()
        elif event.keysym == "c":
          self._visual_start = None
          self._selected_ids = []
        elif event.keysym == "g":
          x, y = self._get_pointer_pos()
          self._grid_size_index = min(self._grid_size_index + 1, len(self._grid_sizes) - 1)
          self._pointerx, self._pointery = self._find_closest_pointer_grid_coord(x, y)
          self._move_pointer_into_screen()
        elif event.keysym == "f":
          x, y = self._get_pointer_pos()
          self._grid_size_index = max(self._grid_size_index - 1, 0)
          self._pointerx, self._pointery = self._find_closest_pointer_grid_coord(x, y)
          self._move_pointer_into_screen()
        elif event.keysym == "e":
          self._centery -= 100
          self._reset_pointer_into_screen()
        elif event.keysym == "y":
          self._centery += 100
          self._reset_pointer_into_screen()
    self.draw()

  def _find_object_by_id(self, id_):
    for obj in self._context._picture:
      if "id" in obj and obj["id"] == id_:
        return obj
    return None

  def _select_targets(self, clear=True):
    if clear:
      self._selected_ids = []
    if self._visual_start is not None:
      x0, y0 = self._visual_start
      x1, y1 = self._get_pointer_pos()
      for id_, bb in self._bounding_boxes.items():
        x, y, width, height = bb
        if intersect((x0, y0, x1, y1), (x, y, x+width, y+height)):
          self._selected_ids.append(id_)

  def _get_pointer_pos(self):
    return self._pointerx * self._grid_size(), self._pointery * self._grid_size()

  def _get_pointer_screen_pos(self):
    x, y = self._get_pointer_pos()
    return map_point(x, y, self._coordinate_system())

  def _find_closest_pointer_grid_coord(self, x, y):
    gs = self._grid_size()
    return round(x / gs), round(y / gs)

  def _move_pointer(self, x, y):
    self._pointerx += x
    self._pointery += y
    self._move_pointer_into_screen()

  def _move_pointer_into_screen(self):
    screenx, screeny = self._get_pointer_screen_pos()
    if screenx < 0:
      self._centerx -= screenx
    elif screenx >= screen_width:
      self._centerx += screen_width - screenx
    if screeny < 0:
      self._centery -= screeny
    elif screeny >= screen_height:
      self._centery += screen_height - screeny

  def _reset_pointer_into_screen(self):
    screenx, screeny = self._get_pointer_screen_pos()
    screenx = max(min(screenx, screen_width - self._scale + 10), self._scale - 10)
    screeny = max(min(screeny, screen_height - self._scale + 10), self._scale - 10)
    x, y = reverse_map_point(screenx, screeny, self._coordinate_system())
    self._pointerx, self._pointery = self._find_closest_pointer_grid_coord(x, y)

  def _boundary_grids(self):
    x0, y0 = reverse_map_point(0, 0, self._coordinate_system())
    x1, y1 = reverse_map_point(screen_width, screen_height, self._coordinate_system())
    step_upper = int(y0 / self._grid_size())
    step_lower = int(y1 / self._grid_size())
    step_left  = int(x0 / self._grid_size())
    step_right = int(x1 / self._grid_size())
    return step_upper, step_lower, step_left, step_right
    
  def draw(self):
    self._canvas.delete("all")
    self._draw_grid(self._canvas)
    self._draw_axes(self._canvas)
    self._draw_picture(self._canvas, self._context)
    self._draw_visual(self._canvas)
    self._draw_pointer(self._canvas)
    self._draw_command(self._canvas)

  def _draw_grid(self, c):
    step_upper, step_lower, step_left, step_right = self._boundary_grids()
    step = round(1 / self._grid_size())
    for i in range(step_lower, step_upper+1):
      x, y = map_point(0, self._grid_size() * i, self._coordinate_system())
      c.create_line((0, y, screen_width, y), fill="gray", dash=2)
      draw_text = i == self._pointery or i % step == 0
      color = "red" if i == self._pointery else "gray"
      if draw_text:
        text = "%.2g" % (i * self._grid_size())
        c.create_text(5, y, text=text, anchor="sw", fill=color)
        c.create_text(screen_width-3, y, text=text, anchor="se", fill=color)
    for i in range(step_left, step_right+1):
      x, y = map_point(self._grid_size() * i, 0, self._coordinate_system())
      c.create_line((x, 0, x, screen_height), fill="gray", dash=2)
      draw_text = i == self._pointerx or i % step == 0
      color = "red" if i == self._pointerx else "gray"
      if draw_text:
        text = "%.2g" % (i * self._grid_size())
        c.create_text(x, 0, text=text, anchor="nw", fill=color)
        c.create_text(x, screen_height, text=text, anchor="sw", fill=color)

  def _draw_axes(self, c):
    c.create_line((0, self._centery, screen_width, self._centery), fill="blue", width=1.5)
    c.create_line((self._centerx, 0, self._centerx, screen_height), fill="blue", width=1.5)

  def _coordinate_system(self):
    return {
      "width": screen_width,
      "height": screen_height,
      "center_x": self._centerx,
      "center_y": self._centery,
      "scale": self._scale,
    }

  def _draw_picture(self, c, ctx):
    env = {
      "bounding box": {},
      "coordinate system": self._coordinate_system(),
      "selected ids": self._selected_ids,
    }
    for obj in ctx._picture:
      drawed = False
      for drawer in self._drawers:
        if drawer.match(obj):
          drawed = True
          drawer.draw(c, obj, env)
          break
    self._bounding_boxes = env["bounding box"]

  def _draw_visual(self, c):
    if self._visual_start is not None:
      x, y = self._visual_start
      x0, y0 = map_point(x, y, self._coordinate_system())
      x1, y1 = self._get_pointer_screen_pos()
      c.create_rectangle((x0, y0, x1, y1), outline="red", width=4, dash=8)


  def _draw_pointer(self, c):
    x, y = map_point(self._pointerx * self._grid_size(), self._pointery * self._grid_size(),
                     self._coordinate_system())
    if self._editing_text is not None:
      if len(self._editing_text.strip()) == 0:
        c.create_line((x, y-10, x, y+10), fill="black", width=3)
      else:
        t = c.create_text(x, y, text=self._editing_text, fill="black")
        bg = c.create_rectangle(c.bbox(t), fill="white", outline="blue")
        c.tag_lower(bg, t)
      return
    c.create_line((0, y, screen_width, y), fill="red", width=1)
    c.create_line((x, 0, x, screen_height), fill="red", width=1)
    c.create_oval(x-10, y-10, x+10, y+10, fill="red", outline="black")

  def _draw_command(self, c):
    if self._command_line is not None:
      c.create_rectangle((3, screen_height-15, screen_width, screen_height), fill="white", outline="black")
      c.create_text(5, screen_height, text=":"+self._command_line, anchor="sw", fill="black")
    elif self._error_msg is not None:
      c.create_rectangle((3, screen_height-15, screen_width, screen_height), fill="white", outline="black")
      c.create_text(5, screen_height, text=self._error_msg, anchor="sw", fill="red")

  def _tokenize(self, code):
    code = code.strip()
    tokens = []
    while len(code) > 0:
      if code.startswith("'''") or code.startswith('"""'):
        escaped, text = False, None
        for i in range(1, len(code)):
          if escaped:
            escaped = False
            continue
          if code[i] == '\\':
            escaped = True
            continue
          if i + 3 <= len(code) and code[i:i+3] == code[0] * 3:
            text = code[0:i+3]
            code = code[i+3:].strip()
            break
        if text:
          tokens.append(("text", text[3:-3]))
          continue
        else:
          raise Exception(f"Unended quote: {code}")
      if code.startswith("'") or code.startswith('"'):
        escaped, text = False, None
        for i in range(1, len(code)):
          if escaped:
            escaped = False
            continue
          if code[i] == '\\':
            escaped = True
            continue
          if code[i] == code[0]:
            text = code[0:i+1]
            code = code[i+1:].strip()
            break
        if text:
          tokens.append(("text", text[1:-1]))
          continue
        else:
          raise Exception(f"Unended quote: {code}")
      if code.startswith("python{{{"):
        end = code.find("python}}}")
        if end < 0:
          raise Exception(f"Unended python code: {code}")
        python_code = code[9:end]
        code = code[end+9:].strip()
        tokens.append(("python", code))
        continue
      match = re.search(r'[\n\s]+', code)
      if match:
        tokens.append(("command", code[0:match.span()[0]]))
        code = code[match.span()[1]:].strip()
        continue
      tokens.append(("command", code))
      break
    return tokens

  def _process_command(self, cmd):
    try:
      tokens = self._tokenize(cmd)
      if len(tokens) == 0:
        raise Exception("Empty command")
      if tokens[0][0] != "command":
        raise Exception("Command does not start with command name")
      cmd_name = tokens[0][1]
      if cmd_name == "set":
        self._set(*tokens[1:])
    except Exception as e:
      self._error_msg = str(e)
      raise e

  def _set(self, *args):
    if len(self._selected_ids) == 0:
      raise Exception("No object selected")
    key = None
    for t, v in args:
      if t == "command":
        if key is not None:
          self._set_selected_objects(key, True)
        eq = v.find("=")
        if eq >= 0:
          self._set_selected_objects(v[:eq], v[eq+1:])
          continue
        key = v
      elif t == "text":
        if key is None:
          raise Exception(f"Unexpected text: [{v}]")
        self._set_selected_objects(key, v)
        key = None
      elif t == "python":
        if key is None:
          raise Exception(f"Unexpected text: [{v}]")
        self._set_selected_objects(key, eval(v))
        key = None
      else:
        raise Exception(f"Unrecognized token type: [{t}]")
    if key is not None:
      self._set_selected_objects(key, True)

  def _set_selected_objects(self, key, value):
    for id_ in self._selected_ids:
      obj = self._find_object_by_id(id_)
      if obj is None:
        raise Exception(f"Cannot find object by id {id_}")
      obj[key] = value
        

if __name__ == "__main__":
  root = tk.Tk()
  canvas = tk.Canvas(root, bg="white", width=screen_width, height=screen_height)
  canvas.pack()

  CanvasManager(root, canvas)

  root.title("Vim Draw")
  root.minsize(screen_width, screen_height)
  root.configure(bg="white")
  root.mainloop()
