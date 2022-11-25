import string
from english2tikz.utils import *


class KeyboardManager(object):

  CTRL = 4
  ALT = 16
  SHIFT = 1

  def __init__(self, leader=None):
    self._bindings = {}
    self._legal_keys = ([c for c in string.printable] +
                        ["Up", "Down", "Left", "Right"] +
                        ["Return", "Tab", "BackSpace"])
    self._leader = leader
    self._in_leader_mode = False

  def bind(self, keyname, callback):
    self._bindings[keyname] = callback

  def handle_key(self, event):
    ctrl = event.state & KeyboardManager.CTRL != 0
    alt = event.state & KeyboardManager.ALT != 0
    shift = event.state & KeyboardManager.SHIFT != 0
    char = (event.char
            if event.char and event.char in string.printable
            else None)
    sym = (event.keysym
           if event.keysym and event.keysym in self._legal_keys
           else None)
    if not ctrl and char:
      if char == "\n" or char == "\r":
        self.handle_key_by_code("Return")
      else:
        self.handle_key_by_code(char)
    elif not ctrl and sym:
      self.handle_key_by_code(sym)
    elif ctrl and sym:
      self.handle_key_by_code(f"Ctrl-{sym}")

  def handle_key_by_code(self, code):
    if not self._in_leader_mode:
      if code == self._leader:
        self._in_leader_mode = True
        return
      if len(code) == 1 and code in string.printable:
        self._invoke(self._bindings.get("Printable"), code)
      self._invoke(self._bindings.get(code))
    else:
      self._in_leader_mode = False
      self._invoke(self._bindings.get("<leader>"+code))

  def _invoke(self, f, *args, **kwargs):
    if f is not None:
      f(*args, **kwargs)
