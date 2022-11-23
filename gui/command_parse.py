import re
from english2tikz.utils import *


def tokenize(code):
  code = code.strip()
  tokens = []
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
        tokens.append(("text", text[3:-3]))
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
        tokens.append(("text", text[1:-1]))
        continue
      else:
        raise Exception(f"Unended quote: {code}")
    if code.startswith("python{{{"):
      end = code.find("python}}}")
      if end < 0:
        raise Exception(f"Unended python code: {code}")
      python_code = code[9:end]
      code = code[end+9:].strip()
      tokens.append(("python", code))
      continue
    match = re.search(r'[\n\s]+', code)
    if match:
      tokens.append(("command", code[0:match.span()[0]]))
      code = code[match.span()[1]:].strip()
      continue
    tokens.append(("command", code))
    break
  return tokens


class Parser(object):
  def __init__(self):
    self._positionals = []
    self._flag_groups = {}
    self._flags = []
    self._require_args = {}

  def split_name_args(code):
    code = code.strip()
    first_space = code.find(' ')
    if first_space > 0:
      return code[:first_space], code[first_space+1:].strip()
    return code, ''

  def flag_group(self, name, values):
    self._flag_groups[name] = values

  def positional(self, name):
    self._positionals.append(name)

  def flag(self, name):
    self._flags.append(name)

  def require_arg(self, name, count):
    self._require_args[name] = count

  def parse(self, code):
    tokens = tokenize(code)
    ret = {}
    positional_index = 0
    expected_args_count = None
    expected_args_name = None
    for t, v in tokens:
      if t == "command":
        is_flag_group = False
        for name, values in self._flag_groups.items():
          if v in values:
            ensure_key(ret, name, [])
            ret[name].append(v)
            is_flag_group = True
            break
        if is_flag_group:
          continue

        if "=" in v:
          key, value = v[:v.find('=')], v[v.find('=')+1:]
          ret[key] = value
          continue

        if expected_args_count is not None and expected_args_count != "*":
          ensure_key(ret, expected_args_name, [])
          ret[expected_args_name].append(v)
          if expected_args_count == "+":
            expected_args_count = "*"
          elif expected_args_count > 0:
            expected_args_count -= 1
            if expected_args_count == 0:
              expected_args_count = None
              expected_args_name = None
          continue

        if v in self._flags:
          ret[v] = True
          continue

        if v in self._require_args:
          expected_args_count = self._require_args[v]
          expected_args_name = v
          ensure_key(ret, expected_args_name, [])
          continue

        if expected_args_count == "*":
          ret[expected_args_name].append(v)
          continue

        if positional_index < len(self._positionals):
          ret[self._positionals[positional_index]] = v
          positional_index += 1
          continue

        ret[v] = True

      elif t == "text":
        if expected_args_count is not None:
          ensure_key(ret, expected_args_name, [])
          ret[expected_args_name].append(v)
          if expected_args_count == "+":
            expected_args_count = "*"
          elif expected_args_count > 0:
            expected_args_count -= 1
            if expected_args_count == 0:
              expected_args_count = None
              expected_args_name = None
          continue

        if positional_index < len(self._positionals):
          ret[self._positionals[positional_index]] = v
          positional_index += 1
          continue

        ensure_key(ret, "positionals", [])
        ret["positionals"].append(v)
    return ret
