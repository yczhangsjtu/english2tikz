from english2tikz.utils import *


class BoundingBox(object):
  def __init__(self, x, y, width, height, shape="rectangle", angle=0,
               center=None, obj=None, points=None):
    self._x = x
    self._y = y
    self._width = width
    self._height = height
    self._angle = angle
    self._shape = shape
    self._obj = obj
    self._points = points
    if center is None:
      self._centerx = x + width/2
      self._centery = y + width/2
    else:
      self._centerx, self._centery = center

    if shape == "rectangle" or shape == "circle" or shape == "ellipse":
      assert self._width >= 0
      assert self._height >= 0

    if shape == "circle":
      assert self._width == self._height

    if shape == "curve":
      assert points is not None

  def from_rect(x0, y0, x1, y1, shape="rectangle",
                angle=0, center=None, obj=None):
    if shape != "line":
      x0, x1 = min(x0, x1), max(x0, x1)
      y0, y1 = min(y0, y1), max(y0, y1)
    return BoundingBox(x0, y0, x1-x0, y1-y0, shape, angle, center, obj)

  def get_bound(self):
    if self._shape == "circle":
      x, y = self.rotated_geometry_center()
      r = self.radius()
      return x - r, y - r, x + r, y + r

    if self._shape == "ellipse":
      bb = BoundingBox.from_rect(*self.rect(),
                                 angle=self._angle,
                                 center=(self._centerx, self._centery))
      return bb.get_bound()

    points = self.rotated_vertices()
    x0, y0, x1, y1 = None, None, None, None
    for x, y in points:
      x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x, y)
    return x0, y0, x1, y1

  def diameter(self):
    if self._shape == "rectangle" or self._shape == "line":
      return math.sqrt(self._width * self._width + self._height * self._height)
    if self._shape == "circle":
      return self.radius() * 2
    if self._shape == "ellipse":
      return max(*self.radius()) * 2
    raise ValueError(f"Cannot compute diameter of shape {self._shape}")

  def _get_anchor_pos(bb, anchor):
    x, y, w, h = bb
    if anchor == "center":
      return x + w/2, y + h/2
    elif anchor == "west":
      return x, y + h/2
    elif anchor == "east":
      return x + w, y + h/2
    elif anchor == "south":
      return x + w/2, y
    elif anchor == "north":
      return x + w/2, y + h
    elif anchor == "north.east":
      return x + w, y + h
    elif anchor == "north.west":
      return x, y + h
    elif anchor == "south.east":
      return x + w, y
    elif anchor == "south.west":
      return x, y
    else:
      raise ValueError(f"Unsupported anchor: {anchor}")

  def get_anchor_pos(self, anchor):
    assert self._shape in ["rectangle", "circle", "ellipse"]
    x, y = BoundingBox._get_anchor_pos(
        (self._x, self._y, self._width, self._height), anchor)
    x, y = rotate(x, y, self._centerx, self._centery, -self._angle)
    return x, y

  def rect(self):
    assert self._shape in ["rectangle", "circle", "ellipse"]
    return self._x, self._y, self._x + self._width, self._y + self._height

  def radius(self):
    if self._shape == "circle":
      return self._width / 2
    if self._shape == "ellipse":
      return self._width / 2, self._height / 2
    raise ValueError("Cannot compute radius of non-oval")

  def rotate(self, x, y):
    return rotate(x, y, self._centerx, self._centery, -self._angle)

  def rev_rotate(self, x, y):
    return rotate(x, y, self._centerx, self._centery, self._angle)

  def geometry_center(self):
    assert self._shape in ["rectangle", "circle", "ellipse", "line"]
    return self._x + self._width / 2, self._y + self._height / 2

  def rotated_geometry_center(self):
    x, y = self.geometry_center()
    return self.rotate(x, y)

  def vertices(self):
    if self._shape == "rectangle":
      return [(self._x, self._y),
              (self._x + self._width, self._y),
              (self._x + self._width, self._y + self._height),
              (self._x, self._y + self._height)]
    if self._shape == "line":
      return [(self._x, self._y),
              (self._x + self._width, self._y + self._height)]
    if self._shape == "curve":
      return self._points
    raise ValueError(f"Shape {self._shape} does not have vertices")

  def rotated_vertices(self):
    points = self.vertices()
    return [self.rotate(x, y) for x, y in points]

  def segments(self):
    points = self.vertices()
    if self._shape == "line":
      return [(points[0][0], points[0][1], points[1][0], points[1][1])]
    if self._shape == "curve":
      return [(points[i][0], points[i][1],
               points[i+1][0], points[i+1][1])
              for i in range(len(points)-1)]
    assert self._shape == "rectangle"
    return [(points[i][0], points[i][1],
             points[(i+1) % 4][0], points[(i+1) % 4][1])
            for i in range(4)]

  def rotated_segments(self):
    points = self.rotated_vertices()
    if self._shape == "line":
      return [(points[0][0], points[0][1], points[1][0], points[1][1])]
    if self._shape == "curve":
      return [(points[i][0], points[i][1],
               points[i+1][0], points[i+1][1])
              for i in range(len(points)-1)]
    assert self._shape == "rectangle"
    return [(points[i][0], points[i][1],
             points[(i+1) % 4][0], points[(i+1) % 4][1])
            for i in range(4)]

  def contain_point(self, x, y, strict=False):
    x, y = self.rev_rotate(x, y)
    if self._shape == "rectangle":
      return point_in_rect(x, y, self.rect(), strict)
    if self._shape == "circle":
      if strict:
        return euclidean_dist((x, y), self.geometry_center()) < self.radius()
      else:
        return euclidean_dist((x, y), self.geometry_center()) <= self.radius()
    if self._shape == "ellipse":
      x0, y0 = self.geometry_center()
      a, b = self.radius()
      if strict:
        return (x-x0)*(x-x0)/(a*a) + (y-y0)*(y-y0)/(b*b) < 1
      else:
        return (x-x0)*(x-x0)/(a*a) + (y-y0)*(y-y0)/(b*b) <= 1
    return False

  def intersect_rect(self, rect):
    bb = BoundingBox.from_rect(*rect)
    if self._shape == "rectangle":
      if point_in_rect(*self.rotated_geometry_center(), rect):
        return True
      if point_in_rect(*self.rev_rotate(*bb.geometry_center()), self.rect()):
        return True
      segs1 = self.rotated_segments()
      segs2 = bb.segments()
      for i in range(4):
        for j in range(4):
          if line_line_intersect(segs1[i], segs2[j]):
            return True
      return False

    if self._shape == "circle":
      x, y = self.rotated_geometry_center()
      segs = bb.segments()
      if bb.contain_point(x, y):
        return True
      for seg in segs:
        if point_line_dist(x, y, seg) < self.radius():
          return True
      return False

    if self._shape == "ellipse":
      """
      In this case, we rotate the line segments of the other rect,
      and scale it simultaneously with this bounding box,
      such that this bounding box becomes a unit circle
      """
      x, y = self.rotated_geometry_center()
      if bb.contain_point(x, y):
        return True
      cx, cy = self.geometry_center()
      a, b = self.radius()
      segs = bb.segments()
      segs = [(*self.rev_rotate(x0, y0), *self.rev_rotate(x1, y1))
              for x0, y0, x1, y1 in segs]
      segs = [((x0-cx)/a+cx, (y0-cy)/b+cy, (x1-cx)/a+cx, (y1-cy)/b+cy)
              for x0, y0, x1, y1 in segs]
      for seg in segs:
        if point_line_dist(cx, cy, seg) < 1:
          return True
      return False

    if self._shape == "line" or self._shape == "curve":
      segs = self.rotated_segments()
      for seg in segs:
        if rect_line_intersect(bb.rect(), seg):
          return True
      return False

    raise ValueError("Cannot compute intersection between "
                     f"shape {self._shape} and rect")

  def get_point_at_direction(self, x1, y1):
    x0, y0 = self.rotated_geometry_center()
    x0p, y0p = self.geometry_center()
    x1p, y1p = self.rev_rotate(x1, y1)
    if self._shape == "rectangle":
      cliped_point = clip_line(x0p, y0p, x1p, y1p,
                               (self._x, self._y, self._width, self._height))
      if cliped_point is None:
        return None
      return self.rotate(*cliped_point)

    if self._shape == "circle":
      distance = euclidean_dist((x0, y0), (x1, y1))
      r = self.radius()
      return (x1 - x0) / distance * r + x0, (y1 - y0) / distance * r + y0

    if self._shape == "ellipse":
      a, b = self.radius()
      sx1p = (x1p - x0p) / a + x0p
      sy1p = (y1p - y0p) / b + y0p
      distance = euclidean_dist((x0p, y0p), (sx1p, sy1p))
      sx1p = (sx1p - x0p) / distance * a + x0p
      sy1p = (sy1p - y0p) / distance * b + y0p
      return self.rotate(sx1p, sy1p)

    raise ValueError(f"Cannot compute direction from a shape: {self._shape}")

  def clip_curve(self, curve):
    for i in range(len(curve)):
      if not self.contain_point(*curve[i], strict=True):
        return curve[i:]
    return None


def shift_by_anchor(x, y, anchor, width, height):
  anchor_x, anchor_y = BoundingBox._get_anchor_pos(
      (x, y, width, height), anchor)
  return 2 * x - anchor_x, 2 * y - anchor_y


def enlarge_bound_box(x0, y0, x1, y1, x, y):
  if x0 is None or x < x0:
    x0 = x
  if y0 is None or y < y0:
    y0 = y
  if x1 is None or x > x1:
    x1 = x
  if y1 is None or y > y1:
    y1 = y
  return x0, y0, x1, y1


def get_bounding_box(data, bounding_boxes):
  x0, y0, x1, y1 = None, None, None, None
  for obj in data:
    id_ = obj.get("id")
    if id_ is not None:
      id_ = obj.get("id")
      bb = bounding_boxes[id_]
      x2, y2, x3, y3 = bb.get_bound()
      x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x2, y2)
      x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x3, y3)
    else:
      for id_, bb in bounding_boxes.items():
        if obj == bb._obj:
          x2, y2, x3, y3 = bb.get_bound()
          x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x2, y2)
          x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x3, y3)
    if "items" in obj:
      for item in obj["items"]:
        if "annotates" in item:
          for annotate in item["annotates"]:
            id_ = annotate.get("id")
            if id_ is not None:
              bb = bounding_boxes[id_]
              x2, y2, x3, y3 = bb.get_bound()
              x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x2, y2)
              x0, y0, x1, y1 = enlarge_bound_box(x0, y0, x1, y1, x3, y3)
  if x0 is None:
    return 0, 0, 0, 0
  return x0, y0, x1, y1
