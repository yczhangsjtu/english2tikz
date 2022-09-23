import json
import re
from .handlers import *
from .renderers import *
from .preprocessor import *


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
  
  def process(self, command_or_text):
    if (command_or_text.startswith('"') and
        command_or_text.endswith('"')) or \
       (command_or_text.startswith("'") and
        command_or_text.endswith("'")):
      """
      This is a string. Pass it to the string processor
      of the handler for the last command
      """
      if self._last_handler is None:
        raise Exception("Cannot start with text")
      text = command_or_text[1:-1]
      for preprocessor in self._preprocessors:
        text = preprocessor.preprocess_text(text)
      self._last_handler.process_text(self, text)
      self._last_text = text
      self._last_is_text = True
      self._last_is_command = False
      self._last_command_or_text = command_or_text
      return
    command = command_or_text
    for handler in reversed(self._handlers):
      for preprocessor in self._preprocessors:
        command = preprocessor.preprocess_command(command)
      if handler.match(command):
        handler(self, command)
        self._history.append(command)
        self._last_handler = handler
        self._last_is_text = False
        self._last_is_command = True
        self._last_command_or_text = command_or_text
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
        raise Exception(f"Object not supported by any render: {json.dumps(obj)}")
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
      match = re.search(r'[\n\s]+', code)
      if match:
        self.process(code[0:match.span()[0]])
        code = code[match.span()[1]:].strip()
        continue
      self.process(code)
      break
      
  def _register_fundamental_handlers(self):
    self._there_is_handler = ThereIsHandler()
    self.register_handler(GlobalHandler())
    self.register_handler(WithAttributeHandler())
    self.register_handler(self._there_is_handler)
    self.register_handler(ThereIsTextHandler())
    self.register_handler(ByHandler())
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
    self.register_handler(RepeatedHandler())
    self.register_handler(CopyLastObjectHandler())
    self.register_handler(RespectivelyWithHandler())
    self.register_handler(RespectivelyAtHandler())
    self.register_handler(RangeHandler())
    self.register_handler(NamedHandler())
    self.register_handler(SizedHandler())
    self.register_handler(ShiftedHandler())
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
    self.register_handler(DefineCommandHandler())
    self.register_handler(DynamicGridHandler())
    self.register_handler(AddRowHandler())
    self.register_handler(AddColHandler())
    
  def _register_fundamental_renderers(self):
    self.register_renderer(BoxRenderer())
    self.register_renderer(TextRenderer())
    self.register_renderer(PathRenderer(self))
    self.register_renderer(NodeNameRenderer())
    self.register_renderer(LineRenderer())
    self.register_renderer(IntersectionRenderer())
    self.register_renderer(CoordinateRenderer())
    self.register_renderer(PointRenderer())
    self.register_renderer(RectangleRenderer())
    self.register_renderer(BraceRenderer(self))
    self.register_renderer(VerticalHorizontalRenderer())

  def _register_fundamental_preprocessors(self):
    self._custom_command_preprocessor = CustomCommandPreprocessor()
    self.register_preprocessor(self._custom_command_preprocessor)

  def register_object_handler(self, handler):
    self._there_is_handler.register_object_handler(handler)

  def register_object_renderer(self, renderer):
    self._there_is_handler.register_object_renderer(renderer)

  def define(self, command, text):
    self._custom_command_preprocessor.define(command, text)
