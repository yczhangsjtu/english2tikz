from english2tikz.utils import *
from english2tikz.gui.grid import Grid
from english2tikz.gui.geometry import *


class Pointer(object):
  def __init__(self, cs):
    self._x = 0
    self._y = 0
    self._grid = Grid()
    self._cs = cs
    self._closest = None

  def ix(self):
    return self._x

  def iy(self):
    return self._y

  def x(self):
    return self._x * self._grid.size()

  def y(self):
    return self._y * self._grid.size()

  def grid_size(self):
    return self._grid.size()

  def pos(self):
    return self._x * self._grid.size(), self._y * self._grid.size()

  def posstr(self):
    return num_to_dist(*self.pos())

  def vpos(self):
    return self._cs.map_point(*self.pos())

  def change_grid_size(self, by):
    x, y = self.pos()
    self._grid.change_size(by)
    self._x, self._y = self._grid.closest_int_coord(x, y)
    self.move_into_view()

  def move_into_view(self):
    self._cs.shift_to_include(*self.vpos())

  def set(self, x, y):
    self._x = x
    self._y = y

  def reset_to_origin(self):
    self.set(0, 0)
    self._cs.reset()

  def goto(self, x, y):
    self.set(round(x / self._grid.size()), round(y / self._grid.size()))
    self.move_into_view()

  def move_by(self, dx, dy):
    self._x += dx
    self._y += dy
    self.move_into_view()

  def move_by_inverse_grid_size(self, x, y):
    self.move_by(round(x/self._grid.size()), round(y/self._grid.size()))

  def boundary_grids(self):
    return self._grid.rect_boundary(*self._cs.view_range())

  def move_to_boundary(self, direction):
    upper, lower, left, right = self.boundary_grids()
    if direction == "left":
      self._x = left
    elif direction == "right":
      self._x = right
    elif direction == "above":
      self._y = upper
    elif direction == "below":
      self._y = lower
    elif direction == "middle":
      self._y = int((upper + lower)/2)
    self.move_into_view()

  def scroll(self, dx, dy):
    self._cs.scroll(dx, dy)
    self.reset_into_view()

  def reset_into_view(self):
    self.set(*self._grid.closest_int_coord(*self._cs.reverse_map_point(
          *self._cs.closest_in_view(*self.vpos()))))

  def find_closest(self, point_collection):
    target_item, mindist, target_pos = None, None, None
    for item, pos in point_collection:
      if mindist is None or euclidean_dist(pos, self.pos()) < mindist:
        target_item, mindist, target_pos = item, euclidean_dist(pos, self.pos()), pos
    if target_item is not None:
      self._closest = (target_item, target_pos)
    else:
      self._closest = None
  
  def has_closest(self):
    return self._closest is not None
  
  def closest(self):
    return self._closest
  
  def closest_vpos(self):
    if not self.has_closest():
      return None
    _, pos = self.closest()
    return self._cs.map_point(*pos)