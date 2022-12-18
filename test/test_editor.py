import unittest
import json
import os
from english2tikz.gui.editor import Editor
from english2tikz.test.mocks import *


class TestEditor(unittest.TestCase):
  def _create_editor_and_run_keys(self, keys, init_data=None):
    editor = Editor(MockTk(), MockCanvas(), 1200, 800)
    keys = [' ' if key == "Space" else key for key in keys]
    if init_data is not None:
      editor.load(init_data)
    for key in keys:
      editor.handle_key_by_code(key)
    return editor

  def _test_editor_operation(self, keys, result, init_data=None):
    editor = self._create_editor_and_run_keys(keys, init_data)
    self.assertEqual(editor._error_msg, None)
    self.assertEqual(json.dumps(editor._context._picture), result)

  def test_editor_operation_1(self):
    with open(os.path.join(os.path.dirname(__file__),
                           "test_editor_data.txt")) as f:
      data = f.read().strip()
    cases = data.split("\n\n")
    for case in cases:
      keys, result = case.split("\n")
      self._test_editor_operation(keys.split(" "), result)


if __name__ == "__main__":
  unittest.main()
