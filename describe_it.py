import json
import re
from functools import partial
from english2tikz.handlers import *
from english2tikz.renderers import *
from english2tikz.object_handlers import SupportMultipleHandler
from english2tikz.object_renderers import SupportMultipleRenderer
from english2tikz.preprocessor import *
from english2tikz.utils import *


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
        raise Exception("Cannot start with text")
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
    raise Exception(f"Unsupported command: {command}")

  def _render(self, obj):
    for renderer in reversed(self._renderers):
      if renderer.match(obj):
        return renderer.render(obj)
    raise Exception(f"Unknown object: {obj}")

  def render(self):
    paths = []
    for obj in self._picture:
      rendered = self._render(obj)
      if rendered is None:
        raise Exception(
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
          raise Exception(f"Unended quote: {code}")
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
          raise Exception(f"Unended quote: {code}")
      if code.startswith("python{{{"):
        end = code.find("python}}}")
        if end < 0:
          raise Exception(f"Unended python code: {code}")
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
      if get_default(obj, "id") == id_:
        return obj
      if "items" in obj:
        items = obj["items"]
        for item in items:
          if get_default(item, "id") == id_:
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
