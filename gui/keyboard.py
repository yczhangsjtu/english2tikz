import string
from english2tikz.utils import *


class KeyboardManager(object):

  CTRL = 4
  ALT = 16
  SHIFT = 1

  def __init__(self):
    self._bindings = {}
    self._legal_keys = ([c for c in string.printable] +
                        ["Up", "Down", "Left", "Right"] +
                        ["Return", "Tab", "BackSpace"])

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
        self._invoke(get_default(self._bindings, "Return"))
      else:
        self._invoke(get_default(self._bindings, "Printable"), char)
        self._invoke(get_default(self._bindings, char))
    elif not ctrl and sym:
      self._invoke(get_default(self._bindings, sym))
    elif ctrl and sym:
      self._invoke(get_default(self._bindings, f"Ctrl-{sym}"))

  def _invoke(self, f, *args, **kwargs):
    if f is not None:
      f(*args, **kwargs)
