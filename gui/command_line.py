import os
from english2tikz.gui.text_editor import TextEditor


class CommandLine(object):
  def __init__(self, path):
    self._editor = None
    self._command_line_buffer = None
    self._command_history_index = None
    self._path = os.path.join(path, "history")
    self._command_history = self._read_command_history()

  def active(self):
    return self._editor is not None

  def _read_command_history(self):
    try:
      with open(self._path) as f:
        history = f.read()
    except IOError:
      return []
    return history.split("\n")

  def insert(self, c):
    self._editor.insert(c)
    self._command_line_buffer = str(self._editor)
    self._command_history_index = None

  def delete(self):
    self._command_history_index = None
    if len(self._editor) > 0:
      self._editor.delete()
      self._command_line_buffer = str(self._editor)
    else:
      self.exit()

  def exit(self):
    self._editor = None
    self._command_line_buffer = None
    self._command_history_index = None

  def __str__(self):
    return str(self._editor)

  def move_cursor(self, offset):
    self._editor.move_cursor(offset)

  def move_to_start(self):
    self._editor.move_to_start()

  def move_to_end(self):
    self._editor.move_to_end()

  def activate(self, init=""):
    self._editor = TextEditor(init)
    self._command_line_buffer = init

  def fetch_previous(self):
    if self._command_history_index is None:
      if len(self._command_history) > 0:
        self._command_history_index = len(self._command_history) - 1
    else:
      self._command_history_index = max(0, self._command_history_index - 1)
    self._editor.set(self._command_history[self._command_history_index])
    self._editor.move_to_end()

  def fetch_next(self):
    if self._command_history_index is not None:
      self._command_history_index += 1
      if self._command_history_index >= len(self._command_history):
        self._command_history_index = None
        self._editor.set(self._command_line_buffer)
      else:
        self._editor.set(self._command_history[self._command_history_index])
      self._editor.move_to_end()

  def set(self, content):
    self._editor.set(content)
    self._editor.move_to_end()
    self._command_line_buffer = content
    self._command_history_index = None

  def view(self):
    return self._editor.view()

  def append(self, cmd):
    self._command_history.append(cmd)
    if len(self._command_history) > 100:
      self._command_history = self._command_history[-100:]
    self.save_history()

  def save_history(self):
    with open(self._path, "w") as f:
      f.write("\n".join(self._command_history))
