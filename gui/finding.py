import string
from english2tikz.utils import *


class Finding(object):
  def __init__(self, candidates, toggle=False):
    self._prefix = ""
    self._toggle = toggle
    self._candidates = {}

    if len(candidates) == 0:
      raise Exception("No object on screen")
    elif len(candidates) <= 26:
      for i in range(0, len(candidates)):
        c = chr(ord('A') + i)
        self._candidates[c] = candidates[i]
    elif len(candidates) <= 26 * 26:
      for i in range(0, len(candidates)):
        c = chr(ord('A') + i // 26) + chr(ord('A') + i % 26)
        self._candidates[c] = candidates[i]
    elif len(candidates) <= 26 * 26 * 26:
      for i in range(0, len(candidates)):
        c = chr(ord('A') + i // (26 * 26)) + \
            chr(ord('A') + (i // 26) % 26) + \
            chr(ord('A') + i % 26)
        self._candidates[c] = candidates[i]
    else:
      raise Exception("Too many objects on screen")

  def is_toggle(self):
    return self._toggle

  def narrow_down(self, char):
    if char not in string.ascii_lowercase:
      return
    self._prefix += char.upper()
    current_candidates = self._current_candidates()
    if len(current_candidates) == 0:
      raise Exception(f"Cannot find object with code {self._prefix}")
    elif len(current_candidates) == 1:
      return current_candidates[0]
    else:
      return None

  def _current_candidates(self):
    return [value for key, value in self._candidates.items()
            if key.startswith(self._prefix)]

  def back(self):
    if len(self._prefix) > 0:
      self._prefix = self._prefix[:-1]
      return True
    else:
      return False

  def get_candidate_code(self, obj):
    for key, value in self._candidates.items():
      if not key.startswith(self._prefix):
        continue
      if isinstance(value, str):
        if get_default(obj, "id") == value:
          return key
      elif obj == value:
        return key
    return None

  def get_chopped_code(self, obj):
    code = self.get_candidate_code(obj)
    if code is not None:
      assert code.startswith(self._prefix)
      return code[len(self._prefix):]
    return None
