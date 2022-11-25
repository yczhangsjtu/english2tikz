import copy
from english2tikz.utils import *
from english2tikz.errors import *
from english2tikz.gui.object_utils import *


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

  def chop(self, i):
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
      raise IndexError(f"Trying to get mark of number {i}")

    mark = self._marks[i]

    if is_type(mark, "nodename"):
      bb = bounding_boxes.get(mark["name"])
      if bb is None:
        return None
      x, y = bb.get_anchor_pos(mark.get("anchor", "center"))
      if "anchor" in mark:
        """
        It's useless in tikz to shift a node name coordinate without specifying
        the anchor.
        """
        x += dist_to_num(mark.get("xshift", 0))
        y += dist_to_num(mark.get("yshift", 0))
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "intersection"):
      bb1 = bounding_boxes.get(mark["name1"])
      bb2 = bounding_boxes.get(mark["name2"])
      if bb1 is None or bb2 is None:
        return None
      x, _ = bb1.get_anchor_pos(mark.get("anchor1", "center"))
      _, y = bb2.get_anchor_pos(mark.get("anchor2", "center"))
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "coordinate"):
      if mark.get("relative", False):
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
    elif is_type(mark, "arc"):
      if i == 0:
        return None
      previous = self._get_pos(i-1, buffer)
      if previous is None:
        return None
      x0, y0 = previous
      start = int(mark["start"])
      end = int(mark["end"])
      radius = dist_to_num(mark["radius"])
      dx1, dy1 = math.cos(start*math.pi/180), math.sin(start*math.pi/180)
      dx2, dy2 = math.cos(end*math.pi/180), math.sin(end*math.pi/180)
      x, y = x0+(dx2-dx1)*radius, y0+(dy2-dy1)*radius
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "cycle"):
      buffer[i] = self._get_pos(0, buffer)
      return buffer[i]
    else:
      raise ValueError(f"Unknown mark type {mark['type']}")

  def get_pos(self, i, bounding_boxes):
    return self._get_pos(i, bounding_boxes, buffer={})

  def get_last_pos(self, bounding_boxes):
    if self.empty():
      raise IndexError("Empty marks")
    return self._get_pos(len(self._marks)-1, bounding_boxes)

  def create_path(self, arrow):
    if self.size() < 2:
      raise ErrorMessage(f"Expect at least two marks")
    items = []
    for i, mark in enumerate(self._marks):
      items.append(copy.deepcopy(mark))
      if i < len(self._marks) - 1 and not is_type(self._marks[i+1], "arc"):
        items.append(create_line())
    return create_path(items, arrow)

  def create_rectangle(self):
    if self.size() != 2:
      raise ErrorMessage(f"Expect exactly two marks")
    return create_path([
        self._marks[0],
        create_rectangle(),
        self._marks[1],
    ])

  def delete(self, index):
    if index < 0 or index >= self.size():
      raise IndexError(f"Index out of bound {index}/{self.size()}")
    del self._marks[index]
