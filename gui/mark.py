import copy
from english2tikz.utils import *


class MarkManager(object):
  def __init__(self):
    self._marks = []

  def size(self):
    return len(self._marks)

  def empty(self):
    return len(self._marks) == 0

  def single(self):
    return len(self._marks) == 1

  def get_single(self):
    assert self.single()
    return self._marks[0]

  def clear(self):
    self._marks = []

  def marks(self):
    return self._marks

  def chop(self):
    self._marks = self._marks[:i]

  def add_coord(self, x, y):
    self.append(create_coordinate(x, y))

  def add(self, mark):
    self.append(copy.deepcopy(mark))

  def append(self, mark):
    self._marks.append(mark)

  def _get_pos(self, i, bounding_boxes, buffer={}):
    if i in buffer:
      return buffer[i]

    if i < 0:
      raise Exception(f"Trying to get mark of number {i}")

    mark = self._marks[i]

    if is_type(mark, "nodename"):
      bb = get_default(bounding_boxes, mark["name"])
      if bb is None:
        return None
      x, y = bb.get_anchor_pos(get_default(mark, "anchor", "center"))
      if "anchor" in mark:
        """
        It's useless in tikz to shift a node name coordinate without specifying
        the anchor.
        """
        x += dist_to_num(get_default(mark, "xshift", 0))
        y += dist_to_num(get_default(mark, "yshift", 0))
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "intersection"):
      bb1 = get_default(bounding_boxes, mark["name1"])
      bb2 = get_default(bounding_boxes, mark["name2"])
      if bb1 is None or bb2 is None:
        return None
      x, _ = bb1.get_anchor_pos(get_default(mark, "anchor1", "center"))
      _, y = bb2.get_anchor_pos(get_default(mark, "anchor2", "center"))
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "coordinate"):
      if get_default(mark, "relative", False):
        if i == 0:
          return None
        previous = self._get_pos(i-1, buffer)
        if previous is None:
          return None
        x0, y0 = previous
        x = x0 + dist_to_num(mark["x"])
        y = y0 + dist_to_num(mark["y"])
      else:
        x, y = dist_to_num(mark["x"], mark["y"])
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "cycle"):
      buffer[i] = self._get_pos(0, buffer)
      return buffer[i]
    else:
      raise Exception(f"Unknown mark type {mark['type']}")

  def get_pos(self, i, bounding_boxes):
    return self._get_pos(i, bounding_boxes, buffer={})

  def get_last_pos(self, bounding_boxes):
    if self.empty():
      raise Exception("Empty marks")
    return self._get_pos(len(self._marks)-1, bounding_boxes)

  def create_path(self, arrow):
    if self.size() < 2:
      raise Exception(f"Expect at least two marks")
    items = []
    for i, mark in enumerate(self._marks):
      items.append(mark)
      if i < len(self._marks) - 1:
        items.append(create_line())
    return create_path(items, arrow)

  def create_rectangle(self):
    if self.size() != 2:
      raise Exception(f"Expect exactly two marks")
    return create_path([
        self._marks[0],
        create_rectangle(),
        self._marks[1],
    ])

  def delete(self, index):
    if index < 0 or index >= self.size():
      raise Exception(f"Index out of bound {index}/{self.size()}")
    del self._marks[index]