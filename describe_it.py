import json
import re
from functools import partial
from english2tikz.handlers import *
from english2tikz.renderers import *
from english2tikz.object_handlers import SupportMultipleHandler
from english2tikz.object_renderers import SupportMultipleRenderer
from english2tikz.preprocessor import *
from english2tikz.utils import *
from english2tikz.errors import *
from english2tikz.gui.object_utils import *


class DescribeIt(object):
  def __init__(self):
    self._state = {}
    self._picture = []
    self._history = []
    self._handlers = []
    self._renderers = []
    self._preprocessors = []
    self._register_fundamental_handlers()
    self._register_fundamental_renderers()
    self._register_fundamental_preprocessors()
    self._last_handler = None
    self._scale = 1

  def getid(self):
    if "nextid" in self._state:
      ret = self._state["nextid"]
      self._state["nextid"] += 1
      return f"id{ret}"
    self._state["nextid"] = 1
    return "id0"

  def process(self, command_or_text):
    if is_str(command_or_text):
      """
      This is a string. Pass it to the string processor
      of the handler for the last command
      """
      if self._last_handler is None:
        raise UserInputError("Cannot start with text")
      if is_long_str(command_or_text):
        text = command_or_text[3:-3]
      else:
        text = command_or_text[1:-1]
      for preprocessor in self._preprocessors:
        text = preprocessor.preprocess_text(text)
      self._last_handler.process_text(self, text)
      self._last_text = text
      self._last_is_text = True
      self._last_is_command = False
      self._last_command_or_text = text
      return
    command = command_or_text
    if self._last_handler is not None:
      self._last_handler.on_finished(self)
    for preprocessor in self._preprocessors:
      command = preprocessor.preprocess_command(command)
    for handler in reversed(self._handlers):
      if handler.match(command):
        handler(self, command)
        self._history.append(command)
        self._last_handler = handler
        self._last_is_text = False
        self._last_is_command = True
        self._last_command_or_text = command
        return
    raise UserInputError(f"Unsupported command: {command}")

  def _render(self, obj):
    for renderer in reversed(self._renderers):
      if renderer.match(obj):
        return renderer.render(obj)
    raise ConfigurationError(f"Unknown object: {obj}")

  def render(self):
    paths = []
    for obj in self._picture:
      rendered = self._render(obj)
      if rendered is None:
        raise ConfigurationError(
            f"Object not supported by any render: {json.dumps(obj)}")
      paths.append(rendered)
    ret = r"""\begin{tikzpicture}
  %s
\end{tikzpicture}""" % "\n  ".join(paths)
    if self._scale != 1:
      ret = f"\\scalebox{{{self._scale}}}{{{ret}}}"
    return ret

  def register_handler(self, handler):
    assert isinstance(handler, Handler)
    self._handlers.append(handler)

  def register_renderer(self, renderer):
    assert isinstance(renderer, Renderer)
    self._renderers.append(renderer)

  def register_preprocessor(self, preprocessor):
    assert isinstance(preprocessor, Preprocessor)
    self._preprocessors.append(preprocessor)

  def parse(self, code):
    code = code.strip()
    while len(code) > 0:
      if code.startswith("'''") or code.startswith('"""'):
        escaped, text = False, None
        for i in range(1, len(code)):
          if escaped:
            escaped = False
            continue
          if code[i] == '\\':
            escaped = True
            continue
          if i + 3 <= len(code) and code[i:i+3] == code[0] * 3:
            text = code[0:i+3]
            code = code[i+3:].strip()
            break
        if text:
          self.process(text)
          continue
        else:
          raise UserInputError(f"Unended quote: {code}")
      if code.startswith("'") or code.startswith('"'):
        escaped, text = False, None
        for i in range(1, len(code)):
          if escaped:
            escaped = False
            continue
          if code[i] == '\\':
            escaped = True
            continue
          if code[i] == code[0]:
            text = code[0:i+1]
            code = code[i+1:].strip()
            break
        if text:
          self.process(text)
          continue
        else:
          raise UserInputError(f"Unended quote: {code}")
      if code.startswith("python{{{"):
        end = code.find("python}}}")
        if end < 0:
          raise UserInputError(f"Unended python code: {code}")
        python_code = code[9:end]
        code = code[end+9:].strip()
        variables = {}
        variables["ctx"] = self
        variables["parse"] = self.parse
        python_code = unindent(python_code)
        exec(python_code, variables)
        continue
      match = re.search(r'[\n\s]+', code)
      if match:
        self.process(code[0:match.span()[0]])
        code = code[match.span()[1]:].strip()
        continue
      self.process(code)
      break
    if self._last_handler is not None:
      self._last_handler.on_finished(self)

  def _register_fundamental_handlers(self):
    self._there_is_handler = ThereIsHandler()
    self._there_are_handler = ThereAreHandler()
    self.register_handler(GlobalHandler())
    self.register_handler(ThisHandler())
    self.register_handler(WithAttributeHandler())
    self.register_handler(self._there_is_handler)
    self.register_handler(self._there_are_handler)
    self.register_handler(ThereIsTextHandler())
    self.register_handler(ThereAreTextsHandler())
    self.register_handler(ByHandler())
    self.register_handler(SpacedByHandler())
    self.register_handler(WhereIsInHandler())
    self.register_handler(WithTextHandler())
    self.register_handler(WithNamesHandler())
    self.register_handler(WithAnnotateHandler())
    self.register_handler(AtIntersectionHandler())
    self.register_handler(AtCoordinateHandler())
    self.register_handler(AnchorAtAnchorHandler())
    self.register_handler(DirectionOfHandler())
    self.register_handler(ForAllHandler())
    self.register_handler(DrawHandler())
    self.register_handler(FillHandler())
    self.register_handler(MoveToNodeHandler())
    self.register_handler(LineToNodeHandler())
    self.register_handler(IntersectionHandler())
    self.register_handler(CoordinateHandler())
    self.register_handler(LineToHandler())
    self.register_handler(MoveVerticalToHandler())
    self.register_handler(MoveHorizontalToHandler())
    self.register_handler(LineVerticalToHandler())
    self.register_handler(LineHorizontalToHandler())
    self.register_handler(GridWithFixedDistancesHandler())
    self.register_handler(RectangleHandler())
    self.register_handler(RectangleToNodeHandler())
    self.register_handler(RepeatedHandler())
    self.register_handler(CopyLastObjectHandler())
    self.register_handler(RespectivelyWithHandler())
    self.register_handler(RespectivelyAtHandler())
    self.register_handler(RangeHandler())
    self.register_handler(NamedHandler())
    self.register_handler(SizedHandler())
    self.register_handler(ShiftedHandler())
    self.register_handler(ShiftedTwoHandler())
    self.register_handler(StartOutHandler())
    self.register_handler(CloseInHandler())
    self.register_handler(MoveDirectionHandler())
    self.register_handler(RectangleHorizontalToByHandler())
    self.register_handler(RectangleVerticalToByHandler())
    self.register_handler(LineDirectionHandler())
    self.register_handler(CopyThemHandler())
    self.register_handler(CopyStyleFromHandler())
    self.register_handler(DrawBraceHandler())
    self.register_handler(RectangleToNodeShiftedHandler())
    self.register_handler(NoSlopeHandler())
    self.register_handler(VerticalHorizontalToHandler())
    self.register_handler(HorizontalVerticalToHandler())
    self.register_handler(DefineCommandHandler())
    self.register_handler(DynamicGridHandler())
    self.register_handler(AddRowHandler())
    self.register_handler(AddColHandler())
    self.register_handler(ReplaceHandler())
    self.register_handler(CommentHandler())
    self.register_handler(DefineMacroHandler())
    self.register_handler(RunMacroHandler())
    self.register_handler(ThereIsTextBetweenHandler())
    self.register_handler(MoveToMiddleOfHandler())
    self.register_handler(ArrangedInHandler())
    self.register_handler(ChainedByArrowsHandler())
    self.register_handler(TheAnnotatesHandler())
    self.register_handler(TheChainHandler())
    self.register_handler(TheFirstHandler())
    self.register_handler(TheSecondHandler())
    self.register_handler(DynamicLayeredGraphHandler())
    self.register_handler(AddLayerHandler())
    self.register_handler(TheLayerHandler())
    self.register_handler(TheLayerBaseHandler())
    self.register_handler(TheLayeredGraphHandler())
    self.register_handler(ConnectLayeredGraphNodesHandler())

  def _register_fundamental_renderers(self):
    self.register_renderer(BoxRenderer())
    self.register_renderer(TextRenderer())
    self.register_renderer(PathRenderer(self))
    self.register_renderer(NodeNameRenderer())
    self.register_renderer(LineRenderer(self))
    self.register_renderer(ArcRenderer(self))
    self.register_renderer(IntersectionRenderer())
    self.register_renderer(CoordinateRenderer())
    self.register_renderer(CycleRenderer())
    self.register_renderer(PointRenderer())
    self.register_renderer(RectangleRenderer())
    self.register_renderer(BraceRenderer(self))
    self.register_renderer(VerticalHorizontalRenderer(self))
    self.register_renderer(HorizontalVerticalRenderer(self))

  def _register_fundamental_preprocessors(self):
    self._custom_command_preprocessor = CustomCommandPreprocessor()
    self.register_preprocessor(self._custom_command_preprocessor)
    self._replace_preprocessor = ReplacePreprocessor()
    self.register_preprocessor(self._replace_preprocessor)
    self.register_preprocessor(CommentPreprocessor())
    self._macro_preprocessor = MacroPreprocessor()
    self.register_preprocessor(self._macro_preprocessor)

  def register_object_handler(self, handler):
    self._there_is_handler.register_object_handler(handler)
    if isinstance(handler, SupportMultipleHandler):
      self._there_are_handler.register_object_handler(handler)

  def register_object_renderer(self, renderer):
    self._there_is_handler.register_object_renderer(renderer)
    if isinstance(renderer, SupportMultipleRenderer):
      self._there_are_handler.register_object_renderer(renderer)

  def define(self, command, text):
    self._custom_command_preprocessor.define(command, text)

  def replace_command(self, pattern, repl, regexp=True):
    self._replace_preprocessor.add_replace_command(pattern, repl, regexp)

  def replace_text(self, pattern, repl, regexp=True):
    self._replace_preprocessor.add_replace_text(pattern, repl, regexp)

  def replace_command_and_text(self, pattern, repl, regexp=True):
    self._replace_preprocessor.add_replace_command_and_text(
        pattern, repl, regexp)

  def find_object_by_id(self, id_):
    for obj in self._picture:
      if obj.get("id") == id_:
        return obj
      if "items" in obj:
        items = obj["items"]
        for item in items:
          if item.get("id") == id_:
            return item
          if "annotates" in item:
            for annotate in item["annotates"]:
              if "id" in annotate and annotate["id"] == id_:
                return annotate
    return None

  def delete_objects_related_to_id(self, id_, deleted_ids=[]):
    to_removes = [obj for obj in self._picture if related_to(obj, id_)]
    deleted_ids.append(id_)
    related_ids = [item["id"] for item in to_removes
                   if "id" in item and item["id"] not in deleted_ids]
    self._picture = [obj for obj in self._picture if not related_to(obj, id_)]

    for obj in self._picture:
      if "items" in obj:
        for item in obj["items"]:
          if "annotates" in item:
            item["annotates"] = [annotate for annotate in item["annotates"]
                                 if "id" not in annotate
                                 or annotate["id"] != id_]
    for id_ in related_ids:
      self.delete_objects_related_to_id(id_, deleted_ids)

  def delete_path(self, path):
    affected_ids = []
    for item in path["items"]:
      if "annotates" in item:
        for annotate in item["annotates"]:
          if "id" in annotate and "id" not in affected_ids:
            affected_ids.append(annotate["id"])
    for i in range(len(self._picture)):
      if self._picture[i] == path:
        del self._picture[i]
        break

    deleted_ids = []
    for id_ in affected_ids:
      self.delete_objects_related_to_id(id_, deleted_ids)

  def paste_data(self, data, atx, aty, check_all_relative_pos=False,
                 bounding_boxes=None):
    if len(data) == 0:
      return
    pos = get_first_absolute_coordinate(data)
    if pos is None:
      if check_all_relative_pos:
        raise PictureError("All copied objects have relative positions")
      if bounding_boxes is None:
        raise ValueError("Must provide the bounding boxes "
                         "if not check relative positions")
      pos = get_top_left_corner(data, bounding_boxes)
    x0, y0 = pos
    dx, dy = atx - x0, aty - y0
    old_to_new_id_dict = {}
    to_replace = []
    for obj in data:
      id_ = obj.get("id")
      if id_ is not None:
        new_id = self.getid()
        old_to_new_id_dict[id_] = new_id
        at = obj.get("at")
        obj["id"] = new_id
        obj["name"] = new_id
        if at is None:
          obj["at"] = create_coordinate(dx, dy)
        elif is_type(at, "coordinate"):
          assert not at.get("relative", False)
          add_to_key(at, "x", dx)
          add_to_key(at, "y", dy)
        elif isinstance(at, str):
          to_replace.append((obj, "at"))
        elif is_type(at, "intersection"):
          assert "name1" in at and "name2" in at
          to_replace.append((at, "name1"))
          to_replace.append((at, "name2"))
      elif is_type(obj, "path"):
        for item in obj["items"]:
          id_ = item.get("id")
          if id_ is not None:
            new_id = self.getid()
            old_to_new_id_dict[id_] = new_id
            item["id"] = new_id
          if is_type(item, "nodename"):
            to_replace.append((item, "name"))
          elif is_type(item, "intersection"):
            to_replace.append((item, "name1"))
            to_replace.append((item, "name2"))
          elif is_type(item, "coordinate"):
            if not item.get("relative", False):
              add_to_key(item, "x", dx)
              add_to_key(item, "y", dy)
          elif "annotates" in item:
            annotates = item["annotates"]
            for annotate in annotates:
              id_ = annotate.get("id")
              if id_ is not None:
                new_id = self.getid()
                old_to_new_id_dict[id_] = new_id
                annotate["id"] = new_id
      else:
        raise PictureError(f"Find an object that is neither object with id, "
                           f"nor path: {obj}")
      self._picture.append(obj)

    for item, key in to_replace:
      if key not in item:
        """
        This is possible because this object might have been modified
        """
        continue
      old_id = item[key]
      if old_id in old_to_new_id_dict:
        item[key] = old_to_new_id_dict[old_id]
      elif check_all_relative_pos:
        raise PictureError(f"Object {item} refers to "
                           f"an id {old_id} that is not copied")
      elif is_type(item, "nodename"):
        """
        We get a nodename item in a path that refers to an id
        that is not copied. In this case, we replace it with an
        absolute position.
        """
        if bounding_boxes is None:
          raise ValueError("Must provide the bounding boxes "
                           "if not check relative positions")
        bb = bounding_boxes[old_id]
        anchor = item.get("anchor", "center")
        x, y = bb.get_anchor_pos(anchor)
        """
        We can only modify 'item' in place, because we cannot
        overwrite item itself without knowing where it is pointed from
        """
        clear_dict(item)
        item["type"] = "coordinate"
        item["x"] = num_to_dist(x + dx)
        item["y"] = num_to_dist(y + dy)
      elif is_type(item, "intersection"):
        if bounding_boxes is None:
          raise ValueError("Must provide the bounding boxes "
                           "if not check relative positions")
        bb = bounding_boxes[old_id]
        """
        key is "name1" or "name2", and the key for anchor is respectively
        "anchor1" "anchor2"
        """
        anchor = item.get(f"anchor{key[4]}", "center")
        x, y = bb.get_anchor_pos(anchor)
        """
        We can only modify 'item' in place, because we cannot overwrite item
        itself without knowing where it is pointed from
        """
        clear_dict(item)
        item["type"] = "coordinate"
        item["x"] = num_to_dist(x + dx)
        item["y"] = num_to_dist(y + dy)
      elif get_default_of_type(item, "at", str) is not None:
        """
        Same as before: replace the relative position with absolute coordinate.
        """
        if bounding_boxes is None:
          raise ValueError("Must provide the bounding boxes "
                           "if not check relative positions")
        bb = bounding_boxes[old_id]
        anchor = item.get("at.anchor", "center")
        x, y = bb.get_anchor_pos(anchor)
        item["at"] = create_coordinate(x + dx, y + dy)
        item.pop("at.anchor", None)
      else:
        raise ConfigurationError("This branch should not be reached at all, "
                                 "unless something is wrong")

  def shift_object_anchor(self, id_, direction):
    obj = self.find_object_by_id(id_)
    if obj is None:
      return

    obj["anchor"] = shift_anchor(obj.get("anchor", "center"),
                                 flipped(direction))

  def shift_object_at_anchor(self, id_, direction):
    obj = self.find_object_by_id(id_)
    if obj is None:
      return False

    if get_default_of_type(obj, "at", str):
      obj["at.anchor"] = shift_anchor(
          obj.get("at.anchor", "center"),
          direction)
    elif "at" in obj and is_type(obj["at"], "intersection"):
      if direction == "left" or direction == "right":
        obj["at"]["anchor1"] = shift_anchor(
            obj["at"].get("anchor1", "center"),
            direction)
      elif direction == "up" or direction == "down":
        obj["at"]["anchor2"] = shift_anchor(
            obj["at"].get("anchor2", "center"),
            direction)
      else:
        raise ValueError(f"Unknown direction {direction}")
    else:
      return False
    return True
