import re


class ObjectHandler(object):
  def match(self, obj_name):
    raise Exception("'match' cannot be invoked directly")
  
  def __call__(self, obj_name):
    raise Exception("'__call__' cannot be invoked directly")


class BoxObjectHandler(ObjectHandler):
  def match(self, obj_name):
    return obj_name == "box"
  
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
