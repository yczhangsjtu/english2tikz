from english2tikz.utils import *
from english2tikz.gui.object_utils import *


class Visual(object):
  def __init__(self, pointer):
    self._start = None
    self._pointer = pointer

  def active(self):
    return self._start is not None

  def rect(self):
    if not self.active():
      return None
    x0, y0 = self._start[0], self._start[1]
    x1, y1 = self._pointer.pos()
    return x0, y0, x1, y1

  def ordered_rect(self):
    r = self.rect()
    if r is None:
      return None
    x0, y0, x1, y1 = r
    x0, x1 = order(x0, x1)
    y0, y1 = order(y0, y1)
    return x0, y0, x1, y1

  def ordered_vrect(self):
    r = self.ordered_rect()
    if r is None:
      return None
    x0, y0, x1, y1 = r
    x0, y0 = self._pointer._cs.map_point(x0, y0)
    x1, y1 = self._pointer._cs.map_point(x1, y1)
    return x0, y0, x1, y1

  def create_path(self):
    if not self.active():
      return None
    return create_path([
        create_coordinate(*self._start),
        create_rectangle(),
        create_coordinate(*self._pointer.pos()),
    ])

  def activate(self, x, y):
    self._start = (x, y)

  def clear(self):
    self._start = None
