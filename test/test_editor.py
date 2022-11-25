import unittest
from english2tikz.gui.editor import Editor


class TestEditor(unittest.TestCase):
  def test_editor_operations(self):
    editor = Editor(root, canvas, 1200, 800)
