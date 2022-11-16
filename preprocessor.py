import re


class Preprocessor(object):
  def preprocess_command(self, command):
    return command

  def preprocess_text(self, text):
    return text


class Command(object):
  def __init__(self, name):
    self._name = name
    self._args = []

  def append(self, arg):
    self._args.append(arg)


class Raw(object):
  def __init__(self):
    self._content = ""

  def append(self, text):
    self._content += text


class CustomCommandPreprocessor(Preprocessor):
  tokens = {
      "Space": r"\s+",
      "Escape": r"\\[^A-Za-z]",
      "Command": r"\\[A-Za-z0-9]+",
      "OpenBrace": r"\{",
      "CloseBrace": r"\}",
  }
  _definitions = {}

  def preprocess_text(self, text):
    return CustomCommandPreprocessor.process(text)

  def define(self, command, text):
    CustomCommandPreprocessor._definitions[command] = text

  def tokenize(line):
    if len(line) == 0:
      return "End", "", ""
    for label, token in CustomCommandPreprocessor.tokens.items():
      match = re.match(token, line)
      if match:
        return label, match.group(0), line[match.span()[1]:]
    return "Char", line[0], line[1:]

  def process(line):
    stack, mode = [Raw()], "normal"
    label, token, line = CustomCommandPreprocessor.tokenize(line)
    while True:
      if mode == "normal":
        """
        In this mode, the top of the stack must be Raw,
        otherwise something is wrong
        """
        if label in ["Space", "Escape", "Char"]:
          stack[-1].append(token)
        elif label == "Command":
          stack.append(Command(token[1:]))
          mode = "expect open"
        elif label == "OpenBrace":
          stack.append(Raw())
        elif label == "CloseBrace":
          last = stack[-1]._content
          stack.pop()
          if len(stack) == 0:
            raise Exception("Extra }")
          if isinstance(stack[-1], Command):
            stack[-1].append(last)
          else:
            stack[-1].append("{%s}" % last)
          mode = "just closed"
        elif label == "End":
          if len(stack) > 1:
            raise Exception("Unexpected End, expecting '}'")
          return stack[0]._content
        else:
          raise Exception(f"Unknown label {label}")
      elif mode == "expect open":
        if label == "OpenBrace":
          stack.append(Raw())
          mode = "normal"
        elif label == "Space":
          pass
        else:
          command = stack[-1]._name
          stack.pop()
          assert len(stack) > 0
          if command in CustomCommandPreprocessor._definitions:
            stack[-1].append(str(CustomCommandPreprocessor._definitions[command]))
          else:
            stack[-1].append("\\" + command)
          mode = "normal"
          continue
      elif mode == "just closed":
        if label == "OpenBrace":
          stack.append(Raw())
          mode = "normal"
        else:
          if isinstance(stack[-1], Command):
            command = stack[-1]._name
            if command in CustomCommandPreprocessor._definitions:
              val = CustomCommandPreprocessor._definitions[command](
                  *stack[-1]._args)
            else:
              val = "\\" + command + "" .join(["{%s}" % arg
                                               for arg in stack[-1]._args])
            stack.pop()
            assert isinstance(stack[-1], Raw)
            stack[-1].append(val)
          mode = "normal"
          continue
      else:
        raise Exception(f"Impossible mode {mode}")

      label, token, line = CustomCommandPreprocessor.tokenize(line)


class ReplacePreprocessor(Preprocessor):
  def __init__(self):
    self._command_replaces = []
    self._text_replaces = []

  def preprocess_command(self, command):
    for replace, repl in self._command_replaces:
      if isinstance(replace, str):
        command = command.replace(replace, repl)
      else:
        command = replace.sub(repl, command)
    return command

  def preprocess_text(self, text):
    for replace, repl in self._text_replaces:
      if isinstance(replace, str):
        text = text.replace(replace, repl)
      else:
        text = replace.sub(repl, text)
    return text

  def add_replace_command(self, pattern, repl, regexp=True):
    if regexp:
      pattern = re.compile(pattern)
    self._command_replaces.append((pattern, repl))

  def add_replace_text(self, pattern, repl, regexp=True):
    if regexp:
      pattern = re.compile(pattern)
    self._text_replaces.append((pattern, repl))

  def add_replace_command_and_text(self, pattern, repl, regexp=True):
    if regexp:
      pattern = re.compile(pattern)
    self._command_replaces.append((pattern, repl))
    self._text_replaces.append((pattern, repl))


class CommentPreprocessor(Preprocessor):
  NORMAL = 0
  ACTIVE = 1
  ACTIVE_ONCE = 2

  def __init__(self):
    self._mode = CommentPreprocessor.NORMAL
    self._comment_start_mark = "###"
    self._comment_end_mark = "###"
    self._one_time_comment_mark = "//"

  def preprocess_command(self, command):
    if self._mode == CommentPreprocessor.NORMAL:
      if command.startswith(self._comment_start_mark):
        self._mode = CommentPreprocessor.ACTIVE
        return "comment"
      if command == self._one_time_comment_mark:
        self._mode = CommentPreprocessor.ACTIVE_ONCE
        return "comment"
      if command.startswith(self._one_time_comment_mark):
        return "comment"
      return command
    if self._mode == CommentPreprocessor.ACTIVE:
      if command.endswith(self._comment_end_mark):
        self._mode = CommentPreprocessor.NORMAL
      return "comment"
    if self._mode == CommentPreprocessor.ACTIVE_ONCE:
      self._mode = CommentPreprocessor.NORMAL
      return "comment"
    raise Exception(f"Invalid comment mode {self._mode}")


class MacroPreprocessor(Preprocessor):
  def __init__(self):
    self._commands = []
    self._current_macro_defined = None
    self._defined_macros = {}

  def preprocess_command(self, command):
    if self._current_macro_defined is None:
      m = re.match("define.macro.([\w\.]+)$", command)
      if m:
        self._current_macro_defined = m.group(1)
        return "macro.define"
      else:
        if command == "end.macro":
          raise Exception("Cannot end macro outside macro definition")
        return command

    if command.startswith("define.macro"):
      raise Exception("Cannot define macro inside macro definition")

    if command == "end.macro":
      self._defined_macros[self._current_macro_defined] = self._commands
      self._commands = []
      self._current_macro_defined = None
      return "macro.define.end"

    self._commands.append(("CMD", command))
    return "macro.define"

  def preprocess_text(self, text):
    if self._current_macro_defined is not None:
      self._commands.append(("TXT", text))
    return text
