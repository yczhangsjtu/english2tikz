from english2tikz.utils import *


class Grid(object):
  def __init__(self):
    self._size_index = 0
    self._sizes = [1, 0.5, 0.2, 0.1, 0.05]

  def change_size(self, by):
    self._size_index = bound_by(self._size_index + by, 0, len(self._sizes) - 1)

  def size(self):
    return self._sizes[self._size_index]

  def closest_int_coord(self, x, y):
    return round(x / self.size()), round(y / self.size())

  def closest_coord(self, x, y):
    return (round(x / self.size()) * self.size(),
            round(y / self.size()) * self.size())

  def rect_boundary(self, x0, y0, x1, y1):
    upper = int(y0 / self.size())
    lower = int(y1 / self.size())
    left = int(x0 / self.size())
    right = int(x1 / self.size())
    return upper, lower, left, right
