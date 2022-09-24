import re
import copy
from .object_handlers import *
from .object_renderers import *


class Handler(object):
  def match(self, command):
    raise Exception("'match' cannot be invoked directly")
  
  def __call__(self, context, command):
    raise Exception("'__call__' cannot be invoked directly")
  
  def process_text(self, context, text):
    raise Exception("This handler does not support handling text")


class GlobalHandler(Handler):
  def match(self, command):
    return command.startswith("global.")

  def __call__(self, context, command):
    m = re.match(r"global\.scale\.([\d\.]+)$", command)
    if m:
      context._scale = m.group(1)
      return

    raise Exception(f"Unsupported command: {command}")


class DefineCommandHandler(Handler):
  def _match(self, command):
    return re.match(r"define\.([A-Za-z0-9]+)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    self._to_define_command = m.group(1)

  def process_text(self, context, text):
    context.define(self._to_define_command, text)


class ReplaceHandler(Handler):
  def _match(self, command):
    return re.match(r"replace(\.command)?(\.text)?\.([\w\.]+)?$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    self.repl_command = m.group(1) is not None
    self.repl_text = m.group(2) is not None
    assert self.repl_text or self.repl_command
    self.pattern = m.group(3)
    self.regexp = False

  def process_text(self, context, text):
    if self.pattern is None:
      self.pattern = text
      self.regexp = True
    else:
      if self.repl_command:
        context.replace_command(self.pattern, text, self.regexp)
      if self.repl_text:
        context.replace_text(self.pattern, text, self.regexp)


class CommentHandler(Handler):
  def match(self, command):
    return command == "comment"

  def __call__(self, context, command):
    pass

  def process_text(self, context, text):
    pass


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
      r"(and|that\.)?(without|with|where|set|let|make\.it|make\.them)\.texts?$",
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
      r"(and|that\.)?(with|set)\.names$",
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


class NamedHandler(Handler):
  def _match(self, command):
    return re.match(r"named\.([\w\.]+)$", command)

  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    name = m.group(1)
    target = context._state["refered_to"]
    if isinstance(target, list):
      assert len(target) == 1
      target = target[0]
    target["name"] = name


class SizedHandler(Handler):
  def _match(self, command):
    return re.match(r"sized\.([\w\.]+)\.by\.([\w\.]+)$", command)

  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    w, h = m.group(1), m.group(2)
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        item["width"] = w
        item["height"] = h
    else:
      target["width"] = w
      target["height"] = h


class ShiftedHandler(Handler):
  def _match(self, command):
    return re.match(r"shifted\.(left|right|up|down)\.by\.([\w\.]+)$", command)

  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    direction, distance = m.group(1), m.group(2)
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        self._handle(item, direction, distance)
    else:
      self._handle(target, direction, distance)

  def _handle(self, target, direction, distance):
    if direction == "left":
      target["xshift"] = f"-{distance}"
    elif direction == "right":
      target["xshift"] = distance
    elif direction == "up":
      target["yshift"] = distance
    elif direction == "down":
      target["yshift"] = f"-{distance}"


class StartOutHandler(Handler):
  def _match(self, command):
    return re.match(r"start.out.(\d+|up|down|left|right)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    direction = m.group(1)
    if direction == "up":
      direction = 90
    elif direction == "down":
      direction = 270
    elif direction == "left":
      direction = 180
    elif direction == "right":
      direction = 0
    else:
      direction = int(direction)
    context._state["the_line"]["out"] = direction


class CloseInHandler(Handler):
  def _match(self, command):
    return re.match(r"close.in.(\d+|up|down|left|right)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    direction = m.group(1)
    if direction == "up":
      direction = 90
    elif direction == "down":
      direction = 270
    elif direction == "left":
      direction = 180
    elif direction == "right":
      direction = 0
    else:
      direction = int(direction)
    context._state["the_line"]["in"] = direction


class WithAttributeHandler(Handler):
  mutually_exclusive = [
    set([
      "above", "below", "left", "right",
      "below.left", "below.right",
      "above.left", "above.right",
    ]),
    set([
      "midway", "pos",
      "near.end", "near.start",
      "very.near.end", "very.near.start",
      "at.end", "at.start"
    ]),
  ]
  def _match(self, command):
    return re.match(
      r"(?:(?:and|that)\.)?(?:without|with|where|has|have|is|are|set|let|make\.it|make\.them)\.([\w\.]+)(?:=([\w\.!\-\(\),]+))?$",
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
    if isinstance(value, str):
      m = re.match(r"rgb\((\d+),(\d+),(\d+)\)", value)
      if m is not None:
        value = f"{{rgb,255:red,{m.group(1)};green,{m.group(2)};blue,{m.group(3)}}}"
    
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
        self._handle(item, key, value)
    else:
      self._handle(target, key, value)

  def _handle(self, target, key, value):
    target[key] = value
    for me in WithAttributeHandler.mutually_exclusive:
      if key in me:
        for other_key in me:
          if other_key != key and other_key in target:
            del target[other_key]


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
      r"(?:(?:is|are|set|let)\.)?(left|right|below|above|below.left|below.right|above.left|above.right)\.of\.([\w\.]+)$",
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
    for other_direction in ["above", "below", "left", "right",
                            "above.left", "above.right",
                            "below.left", "below.right"]:
      if other_direction != direction and other_direction in target:
        del target[other_direction]
  
  def find_object_with_name(context, name):
    for item in reversed(context._picture):
      if "name" in item and item["name"] == name:
        return item
      if "items" in item and isinstance(item["items"], list):
        for subitem in item["items"]:
          if "name" in subitem and subitem["name"] == name and "id" in subitem:
            return subitem
          if "annotates" in subitem:
            for annotate in subitem["annotates"]:
              if "name" in annotate and annotate["name"] == name:
                return annotate
    raise Exception(f"Cannot find object with name {name}")


class NoSlopeHandler(Handler):
  def match(self, command):
    return command == "no.slope" or command == "without.slope"

  def __call__(self, context, command):
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        self._handle(item)
    else:
      self._handle(target)

  def _handle(self, target):
    if "sloped" in target:
      del target["sloped"]


class ByHandler(Handler):
  def _match(self, command):
    return re.match(r"by\.(\-?[\w\.]+)$", command)
  
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
                    r"(south|north|west|east|south.west|south.east|north.west|north.east|center)\.of\.([\w\.]+)$", command)
  
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
    return re.match(r"for.all.([\w\.]+)$", command)
  
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


class DrawBraceHandler(Handler):
  def match(self, command):
    return command == "draw.brace"
  
  def __call__(self, context, command):
    path = {
      "type": "brace",
      "items": []
    }
    context._picture.append(path)
    context._state["refered_to"] = path
    context._state["the_path"] = path
    context._state["filter_mode"] = False


class FillHandler(Handler):
  def _match(self, command):
    return re.match("fill.with.([\w\.!]+)$", command)

  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    path = {
      "type": "path",
      "fill": m.group(1),
      "items": []
    }
    context._picture.append(path)
    context._state["refered_to"] = path
    context._state["the_path"] = path
    context._state["filter_mode"] = False


class MoveToNodeHandler(Handler):
  def _match(self, command):
    return re.match(r"(?:from|move\.to)\.([\w\.]+)$", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    m = re.match(
      r"([\w\.]+?)\.(south|north|east|west|south.west|south.east|north.west|north.east)$", node)
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


class RectangleHorizontalToByHandler(Handler):
  def _match(self, command):
    return re.match(r"rectangle\.horizontal\.to\.([\w\.]+)\.and\.(up|down)\.by\.([\w\.]+)$", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node, direction, distance = m.group(1), m.group(2), m.group(3)
    start_point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": start_point_id,
    })

    m = re.match(
      r"([\w\.]+?)\.(south|north|east|west|south.west|south.east|north.west|north.east)$", node)
    if m:
      obj = {
        "type": "intersection",
        "name1": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor1": m.group(2),
        "name2": start_point_id,
      }
    else:
      obj = {
        "type": "intersection",
        "name1": DirectionOfHandler.find_object_with_name(context, node)["id"],
        "name2": start_point_id,
      }
    context._state["the_path"]["items"].append(obj)

    if direction == "up":
      context._state["the_path"]["items"].append({
        "type": "coordinate",
        "x": "0",
        "y": distance,
        "relative": True,
      })
    else:
      context._state["the_path"]["items"].append({
        "type": "coordinate",
        "x": "0",
        "y": f"-{distance}",
        "relative": True,
      })

    end_point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": end_point_id,
    })

    context._state["the_path"]["items"].append({
      "type": "nodename",
      "name": start_point_id,
    })

    context._state["the_path"]["items"].append({
      "type": "rectangle",
    })

    context._state["the_path"]["items"].append({
      "type": "nodename",
      "name": end_point_id,
    })


class RectangleVerticalToByHandler(Handler):
  def _match(self, command):
    return re.match(r"rectangle\.vertical\.to\.([\w\.]+)\.and\.(left|right)\.by\.([\w\.]+)$", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node, direction, distance = m.group(1), m.group(2), m.group(3)
    start_point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": start_point_id,
    })

    m = re.match(
      r"([\w\.]+?)\.(south|north|east|west|south.west|south.east|north.west|north.east)$", node)
    if m:
      obj = {
        "type": "intersection",
        "name2": DirectionOfHandler.find_object_with_name(context, m.group(1))["id"],
        "anchor2": m.group(2),
        "name1": start_point_id,
      }
    else:
      obj = {
        "type": "intersection",
        "name2": DirectionOfHandler.find_object_with_name(context, node)["id"],
        "name1": start_point_id,
      }
    context._state["the_path"]["items"].append(obj)

    if direction == "right":
      context._state["the_path"]["items"].append({
        "type": "coordinate",
        "x": distance,
        "y": "0",
        "relative": True,
      })
    else:
      context._state["the_path"]["items"].append({
        "type": "coordinate",
        "x": f"-{distance}",
        "y": "0",
        "relative": True,
      })

    end_point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": end_point_id,
    })

    context._state["the_path"]["items"].append({
      "type": "nodename",
      "name": start_point_id,
    })

    context._state["the_path"]["items"].append({
      "type": "rectangle",
    })

    context._state["the_path"]["items"].append({
      "type": "nodename",
      "name": end_point_id,
    })


class RectangleToNodeShiftedHandler(Handler):
  def _match(self, command):
    return re.match(r"rectangle\.to\.([\w\.]+)\.shifted\.by(?:\.x\.(\-?[\w\.]+))?(?:\.y\.(\-?[\w\.]+))?$", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node, x, y = m.group(1), m.group(2), m.group(3)
    start_point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": start_point_id,
    })

    m = re.match(
      r"([\w\.]+?)\.(south|north|east|west|south.west|south.east|north.west|north.east)$", node)
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
    context._state["the_path"]["items"].append({
      "type": "coordinate",
      "x": x if x is not None else "0",
      "y": y if y is not None else "0",
      "relative": True,
    })

    end_point_id = getid()
    context._state["the_path"]["items"].append({
      "type": "point",
      "id": end_point_id,
    })

    context._state["the_path"]["items"].append({
      "type": "nodename",
      "name": start_point_id,
    })

    context._state["the_path"]["items"].append({
      "type": "rectangle",
    })

    context._state["the_path"]["items"].append({
      "type": "nodename",
      "name": end_point_id,
    })


class LineToNodeHandler(Handler):
  def _match(self, command):
    return re.match(r"(?:\-\->?|(?:line|point)\.to\.)([\w\.]+)$", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    node = m.group(1)
    m = re.match(
      r"([\w\.]+?)\.(south|north|east|west|south.west|south.east|north.west|north.east)$", node)
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
    return re.match(r"intersection\.([\w\.]+)\.and\.([\w\.]+)$", command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    x, y = m.group(1), m.group(2)
    obj = {
      "type": "intersection"
    }
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", x)
    if match:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor1"] = match.group(2)
    else:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, x)["id"]
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", y)
    if match:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor2"] = match.group(2)
    else:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, y)["id"]
    context._state["the_path"]["items"].append(obj)
    

class CoordinateHandler(Handler):
  def match(self, command):
    return re.match(r"(x|y)\.[\-\w\.]+$", command) is not None
  
  def __call__(self, context, command):
    if command.endswith(".relative"):
      relative = True
      command = command[:-9]
    else:
      relative = False
    match = re.match(r"x\.([\-\w\.]+)\.y\.([\-\w\.]+)$", command)
    if match:
      x, y = match.group(1), match.group(2)
      
    if not match:
      match = re.match(r"x\.(\-?[\w\.]+)$", command)
      if match:
        x, y = match.group(1), "0"
      
    if not match:
      match = re.match(r"y\.(\-?[\w\.]+)$", command)
      if match:
        x, y = "0", match.group(1)
  
    context._state["the_path"]["items"].append({
      "type": "coordinate",
      "x": x,
      "y": y,
      "relative": relative,
    })


class MoveDirectionHandler(Handler):
  def _match(self, command):
    return re.match(r"move\.(up|down|left|right)\.by\.([\w\.]+)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    direction, distance = m.group(1), m.group(2)
    if direction == "up":
      x, y = "0", distance
    elif direction == "down":
      x, y = "0", f"-{distance}"
    elif direction == "left":
      x, y = f"-{distance}", "0"
    elif direction == "right":
      x, y = distance, "0"
    context._state["the_path"]["items"].append({
      "type": "coordinate",
      "x": x,
      "y": y,
      "relative": True,
    })


class LineDirectionHandler(Handler):
  def _match(self, command):
    return re.match(r"line\.(up|down|left|right)\.by\.([\w\.]+)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    direction, distance = m.group(1), m.group(2)
    if direction == "up":
      x, y = "0", distance
    elif direction == "down":
      x, y = "0", f"-{distance}"
    elif direction == "left":
      x, y = f"-{distance}", "0"
    elif direction == "right":
      x, y = distance, "0"
    line = {
      "type": "line",
    }
    context._state["the_path"]["items"].append(line)
    context._state["the_path"]["items"].append({
      "type": "coordinate",
      "x": x,
      "y": y,
      "relative": True,
    })
    context._state["the_line"] = line


class LineToHandler(Handler):
  def match(self, command):
    return command == "--" or command == "line.to" or command == "line"
  
  def __call__(self, context, command):
    line = {"type": "line"}
    context._state["the_path"]["items"].append(line)
    context._state["the_line"] = line


class VerticalHorizontalToHandler(Handler):
  def match(self, command):
    return command == "|-" or command == "vertical.horizontal.to" or command == "vertical.horizontal"
  
  def __call__(self, context, command):
    line = {"type": "vertical.horizontal"}
    context._state["the_path"]["items"].append(line)
    context._state["the_line"] = line


class LineVerticalToHandler(Handler):
  def _match(self, command):
    return re.match(r"line.vertical.to.([\w\.]+)$", command)
  
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
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", node)
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
    return re.match(r"line.horizontal.to.([\w\.]+)$", command)
  
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
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", node)
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
    return re.match(r"vertical.to.([\w\.]+)$", command)
  
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
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", node)
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
    return re.match(r"horizontal.to.([\w\.]+)$", command)
  
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
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", node)
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
    return re.match(r"(and\.)?with.annotates?$", command) is not None
  
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
    return re.match(r"at\.intersection\.of\.([\w\.]+)\.and\.([\w\.]+)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    x, y = m.group(1), m.group(2)
    obj = {
      "type": "intersection"
    }
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", x)
    if match:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor1"] = match.group(2)
    else:
      obj["name1"] = DirectionOfHandler.find_object_with_name(context, x)["id"]
    match = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", y)
    if match:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, match.group(1))["id"]
      obj["anchor2"] = match.group(2)
    else:
      obj["name2"] = DirectionOfHandler.find_object_with_name(context, y)["id"]
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        item["at"] = obj
    else:
      target["at"] = obj


class AtCoordinateHandler(Handler):
  def _match(self, command):
    return re.match(r"at\.x\.(\-?[\w\.]+)\.y\.(\-?[\w\.]+)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    x, y = m.group(1), m.group(2)
    obj = {
      "type": "coordinate",
      "x": x,
      "y": y,
    }
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        item["at"] = obj
    else:
      target["at"] = obj


class WhereIsInHandler(Handler):
  def _match(self, command):
    return re.match(r"where\.([\w\.]+)\.is\.in$", command)

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


class GridWithFixedDistancesHandler(Handler):
  def _match(self, command):
    return re.match(
      r"there.is.a.(\d+)\.by\.(\d+)\.grid\.with\.fixed\.distances(?:\.aligned\.(top|bottom|center)\.(left|right|center))?$",
      command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    h, w = int(m.group(1)), int(m.group(2))
    v_align = m.group(3) if m.group(3) is not None else "center"
    h_align = m.group(4) if m.group(4) is not None else "center"
    nodes = [[
      {
        "type": "text",
        "id": getid(),
        "text": f"grid-{i}-{j}",
      } for j in range(w)
    ] for i in range(h)]
    nodes[0][0]["origin"] = True
    nodes[0][0]["first.row"] = True
    nodes[0][0]["first.col"] = True
    context._state["to_set_value"] = []
    for i in range(h):
      for j in range(w):
        nodes[i][j]["row"] = i
        nodes[i][j]["col"] = j
        if i % 2 == 0:
          nodes[i][j]["even.row"] = True
        else:
          nodes[i][j]["even.row"] = False
        if j % 2 == 0:
          nodes[i][j]["even.col"] = True
        else:
          nodes[i][j]["even.col"] = False
        if i == 0 and j > 0:
          nodes[i][j]["first.row"] = True
          nodes[i][j]["at"] = nodes[i][j-1]["id"]
          nodes[i][j]["xshift"] = "1cm"
          context._state["to_set_value"].append(nodes[i][j])
          context._state["to_set_value"].append("xshift")
        elif i > 0 and j == 0:
          nodes[i][j]["first.col"] = True
          nodes[i][j]["at"] = nodes[i-1][j]["id"]
          nodes[i][j]["yshift"] = "-1cm"
          context._state["to_set_value"].append(nodes[i][j])
          context._state["to_set_value"].append("yshift")
        elif i > 0 and j > 0:
          nodes[i][j]["at"] = {
            "type": "intersection",
            "name1": nodes[0][j]["id"],
            "name2": nodes[i][0]["id"],
          }
          if h_align == "left":
            nodes[i][j]["at"]["anchor1"] = "west"
          elif h_align == "center":
            nodes[i][j]["at"]["anchor1"] = "center"
          elif h_align == "right":
            nodes[i][j]["at"]["anchor1"] = "east"
            
          if v_align == "top":
            nodes[i][j]["at"]["anchor2"] = "north"
          elif v_align == "center":
            nodes[i][j]["at"]["anchor2"] = "center"
          elif v_align == "bottom":
            nodes[i][j]["at"]["anchor2"] = "south"
            
          if v_align == "top":
            if h_align == "left":
              nodes[i][j]["anchor"] = "north.west"
            elif h_align == "center":
              nodes[i][j]["anchor"] = "north"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "north.east"
          elif v_align == "center":
            if h_align == "left":
              nodes[i][j]["anchor"] = "west"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "east"
          elif v_align == "bottom":
            if h_align == "left":
              nodes[i][j]["anchor"] = "south.west"
            elif h_align == "center":
              nodes[i][j]["anchor"] = "south"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "south.east"

        if (i == 0 and j > 0) or (i > 0 and j == 0):
          if v_align == "top":
            if h_align == "left":
              nodes[i][j]["anchor"] = "north.west"
            elif h_align == "center":
              nodes[i][j]["anchor"] = "north"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "north.east"
          elif v_align == "center":
            if h_align == "left":
              nodes[i][j]["anchor"] = "west"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "east"
          elif v_align == "bottom":
            if h_align == "left":
              nodes[i][j]["anchor"] = "south.west"
            elif h_align == "center":
              nodes[i][j]["anchor"] = "south"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "south.east"
          if "anchor" in nodes[i][j]:
            nodes[i][j]["at.anchor"] = nodes[i][j]["anchor"]

    context._state["refered_to"] = []
    for row in nodes:
      for node in row:
        context._picture.append(node)
        context._state["refered_to"].append(node)

  def process_text(self, context, text):
    obj = context._state["to_set_value"][0]
    key = context._state["to_set_value"][1]
    context._state["to_set_value"] = context._state["to_set_value"][2:]
    obj[key] = text


class RectangleHandler(Handler):
  def match(self, command):
    return command == "rectangle" or command == "rectangle.to"

  def __call__(self, context, command):
    context._state["the_path"]["items"].append({
      "type": "rectangle"
    })


class TextOperationHandler(Handler):
  pass


class RepeatedHandler(TextOperationHandler):
  def _match(self, command):
    return re.match(r"repeated\.((\d+|three|four|five|six|seven|eight|nine|ten)\.times|twice)$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    times = m.group(1)
    number = m.group(2)
    if times == "twice":
      count = 2
    else:
      assert number is not None
      if number == "three":
        count = 3
      elif number == "four":
        count = 4
      elif number == "five":
        count = 5
      elif number == "six":
        count = 6
      elif number == "seven":
        count = 7
      elif number == "eight":
        count = 8
      elif number == "nine":
        count = 9
      elif number == "ten":
        count = 10
      else:
        count = int(number)
    if context._last_is_command:
      """
      Repeat the search for every count, because we do not assume
      that some handlers can only be invoked once or a limited number of
      times and may no longer matches.
      We do not invoke context.process recursively because we want to avoid
      other side effects brought by this method.
      """
      for i in range(count - 1):
        for handler in reversed(context._handlers):
          if handler.match(context._last_command):
            if isinstance(handler, TextOperationHandler):
              raise Exception("Cannot repeat a text operation handler")
            """
            Remember this last handler, because if this repeated handler is
            followed by text, then the text will be fed into this last handler
            """
            context._state["handler_to_repeat"] = handler
            handler(context, context._last_command)
    elif context._last_is_text:
      if not isinstance(context._last_handler, TextOperationHandler):
        handler = context._last_handler
        context._state["handler_to_repeat"] = handler
      else:
        handler = context._state["handler_to_repeat"]
      for i in range(count - 1):
        handler.process_text(context, context._last_text)
    else:
      raise Exception("Neither _last_is_command or _last_is_text is set")

  def process_text(self, context, text):
    context._state["handler_to_repeat"].process_text(context, text)


class CopyLastObjectHandler(Handler):
  def _match(self, command):
    return re.match(r"copy\.last(?:\.(\d+|two|three|four|five|six|seven|eight|nine|ten))?\.objects?(?:\.((\d+|three|four|five|six|seven|eight|nine|ten)\.times|twice))?$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    copied_count = m.group(1)
    copies_count = m.group(2)
    copies_number = m.group(3)
    if copied_count is None:
      copied_count = 1
    elif copied_count == "three":
      copied_count = 3
    elif copied_count == "four":
      copied_count = 4
    elif copied_count == "five":
      copied_count = 5
    elif copied_count == "six":
      copied_count = 6
    elif copied_count == "seven":
      copied_count = 7
    elif copied_count == "eight":
      copied_count = 8
    elif copied_count == "nine":
      copied_count = 9
    elif copied_count == "ten":
      copied_count = 10
    else:
      copied_count = int(copied_count)

    if copies_count is None:
      copies_count = 1
    elif copies_count == "twice":
      copies_count = 2
    else:
      assert copies_number is not None
      if copies_number == "three":
        copies_count = 3
      elif copies_number == "four":
        copies_count = 4
      elif copies_number == "five":
        copies_count = 5
      elif copies_number == "six":
        copies_count = 6
      elif copies_number == "seven":
        copies_count = 7
      elif copies_number == "eight":
        copies_count = 8
      elif copies_number == "nine":
        copies_count = 9
      elif copies_number == "ten":
        copies_count = 10
      else:
        copies_count = int(copies_number)

    to_copy = context._picture[-copied_count:]
    context._state["refered_to"] = []
    for i in range(copies_count):
      for item in to_copy:
        new_item = copy.deepcopy(item)
        if "id" in new_item:
          new_item["id"] = getid()
        context._picture.append(new_item)
        context._state["refered_to"].append(new_item)


class CopyThemHandler(Handler):
  def match(self, command):
    return command == "copy.them" or command == "copy.it"

  def __call__(self, context, command):
    target = context._state["refered_to"]
    if isinstance(target, list):
      copied = [copy.deepcopy(item) for item in target]
      for item in copied:
        if "id" in item:
          item["id"] = getid()
      for item in copied:
        context._picture.append(item)
      context._state["refered_to"] = copied
    else:
      copied = copy.deepcopy(target)
      if "id" in copied:
        copied["id"] = getid()
      context._picture.append(copied)
      context._state["refered_to"] = copied
    context._state["filter_mode"] = False


class CopyStyleFromHandler(Handler):
  def _match(self, command):
    return re.match(r"copy\.style\.from\.([\w\.]+)", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    name = m.group(1)
    obj = DirectionOfHandler.find_object_with_name(context, name)
    target = context._state["refered_to"]
    if isinstance(target, list):
      for item in target:
        self._handle(item, obj)
    else:
      self._handle(target, obj)

  def _handle(self, target, obj):
    for key in ["color", "line.width", "rounded.corners", "fill",
                "scale", "rotate", "circle", "inner.sep", "text",
                "width", "height", "shape", "dashed", "font", "draw"]:
      if key in obj:
        target[key] = obj[key]


class RespectivelyWithHandler(Handler):
  def _match(self, command):
    return re.match(
      r"(?:(?:and|that)\.)?respectively\.(?:with|have|are|set|make\.them|make\.their)\.([\w\.]+)?$",
      command)
  
  def match(self, command):
    return self._match(command) is not None
  
  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    key = m.group(1)
    context._state["to_set_objects"] = [item for item in context._state["refered_to"]]
    if key is not None:
      context._state["to_set_key"] = key
    else:
      context._state["to_set_key"] = None

  def process_text(self, context, text):
    to_set_key = context._state["to_set_key"]
    if to_set_key is None:
      key, value = text, True
    else:
      key, value = to_set_key, text
    context._state["to_set_objects"][0][key] = value
    context._state["to_set_objects"] = context._state["to_set_objects"][1:]


class RespectivelyAtHandler(Handler):
  def _match(self, command):
    return re.match(r"respectively.at$", command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    context._state["to_set_objects"] = [item for item in context._state["refered_to"]]

  def process_text(self, context, text):
    m = re.match(r"x\.(\-?[\w\.]+)\.y\.(\-?[\w\.]+)$", text)
    if m is not None:
      context._state["to_set_objects"][0]["at"] = {
        "type": "coordinate",
        "x": m.group(1),
        "y": m.group(2),
      }
      context._state["to_set_objects"] = context._state["to_set_objects"][1:]
      return
    m = re.match(r"([\w\.]+)\.(south|north|east|west|south\.east|south\.west|north\.east|north\.west|center)$", text)
    if m is not None:
      context._state["to_set_objects"][0]["at"] = {
        "type": "nodename",
        "name": DirectionOfHandler.find_object_with_name(context, m.group(1)),
        "anchor": m.group(2),
      }
    else:
      context._state["to_set_objects"][0]["at"] = {
        "type": "nodename",
        "name": DirectionOfHandler.find_object_with_name(context, text),
      }
    context._state["to_set_objects"] = context._state["to_set_objects"][1:]


class RangeHandler(TextOperationHandler):
  def match(self, command):
    return command == "range"

  def __call__(self, context, command):
    """
    Ensure that "handler_to_repeat" is the correct one
    """
    if not isinstance(context._last_handler, TextOperationHandler):
      context._state["handler_to_repeat"] = context._last_handler
    else:
      assert "handler_to_repeat" in context._state
    context._state["expect_range"] = True

  def process_text(self, context, text):
    if context._state["expect_range"]:
      context._state["expect_range"] = False
      texts = self._generate_range(text)
      for text in texts:
        context._state["handler_to_repeat"].process_text(context, text)
    else:
      context._state["handler_to_repeat"].process_text(context, text)

  def _generate_range(self, text):
    ranges = []
    original_text = text
    while len(text) > 0:
      m = re.search(r"\{\{\{((\-?\d+)(?:\:(\-?\d+))?\:(\-?\d+)|([A-Za-z])(?:\:(\-?\d+))?\:([A-Za-z])|.+?(?:,.+?)+)\}\}\}", text)
      if m is None:
        ranges.append(text)
        break
      ranges.append(text[:m.span()[0]])
      text = text[m.span()[1]:]
      rng = m.group(1)
      start_number, end_number = m.group(2), m.group(4)
      step_number = int(m.group(3)) if m.group(3) else None
      start_letter, end_letter = m.group(5), m.group(7)
      step_letter = int(m.group(6)) if m.group(6) else None
      if start_number is not None:
        start_number, end_number = int(start_number), int(end_number)
        if step_number is None:
          step_number = 1 if start_number < end_number else -1
        """
        Python range is open at the end, we make it close
        """
        ranges.append(list(range(start_number, end_number+step_number, step_number)))
      elif start_letter is not None:
        if step_letter is None:
          step_letter = 1 if start_letter < end_letter else -1
        ranges.append([
          chr(i)
          for i in list(range(ord(start_letter), ord(end_letter)+step_letter, step_letter))
        ])
      else:
        ranges.append([item.strip() for item in rng.split(',')])
    repeated = 1
    for r in ranges:
      if isinstance(r, list):
        if len(r) < 2:
          raise Exception(f"The range size is smaller than 2: {r}")
        if repeated > 1:
          assert len(r) == repeated
        else:
          repeated = len(r)
    if repeated == 1:
      raise Exception(f"No range found in text: {original_text}")
    return [''.join([r if isinstance(r, str) else str(r[i]) for r in ranges])
            for i in range(repeated)]


class DynamicGridHandler(Handler):
  def _match(self, command):
    return re.match(
        r"there\.is\.dynamic\.grid(?:\.aligned\.(top|center|bottom)\.(left|center|right))?\.with\.id.([\w\.]+)$",
        command)

  def match(self, command):
    return self._match(command)

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    v_align, h_align, id_ = m.group(1), m.group(2), m.group(3)
    h_align = h_align if h_align is not None else "center"
    v_align = v_align if v_align is not None else "center"
    origin_id = getid()
    context._state[f"dynamic.grid.{id_}"] = {
      "node.ids": [[origin_id]],
      "col.aligns": [h_align],
      "row.aligns": [v_align],
    }
    origin = {
      "id": origin_id,
      "type": "text",
      "text": "",
      "grid.id": id_,
      "col": 0,
      "row": 0,
    }
    context._picture.append(origin)
    context._state["refered_to"] = origin
    context._state["filter_mode"] = False


class AddRowHandler(Handler):
  def _match(self, command):
    return re.match(
        r"add\.row(?:\.aligned\.(top|center|bottom))?\.to\.grid\.([\w\.]+)$",
        command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    align, id_ = m.group(1), m.group(2)
    align = align if align is not None else "center"
    key = f"dynamic.grid.{id_}"
    if key not in context._state:
      raise Exception(f"Dynamic grid {id_} is not created yet")
    grid = context._state[key]
    nrows = len(grid["row.aligns"])
    ncols = len(grid["col.aligns"])
    assert nrows == len(grid["node.ids"])
    assert ncols == len(grid["node.ids"][0])
    grid["row.aligns"].append(align)
    node_ids, nodes = [], []
    for i in range(ncols):
      node_id = getid()
      node = {
          "id": node_id,
          "type": "text",
          "text": "",
          "grid.id": id_,
          "col": i,
          "row": nrows,
      }
      h_align = grid["col.aligns"][i]
      if i == 0:
        node["at"] = grid["node.ids"][-1][0]
        if h_align == "left":
          node["anchor"] = "north.west"
          node["at.anchor"] = "south.west"
        elif h_align == "center":
          node["anchor"] = "north"
          node["at.anchor"] = "south"
        elif h_align == "right":
          node["anchor"] = "north.east"
          node["at.anchor"] = "south.east"
      else:
        intersection = {
          "type": "intersection",
          "name1": grid["node.ids"][0][i],
          "name2": node_ids[0],
        }
        if align == "top":
          intersection["anchor2"] = "north"
          if h_align == "left":
            node["anchor"] = "north.west"
            intersection["anchor1"] = "west"
          elif h_align == "center":
            node["anchor"] = "north"
            intersection["anchor1"] = "center"
          elif h_align == "right":
            node["anchor"] = "north.east"
            intersection["anchor1"] = "east"
        elif align == "center":
          intersection["anchor2"] = "center"
          if h_align == "left":
            node["anchor"] = "west"
            intersection["anchor1"] = "west"
          elif h_align == "center":
            node["anchor"] = "center"
            intersection["anchor1"] = "center"
          elif h_align == "right":
            node["anchor"] = "east"
            intersection["anchor1"] = "east"
        elif align == "bottom":
          intersection["anchor2"] = "south"
          if h_align == "left":
            node["anchor"] = "south.west"
            intersection["anchor1"] = "west"
          elif h_align == "center":
            node["anchor"] = "south"
            intersection["anchor1"] = "center"
          elif h_align == "right":
            node["anchor"] = "south.east"
            intersection["anchor1"] = "east"
        node["at"] = intersection
      context._picture.append(node)
      node_ids.append(node_id)
      nodes.append(node)
    grid["node.ids"].append(node_ids)
    context._state["refered_to"] = nodes
    context._state["filter_mode"] = False


class AddColHandler(Handler):
  def _match(self, command):
    return re.match(
        r"add\.column(?:\.aligned\.(left|center|right))?\.to\.grid\.([\w\.]+)$",
        command)

  def match(self, command):
    return self._match(command) is not None

  def __call__(self, context, command):
    m = self._match(command)
    assert m is not None
    align, id_ = m.group(1), m.group(2)
    align = align if align is not None else "center"
    key = f"dynamic.grid.{id_}"
    if key not in context._state:
      raise Exception(f"Dynamic grid {id_} is not created yet")
    grid = context._state[key]
    nrows = len(grid["row.aligns"])
    ncols = len(grid["col.aligns"])
    assert nrows == len(grid["node.ids"])
    assert ncols == len(grid["node.ids"][0])
    grid["col.aligns"].append(align)
    node_ids, nodes = [], []
    for i in range(nrows):
      node_id = getid()
      node = {
          "id": node_id,
          "type": "text",
          "text": "",
          "grid.id": id_,
          "col": ncols,
          "row": i,
      }
      v_align = grid["row.aligns"][i]
      if i == 0:
        node["at"] = grid["node.ids"][0][-1]
        if v_align == "top":
          node["anchor"] = "north.west"
          node["at.anchor"] = "north.east"
        elif v_align == "center":
          node["anchor"] = "west"
          node["at.anchor"] = "east"
        elif v_align == "bottom":
          node["anchor"] = "south.west"
          node["at.anchor"] = "south.east"
      else:
        intersection = {
          "type": "intersection",
          "name1": node_ids[0],
          "name2": grid["node.ids"][i][0],
        }
        if v_align == "top":
          intersection["anchor2"] = "north"
          if align == "left":
            node["anchor"] = "north.west"
            intersection["anchor1"] = "west"
          elif align == "center":
            node["anchor"] = "north"
            intersection["anchor1"] = "center"
          elif align == "right":
            node["anchor"] = "north.east"
            intersection["anchor1"] = "east"
        elif v_align == "center":
          intersection["anchor2"] = "center"
          if align == "left":
            node["anchor"] = "west"
            intersection["anchor1"] = "west"
          elif align == "center":
            node["anchor"] = "center"
            intersection["anchor1"] = "center"
          elif align == "right":
            node["anchor"] = "east"
            intersection["anchor1"] = "east"
        elif v_align == "bottom":
          intersection["anchor2"] = "south"
          if align == "left":
            node["anchor"] = "south.west"
            intersection["anchor1"] = "west"
          elif align == "center":
            node["anchor"] = "south"
            intersection["anchor1"] = "center"
          elif align == "right":
            node["anchor"] = "south.east"
            intersection["anchor1"] = "east"
        node["at"] = intersection
      context._picture.append(node)
      node_ids.append(node_id)
      nodes.append(node)
    for i in range(nrows):
      grid["node.ids"][i].append(node_ids[i])
    context._state["refered_to"] = nodes
    context._state["filter_mode"] = False
