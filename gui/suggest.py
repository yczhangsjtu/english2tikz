class Suggestion(object):
  def __init__(self):
    self._content = []


class Suggest(object):
  def __init__(self, editor):
    self._editor = editor
    self._current_suggestion = None
    self._new_suggestions = None
    self._suggestors = []
    self._suggestion_history = []
    self._suggestion_history_index = 0

  def _register_suggestor(self, suggestor):
    self._suggestors.append(suggestor)

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
    self._propose_suggestions()

  def shutdown(self):
    self._current_suggestion = None
    self._new_suggestions = None

  def _propose_suggestions(self):
    self._new_suggestions = []
    for suggestor in self._suggestors:
      self._new_suggestions += suggestor.suggest(
          self._editor, self._current_suggestion)
    if len(self._new_suggestions) > 52:
      self._editor._error_msg = ("Too many suggestions "
                                 f"{len(self._new_suggestions)}")
      self._new_suggestions = self._new_suggestions[:52]

  def _take_suggestion(self):
    pass
