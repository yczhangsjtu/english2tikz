import tkinter as tk
import string
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
    self._grid_size = 1
    self._show_axes = True
    self._show_grid = True
    root.bind("<Key>", self.handle_key)
    self._context.parse("there.is.a.box with.text 'ABC' sized.1cm.by.1cm")
    self.draw()

  def _register_fundamental_drawers(self):
    self.register_drawer(BoxDrawer())

  def register_drawer(self, drawer):
    assert isinstance(drawer, Drawer)
    self._drawers.append(drawer)

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
      if event.char:
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
      elif event.keysym == "Return":
        self._error_msg = None
    self.draw()

  def _move_pointer(self, x, y):
    self._pointerx += x
    self._pointery += y
    self._move_pointer_into_screen()

  def _move_pointer_into_screen(self):
    screenx, screeny = map_point(
        self._pointerx * self._grid_size,
        self._pointery * self._grid_size,
        self._coordinate_system())
    if screenx < 0:
      self._centerx -= screenx
    elif screenx >= screen_width:
      self._centerx += screen_width - screenx
    if screeny < 0:
      self._centery -= screeny
    elif screeny >= screen_height:
      self._centery += screen_height - screeny

  def _boundary_grids(self):
    x0, y0 = reverse_map_point(0, 0, self._coordinate_system())
    x1, y1 = reverse_map_point(screen_width, screen_height, self._coordinate_system())
    step_upper = int(y0 / self._grid_size)
    step_lower = int(y1 / self._grid_size)
    step_left  = int(x0 / self._grid_size)
    step_right = int(x1 / self._grid_size)
    return step_upper, step_lower, step_left, step_right
    
  def draw(self):
    self._canvas.delete("all")
    self._draw_grid(self._canvas)
    self._draw_axes(self._canvas)
    self._draw_picture(self._canvas, self._context)
    self._draw_pointer(self._canvas)
    self._draw_command(self._canvas)

  def _draw_grid(self, c):
    step_upper, step_lower, step_left, step_right = self._boundary_grids()
    for i in range(step_lower, step_upper+1):
      x, y = map_point(0, self._grid_size * i, self._coordinate_system())
      c.create_line((0, y, screen_width, y), fill="gray", dash=2)
      c.create_text(5, y, text=str(i), anchor="sw", fill="gray")
      c.create_text(screen_width-3, y, text=str(i), anchor="se", fill="gray")
    for i in range(step_left, step_right+1):
      x, y = map_point(self._grid_size * i, 0, self._coordinate_system())
      c.create_line((x, 0, x, screen_height), fill="gray", dash=2)
      c.create_text(x, 0, text=str(i), anchor="nw", fill="gray")
      c.create_text(x, screen_height, text=str(i), anchor="sw", fill="gray")

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
    }
    for obj in ctx._picture:
      drawed = False
      for drawer in self._drawers:
        if drawer.match(obj):
          drawed = True
          drawer.draw(c, obj, env)
          break

  def _draw_pointer(self, c):
    x, y = map_point(self._pointerx * self._grid_size, self._pointery * self._grid_size,
                     self._coordinate_system())
    c.create_oval(x-10, y-10, x+10, y+10, fill="red", outline="black")

  def _draw_command(self, c):
    if self._command_line is not None:
      c.create_rectangle((3, screen_height-15, screen_width, screen_height), fill="white", outline="black")
      c.create_text(5, screen_height, text=":"+self._command_line, anchor="sw", fill="black")
    elif self._error_msg is not None:
      c.create_rectangle((3, screen_height-15, screen_width, screen_height), fill="white", outline="black")
      c.create_text(5, screen_height, text=self._error_msg, anchor="sw", fill="red")

  def _process_command(self, cmd):
    try:
      self._context.parse(cmd)
    except Exception as e:
      self._error_msg = str(e)
        

if __name__ == "__main__":
  root = tk.Tk()
  canvas = tk.Canvas(root, bg="white", width=screen_width, height=screen_height)
  canvas.pack()

  CanvasManager(root, canvas)

  root.title("Vim Draw")
  root.minsize(screen_width, screen_height)
  root.configure(bg="white")
  root.mainloop()
