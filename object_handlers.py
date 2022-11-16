import re


class ObjectHandler(object):
  def match(self, obj_name):
    raise Exception("'match' cannot be invoked directly")

  def __call__(self, obj_name):
    raise Exception("'__call__' cannot be invoked directly")


class SupportMultipleHandler(object):
  pass


class BoxObjectHandler(ObjectHandler, SupportMultipleHandler):
  def match(self, obj_name):
    return obj_name == "box" or obj_name == "boxes"

  def __call__(self, obj_name):
    return "box"


class TreeObjectHandler(ObjectHandler):
  def _match(self, obj_name):
    return re.match(r"tree\.with\.branches((?:\.\d+)+)", obj_name)

  def match(self, obj_name):
    return self._match(obj_name) is not None

  def __call__(self, obj_name):
    m = self._match(obj_name)
    assert m is not None
    branches = list(map(int, m.group(1)[1:].split(".")))
    return {
        "type": "tree",
        "branches": branches
    }


class GridObjectHandler(ObjectHandler):
  def _match(self, obj_name):
    return re.match(
        r"(\d+)\.by\.(\d+)\.grid(?:\.aligned\.(top|bottom|center)\.(left|right|center))?",
        obj_name)

  def match(self, obj_name):
    return self._match(obj_name) is not None

  def __call__(self, obj_name):
    m = self._match(obj_name)
    assert m is not None
    h, w = int(m.group(1)), int(m.group(2))
    v_align = m.group(3) if m.group(3) is not None else "center"
    h_align = m.group(4) if m.group(4) is not None else "center"
    return {
        "type": "grid",
        "rows": h,
        "cols": w,
        "v_align": v_align,
        "h_align": h_align,
    }
