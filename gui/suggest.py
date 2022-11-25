import string
import copy
from english2tikz.utils import *
from english2tikz.gui.object_utils import *
from english2tikz.gui.bezier import *


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
      item.pop("hidden", None)
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
      item.pop("line.width", None)


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
    self._register_suggestor(ExtendPathToSelectedNode())
    self._register_suggestor(MakeLastLineSmooth())

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
    if code in string.ascii_lowercase:
      index = ord(code) - ord('a')
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
    self._hint = {}
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
    if "last_path" not in hint or "positions" not in hint["last_path"]:
      return []
    hint_positions = hint["last_path"]["positions"]
    candpos = (x, y)
    if len(hint_positions) > 0:
      x0, y0 = hint["last_path"]["positions"][-1]
      dist = euclidean_dist((x, y), (x0, y0))
      if dist < 0.01:
        return []
      candpos = ((x+x0)/2, (y+y0)/2)
    suggestion = current.copy()
    path = suggestion.get_single_path()
    path['items'].append(create_line())
    path['items'].append(create_coordinate(x, y))
    candcode = create_text(chr(index+ord('A')), x=candpos[0], y=candpos[1])
    candcode["id"] = "extend_path_to_pointer_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "orange"
    candcode["scale"] = 0.3
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    ret = [suggestion]

    if len(hint_positions) > 0:
      suggestion = current.copy()
      path = suggestion.get_single_path()
      path['items'].append(create_line())
      path['items'].append(create_coordinate(x-x0, y-y0, relative=True))
      path['hidden'] = True
      candcode = create_text(chr(index+1+ord('A'))+'(rel)',
                             x=candpos[0]+0.3, y=candpos[1])
      candcode["id"] = "extend_path_to_pointer_relative_candcode_id"
      candcode["candcode"] = True
      candcode["draw"] = True
      candcode["fill"] = "orange"
      candcode["scale"] = 0.3
      suggestion.append(candcode)
      suggestion.change_to_candidate_style()
      ret.append(suggestion)
    return ret


class ExtendPathToPointerByArc(object):
  def suggest(self, editor, current, index, hint):
    if not current.single_path():
      return []
    x, y = editor._pointer.pos()
    suggestion = current.copy()
    path = suggestion.get_single_path()
    start, end, radius = compute_arc_to_extend_path(path, x, y, hint)
    if start is None:
      return []
    path['items'].append(create_arc(start, end, radius))
    dx, dy = math.cos(end*math.pi/180), math.sin(end*math.pi/180)
    centerx, centery = x - dx * radius, y - dy * radius
    if start > end:
      deg = end/180*math.pi+0.3/radius
    else:
      deg = end/180*math.pi-0.3/radius
    candpos = (centerx+math.cos(deg)*radius, centery+math.sin(deg)*radius)
    candcode = create_text(chr(index+ord('A'))+'(arc)',
                           x=candpos[0], y=candpos[1])
    candcode["id"] = "extend_path_to_pointer_by_arc_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "orange!20"
    candcode["scale"] = 0.3
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    return [suggestion]


class ExtendPathToSelectedNode(object):
  def suggest(self, editor, current, index, hint):
    if not current.single_path():
      return []
    if not editor._selection.has_id():
      return []
    id_ = editor._selection.get_id(0)
    suggestion = current.copy()
    path = suggestion.get_single_path()
    path['items'].append(create_line())
    path['items'].append(create_nodename(id_))
    candcode = create_text(chr(index+ord('A')))
    candcode["id"] = "extend_path_to_node_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "red!20"
    candcode["scale"] = 0.3
    candcode["at"] = id_
    candcode["anchor"] = "north"
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    ret = [suggestion]
    return ret


class MakeLastLineSmooth(object):
  def suggest(self, editor, current, index, hint):
    if not current.single_path():
      return []
    x, y = editor._pointer.pos()
    suggestion = current.copy()
    items = suggestion.get_path_items()
    if len(items) < 3:
      return []
    if (not is_type(items[-2], "line") or
        not is_type(items[-1], "coordinate")):
      return []
    if "in" in items[-2] or "out" in items[-2]:
      return []
    if ("last_path" not in hint or
        "positions" not in hint["last_path"] or
        "directions" not in hint["last_path"]):
      return []
    hint_positions = hint["last_path"]["positions"]
    hint_directions = hint["last_path"]["directions"]
    assert len(hint_positions) == len(hint_directions), (
        "Mismatched hint lengths")
    if len(hint_positions) < 2:
      return []
    x0, y0 = hint_positions[-2]
    x1, y1 = hint_positions[-1]
    x2, y2 = editor._pointer.pos()
    deg2 = get_angle(x1, y1, x2, y2)
    if deg2 is None:
      return []
    deg1, deg2 = hint_directions[-1], deg2 % 360
    path = suggestion.get_single_path()
    items.pop()
    items.pop()
    line = create_line()
    line["out"] = deg1
    line["in"] = (deg2 + 180) % 360
    items.append(line)
    items.append(create_coordinate(x, y))
    dist = euclidean_dist((x0, y0), (x2, y2))
    ix0 = x0 + math.cos(deg1/180*math.pi) * dist/3
    iy0 = y0 + math.sin(deg1/180*math.pi) * dist/3
    ix2 = x2 - math.cos(deg2/180*math.pi) * dist/3
    iy2 = y2 - math.sin(deg2/180*math.pi) * dist/3
    candpos = Bezier.Point(0.5, (x0, y0), (ix0, iy0), (ix2, iy2), (x2, y2))
    candcode = create_text(chr(index+ord('A')),
                           x=candpos[0], y=candpos[1])
    candcode["id"] = "make_last_line_smooth_candcode_id"
    candcode["candcode"] = True
    candcode["draw"] = True
    candcode["fill"] = "yellow"
    candcode["scale"] = 0.3
    suggestion.append(candcode)
    suggestion.change_to_candidate_style()
    return [suggestion]
