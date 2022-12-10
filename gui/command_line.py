import os
from english2tikz.gui.text_editor import TextEditor


class CommandLine(object):
  def __init__(self, path):
    self._editor = None
    self._command_line_buffer = None
    self._command_history_index = None
    self._path = os.path.join(path, "history")
    self._command_history = self._read_command_history()
    self._matches = None
    self._match_index = None
    self._match_base = None

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
    self._matches = None
    self._match_index = None
    self._match_base = None

  def delete(self):
    self._command_history_index = None
    self._matches = None
    self._match_index = None
    self._match_base = None
    if len(self._editor) > 0:
      self._editor.delete()
      self._command_line_buffer = str(self._editor)
    else:
      self.exit()

  def exit(self):
    self._editor = None
    self._command_line_buffer = None
    self._command_history_index = None
    self._matches = None
    self._match_index = None
    self._match_base = None

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
  
  def find_previous_with_prefix(self, prefix, index):
    for i in reversed(range(index)):
      if self._command_history[i].startswith(prefix):
        return i
    return None
  
  def find_next_with_prefix(self, prefix, index):
    for i in range(index+1, len(self._command_history)):
      if self._command_history[i].startswith(prefix):
        return i
    return None

  def fetch_previous(self):
    if self._command_history_index is None:
      if len(self._command_history) > 0:
        current_index = len(self._command_history)
      else:
        return
    else:
      current_index = self._command_history_index
    current_index = self.find_previous_with_prefix(
      self._command_line_buffer, current_index)
    if current_index is not None:
      if self._command_history_index is None:
        self._command_line_buffer = str(self._editor)
      self._command_history_index = current_index
      self._editor.set(self._command_history[self._command_history_index])
      self._editor.move_to_end()

  def fetch_next(self):
    if self._command_history_index is None:
      return
    current_index = self.find_next_with_prefix(
      self._command_line_buffer,
      self._command_history_index)
    self._command_history_index = current_index
    if current_index is None:
      self._editor.set(self._command_line_buffer)
    else:
      self._editor.set(self._command_history[self._command_history_index])
      self._editor.move_to_end()
  
  def complete(self):
    if self._matches is None:
      current = str(self._editor).lstrip()
      current = current.split(' ')[-1]
      directory = os.path.join('.', os.path.dirname(current))
      prefix = os.path.basename(current)
      matches = [file for file in os.listdir(directory)
                if file.startswith(prefix)]
      for i in range(len(matches)):
        if os.path.isdir(os.path.join(directory, matches[i])):
          matches[i] += '/'
      if len(matches) > 0:
        self._matches = matches
        self._match_index = 0
        self._command_line_buffer = str(self._editor)
        if len(prefix) > 0:
          self._match_base = self._command_line_buffer[:-len(prefix)]
        else:
          self._match_base = self._command_line_buffer
        self._command_history_index = None
        self._editor.set(self._match_base + self._matches[0])
        self._editor.move_to_end()
    elif self._match_index is None:
      if len(self._matches) > 0:
        self._match_index = 0
        self._editor.set(self._match_base + self._matches[0])
        self._editor.move_to_end()
    else:
      self._match_index += 1
      if self._match_index >= len(self._matches):
        self._match_index = None
        self._editor.set(self._command_line_buffer)
        self._editor.move_to_end()
      else:
        self._editor.set(self._match_base + self._matches[self._match_index])
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
