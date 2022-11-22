from english2tikz.utils import *


class CoordinateSystem(object):
  def __init__(self, view_width, view_height, scale):
    self._view_width = view_width
    self._view_height = view_height
    self._scale = 100
    self._centerx = view_width / 2
    self._centery = view_height / 2

  def map_point(self, x, y):
    return self._centerx + x * self._scale, self._centery - y * self._scale

  def reverse_map_point(self, x, y):
    return ((x - self._centerx) / self._scale,
            (self._centery - y) / self._scale)

  def view_range(self):
    x0, y0 = self.reverse_map_point(0, 0)
    x1, y1 = self.reverse_map_point(self._view_width, self._view_height)
    return x0, y0, x1, y1

  def reset(self):
    self._centerx = self._view_width / 2
    self._centery = self._view_height / 2

  def shift_to_include(self, x, y):
    if x < 0:
      self._centerx -= x
    elif x >= self._view_width:
      self._centerx += self._view_width - x
    if y < 0:
      self._centery -= y
    elif y >= self._view_height:
      self._centery += self._view_height - y

  def closest_in_view(self, x, y):
    x = bound_by(x, self._scale - 10, self._view_width - self._scale + 10)
    y = bound_by(y, self._scale - 10, self._view_height - self._scale + 10)
    return x, y

  def horizontal_line(self, y):
    return (0, y, self._view_width, y)

  def vertical_line(self, x):
    return (x, 0, x, self._view_height)

  def center_horizontal_line(self):
    return self.horizontal_line(self._centery)

  def center_vertical_line(self):
    return self.vertical_line(self._centerx)

  def right_boundary(self):
    return self._view_width

  def bottom_boundary(self):
    return self._view_height

  def scroll(self, dx, dy):
    self._centerx += dx
    self._centery += dy
