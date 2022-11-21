class TextEditor(object):
  def __init__(self, s=""):
    self._content = s
    self._position = len(s)

  def insert(self, c):
    self._fix_position()
    self._content = (self._content[:self._position] +
                     c + self._content[self._position:])
    self._position += len(c)

  def delete(self):
    self._fix_position()
    if self._position > 0:
      self._content = (self._content[:self._position-1] +
                       self._content[self._position:])
    self._position -= 1

  def move_carret(self, offset):
    self._position += offset
    self._fix_position()

  def clear(self):
    self._content = ""
    self._position = 0

  def set(self, s):
    self._content = s
    self._fix_position()

  def __str__(self):
    return self._content

  def view(self):
    self._fix_position()
    return (self._content[:self._position] +
            '\u2588' + self._content[self._position:])

  def __len__(self):
    return len(self._content)

  def _fix_position(self):
    if self._position > len(self._content):
      self._position = len(self._content)
    if self._position < 0:
      self._position = 0
