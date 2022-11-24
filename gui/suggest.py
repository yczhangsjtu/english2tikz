import string
import copy
from english2tikz.utils import *
from english2tikz.gui.object_utils import *


class Suggestion(object):
  def __init__(self):
    self._content = []

  def copy(self):
    ret = Suggestion()
    ret._content = copy.deepcopy(self._content)
    return ret

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

  def change_to_chosen_style(self):
    self._content = [item for item in self._content if "candcode" not in item]
    for item in self._content:
      item["color"] = "green!50!black"
      if is_type(item, "text"):
        item["text.color"] = "green!50!black"

  def change_to_candidate_style(self):
    for item in self._content:
      if "candcode" in item:
        continue
      item["color"] = "red!50"
      if is_type(item, "text"):
        item["text.color"] = "red!50"

  def change_to_fix_style(self, context):
    self._content = [item for item in self._content if "candcode" not in item]
    for item in self._content:
      item["color"] = "black"
      if is_type(item, "text"):
        item["text.color"] = "black"
        item["id"] = context.getid()
      del_if_has(item, "line.width")


class Suggest(object):
  def __init__(self, editor):
    self._editor = editor
    self._current_suggestion = None
    self._new_suggestions = None
    self._suggestors = []
    self._suggestion_history = []
    self._suggestion_history_index = 0
    self._register_suggestors()
    self._hint = {}

  def _register_suggestor(self, suggestor):
    self._suggestors.append(suggestor)

  def _register_suggestors(self):
    self._register_suggestor(CreateTextAtPointer())
    self._register_suggestor(CreatePathAtPointer())
    self._register_suggestor(ExtendPathToPointer())
    self._register_suggestor(ExtendPathToPointerByArc())

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
    self._hint = {}

  def shutdown(self):
    self._current_suggestion = None
    self._new_suggestions = None
    self._suggestion_history = []
    self._suggestion_history_index = 0
    self._hint = {}

  def _propose_suggestions(self):
    self._new_suggestions = []
    for suggestor in self._suggestors:
      self._new_suggestions += suggestor.suggest(
          self._editor, self._current_suggestion,
          len(self._new_suggestions),
          self._hint)
    if len(self._new_suggestions) > 26:
      self._editor._error_msg = ("Too many suggestions "
                                 f"{len(self._new_suggestions)}, only"
                                 f"take the first 26")
      self._new_suggestions = self._new_suggestions[:26]

  def take_suggestion(self, code):
    if code in string.ascii_uppercase:
      index = ord(code) - ord('A')
    else:
      raise ErrorMessage(f'Invalid code {code}')
    if index >= len(self._new_suggestions):
      raise ErrorMessage(f'Code {code} does not exist')
    suggestion = self._new_suggestions[index]
    self._suggestion_history = self._suggestion_history[
        :self._suggestion_history_index+1]
    self._suggestion_history.append(suggestion)
    self._current_suggestion = suggestion
    self._current_suggestion.change_to_chosen_style()
    self._suggestion_history_index = len(self._suggestion_history) - 1
    self._propose_suggestions()

  def revert(self):
    if self._suggestion_history_index == 0:
      raise ErrorMessage('Already the oldest')
    self._suggestion_history_index -= 1
    self._current_suggestion = self._suggestion_history[
        self._suggestion_history_index]
    self._current_suggestion.change_to_chosen_style()
    self._propose_suggestions()

  def redo(self):
    if self._suggestion_history_index >= len(self._suggestion_history)-1:
      raise ErrorMessage('Already the newest')
    self._suggestion_history_index += 1
    self._current_suggestion = self._suggestion_history[
        self._suggestion_history_index]
    self._current_suggestion.change_to_chosen_style()
    self._propose_suggestions()

  def fix(self):
    self._current_suggestion.change_to_fix_style(self._editor._context)
    ret = self._current_suggestion._content
    self.shutdown()
    return ret


class CreateTextAtPointer(object):
  def suggest(self, editor, current, index, hint):
    if not current.empty():
      return []
    x, y = editor._pointer.pos()
    suggestion = Suggestion()
    text = create_text("A", x=x, y=y)
    text["id"] = "create_text_at_pointer_id"
    text["draw"] = True
    text["line.width"] = 2
    suggestion.append(text)
    candcode = create_text(chr(index+ord('A')), x=x-0.3, y=y+0.3)
    candcode["id"] = "create_text_at_pointer_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "yellow"
    candcode["scale"] = 0.3
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    return [suggestion]


class CreatePathAtPointer(object):
  def suggest(self, editor, current, index, hint):
    if not current.empty():
      return []
    x, y = editor._pointer.pos()
    suggestion = Suggestion()
    path = create_path([create_coordinate(x, y)])
    path["line.width"] = 2
    suggestion.append(path)
    candcode = create_text(chr(index+ord('A'))+'(path)', x=x, y=y)
    candcode["id"] = "create_path_at_pointer_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "orange"
    candcode["scale"] = 0.3
    candcode["anchor"] = "south.east"
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    return [suggestion]


class ExtendPathToPointer(object):
  def suggest(self, editor, current, index, hint):
    if not current.single_path():
      return []
    x, y = editor._pointer.pos()
    suggestion = current.copy()
    path = suggestion.get_single_path()
    path['items'].append(create_line())
    path['items'].append(create_coordinate(x, y))
    candcode = create_text(chr(index+ord('A')), x=x, y=y)
    candcode["id"] = "extend_path_to_pointer_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "orange"
    candcode["scale"] = 0.3
    candcode["anchor"] = "south.east"
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    return [suggestion]


class ExtendPathToPointerByArc(object):
  def suggest(self, editor, current, index, hint):
    if not current.single_path():
      return []
    x, y = editor._pointer.pos()
    suggestion = current.copy()
    path = suggestion.get_single_path()
    start, end, radius = compute_arc_to_extend_path(path, x, y, hint)
    path['items'].append(create_arc(start, end, radius))
    candcode = create_text(chr(index+ord('A')), x=x, y=y)
    candcode["id"] = "extend_path_to_pointer_by_arc_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "orange"
    candcode["scale"] = 0.3
    candcode["anchor"] = "south.east"
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    return [suggestion]
