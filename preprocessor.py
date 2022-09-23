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
              val = CustomCommandPreprocessor._definitions[command](*stack[-1]._args)
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
