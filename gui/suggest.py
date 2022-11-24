import string
from english2tikz.utils import *


class Suggestion(object):
  def __init__(self):
    self._content = []

  def append(self, item):
    self._content.append(item)

  def append_to_last(self, item):
    assert self.last_is_path(), "Suggestion last is not path"
    self._content[-1]["items"].append(item)

  def empty(self):
    return len(self._content) == 0

  def single_path(self):
    return self.single() and self.last_is_path()

  def single(self):
    return len(self._content) == 1

  def last_is_path(self):
    return is_type(self._content[-1], "path")

  def get_single(self):
    assert self.single(), "Suggestion is not single"
    return self._content[-1]

  def get_single_path(self):
    assert self.single_path(), "Suggestion is not single path"
    return self._content[-1]

  def get_path_items(self):
    assert self.single_path(), "Suggestion is not single path"
    return self._content[-1]["items"]


class Suggest(object):
  def __init__(self, editor):
    self._editor = editor
    self._current_suggestion = None
    self._new_suggestions = None
    self._suggestors = []
    self._suggestion_history = []
    self._suggestion_history_index = 0
    self._register_suggestors()

  def _register_suggestor(self, suggestor):
    self._suggestors.append(suggestor)

  def _register_suggestors(self):
    self._register_suggestor(CreateTextAtPointer())

  def _context(self):
    return self._editor._context

  def _picture(self):
    return self._context()._picture

  def suggestion(self):
    return self._current_suggestion

  def active(self):
    return self.suggestion() is not None

  def activate(self):
    self._current_suggestion = Suggestion()
    self._suggestion_history = [self._current_suggestion]
    self._suggestion_history_index = 0
    self._propose_suggestions()

  def shutdown(self):
    self._current_suggestion = None
    self._new_suggestions = None
    self._suggestion_history = []
    self._suggestion_history_index = 0

  def _propose_suggestions(self):
    self._new_suggestions = []
    for suggestor in self._suggestors:
      self._new_suggestions += suggestor.suggest(
          self._editor, self._current_suggestion)
    if len(self._new_suggestions) > 10:
      self._editor._error_msg = ("Too many suggestions "
                                 f"{len(self._new_suggestions)}, only"
                                 f"take the first 10")
      self._new_suggestions = self._new_suggestions[:10]

  def take_suggestion(self, code):
    if code in string.lowercase:
      index = ord(code) - ord('a')
    elif code in string.uppercase:
      index = ord(code) - ord('A') + 26
    else:
      raise ErrorMessage(f'Invalid code {code}')
    if index >= len(self._new_suggestions):
      raise ErrorMessage(f'Code {code} does not exist')
    suggestion = self._new_suggestions(index)
    self._suggestion_history = self._suggestion_history[
        :self._suggestion_history_index+1]
    self._suggestion_history.append(suggestion)
    self._current_suggestion = suggestion
    self._suggestion_history_index = len(self._suggestion_history) - 1

  def revert(self):
    if self._suggestion_history_index == 0:
      raise ErrorMessage('Already the oldest')
    self._suggestion_history_index -= 1
    self._current_suggestion = self._suggestion_history[
        self._suggestion_history_index]
    self._propose_suggestions()

  def redo(self):
    if self._suggestion_history_index >= len(self._suggestion_history)-1:
      raise ErrorMessage('Already the newest')
    self._suggestion_history_index += 1
    self._current_suggestion = self._suggestion_history[
        self._suggestion_history_index]
    self._propose_suggestions()


class CreateTextAtPointer(object):
  def suggest(self, editor, current):
    if not current.empty():
      return []
    x, y = editor._pointer.pos()
    suggestion = Suggestion()
    text = create_text("A", x=x, y=y)
    text["id"] = "create_text_at_pointer_id"
    text["color"] = "blue"
    text["text.color"] = "blue!50"
    text["draw"] = True
    text["dashed"] = True
    suggestion.append(text)
    return [suggestion]
