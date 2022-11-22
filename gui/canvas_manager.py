import tkinter as tk
import string
import copy
import re
import json
import os
import traceback
from functools import partial
from english2tikz.describe_it import DescribeIt
from english2tikz.handlers import WithAttributeHandler
from english2tikz.latex import tikzimage
from english2tikz.utils import *
from english2tikz.gui.drawers import *
from english2tikz.gui.keyboard import KeyboardManager
from english2tikz.gui.text_editor import TextEditor
from english2tikz.gui.selection import Selection
from english2tikz.gui.finding import Finding


class CanvasManager(object):
  def __init__(self, root, canvas, screen_width, screen_height,
               picture=None, object_path=".english2tikz"):
    self._canvas = canvas
    self._root = root
    self._object_path = os.path.join(os.getenv("HOME"), object_path)
    self._context = DescribeIt()
    if picture is not None:
      self._context._picture = picture
    self._end = False
    self._drawers = []
    self._register_fundamental_drawers()
    self._centerx = screen_width / 2
    self._centery = screen_height / 2
    self._screen_width = screen_width
    self._screen_height = screen_height
    self._pointerx = 0
    self._pointery = 0
    self._scale = 100
    self._command_line = None
    self._command_line_buffer = None
    self._command_history_index = None
    self._command_history = self._read_command_history()
    self._error_msg = None
    self._grid_size_index = 0
    self._grid_sizes = [1, 0.5, 0.2, 0.1, 0.05]
    self._show_axes = True
    self._show_grid = True
    self._show_attributes = True
    self._obj_to_edit_text = None
    self._editing_text = None
    self._editing_text_pos = None
    self._history = [self._context._picture]
    self._history_index = 0
    self._visual_start = None
    self._bounding_boxes = {}
    self._marks = []
    self._image_references = {}
    self._clipboard = []
    self._finding = None
    self._command_refershing_timer_started = True
    self._editing_refershing_timer_started = True
    self._start_time = now()
    self._pointer_objects = []
    self.filename = None
    self._keyboard_managers = {
        "normal": KeyboardManager(),
        "visual": KeyboardManager(),
        "editing": KeyboardManager(),
        "command": KeyboardManager(),
        "finding": KeyboardManager(),
    }
    self._normal_keyboard_manager = KeyboardManager()
    self._visual_keyboard_manager = KeyboardManager()
    self._edit_keyboard_manager = KeyboardManager()
    self._command_keyboard_manager = KeyboardManager()
    self._selection = Selection(self._context)
    self._register_keys()
    root.bind("<Key>", self.handle_key)
    root.after(50, self._draw_animated)
    root.after(1, self.draw)

  def register_key(self, mode, key, f):
    self._keyboard_managers[mode].bind(key, f)

  def _register_fundamental_drawers(self):
    self.register_drawer(BoxDrawer())
    self.register_drawer(PathDrawer())

  def register_drawer(self, drawer):
    assert isinstance(drawer, Drawer)
    self._drawers.append(drawer)

  def _register_keys(self):
    self.register_key("editing", "Printable", self._insert_char_to_edit)
    self.register_key("editing", "BackSpace", self._delete_char_from_edit)
    self.register_key("editing", "Return",
                      partial(self._insert_char_to_edit, '\n'))
    self.register_key("editing", "Ctrl-c", self._exit_editing_mode)
    self.register_key("editing", "Ctrl-Return", self._exit_editing_mode)
    self.register_key("editing", "Ctrl-o", self._external_editor_for_editing)
    self.register_key("editing", "Left", partial(self._move_edit_cursor, -1))
    self.register_key("editing", "Right", partial(self._move_edit_cursor, 1))
    self.register_key("editing", "Ctrl-6", self._move_edit_cursor_sol)
    self.register_key("editing", "Ctrl-0", self._move_edit_cursor_start)
    self.register_key("editing", "Ctrl-4", self._move_edit_cursor_eol)
    self.register_key("editing", "Ctrl-g", self._move_edit_cursor_end)
    self.register_key("editing", "Ctrl-j", self._move_edit_cursor_down)
    self.register_key("editing", "Ctrl-k", self._move_edit_cursor_up)
    self.register_key("editing", "Ctrl-h", self._move_edit_cursor_left)
    self.register_key("editing", "Ctrl-l", self._move_edit_cursor_right)
    self.register_key("command", "Printable", self._insert_char_to_command)
    self.register_key("command", "BackSpace", self._delete_char_from_command)
    self.register_key("command", "Ctrl-c", self._exit_command_mode)
    self.register_key("command", "Return", self._execute_command)
    self.register_key("command", "Up", self._fetch_previous_command)
    self.register_key("command", "Down", self._fetch_next_command)
    self.register_key("command", "Ctrl-o", self._external_editor_for_command)
    self.register_key("command", "Left",
                      partial(self._move_command_cursor, -1))
    self.register_key("command", "Right",
                      partial(self._move_command_cursor, 1))
    self.register_key("command", "Ctrl-0", self._move_command_cursor_start)
    self.register_key("command", "Ctrl-g", self._move_command_cursor_end)
    self.register_key("normal", "i", self._enter_edit_mode_without_visual)
    self.register_key("normal", "a",
                      partial(self._append_to_selected_object, "right"))
    self.register_key("normal", "I",
                      partial(self._append_to_selected_object, "left"))
    self.register_key("normal", "o",
                      partial(self._append_to_selected_object, "below"))
    self.register_key("normal", "O",
                      partial(self._append_to_selected_object, "above"))
    self.register_key("normal", ":", self._enter_command_mode)
    self.register_key("normal", "/", self._enter_command_mode_and_search)
    self.register_key("normal", "v", self._enter_visual_mode)
    self.register_key("normal", "f", partial(self._enter_finding_mode, False))
    self.register_key("normal", "F", partial(self._enter_finding_mode, True))
    self.register_key("normal", "Ctrl-c", self._deselect)
    self.register_key("normal", ">",
                      partial(self._shift_selected_objects_by_grid, 1, 0))
    self.register_key("normal", "<",
                      partial(self._shift_selected_objects_by_grid, -1, 0))
    self.register_key("normal", "K",
                      partial(self._shift_selected_objects_by_grid, 0, 1))
    self.register_key("normal", "J",
                      partial(self._shift_selected_objects_by_grid, 0, -1))
    self.register_key("normal", "u", self._undo)
    self.register_key("normal", "Ctrl-r", self._redo)
    self.register_key("normal", "m", self._add_simple_mark)
    self.register_key("normal", "D", self._delete_selected_objects)
    self.register_key("normal", "y", self._copy_selected_objects)
    self.register_key("normal", "p", self._paste)
    self.register_key("normal", "Ctrl-g", partial(self._change_grid_size, 1))
    self.register_key("normal", "Ctrl-f", partial(self._change_grid_size, -1))
    self.register_key("normal", "Return", partial(self._clear_error_message))
    self.register_key("normal", "j", partial(self._move_pointer, 0, -1))
    self.register_key("normal", "k", partial(self._move_pointer, 0, 1))
    self.register_key("normal", "h", partial(self._move_pointer, -1, 0))
    self.register_key("normal", "l", partial(self._move_pointer, 1, 0))
    self.register_key("normal", "w",
                      partial(self._move_pointer_by_inverse_grid_size, 1, 0))
    self.register_key("normal", "b",
                      partial(self._move_pointer_by_inverse_grid_size, -1, 0))
    self.register_key("normal", "W",
                      partial(self._move_pointer_by_inverse_grid_size, 4, 0))
    self.register_key("normal", "B",
                      partial(self._move_pointer_by_inverse_grid_size, -4, 0))
    self.register_key("normal", "e",
                      partial(self._move_pointer_by_inverse_grid_size, 0, -1))
    self.register_key("normal", "E",
                      partial(self._move_pointer_by_inverse_grid_size, 0, 1))
    self.register_key("normal", "L",
                      partial(self._move_pointer_to_screen_boundary, "below"))
    self.register_key("normal", "H",
                      partial(self._move_pointer_to_screen_boundary, "above"))
    self.register_key("normal", "0",
                      partial(self._move_pointer_to_screen_boundary, "left"))
    self.register_key("normal", "$",
                      partial(self._move_pointer_to_screen_boundary, "right"))
    self.register_key("normal", "M",
                      partial(self._move_pointer_to_screen_boundary, "middle"))
    self.register_key("normal", "n", partial(self._jump_to_next_selected, 1))
    self.register_key("normal", "N", partial(self._jump_to_next_selected, -1))
    self.register_key("normal", "G", self._reset_pointer_to_origin)
    self.register_key("normal", "Ctrl-e", partial(self._scroll, 0, -100))
    self.register_key("normal", "Ctrl-y", partial(self._scroll, 0, 100))
    self.register_key("normal", "Ctrl-m", self._set_position_to_mark)
    self.register_key("visual", "i", self._enter_edit_mode_at_visual)
    self.register_key("visual", ":", self._enter_command_mode)
    self.register_key("visual", "/", self._enter_command_mode_and_search)
    self.register_key("visual", "v",
                      partial(self._select_and_exit_visual_mode, "merge"))
    self.register_key("visual", "Return",
                      partial(self._select_and_exit_visual_mode, "clear"))
    self.register_key("visual", "-",
                      partial(self._select_and_exit_visual_mode, "exclude"))
    self.register_key("visual", "^",
                      partial(self._select_and_exit_visual_mode, "intersect"))
    self.register_key("visual", "Ctrl-c", self._exit_visual_mode)
    self.register_key("visual", "j", partial(self._move_pointer, 0, -1))
    self.register_key("visual", "k", partial(self._move_pointer, 0, 1))
    self.register_key("visual", "h", partial(self._move_pointer, -1, 0))
    self.register_key("visual", "l", partial(self._move_pointer, 1, 0))
    self.register_key("visual", "w",
                      partial(self._move_pointer_by_inverse_grid_size, 1, 0))
    self.register_key("visual", "b",
                      partial(self._move_pointer_by_inverse_grid_size, -1, 0))
    self.register_key("visual", "W",
                      partial(self._move_pointer_by_inverse_grid_size, 4, 0))
    self.register_key("visual", "B",
                      partial(self._move_pointer_by_inverse_grid_size, -4, 0))
    self.register_key("visual", "e",
                      partial(self._move_pointer_by_inverse_grid_size, 0, -1))
    self.register_key("visual", "E",
                      partial(self._move_pointer_by_inverse_grid_size, 0, 1))
    self.register_key("visual", "n", partial(self._jump_to_next_selected, 1))
    self.register_key("visual", "N", partial(self._jump_to_next_selected, -1))
    self.register_key("visual", "L",
                      partial(self._move_pointer_to_screen_boundary, "below"))
    self.register_key("visual", "H",
                      partial(self._move_pointer_to_screen_boundary, "above"))
    self.register_key("visual", "0",
                      partial(self._move_pointer_to_screen_boundary, "left"))
    self.register_key("visual", "$",
                      partial(self._move_pointer_to_screen_boundary, "right"))
    self.register_key("visual", "M",
                      partial(self._move_pointer_to_screen_boundary, "middle"))
    self.register_key("visual", "Ctrl-h",
                      partial(self._shift_selected_object_at_anchor, "left"))
    self.register_key("visual", "Ctrl-j",
                      partial(self._shift_selected_object_at_anchor, "down"))
    self.register_key("visual", "Ctrl-k",
                      partial(self._shift_selected_object_at_anchor, "up"))
    self.register_key("visual", "Ctrl-l",
                      partial(self._shift_selected_object_at_anchor, "right"))
    self.register_key("visual", "Ctrl-a",
                      partial(self._shift_selected_object_anchor, "left"))
    self.register_key("visual", "Ctrl-s",
                      partial(self._shift_selected_object_anchor, "down"))
    self.register_key("visual", "Ctrl-w",
                      partial(self._shift_selected_object_anchor, "up"))
    self.register_key("visual", "Ctrl-d",
                      partial(self._shift_selected_object_anchor, "right"))
    self.register_key("visual", "G", self._reset_pointer_to_origin)
    self.register_key("visual", "Ctrl-g", partial(self._change_grid_size, 1))
    self.register_key("visual", "Ctrl-f", partial(self._change_grid_size, -1))
    self.register_key("finding", "Printable", self._finding_narrow_down)
    self.register_key("finding", "BackSpace", self._finding_back)
    self.register_key("finding", "Ctrl-c", self._exit_finding_mode)

  def handle_key(self, event):
    self._keyboard_managers[self._get_mode()].handle_key(event)
    self.draw()

  def _scroll(self, dx, dy):
    self._centerx += dx
    self._centery += dy
    self._reset_pointer_into_screen()

  def _set_position_to_mark(self):
    if self._is_in_path_position_mode():
      if len(self._marks) == 1:
        self._before_change()
        self._selection.set_selected_path_item(self._marks[0])
        self._after_change()
      else:
        self._error_msg = "Can only set position to one mark"
    else:
      self._error_msg = "Not in path position mode"

  def _insert_char_to_edit(self, c):
    self._editing_text.insert(c)
    self._editing_refershing_timer_started = False

  def _move_edit_cursor(self, offset):
    self._editing_text.move_cursor(offset)

  def _move_edit_cursor_start(self):
    self._editing_text.move_to_start()

  def _move_edit_cursor_sol(self):
    self._editing_text.move_to_sol()

  def _move_edit_cursor_end(self):
    self._editing_text.move_to_end()

  def _move_edit_cursor_eol(self):
    self._editing_text.move_to_eol()

  def _move_edit_cursor_up(self):
    self._editing_text.move_up()

  def _move_edit_cursor_down(self):
    self._editing_text.move_down()

  def _move_edit_cursor_left(self):
    self._editing_text.move_left()

  def _move_edit_cursor_right(self):
    self._editing_text.move_right()

  def _insert_char_to_command(self, c):
    self._command_refershing_timer_started = False
    self._command_line.insert(c)
    self._command_line_buffer = str(self._command_line)
    self._command_history_index = None

  def _delete_char_from_edit(self):
    self._editing_text.delete()
    self._editing_refershing_timer_started = False

  def _delete_char_from_command(self):
    self._command_refershing_timer_started = False
    self._command_history_index = None
    if len(self._command_line) > 0:
      self._command_line.delete()
      self._command_line_buffer = str(self._command_line)
    else:
      self._exit_command_mode()

  def _move_command_cursor(self, offset):
    self._command_line.move_cursor(offset)

  def _move_command_cursor_start(self):
    self._command_line.move_to_start()

  def _move_command_cursor_end(self):
    self._command_line.move_to_end()

  def _is_in_command_mode(self):
    return self._command_line is not None

  def _is_in_editing_mode(self):
    return self._editing_text is not None

  def _is_in_visual_mode(self):
    return self._visual_start is not None

  def _is_in_finding_mode(self):
    return self._finding is not None

  def _is_in_normal_mode(self):
    return (not self._is_in_command_mode() and
            not self._is_in_editing_mode() and
            not self._is_in_visual_mode() and
            not self._is_in_finding_mode())

  def _get_mode(self):
    if self._is_in_command_mode():
      return "command"
    if self._is_in_editing_mode():
      return "editing"
    if self._is_in_visual_mode():
      return "visual"
    if self._is_in_finding_mode():
      return "finding"
    if self._is_in_normal_mode():
      return "normal"
    raise Exception("Invalid mode")

  def _enter_edit_mode_without_visual(self):
    if self._selection.num_ids() > 2:
      self._error_msg = "Cannot edit more than two objects"
    elif self._selection.num_ids() == 2:
      self._create_node_at_intersection(*self._selection.get_two_ids())
    elif self._selection.single_id():
      self._start_edit_text(self._selection.get_single_id())
    elif self._selection.num_paths() == 1:
      self._create_annotate(self._selection.get_single_path())
    else:
      self._start_edit_text()

  def _append_to_selected_object(self, direction):
    if self._selection.num_ids() > 1:
      self._error_msg = "Cannot append to more than one objects"
    elif self._selection.single_id():
      self._insert_text_following_id(self.get_single_id(), direction)

  def _enter_edit_mode_at_visual(self):
    self._create_node_at_visual()
    self._exit_visual_mode()

  def _exit_editing_mode(self):
    self._editing_refershing_timer_started = False
    if self._obj_to_edit_text is None:
      if len(self._editing_text) > 0:
        x, y = self._get_pointer_pos_str()
        self._parse(f"""there.is.text "{self._editing_text}" at.x.{x}.y.{y}
                        with.align=left""")
    else:
      self._before_change()
      self._obj_to_edit_text["text"] = str(self._editing_text)
      self._after_change()
    self._editing_text = None

  def _enter_command_mode(self):
    self._command_line = TextEditor()
    self._command_line_buffer = ""
    self._clear_error_message()

  def _enter_command_mode_and_search(self):
    self._command_line = TextEditor("search ")
    self._command_line_buffer = str(self._command_line)
    self._clear_error_message()

  def _exit_command_mode(self):
    self._command_line = None
    self._command_line_buffer = None
    self._command_history_index = None
    self._command_refershing_timer_started = False

  def _execute_command(self):
    self._process_command(str(self._command_line))
    self._exit_command_mode()

  def _fetch_previous_command(self):
    self._command_refershing_timer_started = False
    if self._command_history_index is None:
      if len(self._command_history) > 0:
        self._command_history_index = len(self._command_history) - 1
    else:
      self._command_history_index = max(0, self._command_history_index - 1)
    self._command_line.set(self._command_history[self._command_history_index])
    self._command_line.move_to_end()

  def _fetch_next_command(self):
    self._command_refershing_timer_started = False
    if self._command_history_index is not None:
      self._command_history_index += 1
      if self._command_history_index >= len(self._command_history):
        self._command_history_index = None
        self._command_line.set(self._command_line_buffer)
      else:
        self._command_line.set(
            self._command_history[self._command_history_index])
      self._command_line.move_to_end()

  def _external_editor_for_command(self):
    """
    It is very inconvenient to edit text in our tool, and I'm too lazy
    to implement a powerful text editor or using the tkinter text field.
    So press Ctrl+o to open an external editor for assistance.
    """
    if not self._command_refershing_timer_started:
      self._start_timer_for_refreshing_command()
    with open("/tmp/command", "w") as f:
      f.write(str(self._command_line))
    os.system(f"open -a 'Sublime Text' /tmp/command")

  def _external_editor_for_editing(self):
    """
    It is very inconvenient to edit text in our tool, and I'm too lazy
    to implement a powerful text editor or using the tkinter text field.
    So press Ctrl+o to open an external editor for assistance.
    """
    if not self._editing_refershing_timer_started:
      self._start_timer_for_refreshing_editing()
    with open("/tmp/editing", "w") as f:
      f.write(str(self._editing_text))
    os.system(f"open -a 'Sublime Text' /tmp/editing")

  def _enter_visual_mode(self):
    x, y = self._get_pointer_pos()
    self._visual_start = (x, y)

  def _select_and_exit_visual_mode(self, mode="clear"):
    self._clear_error_message()
    self._select_targets(mode)
    self._exit_visual_mode()

  def _intersect_and_exit_visual_mode(self):
    self._clear_error_message()
    self._intersect_select_targets()
    self._exit_visual_mode()

  def _clear_error_message(self):
    self._error_msg = None

  def _exit_visual_mode(self):
    self._visual_start = None

  def _deselect(self):
    if not self._selection.deselect():
      self._marks = []

  def _delete_selected_objects(self):
    self._before_change()
    if self._selection.has_id():
      deleted_ids = []
      for id_ in self._selection.ids():
        self._delete_objects_related_to_id(id_, deleted_ids)
    if self._selection.has_path():
      for path in self._selection.paths():
        self._delete_path(path)
    self._after_change()
    self._selection.clear()

  def _copy_selected_objects(self):
    self._clipboard = [copy.deepcopy(obj)
                       for obj in self._context._picture
                       if self._selection.selected(obj)]

  def _parse(self, code):
    self._before_change()
    self._context.parse(code)
    self._after_change()

  def _before_change(self):
    self._history = self._history[:self._history_index+1]
    self._history[self._history_index] = copy.deepcopy(
        self._history[self._history_index])

  def _after_change(self):
    self._history.append(self._context._picture)
    self._history_index = len(self._history) - 1

  def _undo(self):
    if self._history_index == 0:
      self._error_msg = "Already the oldest"
      return

    self._history_index -= 1
    self._context._picture = self._history[self._history_index]

  def _redo(self):
    if self._history_index >= len(self._history) - 1:
      self._error_msg = "Already at newest change"
      return
    self._history_index += 1
    self._context._picture = self._history[self._history_index]

  def _add_simple_mark(self):
    if self._is_in_path_position_mode():
      self._marks.append(copy.deepcopy(self._selection.get_path_position()))
    else:
      x, y = self._get_pointer_pos()
      self._marks.append(create_coordinate(x, y))

  def _grid_size(self):
    return self._grid_sizes[self._grid_size_index]

  def _start_timer_for_refreshing_command(self):
    self._command_refershing_timer_started = True
    self._root.after(100, self._refresh_command)

  def _refresh_command(self):
    if not self._command_refershing_timer_started:
      return
    if self._command_line is None:
      self._command_refershing_timer_started = False
      return
    try:
      with open("/tmp/command") as f:
        self._command_line.set(f.read())
    except Exception as e:
      self._error_msg = f"Failed to refresh command: {e}"
    self._root.after(100, self._refresh_command)
    self.draw()

  def _start_timer_for_refreshing_editing(self):
    self._editing_refershing_timer_started = True
    self._root.after(100, self._refresh_editing)

  def _refresh_editing(self):
    if not self._editing_refershing_timer_started:
      return
    if self._editing_text is None:
      self._editing_refershing_timer_started = False
      return
    try:
      with open("/tmp/editing") as f:
        self._editing_text.set(f.read())
    except Exception as e:
      self._error_msg = f"Failed to refresh editing: {e}"
    self._root.after(100, self._refresh_editing)
    self.draw()

  def _finding_narrow_down(self, char):
    try:
      obj = self._finding.narrow_down(char)
    except Exception as e:
      self._error_msg = f"Error in finding: {e}"
      return
    if obj is not None:
      if self._finding.is_toggle():
        self._selection.toggle(obj)
      else:
        self._selection.select(obj)
      self._exit_finding_mode()

  def _finding_back(self):
    if not self._finding.back():
      self._exit_finding_mode()

  def _exit_finding_mode(self):
    self._finding = None

  def _clear(self):
    self._visual_start = None
    self._marks = []
    self._clear_selects()

  def _clear_selects(self):
    self._selection.clear()

  def _change_grid_size(self, by):
    x, y = self._get_pointer_pos()
    self._grid_size_index = bound_by(self._grid_size_index + by,
                                     0, len(self._grid_sizes) - 1)
    self._pointerx, self._pointery = self._find_closest_pointer_grid_coord(x,
                                                                           y)
    self._move_pointer_into_screen()

  def _is_in_path_position_mode(self):
    return self._selection.is_in_path_position_mode()

  def _enter_finding_mode(self, toggle=False):
    candidate_ids, candidate_paths = self._find_all_in_screen()
    candidates = candidate_ids + candidate_paths
    candidates_number = len(candidates)
    try:
      self._finding = Finding(candidates, toggle)
    except Exception as e:
      self._error_msg = f"Error entering finding mode: {e}"

  def _get_selected_id_objects(self):
    return self._selection.get_selected_id_objects()

  def _get_selected_objects(self):
    return self._selection.get_selected_objects()

  def _shift_object_at_anchor(self, id_, direction):
    obj = self._find_object_by_id(id_)
    if obj is None:
      return

    if get_default_of_type(obj, "at", str):
      obj["at.anchor"] = shift_anchor(
          get_default(obj, "at.anchor", "center"),
          direction)
    elif "at" in obj and is_type(obj["at"], "intersection"):
      if direction == "left" or direction == "right":
        obj["at"]["anchor1"] = shift_anchor(
            get_default(obj["at"], "anchor1", "center"),
            direction)
      elif direction == "up" or direction == "down":
        obj["at"]["anchor2"] = shift_anchor(
            get_default(obj["at"], "anchor2", "center"),
            direction)
      else:
        raise Exception(f"Unknown direction {direction}")
    else:
      self._error_msg = f"Object {id_} is not anchored to another object, " \
          "nor at intersection"
      return

  def _shift_object_anchor(self, id_, direction):
    obj = self._find_object_by_id(id_)
    if obj is None:
      return

    obj["anchor"] = shift_anchor(
        get_default(obj, "anchor", "center"),
        flipped(direction))

  def _shift_selected_object_at_anchor(self, direction):
    for id_ in self._selection.ids():
      self._shift_object_at_anchor(id_, direction)

  def _shift_selected_object_anchor(self, direction):
    for id_ in self._selection.ids():
      self._shift_object_anchor(id_, direction)

  def _jump_to_next_selected(self, by):
    if self._selection.jump_to_next_selected(by):
      self._jump_to_select()

  def _reset_pointer_to_origin(self):
    self._pointerx = 0
    self._pointery = 0
    self._centerx = self._screen_width / 2
    self._centery = self._screen_height / 2

  def _create_node_at_visual(self):
    x0, y0 = self._get_pointer_pos()
    x1, y1 = self._visual_start
    x0, x1 = order(x0, x1)
    y0, y1 = order(y0, y1)
    w, h = x1 - x0, y1 - y0
    self._editing_text_pos = x0 + w/2, y0 + h/2
    x0, y0, w, h = num_to_dist(x0, y0, w, h)
    self._parse(f"there.is.a.box at.x.{x0}.y.{y0} "
                f"sized.{w}.by.{h} with.anchor=south.west")
    self._obj_to_edit_text = self._context._picture[-1]
    self._editing_text = TextEditor(self._obj_to_edit_text["text"])

  def _create_node_at_intersection(self, id0, id1):
    self._ensure_name_is_id(id0)
    self._ensure_name_is_id(id1)
    x0, _ = self._bounding_boxes[id0].get_anchor_pos("center")
    _, y0 = self._bounding_boxes[id1].get_anchor_pos("center")
    self._editing_text_pos = x0, y0
    self._parse(f"there.is.text at.intersection.of.{id0}.and.{id1}")
    self._obj_to_edit_text = self._context._picture[-1]
    self._editing_text = TextEditor(self._obj_to_edit_text["text"])

  def _create_annotate(self, path):
    lines = [item for item in path["items"] if item["type"] == "line"]
    if len(lines) == 0:
      self._error_msg = "Selected path has no segment"
      return
    elif len(lines) > 1:
      self._error_msg = "Selected path has multiple segments"
      return
    annotates = ensure_key(lines[0], "annotates", [])
    annotate = {
        "id": self._context.getid(),
        "type": "text",
        "in_path": True,
        "text": "",
        "midway": True,
        "above": True,
        "sloped": True,
        "scale": "0.7",
    }
    annotates.append(annotate)
    self._obj_to_edit_text = annotate
    self._editing_text_pos = self._get_pointer_pos()
    self._editing_text = TextEditor()

  def _start_edit_text(self, id_=None):
    if id_ is None:
      self._editing_text = TextEditor()
      self._obj_to_edit_text = None
      self._editing_text_pos = self._get_pointer_pos()
      return

    self._obj_to_edit_text = self._find_object_by_id(id_)
    if self._obj_to_edit_text is None:
      self._error_msg = f"Cannot find object with id {id_}"
      return

    if "text" not in self._obj_to_edit_text:
      self._error_msg = f"The selected object {id_} does not support text."
      return

    self._editing_text = TextEditor(self._obj_to_edit_text["text"])
    self._editing_text_pos = self._bounding_boxes[id_].get_anchor_pos("center")

  def _find_object_by_id(self, id_):
    return self._context.find_object_by_id(id_)

  def _ensure_name_is_id(self, id_):
    obj = self._find_object_by_id(id_)
    if obj is not None:
      obj["name"] = id_
    else:
      self._error_msg = f"Cannot find object with id {id_}"
      traceback.print_exc()

  def _insert_text_following_id(self, id_, direction):
    if direction == "right":
      anchor, at_anchor = "west", "east"
    elif direction == "left":
      anchor, at_anchor = "east", "west"
    elif direction == "above":
      anchor, at_anchor = "south", "north"
    elif direction == "below":
      anchor, at_anchor = "north", "south"
    else:
      raise Exception(f"Unknown direction: {direction}")

    self._ensure_name_is_id(id_)
    self._parse(f"there.is.text '' with.{anchor}.at.{at_anchor}.of.{id_}")
    self._obj_to_edit_text = self._context._picture[-1]
    self._editing_text = TextEditor()
    self._editing_text_pos = self._bounding_boxes[id_].get_anchor_pos(
        at_anchor)
    self._selection.select(self._obj_to_edit_text)

  def _shift_selected_objects(self, dx, dy):
    if self._selection.has_id():
      self._before_change()
      for id_ in self._selection.ids():
        self._shift_object(id_, dx, dy)
      self._after_change()
    elif self._selection.is_in_path_position_mode():
      self._before_change()
      self._shift_path_position(self.get_path_position(), dx, dy)
      self._after_change()

  def _shift_selected_objects_by_grid(self, dx, dy):
    return self._shift_selected_objects(dx * self._grid_size(),
                                        dy * self._grid_size())

  def _shift_dist(self, obj, key, delta, empty_val=None):
    if delta == 0:
      return
    val = dist_to_num(get_default(obj, key, 0)) + delta
    val = round(val / self._grid_size()) * self._grid_size()
    val = num_to_dist(val)
    set_or_del(obj, key, val, empty_val)

  def _shift_object(self, id_, dx, dy):
    obj = self._find_object_by_id(id_)
    at = get_default(obj, "at")
    if is_type(at, "coordinate"):
      self._shift_dist(at, "x", dx)
      self._shift_dist(at, "y", dy)
    elif get_default(obj, "in_path", False):
      self._shift_dist(obj, "xshift", dx, "0")
      self._shift_dist(obj, "yshift", dy, "0")
    elif isinstance(at, str):
      self._shift_dist(obj, "xshift", dx, "0")
      self._shift_dist(obj, "yshift", dy, "0")
    elif is_type(at, "intersection"):
      self._shift_dist(obj, "xshift", dx, "0")
      self._shift_dist(obj, "yshift", dy, "0")
    elif get_direction_of(obj) is not None:
      self._shift_dist(obj, "xshift", dx, "0")
      self._shift_dist(obj, "yshift", dy, "0")
    else:
      obj["at"] = {
          "type": "coordinate",
          "x": dx,
          "y": dy,
      }

  def _shift_path_position(self, item, dx, dy):
    if is_type(item, "coordinate"):
      self._shift_dist(item, "x", dx)
      self._shift_dist(item, "y", dy)
      return
    if is_type(item, "nodename"):
      self._shift_dist(item, "xshift", dx)
      self._shift_dist(item, "yshift", dy)

  def _screen_range(self):
    x0, y0 = reverse_map_point(0, 0, self._coordinate_system())
    x1, y1 = reverse_map_point(self._screen_width,
                               self._screen_height,
                               self._coordinate_system())
    return x0, y0, x1, y1

  def _find_all_in_screen(self):
    sel = self._screen_range()
    selected_ids, selected_paths = [], []

    for id_, bb in self._bounding_boxes.items():
      if bb.intersect_rect(sel):
        if id_.startswith("segment_"):
          append_if_not_in(selected_paths, bb._obj)
        else:
          append_if_not_in(selected_ids, id_)

    return selected_ids, selected_paths

  def _select_targets(self, mode="clear"):
    x0, y0 = self._visual_start
    x1, y1 = self._get_pointer_pos()
    x0, x1 = order(x0, x1)
    y0, y1 = order(y0, y1)
    sel = (x0, y0, x1, y1)

    items = []
    for id_, bb in self._bounding_boxes.items():
      if bb.intersect_rect(sel):
        if id_.startswith("segment_"):
          items.append(bb._obj)
        else:
          items.append(id_)

    if mode == "clear":
      self._selection.select(*items)
    elif mode == "exclude":
      self._selection.exclude(*items)
    elif mode == "intersect":
      self._selection.intersect(*items)
    elif mode == "toggle":
      self._selection.toggle(*items)
    elif mode == "merge":
      self._selection.include(*items)

  def _delete_objects_related_to_id(self, id_, deleted_ids=[]):
    to_removes = [obj for obj in self._context._picture
                  if self._related_to(obj, id_)]
    deleted_ids.append(id_)
    related_ids = [item["id"] for item in to_removes
                   if "id" in item and item["id"] not in deleted_ids]
    self._context._picture = [obj for obj in self._context._picture
                              if not self._related_to(obj, id_)]

    for obj in self._context._picture:
      if "items" in obj:
        for item in obj["items"]:
          if "annotates" in item:
            item["annotates"] = [annotate for annotate in item["annotates"]
                                 if "id" not in annotate
                                 or annotate["id"] != id_]
    for id_ in related_ids:
      self._delete_objects_related_to_id(id_, deleted_ids)

  def _related_to(self, obj, id_):
    if "id" in obj and obj["id"] == id_:
      return True
    if "at" in obj and obj["at"] == id_:
      return True
    if "items" in obj:
      for item in obj["items"]:
        if "type" in item and item["type"] == "nodename":
          if item["name"] == id_:
            return True
    return False

  def _delete_path(self, path):
    affected_ids = []
    for item in path["items"]:
      if "annotates" in item:
        for annotate in item["annotates"]:
          if "id" in annotate and "id" not in affected_ids:
            affected_ids.append(annotate["id"])
    for i in range(len(self._context._picture)):
      if self._context._picture[i] == path:
        del self._context._picture[i]
        break

    deleted_ids = []
    for id_ in affected_ids:
      self._delete_objects_related_to_id(id_, deleted_ids)

  def _paste(self):
    if len(self._clipboard) == 0:
      return
    self._before_change()
    self._paste_data(copy.deepcopy(self._clipboard), False,
                     self._bounding_boxes)
    self._after_change()

  def _jump_to_select(self):
    id_ = self.id_to_jump()
    if id_ not in self._bounding_boxes:
      return
    bb = self._bounding_boxes[id_]
    x, y = bb.get_anchor_pos("center")
    self._pointerx = round(x / self._grid_size())
    self._pointery = round(y / self._grid_size())
    self._reset_pointer_into_screen()

  def _get_pointer_pos(self):
    return (self._pointerx * self._grid_size(),
            self._pointery * self._grid_size())

  def _get_pointer_pos_str(self):
    x, y = self._get_pointer_pos()
    return num_to_dist(x), num_to_dist(y)

  def _get_pointer_screen_pos(self):
    x, y = self._get_pointer_pos()
    return map_point(x, y, self._coordinate_system())

  def _find_closest_pointer_grid_coord(self, x, y):
    gs = self._grid_size()
    return round(x / gs), round(y / gs)

  def _move_pointer(self, x, y):
    self._pointerx += x
    self._pointery += y
    self._move_pointer_into_screen()

  def _move_pointer_by_inverse_grid_size(self, x, y):
    self._move_pointer(round(x/self._grid_size()),
                       round(y/self._grid_size()))

  def _move_pointer_into_screen(self):
    screenx, screeny = self._get_pointer_screen_pos()
    if screenx < 0:
      self._centerx -= screenx
    elif screenx >= self._screen_width:
      self._centerx += self._screen_width - screenx
    if screeny < 0:
      self._centery -= screeny
    elif screeny >= self._screen_height:
      self._centery += self._screen_height - screeny

  def _move_pointer_to_screen_boundary(self, direction):
    upper, lower, left, right = self._boundary_grids()
    if direction == "left":
      self._pointerx = left
    elif direction == "right":
      self._pointerx = right
    elif direction == "above":
      self._pointery = upper
    elif direction == "below":
      self._pointery = lower
    elif direction == "middle":
      self._pointery = int((upper + lower)/2)
    self._move_pointer_into_screen()

  def _reset_pointer_into_screen(self):
    screenx, screeny = self._get_pointer_screen_pos()
    screenx = bound_by(screenx, self._scale - 10,
                       self._screen_width - self._scale + 10)
    screeny = bound_by(screeny, self._scale - 10,
                       self._screen_height - self._scale + 10)
    self._pointerx, self._pointery = self._find_closest_pointer_grid_coord(
        *reverse_map_point(screenx, screeny, self._coordinate_system()))

  def _boundary_grids(self):
    x0, y0 = reverse_map_point(0, 0, self._coordinate_system())
    x1, y1 = reverse_map_point(self._screen_width,
                               self._screen_height,
                               self._coordinate_system())
    step_upper = int(y0 / self._grid_size())
    step_lower = int(y1 / self._grid_size())
    step_left = int(x0 / self._grid_size())
    step_right = int(x1 / self._grid_size())
    return step_upper, step_lower, step_left, step_right

  def draw(self):
    if self._end:
      return
    self._canvas.delete("all")
    if self._show_grid:
      self._draw_grid(self._canvas)
    if self._show_axes:
      self._draw_axes(self._canvas)
    self._draw_picture(self._canvas, self._context)
    self._draw_visual(self._canvas)
    self._draw_marks(self._canvas)
    self._draw_attributes(self._canvas)
    if self._editing_text is not None:
      self._draw_editing_text(self._canvas)
    else:
      self._draw_pointer_indicator(self._canvas)
    self._draw_command(self._canvas)

  def _draw_animated(self):
    if self._end:
      return
    for obj in self._pointer_objects:
      self._canvas.delete(obj)
    if self._editing_text is None:
      self._pointer_objects = self._draw_pointer(self._canvas)
    else:
      self._pointer_objects = []
    self._root.after(100, self._draw_animated)

  def _draw_grid(self, c):
    step_upper, step_lower, step_left, step_right = self._boundary_grids()
    step = round(1 / self._grid_size())
    for i in range(step_lower, step_upper+1):
      x, y = map_point(0, self._grid_size() * i, self._coordinate_system())
      c.create_line((0, y, self._screen_width, y), fill="gray", dash=2)
      draw_text = i == self._pointery or i % step == 0
      color = "red" if i == self._pointery else "gray"
      if draw_text:
        text = "%g" % (i * self._grid_size())
        c.create_text(5, y, text=text, anchor="sw", fill=color)
        c.create_text(self._screen_width-3, y,
                      text=text, anchor="se", fill=color)
    for i in range(step_left, step_right+1):
      x, y = map_point(self._grid_size() * i, 0, self._coordinate_system())
      c.create_line((x, 0, x, self._screen_height), fill="gray", dash=2)
      draw_text = i == self._pointerx or i % step == 0
      color = "red" if i == self._pointerx else "gray"
      if draw_text:
        text = "%g" % (i * self._grid_size())
        c.create_text(x, 0, text=text, anchor="nw", fill=color)
        c.create_text(x, self._screen_height,
                      text=text, anchor="sw", fill=color)

  def _draw_axes(self, c):
    c.create_line((0, self._centery, self._screen_width, self._centery),
                  fill="#888888", width=1.5)
    c.create_line((self._centerx, 0, self._centerx, self._screen_height),
                  fill="#888888", width=1.5)

  def _coordinate_system(self):
    return {
        "width": self._screen_width,
        "height": self._screen_height,
        "center_x": self._centerx,
        "center_y": self._centery,
        "scale": self._scale,
    }

  def _draw_picture(self, c, ctx):
    env = {
        "bounding box": {},
        "coordinate system": self._coordinate_system(),
        "selection": self._selection,
        "image references": self._image_references,
        "finding": self._finding,
    }
    for obj in ctx._picture:
      self._draw_obj(c, obj, env)
    self._bounding_boxes = env["bounding box"]

  def _draw_obj(self, c, obj, env):
    for drawer in self._drawers:
      if not drawer.match(obj):
        continue
      try:
        drawer.draw(c, obj, env)
      except Exception as e:
        traceback.print_exc()
        self._error_msg = f"Error in draw: {e}"
      return
    raise Exception(f"Cannot find drawer for obj {obj}")

  def _draw_visual(self, c):
    if self._visual_start is None:
      return
    x, y = self._visual_start
    x0, y0 = map_point(x, y, self._coordinate_system())
    x1, y1 = self._get_pointer_screen_pos()
    c.create_rectangle((x0, y0, x1, y1), outline="red", width=4, dash=8)

  def _get_mark_pos(self, i, buffer={}):
    if i in buffer:
      return buffer[i]

    if i < 0:
      raise Exception(f"Trying to get mark of number {i}")

    mark = self._marks[i]

    if is_type(mark, "nodename"):
      bb = self._bounding_boxes[mark["name"]]
      x, y = bb.get_anchor_pos(get_default(mark, "anchor", "center"))
      if "anchor" in mark:
        """
        It's useless in tikz to shift a node name coordinate without specifying
        the anchor.
        """
        x += dist_to_num(get_default(mark, "xshift", 0))
        y += dist_to_num(get_default(mark, "yshift", 0))
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "intersection"):
      bb1 = self._bounding_boxes[mark["name1"]]
      bb2 = self._bounding_boxes[mark["name2"]]
      x, _ = bb1.get_anchor_pos(get_default(mark, "anchor1", "center"))
      _, y = bb2.get_anchor_pos(get_default(mark, "anchor2", "center"))
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "coordinate"):
      if get_default(mark, "relative", False):
        x0, y0 = self._get_mark_pos(i-1, buffer)
        x = x0 + dist_to_num(mark["x"])
        y = y0 + dist_to_num(mark["y"])
      else:
        x, y = dist_to_num(mark["x"], mark["y"])
      buffer[i] = (x, y)
      return x, y
    elif is_type(mark, "cycle"):
      buffer[i] = buffer[0]
      return buffer[i]
    else:
      raise Exception(f"Unknown mark type {mark['type']}")

  def _draw_marks(self, c):
    buffer = {}
    for i, mark in enumerate(self._marks):
      try:
        """
        When a mark is deleted, it may cause marks with relative positions
        to be invalid. So it is possible to have exception here, and in
        this case, we simply remove all the following marks.
        """
        x, y = self._get_mark_pos(i, buffer)
      except Exception:
        self._marks = self._marks[:i]
        return

      x, y = map_point(x, y, self._coordinate_system())
      radius = 10
      if is_type(mark, "coordinate"):
        if get_default(mark, "relative", False):
          fill, outline = "#ff7777", "red"
        else:
          fill, outline = "#77ff77", "green"
      elif is_type(mark, "nodename"):
        if "xshift" in mark or "yshift" in mark:
          fill, outline = "#7777ff", "blue"
        else:
          fill, outline = "#ffff77", "orange"
      elif is_type(mark, "intersection"):
        fill, outline = "white", "black"
      elif is_type(mark, "cycle"):
        fill, outline, radius = "red", "black", 12
      c.create_oval(x-radius, y-radius, x+radius, y + radius,
                    fill=fill, outline=outline)
      c.create_text(x, y, text=str(i), fill="black")

  def _draw_editing_text(self, c):
    x, y = map_point(*self._editing_text_pos, self._coordinate_system())
    t = c.create_text(x, y, text=self._editing_text.view(),
                      fill="black", font=("Courier", 20, "normal"))
    bg = c.create_rectangle(c.bbox(t), fill="white", outline="blue")
    c.tag_lower(bg, t)

  def _elapsed(self):
    return now() - self._start_time

  def _draw_pointer_indicator(self, c):
    x, y = map_point(self._pointerx * self._grid_size(),
                     self._pointery * self._grid_size(),
                     self._coordinate_system())
    c.create_line((0, y, self._screen_width, y), fill="red", width=1)
    c.create_line((x, 0, x, self._screen_height), fill="red", width=1)

  def _draw_pointer(self, c):
    ret = []
    x, y = map_point(self._pointerx * self._grid_size(),
                     self._pointery * self._grid_size(),
                     self._coordinate_system())
    angle = int((self._elapsed() / 5)) % 360
    rad = angle / 180 * math.pi
    dx1, dy1 = 10 * math.cos(rad), 10 * math.sin(rad)
    dx2, dy2 = -10 * math.sin(rad), 10 * math.cos(rad)
    ret.append(c.create_line((x+dx1, y+dy1, x-dx1, y-dy1),
                             fill="red", width=2))
    ret.append(c.create_line((x+dx2, y+dy2, x-dx2, y-dy2),
                             fill="red", width=2))
    return ret

  def _selected_single_object(self):
    return self._selection.get_single_object()

  def _draw_attributes(self, c):
    if not self._show_attributes:
      return

    to_draw = self._selection.get_selected_objects_common_description()
    keys = sorted(list(to_draw.keys()))

    y = 5
    for key in keys:
      value = to_draw[key]
      if isinstance(value, str):
        t = c.create_text(15, y, anchor="nw", text=key, fill="blue",
                          font=("Courier", 15, "normal"))
        t = c.create_text(120, y, anchor="nw", text=str(value),
                          fill="#000077", font=("Courier", 15, "normal"))
        _, _, _, y = c.bbox(t)
      elif isinstance(value, dict):
        t = c.create_text(15, y, anchor="nw", text=key, fill="blue",
                          font=("Courier", 15, "normal"))
        for k, v in value.items():
          t = c.create_text(120, y, anchor="nw", text=k,
                            fill="#000077", font=("Courier", 15, "normal"))
          t = c.create_text(200, y, anchor="nw", text=v,
                            fill="#007700", font=("Courier", 15, "normal"))
          _, _, _, y = c.bbox(t)
      elif value is True:
        t = c.create_text(15, y, anchor="nw", text=key, fill="blue",
                          font=("Courier", 15, "normal"))
        _, _, _, y = c.bbox(t)

  def _draw_command(self, c):
    if self._is_in_command_mode():
      c.create_rectangle((3, self._screen_height-28,
                          self._screen_width, self._screen_height),
                         fill="white", outline="black")
      c.create_text(5, self._screen_height, text=":"+self._command_line.view(),
                    anchor="sw", fill="black", font=("Courier", 20, "normal"))
    elif self._error_msg is not None:
      c.create_rectangle((3, self._screen_height-15,
                          self._screen_width, self._screen_height),
                         fill="white", outline="black")
      c.create_text(5, self._screen_height, text=self._error_msg,
                    anchor="sw", fill="red")

  def _tokenize(self, code):
    code = code.strip()
    tokens = []
    while len(code) > 0:
      if code.startswith("'''") or code.startswith('"""'):
        escaped, text = False, None
        for i in range(1, len(code)):
          if escaped:
            escaped = False
            continue
          if code[i] == '\\':
            escaped = True
            continue
          if i + 3 <= len(code) and code[i:i+3] == code[0] * 3:
            text = code[0:i+3]
            code = code[i+3:].strip()
            break
        if text:
          tokens.append(("text", text[3:-3]))
          continue
        else:
          raise Exception(f"Unended quote: {code}")
      if code.startswith("'") or code.startswith('"'):
        escaped, text = False, None
        for i in range(1, len(code)):
          if escaped:
            escaped = False
            continue
          if code[i] == '\\':
            escaped = True
            continue
          if code[i] == code[0]:
            text = code[0:i+1]
            code = code[i+1:].strip()
            break
        if text:
          tokens.append(("text", text[1:-1]))
          continue
        else:
          raise Exception(f"Unended quote: {code}")
      if code.startswith("python{{{"):
        end = code.find("python}}}")
        if end < 0:
          raise Exception(f"Unended python code: {code}")
        python_code = code[9:end]
        code = code[end+9:].strip()
        tokens.append(("python", code))
        continue
      match = re.search(r'[\n\s]+', code)
      if match:
        tokens.append(("command", code[0:match.span()[0]]))
        code = code[match.span()[1]:].strip()
        continue
      tokens.append(("command", code))
      break
    return tokens

  def _save(self):
    if len(self._context._picture) == 0:
      x0, y0, x1, y1 = 0, 0, 0, 0
    else:
      x0, y0, x1, y1 = get_bounding_box(self._context._picture,
                                        self._bounding_boxes)
    return {
        "picture": self._context._picture,
        "nextid": get_default(self._context._state, "nextid", 0),
        "bound_box": [x0, y0, x1, y1],
        "width": x1 - x0,
        "height": y1 - y0,
    }

  def load(self, data):
    if "picture" in data:
      self._context._picture = data["picture"]
    if "nextid" in data:
      self._context._state["nextid"] = data["nextid"]
    self._history = [self._context._picture]
    self._fix_id_and_names()
    self.draw()

  def _fix_id_and_names(self):
    for item in self._context._picture:
      id_ = get_default(item, "id")
      if id_ is not None:
        item["name"] = id_

  def _process_command(self, cmd):
    self._append_command(cmd)
    self._save_command_history(self._command_history)
    try:
      tokens = self._tokenize(cmd)
      if len(tokens) == 0:
        raise Exception("Empty command")
      if tokens[0][0] != "command":
        raise Exception("Command does not start with command name")
      cmd_name = tokens[0][1]
      if cmd_name == "set":
        self._set(*tokens[1:])
      elif cmd_name == "unset" or cmd_name == "un":
        self._unset(*tokens[1:])
      elif cmd_name == "fill" or cmd_name == "f":
        self._set_fill(*tokens[1:])
      elif cmd_name in anchor_list:
        self._set(("command", cmd_name))
      elif cmd_name == "make" or cmd_name == "mk":
        self._make(*tokens[1:])
      elif cmd_name == "rect":
        self._make(("command", "rect"), *tokens[1:])
      elif cmd_name == "path":
        self._make(("command", "path"), *tokens[1:])
      elif cmd_name == "cn" or cmd_name == "connect":
        self._connect(*tokens[1:])
      elif cmd_name == "grid" or cmd_name == "g":
        self._set_grid(*tokens[1:])
      elif cmd_name == "axes" or cmd_name == "a":
        self._set_axes(*tokens[1:])
      elif cmd_name == "mark" or cmd_name == "m":
        self._add_mark(*tokens[1:])
      elif cmd_name == "attr":
        self._show_attributes = not self._show_attributes
      elif cmd_name == "ann" or cmd_name == "annotate":
        self._annotate(*tokens[1:])
      elif cmd_name == "ch" or cmd_name == "chain":
        self._chain(*tokens[1:])
      elif cmd_name == "search":
        self._search(*tokens[1:])
      elif cmd_name == "read":
        self._read(*tokens[1:])
      elif cmd_name == "w":
        if self.filename is None:
          print("%%drawjson\n"+json.dumps(self._save()))
        else:
          data = json.dumps(self._save())
          with open(self.filename, "w") as f:
            f.write(data)
      elif cmd_name == "sao":
        self._save_as_object(*tokens[1:])
      elif cmd_name == "ro":
        self._read_object(*tokens[1:])
      elif cmd_name == "q":
        self._end = True
        self._root.after(100, self._root.destroy())
      elif cmd_name == "py":
        self._execute_python_code()
      elif cmd_name == "epy":
        self._edit_python_code()
      elif cmd_name == "eg":
        self._execute_describeit_code()
      elif cmd_name == "eeg":
        self._edit_describeit_code()
      elif cmd_name == "dump":
        self._dump()
      else:
        raise Exception(f"Unkown command: {cmd_name}")
    except Exception as e:
      self._error_msg = f"Error in executing command: {e}"

  def _append_command(self, cmd):
    self._command_history.append(cmd)
    if len(self._command_history) > 100:
      self._command_history = self._command_history[-100:]

  def _set(self, *args):
    if self._selection.empty():
      raise Exception("No object selected")
    key = None
    for t, v in args:
      if t == "command":
        if key is not None:
          self._set_selected_objects(key, True)
        eq = v.find("=")
        if eq >= 0:
          self._set_selected_objects(v[:eq], v[eq+1:])
          continue
        key = v
      elif t == "text":
        if key is None:
          raise Exception(f"Unexpected text: [{v}]")
        self._set_selected_objects(key, v)
        key = None
      elif t == "python":
        if key is None:
          raise Exception(f"Unexpected text: [{v}]")
        self._set_selected_objects(key, eval(v))
        key = None
      else:
        raise Exception(f"Unrecognized token type: [{t}]")
    if key is not None:
      self._set_selected_objects(key, True)

  def _unset(self, *args):
    if self._selection.empty():
      raise Exception("No object selected")
    for t, v in args:
      if t == "command":
        self._set_selected_objects(v, False)

  def _process_key_value(self, key, value):
    """
    Implement acronyms and aliases.
    """
    if is_color(key) and value is True:
      """
      set blue <=> set color=blue
      """
      return [("color", key)]
    if key in anchor_list and value is True:
      return [("anchor", key)]
    if key in short_anchor_dict and value is True:
      return [("anchor", short_anchor_dict[key])]
    if key == "at" and value in anchor_list:
      return [("at.anchor", value)]
    if key == "at" and value in short_anchor_dict:
      return [("at.anchor", short_anchor_dict[value])]
    if key == "at":
      raise Exception("Does not support setting node position (except anchor)")
    if key == "rc":
      key = "rounded.corners"
    if value == "False" or value == "None":
      return [(key, None)]
    if key in ["width", "height", "xshift", "yshift"]:
      value = num_to_dist(value)
    if key in ["out", "in"] and value in directions:
      return [(key, direction_to_angle(value))]
    if key in ["rectangle", "line"]:
      return [("type", key)]
    ret = [(key, value)]
    for s in WithAttributeHandler.mutually_exclusive:
      if key in s:
        ret = ret + [(k, False) for k in s if k != key]
    return ret

  def _set_object(self, obj, key_values):
    for key, value in key_values:
      if value is None or value is False:
        del_if_has(obj, key)
      else:
        obj[key] = value

  def _set_path_position(self, key, value):
    obj = self._selection.get_selected_path_item()
    key_values = self._process_key_value(key, value)
    self._before_change()
    if key in ["xshift", "yshift", "anchor"]:
      if is_type(obj, "nodename"):
        self._set_object(obj, key_values)
      else:
        raise Exception("Can only shift node name")
    elif key in ["x", "y"]:
      if is_type(obj, "coordinate"):
        self._set_object(obj, key_values)
      else:
        raise Exception("Can only set x, y of coordinate")
    elif key in ["in"]:
      obj = self._selection.previous_line()
      if obj is None:
        raise Exception("Cannot set 'in' of a position not at end of line")
      self._set_object(obj, key_values)
    else:
      obj = self._selection.next_line()
      if obj is None:
        raise Exception("Cannot find segment following the position")
      self._set_object(obj, key_values)
    self._after_change()

  def _set_selected_objects(self, key, value):
    if self.is_in_path_position_mode():
      self._set_path_position(key, value)
      return
    self._before_change()
    key_values = self._process_key_value(key, value)
    for obj in self._selection.get_selected_objects():
      self._set_object(obj, key_values)
    self._after_change()

  def _set_fill(self, *args):
    color = None
    for t, v in args:
      if t == "command":
        color = v
    self._set_selected_objects("fill", color)

  def _make(self, *args):
    obj = "path"
    arrow = None
    for t, v in args:
      if t == "command":
        if v == "rect" or v == "r":
          obj = "rect"
        elif v == "path" or v == "p":
          obj = "path"
        elif v == "->":
          arrow = "stealth"
        elif v == "<-":
          arrow = "reversed.stealth"
        elif v == "<->":
          arrow = "double.stealth"

    if obj == "path":
      if len(self._marks) < 2:
        raise Exception(f"Expect at least two marks")
      self._before_change()
      items = []
      for i, mark in enumerate(self._marks):
        items.append(mark)
        if i < len(self._marks) - 1:
          items.append(create_line())
      self._context._picture.append(create_path(items, arrow))
      self._after_change()

    elif obj == "rect":
      if self._visual_start is not None:
        self._before_change()
        self._context._picture.append(create_path([
            create_coordinate(*self._visual_start),
            create_rectangle(),
            create_coordinate(*self._get_pointer_pos()),
        ]))
        self._after_change()
      elif len(self._marks) == 2:
        self._before_change()
        self._context._picture.append(create_path([
            self._marks[0],
            create_rectangle(),
            self._marks[1],
        ]))
        self._after_change()
      else:
        raise Exception("Please set exactly two marks "
                        "or draw a rect in visual mode")

    else:
      raise Exception("Unknown object type")

  def _connect_objects_by_ids(self, ids, *args):
    assert len(ids) >= 2
    arrow, annotates = "", [""] * (len(ids) - 1)
    anchors = [""] * len(ids)
    pairs = [(0, i) for i in range(1, len(ids))]
    action = "line"
    start_out, close_in = "", ""
    for t, v in args:
      if t == "command":
        if v in arrow_symbols:
          arrow = f"with.{arrow_symbols[v]}"
        elif v == "h":
          action = "line.horizontal"
        elif v == "v":
          action = "line.vertical"
        elif v == "chain":
          pairs = [(i-1, i) for i in range(1, len(ids))]
        elif v in anchor_list or v in short_anchor_dict:
          if v in short_anchor_dict:
            v = short_anchor_dict[v]
          for j in range(len(anchors)):
            if anchors[j] == "":
              anchors[j] = f".{v}"
              break
        elif v.startswith("out="):
          start_out = f"start.out.{v[4:]}"
        elif v.startswith("in="):
          close_in = f"close.in.{v[3:]}"
      elif t == "text" and len(v) > 0:
        for j in range(len(annotates)):
          if annotates[j] == "":
            annotates[j] = f"with.annotate '{v}'"
            break
    for id_ in ids:
      self._ensure_name_is_id(id_)
    for k, pair in enumerate(pairs):
      i, j = pair
      id1, id2 = ids[i], ids[j]
      anchor1, anchor2 = anchors[i], anchors[j]
      annotate = annotates[k]
      self._parse(f"draw {arrow} from.{id1}{anchor1} "
                  f"{action}.to.{id2}{anchor2} "
                  f"{start_out} {close_in} {annotate}")

  def _connect_mark_with_objects_by_ids(self, mark, ids, *args):
    if mark["type"] == "coordinate":
      start_point = f"x.{mark['x']}.y.{mark['y']}"
    elif mark["type"] == "nodename":
      start_point = f"move.to.{mark['name']}"
      if "anchor" in mark:
        start_point += f".{mark['anchor']}"
      if "xshift" in mark:
        xshift = mark["xshift"]
        if xshift.startswith("-"):
          start_point += f" shifted.left.by.{xshift[1:]}"
        else:
          start_point += f" shifted.right.by.{xshift}"
      if "yshift" in mark:
        yshift = mark["yshift"]
        if yshift.startswith("-"):
          start_point += f" shifted.down.by.{yshift[1:]}"
        else:
          start_point += f" shifted.up.by.{yshift}"
    else:
      raise Exception(f"Unknown mark type: {mark['type']}")

    action, anchor = "line", ""
    start_out, close_in = "", ""
    arrow = ""
    annotates = []
    for t, v in args:
      if t == "command":
        if v in arrow_symbols:
          arrow = f"with.{arrow_symbols[v]}"
        elif v == "h":
          action = "line.horizontal"
        elif v == "v":
          action = "line.vertical"
        elif v in anchor_list:
          anchor = f".{v}"
        elif v in short_anchor_dict:
          anchor = f".{short_anchor_dict[v]}"
        elif v.startswith("out="):
          start_out = f"start.out.{v[4:]}"
        elif v.startswith("in="):
          close_in = f"close.in.{v[3:]}"
      elif t == "text" and len(v) > 0:
        annotates.append(f"with.annotate '{v}'")
    for id_ in ids:
      self._ensure_name_is_id(id_)
      self._ensure_name_is_id(id_)
      self._parse(f"draw {arrow} {start_point} "
                  f"{action}.to.{id_}{anchor} "
                  f"{start_out} {close_in} {' '.join(annotates)}")

  def _connect(self, *args):
    if self._selection.has_path():
      raise Exception("Cannot connect paths")
    if len(self._marks) == 0:
      if self._selection.num_ids() < 2:
        raise Exception("Should select at least two objects, "
                        "or set at least one mark")
      self._connect_objects_by_ids(self._selection.ids(), *args)
    elif len(self._marks) == 1:
      if not self._selection.has_id():
        raise Exception("Should select at least one object")
      self._connect_mark_with_objects_by_ids(self._marks[0],
                                             self._selection.ids(),
                                             *args)

  def _set_grid(self, *args):
    self._show_grid = True
    for t, v in args:
      if v == "off":
        self._show_grid = False

  def _set_axes(self, *args):
    self._show_axes = True
    for t, v in args:
      if v == "off":
        self._show_axes = False

  def _add_mark(self, *args):
    x, y = self._get_pointer_pos()
    mark = create_coordinate(x, y)
    to_del = None
    for t, v in args:
      if t == "command":
        if v in anchor_list or v in short_anchor_dict:
          if self._selection.num_ids() > 2:
            raise Exception("Cannot mark more than two object anchors")
          if not self._selection.has_id():
            raise Exception("Please select one or two objects")
          if self._selection.single_id():
            id_ = self._selection.get_single_id()
            self._ensure_name_is_id(id_)
            mark = {
                "type": "nodename",
                "name": id_,
                "anchor": v if v in anchor_list else short_anchor_dict[v],
            }
          else:
            id1, id2 = self.get_two_ids()
            self._ensure_name_is_id(id1)
            self._ensure_name_is_id(id2)
            if is_type(mark, "coordinate"):
              mark = {
                  "type": "intersection",
                  "name1": id1,
                  "name2": id2,
                  "anchor1": v if v in anchor_list else short_anchor_dict[v],
              }
            elif is_type(mark, "intersection"):
              mark["anchor2"] = v if v in anchor_list else short_anchor_dict[v]
            else:
              raise Exception(f"Unexpected mark type {mark['type']}")
        elif v == "shift":
          if mark["type"] != "nodename":
            raise Exception("Please specify anchor before shift")
          anchor = mark["anchor"]
          bb = self._bounding_boxes[mark["name"]]
          pointerx, pointery = self._get_pointer_pos()
          anchorx, anchory = bb.get_anchor_pos(anchor)
          xshift = pointerx - anchorx
          yshift = pointery - anchory
          if xshift != 0:
            mark["xshift"] = num_to_dist(xshift)
          if yshift != 0:
            mark["yshift"] = num_to_dist(yshift)
        elif v == "relative" or v == "rel":
          if mark["type"] != "coordinate":
            raise Exception("Do not specify anchor")
          x0, y0 = self._get_mark_pos(len(self._marks)-1, {})
          pointerx, pointery = self._get_pointer_pos()
          xshift = pointerx - x0
          yshift = pointery - y0
          mark["x"] = num_to_dist(xshift)
          mark["y"] = num_to_dist(yshift)
          mark["relative"] = True
        elif v == "clear":
          self._marks = []
          return
        elif v == "del":
          to_del = len(self._marks) - 1
        elif re.match(r"\d+$", v):
          if to_del is None:
            raise Exception("Add del command before specifying the index")
          to_del = int(v)
          if to_del >= len(self._marks):
            raise Exception("Index too large")
        elif v == "cycle":
          if len(self._marks) == 0:
            raise Exception("No marks set yet")
          mark = {"type": "cycle"}
        else:
          raise Exception(f"Unknown argument {v}")
    if to_del is not None:
      del self._marks[to_del]
    else:
      self._marks.append(mark)

  def _annotate(self, *args):
    if self._selection.num_paths() > 1:
      raise Exception("Cannot annotate more than one paths")
    if not self._selection.has_path():
      raise Exception("Please select one path")
    path = self.get_single_path()
    lines = [item for item in path["items"] if item["type"] == "line"]
    if len(lines) == 0:
      raise Exception("Selected path does not have any lines")
    index, text = 0, ""
    for t, v in args:
      if t == "command":
        if re.match(r"\d+$", v):
          index = int(v)
          if index >= len(lines):
            raise Exception("Line index exceeds the maximal number")
      elif t == "text":
        text = v

    line = lines[index]
    self._before_change()
    if "annotates" not in line:
      line["annotates"] = []
    line["annotates"].append({
        "id": self._context.getid(),
        "type": "text",
        "in_path": True,
        "text": v,
        "midway": True,
        "above": True,
        "sloped": True,
        "scale": "0.7",
    })
    self._after_change()

  def _chain(self, *args):
    if self._selection.num_ids() < 2:
      raise Exception("Please select at least two objects")

    direction = "horizontal"

    for t, v in args:
      if t == "command":
        if v == "h":
          direction = "horizontal"
        elif v == "v":
          direction = "vertical"
        elif v == "\\":
          direction = "down right"
        elif v == "/":
          direction = "down left"

    self._before_change()
    for i in range(1, self._selection.num_ids()):
      id_ = self._selection.get_id(i)
      obj = self._find_object_by_id(id_)
      obj["at"] = self_selection.get_id(i-1)
      if direction == "horizontal":
        obj["at.anchor"] = "east"
        obj["anchor"] = "west"
      elif direction == "vertical":
        obj["at.anchor"] = "south"
        obj["anchor"] = "north"
      elif direction == "down right":
        obj["at.anchor"] = "south.east"
        obj["anchor"] = "north.west"
      elif direction == "down left":
        obj["at.anchor"] = "south.west"
        obj["anchor"] = "north.east"
    self._after_change()

  def _search(self, *args):
    self._selection.search(*args)

  def _read(self, *args):
    filename = None
    for t, v in args:
      if t == "command":
        filename = v
    with open(filename) as f:
      data = json.loads(f.read())

    self._before_change()
    if "picture" in data:
      self._context._picture = data["picture"]
    if "nextid" in data:
      self._context._state["nextid"] = data["nextid"]
    self._after_change()

  def _save_as_object(self, *args):
    object_name = None
    for t, v in args:
      if t == "command":
        object_name = v
    if self._selection.nonempty():
      data = json.dumps([obj for obj in self._context._picture
                         if self._selection.selected(obj)])
    else:
      data = json.dumps(self._context._picture)
    with open(self._get_object_path(object_name), "w") as f:
      f.write(data)

  def _read_object(self, *args):
    object_name = None
    for t, v in args:
      if t == "command":
        object_name = v
    with open(self._get_object_path(object_name)) as f:
      data = json.loads(f.read())
    self._before_change()
    self._paste_data(data, True)
    self._after_change()

  def _paste_data(self, data, check_all_relative_pos=False,
                  bounding_boxes=None):
    if len(data) == 0:
      return
    pos = get_first_absolute_coordinate(data)
    if pos is None:
      if check_all_relative_pos:
        raise Exception("All copied objects have relative positions")
      if bounding_boxes is None:
        raise Exception("Must provide the bounding boxes "
                        "if not check relative positions")
      pos = get_top_left_corner(data, bounding_boxes)
    x0, y0 = pos
    x1, y1 = self._get_pointer_pos()
    dx, dy = x1 - x0, y1 - y0
    old_to_new_id_dict = {}
    to_replace = []
    for obj in data:
      id_ = get_default(obj, "id")
      if id_ is not None:
        new_id = self._context.getid()
        old_to_new_id_dict[id_] = new_id
        at = get_default(obj, "at")
        obj["id"] = new_id
        obj["name"] = new_id
        if at is None:
          obj["at"] = create_coordinate(dx, dy)
        elif is_type(at, "coordinate"):
          assert not get_default(at, "relative", False)
          add_to_key(at, "x", dx)
          add_to_key(at, "y", dy)
        elif isinstance(at, str):
          to_replace.append((obj, "at"))
        elif is_type(at, "intersection"):
          assert "name1" in at and "name2" in at
          to_replace.append((at, "name1"))
          to_replace.append((at, "name2"))
      elif is_type(obj, "path"):
        for item in obj["items"]:
          id_ = get_default(item, "id")
          if id_ is not None:
            new_id = self._context.getid()
            old_to_new_id_dict[id_] = new_id
            item["id"] = new_id
          if is_type(item, "nodename"):
            to_replace.append((item, "name"))
          elif is_type(item, "intersection"):
            to_replace.append((item, "name1"))
            to_replace.append((item, "name2"))
          elif is_type(item, "coordinate"):
            if not get_default(item, "relative", False):
              add_to_key(item, "x", dx)
              add_to_key(item, "y", dy)
          elif "annotates" in item:
            annotates = item["annotates"]
            for annotate in annotates:
              id_ = get_default(annotate, "id")
              if id_ is not None:
                new_id = self._context.getid()
                old_to_new_id_dict[id_] = new_id
                annotate["id"] = new_id
      else:
        raise Exception(f"Find an object that is neither object with id, "
                        f"nor path: {obj}")
      self._context._picture.append(obj)

    for item, key in to_replace:
      if key not in item:
        """
        This is possible because this object might have been modified
        """
        continue
      old_id = item[key]
      if old_id in old_to_new_id_dict:
        item[key] = old_to_new_id_dict[old_id]
      elif check_all_relative_pos:
        raise Exception(f"Object {item} refers to "
                        f"an id {old_id} that is not copied")
      elif is_type(item, "nodename"):
        """
        We get a nodename item in a path that refers to an id
        that is not copied. In this case, we replace it with an
        absolute position.
        """
        if bounding_boxes is None:
          raise Exception("Must provide the bounding boxes "
                          "if not check relative positions")
        bb = bounding_boxes[old_id]
        anchor = get_default(item, "anchor", "center")
        x, y = bb.get_anchor_pos(anchor)
        """
        We can only modify 'item' in place, because we cannot
        overwrite item itself without knowing where it is pointed from
        """
        clear_dict(item)
        item["type"] = "coordinate"
        item["x"] = num_to_dist(x + dx)
        item["y"] = num_to_dist(y + dy)
      elif is_type(item, "intersection"):
        if bounding_boxes is None:
          raise Exception("Must provide the bounding boxes "
                          "if not check relative positions")
        bb = bounding_boxes[old_id]
        """
        key is "name1" or "name2", and the key for anchor is respectively
        "anchor1" "anchor2"
        """
        anchor = get_default(item, f"anchor{key[4]}", "center")
        x, y = bb.get_anchor_pos(anchor)
        """
        We can only modify 'item' in place, because we cannot overwrite item
        itself without knowing where it is pointed from
        """
        clear_dict(item)
        item["type"] = "coordinate"
        item["x"] = num_to_dist(x + dx)
        item["y"] = num_to_dist(y + dy)
      elif get_default_of_type(item, "at", str) is not None:
        """
        Same as before: replace the relative position with absolute coordinate.
        """
        if bounding_boxes is None:
          raise Exception("Must provide the bounding boxes "
                          "if not check relative positions")
        bb = bounding_boxes[old_id]
        anchor = get_default(item, "at.anchor", "center")
        x, y = bb.get_anchor_pos(anchor)
        item["at"] = create_coordinate(x + dx, y + dy)
        del_if_has(item, "at.anchor")
      else:
        raise Exception("This branch should not be reached at all, "
                        "unless something is wrong")

  def _get_object_path(self, name):
    if not os.path.exists(self._object_path):
      os.mkdir(self._object_path)
    return os.path.join(self._object_path, f"{name}.json")

  def _read_command_history(self):
    path = os.path.join(self._object_path, "history")
    try:
      with open(path) as f:
        history = f.read()
    except Exception:
      return []
    return history.split("\n")

  def _save_command_history(self, history):
    path = os.path.join(self._object_path, "history")
    if not os.path.exists(self._object_path):
      os.mkdir(self._object_path)
    with open(path, "w") as f:
      f.write("\n".join(history))

  def _execute_python_code(self):
    self._before_change()
    with open("/tmp/english2tikz.py") as f:
      code = f.read()
    selected_objects = self._selection.get_selected_id_objects()
    selected_paths = self._selection.paths()
    exec(code, locals())
    self._after_change()

  def _edit_python_code(self):
    if not os.path.exists("/tmp/english2tikz.py"):
      with open("/tmp/english2tikz.py", "w") as f:
        f.write(r"""# Available local variables:
# selected_objects: list, objects with ids
# selected_paths: list, paths
""")
    os.system("open -a 'Sublime Text' /tmp/english2tikz.py")

  def _execute_describeit_code(self):
    self._before_change()
    with open("/tmp/english2tikz.desc") as f:
      code = f.read()
    ctx = self._context
    ctx._state["refered_to"] = self._selection.get_selected_objects()
    for i, id_ in enumerate(self._selection.ids()):
      code = code.replace(f"{{#{i}}}", id_)
    x, y = self._get_pointer_pos_str()
    code = code.replace(f"{{#x}}", x)
    code = code.replace(f"{{#y}}", y)
    ctx.parse(code)
    self._after_change()

  def _edit_describeit_code(self):
    if not os.path.exists("/tmp/english2tikz.desc"):
      with open("/tmp/english2tikz.desc", "w") as f:
        f.write("### Write the describe it code here ###")
    os.system("open -a 'Sublime Text' /tmp/english2tikz.desc")

  def _dump(self):
    tikzcode = self._context.render()
    tikzimage(tikzcode)
    os.system("open ./view/view.png")
