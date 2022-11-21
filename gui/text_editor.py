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

  def move_cursor(self, offset):
    self._position += offset
    self._fix_position()

  def move_to_start(self):
    self._position = 0

  def move_to_end(self):
    self._position = len(self._content)

  def char_under_cursor(self):
    self._fix_position()
    if self.at_start():
      return None
    return self._content[self._position-1]

  def char_next_cursor(self):
    self._fix_position()
    if self.at_end():
      return None
    return self._content[self._position]

  def move_to_eol(self):
    self._fix_position()
    while self.char_next_cursor() != '\n' and not self.at_end():
      self._position += 1

  def move_to_sol(self):
    self._fix_position()
    while self.char_under_cursor() != '\n' and not self.at_start():
      self._position -= 1

  def move_up(self):
    self._fix_position()
    x, y = self.get_coordinate()
    self.set_coordinate(x, y-1)

  def move_down(self):
    self._fix_position()
    x, y = self.get_coordinate()
    self.set_coordinate(x, y+1)

  def move_left(self):
    self._fix_position()
    x, y = self.get_coordinate()
    self.set_coordinate(x-1, y)

  def move_right(self):
    self._fix_position()
    x, y = self.get_coordinate()
    self.set_coordinate(x+1, y)

  def get_coordinate(self):
    self._fix_position()
    x, y = 0, 0
    for i in range(self._position):
      if self._content[i] == '\n':
        x, y = 0, y+1
      else:
        x, y = x+1, y
    return x, y

  def get_position_by_coordinate(self, x, y):
    lines = self.get_lines()
    if y >= len(lines) or y < 0:
      return None
    x = max(0, min(x, len(lines[y])))
    return sum([len(line)+1 for line in lines[:y]]) + x

  def set_coordinate(self, x, y):
    new_pos = self.get_position_by_coordinate(x, y)
    if new_pos is not None:
      self._position = new_pos
    self._fix_position()

  def get_lines(self):
    return self._content.split("\n")

  def at_end(self):
    self._fix_position()
    return self._position == len(self._content)

  def at_start(self):
    self._fix_position()
    return self._position == 0

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
