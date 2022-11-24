class Suggest(object):
  def __init__(self, editor):
    self._editor = editor
    self._suggestions = None

  def _context(self):
    return self._editor._context

  def _picture(self):
    return self._context()._picture

  def suggestion(self):
    return self._suggestions

  def active(self):
    return self._suggestions is not None

  def activate(self):
    pass

  def shutdown(self):
    self._suggestions = None
