import re
from .object_handlers import *
from .object_renderers import *


class Handler(object):
  def match(self, command):
    raise Exception("'match' cannot be invoked directly")
  
  def __call__(self, context, command):
    raise Exception("'__call__' cannot be invoked directly")
  
  def process_text(self, context, text):
    raise Exception("This handler does not support handling text")


class ThereIsHandler(Handler):
  def __init__(self):
    self._object_handlers = []
    self._object_renderers = []
    self._register_fundamental_handlers()
    self._register_fundamental_renderers()
    
  def _match(self, command):
    m = re.match(r"^there\.is\.an?\.([\w\.]+)$", command)
    if m:
      obj_name = m.group(1)
      for handler in self._object_handlers:
        if handler.match(obj_name):
          return handler(obj_name)
    return None
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    for renderer in self._object_renderers:
      if renderer.match(m):
        obj = renderer.render(m)
        if isinstance(obj, list):
          for item in obj:
            context._picture.append(item)
        else:
          context._picture.append(obj)
        context._state["refered_to"] = obj
        break
    context._state["filter_mode"] = False
  
  def register_object_handler(self, handler):
    assert isinstance(handler, ObjectHandler)
    self._object_handlers.append(handler)
  
  def register_object_renderer(self, renderer):
    assert isinstance(renderer, ObjectRenderer)
    self._object_renderers.append(renderer)
      
  def _register_fundamental_handlers(self):
    self.register_object_handler(BoxObjectHandler())
    self.register_object_handler(TreeObjectHandler())
    self.register_object_handler(GridObjectHandler())
    
  def _register_fundamental_renderers(self):
    self.register_object_renderer(BoxObjectRenderer())
    self.register_object_renderer(TreeObjectRenderer())
    self.register_object_renderer(GridObjectRenderer())


class WithTextHandler(Handler):
  def match(self, command):
    return re.match(
      r"(and|that\.)?(without|with|where|set|let|make\.it|make\.them)\.texts?",
      command) is not None
  
  def __call__(self, context, command):
    batch_mode = command.endswith("texts")
    exclude = re.match(r"(and\.)?without", command) is not None
    context._state["filter_text"] = "filter_mode" in context._state and context._state["filter_mode"]
    context._state["batch_mode"] = batch_mode
    context._state["exclude"] = exclude
    if re.match(r"(and|that\.)?(set|let|make\.it|make\.them)", command):
      context._state["filter_text"] = False
    if re.match(r"(and|that\.)?where", command):
      context._state["filter_text"] = True
      context._state["filter_mode"] = True
    if batch_mode and not exclude:
      context._state["filter_text"] = False
      context._state["counter"] = 0
    if exclude:
      context._state["filter_text"] = True
      context._state["filter_mode"] = True
  
  def process_text(self, context, text):
    if "filter_text" in context._state and context._state["filter_text"]:
      assert isinstance(context._state["refered_to"], list)
      if "exclude" in context._state and context._state["exclude"]:
        context._state["refered_to"] = [obj
                                        for obj in context._state["refered_to"]
                                        if "text" not in obj or obj["text"] != text]
      else:
        context._state["refered_to"] = [obj
                                        for obj in context._state["refered_to"]
                                        if "text" in obj and obj["text"] == text]
      return
    
    target = context._state["refered_to"]
    if isinstance(target, list):
      if context._state["batch_mode"]:
        target[context._state["counter"]]["text"] = text
        context._state["counter"] += 1
      else:
        for item in target:
          item["text"] = text
    else:
      target["text"] = text


class WithNamesHandler(Handler):
  def match(self, command):
    return re.match(
      r"(and|that\.)?(with|set)\.names",
      command) is not None
  
  def __call__(self, context, command):
    context._state["counter"] = 0
  
  def process_text(self, context, text):
    target = context._state["refered_to"]
    if isinstance(target, list):
      target[context._state["counter"]]["name"] = text
      context._state["counter"] += 1
    else:
      target["name"] = text


class WithAttributeHandler(Handler):
  def _match(self, command):
    return re.match(
      r"(?:(?:and|that)\.)?(?:without|with|where|has|have|is|are|set|let|make\.it|make\.them)\.([\w\.]+)(?:=([\w\.!\-]+))?",
      command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    filter_mode = "filter_mode" in context._state and context._state["filter_mode"]
    if re.match(r"(and|that\.)?(has|have|is|are|set|let|make\.it|make\.them)", command):
      filter_mode = False
    if re.match(r"(and|that\.)?where", command):
      filter_mode = True
      context._state["filter_mode"] = True
    exclude = re.match(r"(and\.)?without", command) is not None
    if exclude:
      filter_mode = True
      context._state["filter_mode"] = True
    key = m.group(1)
    value = m.group(2)
    if value is None:
      value = True
    
    if filter_mode:
      assert isinstance(context._state["refered_to"], list)
      if exclude:
        context._state["refered_to"] = [obj
                                        for obj in context._state["refered_to"]
                                        if key not in obj or str(obj[key]) != str(value)]
      else:
        context._state["refered_to"] = [obj
                                        for obj in context._state["refered_to"]
                                        if key in obj and str(obj[key]) == str(value)]
      return
      
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        item[key] = value
    else:
      target[key] = value


class ThereIsTextHandler(Handler):
  def match(self, command):
    return command == "there.is.text"
  
  def __call__(self, context, command):
    obj = {
      "id": getid(),
      "type": "text",
      "text": "",
    }
    context._picture.append(obj)
    context._state["refered_to"] = obj
    context._state["filter_mode"] = False
  
  def process_text(self, context, text):
    context._state["refered_to"]["text"] = text


class DirectionOfHandler(Handler):
  def _match(self, command):
    return re.match(
      r"(?:(?:is|are|set|let)\.)?(left|right|below|above|below.left|below.right|above.left|above.right)\.of\.([\w\.]+)",
      command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    direction = m.group(1)
    name = m.group(2)
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        self._handle(context, item, direction, name)
    else:
      self._handle(context, target, direction, name)
  
  def _handle(self, context, target, direction, name):
    target[direction] = DirectionOfHandler.find_object_with_name(context, name)["id"]
  
  def find_object_with_name(context, name):
    for item in reversed(context._picture):
      if "name" in item and item["name"] == name:
        return item
      if "items" in item and isinstance(item["items"], list):
        for subitem in item["items"]:
          if "name" in subitem and subitem["name"] == name:
            return subitem
    raise Exception(f"Cannot find object with name {name}")


class ByHandler(Handler):
  def _match(self, command):
    return re.match(r"by\.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    dist = m.group(1)
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        self._handle(context, item, dist)
    else:
      self._handle(context, target, dist)
  
  def _handle(self, context, target, dist):
    target["distance"] = dist
    
    
class AnchorAtAnchorHandler(Handler):
  def _match(self, command):
    return re.match(r"(?:with|whose)\.(south|north|west|east|south.west|south.east|north.west|north.east|center)\.(?:(?:is|are)\.)?at\."
                    r"(south|north|west|east|south.west|south.east|north.west|north.east|center)\.of\.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    anchor1, anchor2, name = m.group(1), m.group(2), m.group(3)
    _id = DirectionOfHandler.find_object_with_name(context, name)["id"]
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        self._handle(context, item, anchor1, anchor2, _id)
    else:
      self._handle(context, target, anchor1, anchor2, _id)
  
  def _handle(self, context, target, anchor1, anchor2, _id):
    target["anchor"] = anchor1
    target["at"] = _id
    target["at.anchor"] = anchor2


class ForAllHandler(Handler):
  def _match(self, command):
    return re.match(r"for.all.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    type_name = m.group(1)
    context._state["refered_to"] = [
      obj
      for obj in context._picture
      if "type" in obj and obj["type"] == type_name
    ]
    context._state["filter_mode"] = True


class DrawHandler(Handler):
  def match(self, command):
    return command == "draw"
  
  def __call__(self, context, command):
    path = {
      "type": "path",
      "draw": True,
      "items": []
    }
    context._picture.append(path)
    context._state["refered_to"] = path
    context._state["the_path"] = path
    context._state["filter_mode"] = False


class MoveToNodeHandler(Handler):
  def _match(self, command):
    return re.match(r"(?:from|move\.to)\.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    m = re.match(
      r"([\w\.]+)\.(south|north|east|west|south.west|south.east|north.west|north.east)", node)
    if m:
      obj = {
        "type": "nodename",
        "name": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor": m.group(2),
      }
    else:
      obj = {
        "type": "nodename",
        "name": DirectionOfHandler.find_object_with_name(context, node)["id"],
      }
    context._state["the_path"]["items"].append(obj)
    context._state["refered_to"] = obj


class LineToNodeHandler(Handler):
  def _match(self, command):
    return re.match(r"(?:\-\->?|(?:line|point)\.to\.)([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    m = re.match(
      r"([\w\.]+)\.(south|north|east|west|south.west|south.east|north.west|north.east)", node)
    if m:
      obj = {
        "type": "nodename",
        "name": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor": m.group(2),
      }
    else:
      obj = {
        "type": "nodename",
        "name": DirectionOfHandler.find_object_with_name(context, node)["id"],
      }
    if command.startswith("point") or command.startswith("-->"):
      context._state["the_path"]["stealth"] = True
    line = {"type": "line"}
    context._state["the_path"]["items"].append(line)
    context._state["the_path"]["items"].append(obj)
    context._state["refered_to"] = obj
    context._state["the_line"] = line


class IntersectionHandler(Handler):
  def _match(self, command):
    return re.match(r"intersection\.([\w\.]+)\.and\.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    x, y = m.group(1), m.group(2)
    obj = {
      "type": "intersection"
    }
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", x)
    if match:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor1"] = match.group(2)
    else:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, x)["id"]
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", y)
    if match:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor2"] = match.group(2)
    else:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, y)["id"]
    context._state["the_path"]["items"].append(obj)
    

class CoordinateHandler(Handler):
  def match(self, command):
    return re.match(r"(x|y)\.[\-\w\.]+", command) is not None
  
  def __call__(self, context, command):
    if command.endswith(".relative"):
      relative = True
      command = command[:-9]
    else:
      relative = False
    match = re.match(r"x\.([\-\w\.]+)\.y\.([\-\w\.]+)", command)
    if match:
      x, y = match.group(1), match.group(2)
      
    if not match:
      match = re.match(r"x\.(\-?[\w\.]+)", command)
      if match:
        x, y = match.group(1), "0"
      
    if not match:
      match = re.match(r"y\.(\-?[\w\.]+)", command)
      if match:
        x, y = "0", match.group(1)
  
    context._state["the_path"]["items"].append({
      "type": "coordinate",
      "x": x,
      "y": y,
      "relative": relative,
    })



class LineToHandler(Handler):
  def match(self, command):
    return command == "--" or command == "line.to"
  
  def __call__(self, context, command):
    line = {"type": "line"}
    context._state["the_path"]["items"].append(line)
    context._state["the_line"] = line


class LineVerticalToHandler(Handler):
  def _match(self, command):
    return re.match(r"line.vertical.to.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": point_id,
    })
    line = {"type": "line"}
    context._state["the_path"]["items"].append(line)
    context._state["the_line"] = line
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", node)
    if m:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name1": point_id,
        "name2": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor2": m.group(2),
      })
    else:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name1": point_id,
        "name2": DirectionOfHandler.find_object_with_name(context, node)["id"],
      })

      
class LineHorizontalToHandler(Handler):
  def _match(self, command):
    return re.match(r"line.horizontal.to.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": point_id,
    })
    line = {"type": "line"}
    context._state["the_path"]["items"].append(line)
    context._state["the_line"] = line
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", node)
    if m:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name2": point_id,
        "name1": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor1": m.group(2),
      })
    else:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name2": point_id,
        "name1": DirectionOfHandler.find_object_with_name(context, node)["id"],
      })
      
      
class MoveVerticalToHandler(Handler):
  def _match(self, command):
    return re.match(r"vertical.to.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": point_id,
    })
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", node)
    if m:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name1": point_id,
        "name2": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor2": m.group(2),
      })
    else:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name1": point_id,
        "name2": DirectionOfHandler.find_object_with_name(context, node)["id"],
      })

      
class MoveHorizontalToHandler(Handler):
  def _match(self, command):
    return re.match(r"horizontal.to.([\w\.]+)", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": point_id,
    })
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", node)
    if m:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name2": point_id,
        "name1": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor1": m.group(2),
      })
    else:
      context._state["the_path"]["items"].append({
        "type": "intersection",
        "name2": point_id,
        "name1": DirectionOfHandler.find_object_with_name(context, node)["id"],
      })


class WithAnnotateHandler(Handler):
  def match(self, command):
    return re.match(r"(and\.)?with.annotates?", command) is not None
  
  def __call__(self, context, command):
    line = context._state["the_line"]
    if "annotates" not in line:
      line["annotates"] = []
    context._state["refered_to"] = []
  
  def process_text(self, context, text):
    line = context._state["the_line"]
    obj = {
      "id": getid(),
      "type": "annotate",
      "text": text,
      "scale": "0.7",
      "midway": True,
      "sloped": True,
      "above": True,
    }
    line["annotates"].append(obj)
    context._state["refered_to"].append(obj)


class AtIntersectionHandler(Handler):
  def _match(self, command):
    return re.match(r"at\.intersection\.of\.([\w\.]+)\.and\.([\w\.]+)", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    x, y = m.group(1), m.group(2)
    obj = {
      "type": "intersection"
    }
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", x)
    if match:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor1"] = match.group(2)
    else:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, x)["id"]
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south east|south west|north east|north west|center)", y)
    if match:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor2"] = match.group(2)
    else:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, y)["id"]
    context._state["refered_to"]["at"] = obj


class WhereIsInHandler(Handler):
  def _match(self, command):
    return re.match(r"where\.([\w\.]+)\.is\.in", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    context._state["filter_mode"] = True
    context._state["filter_key"] = m.group(1)
    context._state["select_from"] = context._state["refered_to"]
    context._state["refered_to"] = []

  def process_text(self, context, text):
    key = context._state["filter_key"]
    for item in context._state["select_from"]:
      if key in item and str(item[key]) == text:
        context._state["refered_to"].append(item)
        return
