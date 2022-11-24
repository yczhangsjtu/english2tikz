import os
import re
import json
import copy
import string
import traceback
from functools import partial
from contextlib import contextmanager


from english2tikz.utils import *
from english2tikz.describe_it import DescribeIt
from english2tikz.handlers import WithAttributeHandler, DirectionOfHandler
from english2tikz.latex import tikzimage
from english2tikz.errors import *
from english2tikz.gui.canvas_manager import CanvasManager
from english2tikz.gui.keyboard import KeyboardManager
from english2tikz.gui.text_editor import TextEditor
from english2tikz.gui.selection import Selection
from english2tikz.gui.finding import Finding
from english2tikz.gui.coordinate_system import CoordinateSystem
from english2tikz.gui.command_line import CommandLine
from english2tikz.gui.pointer import Pointer
from english2tikz.gui.mark import MarkManager
from english2tikz.gui.visual import Visual
from english2tikz.gui.command_parse import Parser
from english2tikz.gui.suggest import Suggest


class Editor(object):
  def __init__(self, root, canvas, screen_width, screen_height,
               picture=None, object_path=".english2tikz"):
    self._root = root
    self._object_path = os.path.join(os.getenv("HOME"), object_path)
    self._context = DescribeIt()
    if picture is not None:
      self._context._picture = picture
    self._error_msg = None
    self._pointer = Pointer(CoordinateSystem(screen_width, screen_height, 100))
    self._obj_to_edit_text = None
    self._editing_text = None
    self._editing_text_pos = None
    self._command_line = CommandLine(self._object_path)
    self._history = [self._context._picture]
    self._history_index = 0
    self._visual = Visual(self._pointer)
    self._marks = MarkManager()
    self._clipboard = []
    self._finding = None
    self._command_refreshing_timer_started = True
    self._editing_refreshing_timer_started = True
    self.filename = None
    self._selection = Selection(self._context)
    self._suggest = Suggest(self)
    self._keyboard_managers = {
        "normal": KeyboardManager(),
        "visual": KeyboardManager(),
        "editing": KeyboardManager(),
        "command": KeyboardManager(),
        "finding": KeyboardManager(),
        "preview": KeyboardManager(),
        "suggest": KeyboardManager(),
    }
    self._canvas_manager = CanvasManager(root, canvas,
                                         screen_width, screen_height, self)
    root.bind("<Key>", self.handle_key)
    self._register_keys()

  def register_key(self, mode, key, f):
    self._keyboard_managers[mode].bind(key, f)

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
    self.register_key("normal", "Ctrl-h",
                      partial(self._shift_selected_object_at_anchor, "left"))
    self.register_key("normal", "Ctrl-j",
                      partial(self._shift_selected_object_at_anchor, "down"))
    self.register_key("normal", "Ctrl-k",
                      partial(self._shift_selected_object_at_anchor, "up"))
    self.register_key("normal", "Ctrl-l",
                      partial(self._shift_selected_object_at_anchor, "right"))
    self.register_key("normal", "Ctrl-a",
                      partial(self._shift_selected_object_anchor, "left"))
    self.register_key("normal", "Ctrl-s",
                      partial(self._shift_selected_object_anchor, "down"))
    self.register_key("normal", "Ctrl-w",
                      partial(self._shift_selected_object_anchor, "up"))
    self.register_key("normal", "Ctrl-d",
                      partial(self._shift_selected_object_anchor, "right"))
    self.register_key("normal", "s", self._enter_or_exit_suggest_mode)
    for c in string.ascii_uppercase:
      self.register_key("normal", f"Ctrl-{c}",
                        partial(self._take_suggestion, c))
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
    self.register_key("visual", "G", self._reset_pointer_to_origin)
    self.register_key("visual", "Ctrl-g", partial(self._change_grid_size, 1))
    self.register_key("visual", "Ctrl-f", partial(self._change_grid_size, -1))
    self.register_key("visual", "s", self._enter_or_exit_suggest_mode)
    for c in string.ascii_uppercase:
      self.register_key("visual", f"Ctrl-{c}",
                        partial(self._take_suggestion, c))
    self.register_key("finding", "Printable", self._finding_narrow_down)
    self.register_key("finding", "BackSpace", self._finding_back)
    self.register_key("finding", "Ctrl-c", self._exit_finding_mode)
    self.register_key("preview", "Ctrl-c", self._exit_preview)

  @contextmanager
  def _modify_picture(self):
    self._history = self._history[:self._history_index+1]
    self._history[self._history_index] = copy.deepcopy(
        self._history[self._history_index])
    yield
    self._history.append(self._context._picture)
    self._history_index = len(self._history) - 1

  def _undo(self):
    if self._has_suggest():
      self._suggest.revert()
      return
    if self._history_index == 0:
      self._error_msg = "Already the oldest"
      return

    self._history_index -= 1
    self._context._picture = self._history[self._history_index]

  def _redo(self):
    if self._has_suggest():
      self._suggest.redo()
      return
    if self._history_index >= len(self._history) - 1:
      self._error_msg = "Already at newest change"
      return
    self._history_index += 1
    self._context._picture = self._history[self._history_index]

  def handle_key(self, event):
    try:
      self._keyboard_managers[self._get_mode()].handle_key(event)
    except ErrorMessage as e:
      self._error_msg = f"Error: {e}"
    except Exception as e:
      self._error_msg = f"Error: {e}"
      traceback.print_exc()

    if self._has_suggest():
      self._suggest._propose_suggestions()
    self._canvas_manager.draw()

  def _scroll(self, dx, dy):
    self._pointer.scroll(dx, dy)

  def _set_position_to_mark(self):
    if self._is_in_path_position_mode():
      if self._marks.single():
        with self._modify_picture():
          self._selection.set_selected_path_item(self._marks.get_single())
      else:
        self._error_msg = "Can only set position to one mark"
    else:
      self._error_msg = "Not in path position mode"

  def _insert_char_to_edit(self, c):
    self._editing_text.insert(c)
    self._editing_refreshing_timer_started = False

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
    self._command_refreshing_timer_started = False
    self._command_line.insert(c)

  def _delete_char_from_edit(self):
    self._editing_text.delete()
    self._editing_refreshing_timer_started = False

  def _delete_char_from_command(self):
    self._command_refreshing_timer_started = False
    self._command_line.delete()

  def _move_command_cursor(self, offset):
    self._command_line.move_cursor(offset)

  def _move_command_cursor_start(self):
    self._command_line.move_to_start()

  def _move_command_cursor_end(self):
    self._command_line.move_to_end()

  def _is_in_command_mode(self):
    return self._command_line.active()

  def _is_in_editing_mode(self):
    return self._editing_text is not None

  def _is_in_visual_mode(self):
    return self._visual.active()

  def _is_in_finding_mode(self):
    return self._finding is not None

  def _is_in_normal_mode(self):
    return (not self._is_in_command_mode() and
            not self._is_in_editing_mode() and
            not self._is_in_visual_mode() and
            not self._is_in_finding_mode() and
            not self._is_in_preview_mode())

  def _is_in_preview_mode(self):
    return self._canvas_manager._preview is not None

  def _has_suggest(self):
    return self._suggest.active()

  def _get_mode(self):
    if self._is_in_command_mode():
      return "command"
    if self._is_in_editing_mode():
      return "editing"
    if self._is_in_visual_mode():
      return "visual"
    if self._is_in_finding_mode():
      return "finding"
    if self._is_in_preview_mode():
      return "preview"
    if self._is_in_normal_mode():
      return "normal"
    raise ValueError("Invalid mode")

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
      self._insert_text_following_id(self._selection.get_single_id(),
                                     direction)

  def _enter_edit_mode_at_visual(self):
    self._create_node_at_visual()
    self._exit_visual_mode()

  def _exit_editing_mode(self):
    self._editing_refreshing_timer_started = False
    if self._obj_to_edit_text is None:
      if len(self._editing_text) > 0:
        x, y = self._pointer.posstr()
        self._parse(f"""there.is.text "{self._editing_text}" at.x.{x}.y.{y}
                        with.align=left""")
    else:
      with self._modify_picture():
        self._obj_to_edit_text["text"] = str(self._editing_text)
    self._editing_text = None

  def _enter_command_mode(self):
    self._command_line.activate()
    self._clear_error_message()

  def _enter_command_mode_and_search(self):
    self._command_line.activate("search ")
    self._clear_error_message()

  def _exit_command_mode(self):
    self._command_refreshing_timer_started = False
    self._command_line.exit()

  def _execute_command(self):
    try:
      self._process_command(str(self._command_line))
    finally:
      self._exit_command_mode()

  def _fetch_previous_command(self):
    self._command_refreshing_timer_started = False
    self._command_line.fetch_previous()

  def _fetch_next_command(self):
    self._command_refreshing_timer_started = False
    self._command_line.fetch_next()

  def _external_editor_for_command(self):
    """
    It is very inconvenient to edit text in our tool, and I'm too lazy
    to implement a powerful text editor or using the tkinter text field.
    So press Ctrl+o to open an external editor for assistance.
    """
    if not self._command_refreshing_timer_started:
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
    if not self._editing_refreshing_timer_started:
      self._start_timer_for_refreshing_editing()
    with open("/tmp/editing", "w") as f:
      f.write(str(self._editing_text))
    os.system(f"open -a 'Sublime Text' /tmp/editing")

  def _enter_visual_mode(self):
    x, y = self._pointer.pos()
    self._visual.activate(x, y)

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
    self._visual.clear()

  def _exit_preview(self):
    self._canvas_manager._preview = None

  def _enter_or_exit_suggest_mode(self):
    if self._suggest.active():
      self._fix_suggestion()
    else:
      self._suggest.activate()

  def _take_suggestion(self, code):
    if self._has_suggest():
      self._suggest.take_suggestion(code)
    else:
      raise ErrorMessage("Suggestion mode is not on. Press s.")

  def _fix_suggestion(self):
    new_objects = self._suggest.fix()
    if len(new_objects) == 0:
      raise ErrorMessage("No suggestion is taken.")
    self._context._picture += new_objects

  def _exit_suggest_mode(self):
    self._suggest.shutdown()

  def _deselect(self):
    if self._selection.deselect():
      return
    if not self._marks.empty():
      self._marks.clear()
      return
    self._suggest.shutdown()

  def _delete_selected_objects(self):
    with self._modify_picture():
      if self._selection.has_id():
        deleted_ids = []
        for id_ in self._selection.ids():
          self._context.delete_objects_related_to_id(id_, deleted_ids)
      if self._selection.has_path():
        for path in self._selection.paths():
          self._context.delete_path(path)
    self._selection.clear()

  def _copy_selected_objects(self):
    self._clipboard = [copy.deepcopy(obj)
                       for obj in self._context._picture
                       if self._selection.selected(obj)]

  def _parse(self, code):
    with self._modify_picture():
      self._context.parse(code)

  def _add_simple_mark(self):
    if self._is_in_path_position_mode():
      self._marks.add(self._selection.get_path_position())
    else:
      x, y = self._pointer.pos()
      self._marks.add_coord(x, y)

  def _start_timer_for_refreshing_command(self):
    self._command_refreshing_timer_started = True
    self._root.after(100, self._refresh_command)

  def _refresh_command(self):
    if not self._command_refreshing_timer_started:
      return
    if self._command_line is None:
      self._command_refreshing_timer_started = False
      return
    try:
      with open("/tmp/command") as f:
        self._command_line.set(f.read())
    except ErrorMessage as e:
      self._error_msg = f"Failed to refresh command: {e}"
    except Exception as e:
      self._error_msg = f"Failed to refresh command: {e}"
      self._command_refreshing_timer_started = False
      traceback.print_exc()
    self._root.after(100, self._refresh_command)
    self._canvas_manager.draw()

  def _start_timer_for_refreshing_editing(self):
    self._editing_refreshing_timer_started = True
    self._root.after(100, self._refresh_editing)

  def _refresh_editing(self):
    if not self._editing_refreshing_timer_started:
      return
    if self._editing_text is None:
      self._editing_refreshing_timer_started = False
      return
    try:
      with open("/tmp/editing") as f:
        self._editing_text.set(f.read())
        self._editing_text.move_to_end()
    except ErrorMessage as e:
      self._error_msg = f"Failed to refresh editing: {e}"
    except Exception as e:
      self._error_msg = f"Failed to refresh editing: {e}"
      self._editing_refreshing_timer_started = False
      traceback.print_exc()
    self._root.after(100, self._refresh_editing)
    self._canvas_manager.draw()

  def _finding_narrow_down(self, char):
    try:
      obj = self._finding.narrow_down(char)
    finally:
      self._exit_finding_mode()
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
    self._visual.clear()
    self._marks.clear()
    self._clear_selects()

  def _clear_selects(self):
    self._selection.clear()

  def _change_grid_size(self, by):
    self._pointer.change_grid_size(by)

  def _is_in_path_position_mode(self):
    return self._selection.is_in_path_position_mode()

  def _enter_finding_mode(self, toggle=False):
    candidate_ids, candidate_paths = self._canvas_manager.find_all_in_screen()
    candidates = candidate_ids + candidate_paths
    candidates_number = len(candidates)
    self._finding = Finding(candidates, toggle)

  def _get_selected_id_objects(self):
    return self._selection.get_selected_id_objects()

  def _get_selected_objects(self):
    return self._selection.get_selected_objects()

  def _shift_selected_object_at_anchor(self, direction):
    with self._modify_picture():
      for id_ in self._selection.ids():
        if not self._context.shift_object_at_anchor(id_, direction):
          self._error_msg = f"Object {id_} is not anchored to " \
              "another object, nor at intersection"

  def _shift_selected_object_anchor(self, direction):
    with self._modify_picture():
      for id_ in self._selection.ids():
        self._context.shift_object_anchor(id_, direction)

  def _jump_to_next_selected(self, by):
    if self._selection.jump_to_next_selected(by):
      self._jump_to_select()

  def _reset_pointer_to_origin(self):
    self._pointer.reset_to_origin()

  def _create_node_at_visual(self):
    x0, y0, x1, y1 = self._visual.ordered_rect()
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
    x0, _ = self._canvas_manager._bounding_boxes[id0].get_anchor_pos("center")
    _, y0 = self._canvas_manager._bounding_boxes[id1].get_anchor_pos("center")
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
    with self._modify_picture():
      annotates.append(annotate)
    self._obj_to_edit_text = annotate
    self._editing_text_pos = self._pointer.pos()
    self._editing_text = TextEditor()

  def _start_edit_text(self, id_=None):
    if id_ is None:
      self._editing_text = TextEditor()
      self._obj_to_edit_text = None
      self._editing_text_pos = self._pointer.pos()
      return

    self._obj_to_edit_text = self._context.find_object_by_id(id_)
    if self._obj_to_edit_text is None:
      self._error_msg = f"Cannot find object with id {id_}"
      return

    if "text" not in self._obj_to_edit_text:
      self._error_msg = f"The selected object {id_} does not support text."
      return

    self._editing_text = TextEditor(self._obj_to_edit_text["text"])
    bb = self._canvas_manager._bounding_boxes[id_]
    self._editing_text_pos = bb.get_anchor_pos("center")

  def _ensure_name_is_id(self, id_):
    obj = self._context.find_object_by_id(id_)
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
      raise ValueError(f"Unknown direction: {direction}")

    self._ensure_name_is_id(id_)
    self._parse(f"there.is.text '' with.{anchor}.at.{at_anchor}.of.{id_}")
    self._obj_to_edit_text = self._context._picture[-1]
    self._editing_text = TextEditor()
    bb = self._canvas_manager._bounding_boxes[id_]
    self._editing_text_pos = bb.get_anchor_pos(at_anchor)
    self._selection.select(self._obj_to_edit_text)

  def _shift_selected_objects(self, dx, dy):
    if self._selection.has_id():
      with self._modify_picture():
        for id_ in self._selection.ids():
          shift_object(self._context.find_object_by_id(id_),
                       dx, dy, self._pointer.grid_size())
    elif self._selection.is_in_path_position_mode():
      with self._modify_picture():
        shift_path_position(self._selection.get_path_position(), dx, dy,
                            self._pointer.grid_size())

  def _shift_selected_objects_by_grid(self, dx, dy):
    return self._shift_selected_objects(dx * self._pointer.grid_size(),
                                        dy * self._pointer.grid_size())

  def _select_targets(self, mode="clear"):
    sel = self._visual.ordered_rect()
    items = []
    for id_, bb in self._canvas_manager._bounding_boxes.items():
      if bb.intersect_rect(sel):
        if id_.startswith("segment_"):
          items.append(bb._obj)
        else:
          items.append(id_)
    self._selection.update(mode, *items)

  def _paste(self):
    if len(self._clipboard) == 0:
      return
    with self._modify_picture():
      self._context.paste_data(copy.deepcopy(self._clipboard),
                               *self._pointer.pos(),
                               False, self._canvas_manager._bounding_boxes)

  def _jump_to_select(self):
    id_ = self._selection.id_to_jump()
    if id_ not in self._canvas_manager._bounding_boxes:
      return
    bb = self._canvas_manager._bounding_boxes[id_]
    x, y = bb.get_anchor_pos("center")
    self._pointer.goto(x, y)

  def _move_pointer(self, x, y):
    self._pointer.move_by(x, y)

  def _move_pointer_by_inverse_grid_size(self, x, y):
    self._pointer.move_by_inverse_grid_size(x, y)

  def _move_pointer_to_screen_boundary(self, direction):
    self._pointer.move_to_boundary(direction)

  def _save(self):
    if len(self._context._picture) == 0:
      x0, y0, x1, y1 = 0, 0, 0, 0
    else:
      x0, y0, x1, y1 = get_bounding_box(self._context._picture,
                                        self._canvas_manager._bounding_boxes)
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
    self._canvas_manager.draw()

  def _fix_id_and_names(self):
    for item in self._context._picture:
      id_ = get_default(item, "id")
      if id_ is not None:
        item["name"] = id_

  def _process_command(self, cmd):
    self._command_line.append(cmd)
    cmd_name, code = Parser.split_name_args(cmd)
    if cmd_name == "set":
      self._set(code)
    elif cmd_name == "unset" or cmd_name == "un":
      self._unset(code)
    elif cmd_name == "fill" or cmd_name == "f":
      self._set_fill(code)
    elif cmd_name in anchor_list:
      self._set(cmd_name)
    elif cmd_name == "make" or cmd_name == "mk":
      self._make(code)
    elif cmd_name == "rect":
      self._make(f"rect {code}")
    elif cmd_name == "path":
      self._make(f"path {code}")
    elif cmd_name == "cn" or cmd_name == "connect":
      self._connect(code)
    elif cmd_name == "grid" or cmd_name == "g":
      self._set_grid(code)
    elif cmd_name == "axes" or cmd_name == "a":
      self._set_axes(code)
    elif cmd_name == "mark" or cmd_name == "m":
      self._add_mark(code)
    elif cmd_name == "attr":
      self._show_attributes = not self._show_attributes
    elif cmd_name == "ann" or cmd_name == "annotate":
      self._annotate(code)
    elif cmd_name == "ch" or cmd_name == "chain":
      self._chain(code)
    elif cmd_name == "search":
      self._search(code)
    elif cmd_name == "read":
      self._read(code)
    elif cmd_name == "w":
      self._write(code)
    elif cmd_name == "sao":
      self._save_as_object(code)
    elif cmd_name == "export":
      self._export(code)
    elif cmd_name == "ro":
      self._read_object(code)
    elif cmd_name == "q":
      self._canvas_manager._end = True
      self._root.after(100, self._root.destroy())
    elif cmd_name == "py":
      self._execute_python_code()
    elif cmd_name == "epy":
      self._edit_python_code()
    elif cmd_name == "eg":
      self._execute_describeit_code()
    elif cmd_name == "eeg":
      self._edit_describeit_code()
    elif cmd_name == "view":
      self._view()
    else:
      raise ErrorMessage(f"Unkown command: {cmd_name}")

  def _set(self, code):
    if self._selection.empty():
      raise ErrorMessage("No object selected")
    parser = Parser()
    parser.require_arg("text", 1)
    parser.require_arg("color", 1)
    parser.require_arg("width", 1)
    parser.require_arg("height", 1)
    parser.require_arg("line.height", 1)
    parser.require_arg("fill", 1)
    args = parser.parse(code)
    with self._modify_picture():
      for key, value in args.items():
        self._set_selected_objects(key, value)

  def _unset(self, code):
    if self._selection.empty():
      raise ErrorMessage("No object selected")
    parser = Parser()
    args = parser.parse(code)
    with self._modify_picture():
      for key, _ in args.items():
        self._set_selected_objects(key, False)

  def _set_object(self, obj, key_values):
    for key, value in key_values:
      if value is None or value is False:
        del_if_has(obj, key)
      else:
        obj[key] = value

  def _set_path_position(self, key, value):
    obj = self._selection.get_selected_path_item()
    key_values = smart_key_value(key, value)
    if key in ["xshift", "yshift", "anchor"]:
      if is_type(obj, "nodename"):
        self._set_object(obj, key_values)
      else:
        raise ErrorMessage("Can only shift node name")
    elif key in ["x", "y"]:
      if is_type(obj, "coordinate"):
        self._set_object(obj, key_values)
      else:
        raise ErrorMessage("Can only set x, y of coordinate")
    elif key in ["in"]:
      obj = self._selection.previous_line()
      if obj is None:
        raise ErrorMessage("Cannot set 'in' of a position not at end of line")
      self._set_object(obj, key_values)
    else:
      obj = self._selection.next_line()
      if obj is None:
        raise ErrorMessage("Cannot find segment following the position")
      self._set_object(obj, key_values)

  def _set_selected_objects(self, key, value):
    if self._selection.is_in_path_position_mode():
      self._set_path_position(key, value)
      return
    key_values = smart_key_value(key, value)
    for obj in self._selection.get_selected_objects():
      self._set_object(obj, key_values)

  def _set_fill(self, code):
    parser = Parser()
    parser.positional("color")
    args = parser.parse(code)
    color = get_default(args, "color", None)
    if color is None:
      raise ErrorMessage("Expected a color name")
    self._set_selected_objects("fill", color)

  def _make(self, code):
    parser = Parser()
    parser.flag_group("rect", ["rect", "r"])
    parser.flag_group("path", ["path", "p"])
    parser.flag_group("arrow", ["stealth", "->", "reversed.stealth", "<-",
                                "double.stealth", "<->"])
    args = parser.parse(code)

    obj = "path"
    if "rect" in args:
      obj = "rect"
    elif "path" in args:
      obj = "path"

    arrow = get_default(args, "arrow", [None])[0]

    if obj == "path":
      with self._modify_picture():
        self._context._picture.append(self._marks.create_path(arrow))

    elif obj == "rect":
      if self._visual.active():
        with self._modify_picture():
          self._context._picture.append(self._visual.create_path())
      elif self._marks.size() == 2:
        with self._modify_picture():
          self._context._picture.append(self._marks.create_rectangle())
      else:
        raise ErrorMessage("Please set exactly two marks "
                           "or draw a rect in visual mode")
    else:
      raise ErrorMessage("Unknown object type")

  def _connect_objects_by_ids(self, ids, code):
    assert len(ids) >= 2

    parser = Parser()
    parser.flag_group("arrow", list(arrow_symbols.keys()))
    parser.flag("h")
    parser.flag("v")
    parser.flag("chain")
    parser.flag_group("anchor", anchor_list + list(short_anchor_dict.keys()))
    args = parser.parse(code)

    arrow = get_default(args, "arrow", [""])[0]
    if arrow:
      arrow = f"with.{arrow_symbols[arrow]}"

    action = "line"
    if "h" in args:
      action = "line.horizontal"
    elif "v" in args:
      action = "line.vertical"

    if "chain" in args:
      pairs = [(i-1, i) for i in range(1, len(ids))]
    else:
      pairs = [(0, i) for i in range(1, len(ids))]

    anchors = get_default(args, "anchor", [])
    anchors = [short_anchor_dict[anchor]
               if anchor in short_anchor_dict else anchor
               for anchor in anchors]
    anchors = [f".{anchor}" for anchor in anchors]
    while len(anchors) < len(ids):
      anchors.append("")

    out = get_default(args, "out", None)
    in_ = get_default(args, "in", None)
    start_out, close_in = "", ""
    if out is not None:
      start_out = f"start.out.{out}"
    if in_ is not None:
      close_in = f"close.in.{in_}"

    annotates = get_default(args, "positionals", [])
    annotates = [f"with.annotate '{v}'" for v in annotates]
    while len(annotates) < len(ids):
      annotates.append("")

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

  def _connect_mark_with_objects_by_ids(self, mark, ids, code):
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
      raise ErrorMessage(f"Unknown mark type: {mark['type']}")

    parser = Parser()
    parser.flag_group("arrow", list(arrow_symbols.keys()))
    parser.flag("h")
    parser.flag("v")
    parser.flag_group("anchor", anchor_list + list(short_anchor_dict.keys()))
    args = parser.parse(code)

    arrow = get_default(args, "arrow", [""])[0]
    if arrow:
      arrow = f"with.{arrow_symbols[arrow]}"

    action = "line"
    if "h" in args:
      action = "line.horizontal"
    elif "v" in args:
      action = "line.vertical"

    anchor = get_default(args, "anchor", [""])[0]
    anchor = (short_anchor_dict[anchor]
              if anchor in short_anchor_dict else anchor)
    anchor = f".{anchor}" if anchor != "" else ""

    out = get_default(args, "out", None)
    in_ = get_default(args, "in", None)
    start_out, close_in = "", ""
    if out is not None:
      start_out = f"start.out.{out}"
    if in_ is not None:
      close_in = f"close.in.{in_}"

    annotates = get_default(args, "positionals", [])
    annotates = [f"with.annotate '{v}'" for v in annotates]
    while len(annotates) < len(ids):
      annotates.append("")

    for id_, annotate in zip(ids, annotates):
      self._ensure_name_is_id(id_)
      self._parse(f"draw {arrow} {start_point} "
                  f"{action}.to.{id_}{anchor} "
                  f"{start_out} {close_in} {annotate}")

  def _connect(self, code):
    if self._selection.has_path():
      raise ErrorMessage("Cannot connect paths")
    if self._marks.empty():
      if self._selection.num_ids() < 2:
        raise ErrorMessage("Should select at least two objects, "
                           "or set at least one mark")
      self._connect_objects_by_ids(self._selection.ids(), code)
    elif self._marks.single():
      if not self._selection.has_id():
        raise ErrorMessage("Should select at least one object")
      self._connect_mark_with_objects_by_ids(self._marks.get_single(),
                                             self._selection.ids(),
                                             code)

  def _set_grid(self, code):
    parser = Parser()
    parser.flag("off")
    parser.flag("on")
    args = parser.parse(code)
    if "off" in args:
      self._canvas_manager._show_grid = False
    elif "on" in args:
      self._canvas_manager._show_grid = True
    else:
      self._canvas_manager._show_grid = not self._canvas_manager._show_grid

  def _set_axes(self, code):
    parser = Parser()
    parser.flag("off")
    parser.flag("on")
    args = parser.parse(code)
    if "off" in args:
      self._canvas_manager._show_axes = False
    elif "on" in args:
      self._canvas_manager._show_axes = True
    else:
      self._canvas_manager._show_axes = not self._canvas_manager._show_axes

  def _add_mark(self, code):
    x, y = self._pointer.pos()
    to_del = None
    parser = Parser()
    parser.flag_group("anchor", anchor_list + list(short_anchor_dict.keys()))
    parser.flag("shift")
    parser.flag_group("rel", ["relative", "rel"])
    parser.flag("clear")
    parser.flag("cycle")
    parser.require_arg("del", 1)
    parser.require_arg("arc", 3)

    args = parser.parse(code)
    anchors = get_default(args, "anchor", [])
    if len(anchors) > 2:
      raise ErrorMessage("Too many anchors. Expect no more than two.")
    elif len(anchors) > 0:
      if self._selection.num_ids() > 2:
        raise ErrorMessage("Cannot mark more than two object anchors")
      elif not self._selection.has_id():
        raise ErrorMessage("Please select one or two objects")
      if self._selection.num_ids() == 2:
        id1, id2 = self._selection.ids()
        mark = {
            "type": "intersection",
            "name1": id1,
            "name2": id2,
            "anchor1": anchors[0] if anchors[0] in anchor_list
            else short_anchor_dict[anchors[0]],
        }
        if len(anchors) > 1:
          mark["anchor2"] = (anchors[1] if anchors[1] in anchor_list
                             else short_anchor_dict[anchors[1]])
      else:
        if len(anchors) == 2:
          raise ErrorMessage("Too many anchors. Expect no more than one.")
        anchor = anchors[0]
        if anchor in short_anchor_dict:
          anchor = short_anchor_dict[anchor]
        mark = {
            "type": "nodename",
            "name": self._selection.get_single_id(),
            "anchor": anchor,
        }
        if "shift" in args:
          bb = self._canvas_manager._bounding_boxes[mark["name"]]
          pointerx, pointery = self._pointer.pos()
          anchorx, anchory = bb.get_anchor_pos(anchor)
          xshift = pointerx - anchorx
          yshift = pointery - anchory
          if xshift != 0:
            mark["xshift"] = num_to_dist(xshift)
          if yshift != 0:
            mark["yshift"] = num_to_dist(yshift)
    elif "rel" in args:
      x0, y0 = self._marks.get_last_pos(
          self._canvas_manager._bounding_boxes)
      pointerx, pointery = self._pointer.pos()
      xshift = pointerx - x0
      yshift = pointery - y0
      mark = create_coordinate(xshift, yshift)
      mark["relative"] = True
    elif "clear" in args:
      self._marks.clear()
      return
    elif "del" in args:
      indices = args["del"]
      if len(indices) > 0:
        index = indices[0]
      else:
        index = self._marks.size() - 1
      if index >= self._marks.size():
        raise ErrorMessage("Index too large")
      self._marks.delete(index)
      return
    elif "arc" in args:
      arc_args = args["arc"]
      assert len(arc_args) == 3, ("Invalid number of args for arc: "
                                  f"expected 3, got {len(arc_args)}")
      start = int(arc_args[0])
      end = int(arc_args[1])
      radius = arc_args[2]
      mark = create_arc(start, end, radius)
    elif "cycle" in args:
      if self._marks.empty():
        raise ErrorMessage("No marks set yet")
      mark = {"type": "cycle"}
    else:
      mark = create_coordinate(x, y)

    self._marks.add(mark)

  def _annotate(self, code):
    if self._selection.num_paths() > 1:
      raise ErrorMessage("Cannot annotate more than one paths")
    if not self._selection.has_path():
      raise ErrorMessage("Please select one path")
    path = self._selection.get_single_path()
    lines = [item for item in path["items"] if item["type"] == "line"]
    if len(lines) == 0:
      raise ErrorMessage("Selected path does not have any lines")
    if len(lines) > 1:
      if self._selection.is_in_path_position_mode():
        line = self._selection.next_line()
        if line is None:
          raise ErrorMessage("Selected position is not followed by line")
        if not is_type(line, "line") and not is_type(line, "arc"):
          raise ErrorMessage("Selected position is not followed by line")
      else:
        raise ErrorMessage("Selected path has multiple lines")
    else:
      line = lines[0]

    parser = Parser()
    args = parser.parse(code)
    text = get_default(args, "positionals", [""])[0]
    with self._modify_picture():
      ensure_key(line, "annotates", [])
      line["annotates"].append({
          "id": self._context.getid(),
          "type": "text",
          "in_path": True,
          "text": text,
          "midway": True,
          "above": True,
          "sloped": True,
          "scale": "0.7",
      })

  def _chain(self, code):
    if self._selection.num_ids() < 2:
      raise ErrorMessage("Please select at least two objects")

    direction = "horizontal"

    parser = Parser()
    parser.flag("h")
    parser.flag("v")
    parser.flag("\\")
    parser.flag("/")
    args = parser.parse(code)

    if "h" in args:
      direction = "horizontal"
    elif "v" in args:
      direction = "vertical"
    elif "\\" in args:
      direction = "down right"
    elif "/" in args:
      direction = "down left"

    with self._modify_picture():
      for i in range(1, self._selection.num_ids()):
        id_ = self._selection.get_id(i)
        obj = self._context.find_object_by_id(id_)
        obj["at"] = self._selection.get_id(i-1)
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

  def _search(self, code):
    parser = Parser()
    args = parser.parse(code)
    self._selection.search(**args)

  def _read(self, code):
    filename = code
    with open(filename) as f:
      data = json.loads(f.read())

    with self._modify_picture():
      if "picture" in data:
        self._context._picture = data["picture"]
      if "nextid" in data:
        self._context._state["nextid"] = data["nextid"]

  def _save_as_object(self, code):
    object_name = code
    if self._selection.nonempty():
      data = json.dumps([obj for obj in self._context._picture
                         if self._selection.selected(obj)])
    else:
      data = json.dumps(self._context._picture)
    with open(self._get_object_path(object_name), "w") as f:
      f.write(data)

  def _write(self, code):
    filename = code

    if self.filename is None and len(filename) > 0:
      self.filename = filename

    if len(filename) == 0 and self.filename is not None:
      filename = self.filename

    data = json.dumps(self._save())
    if len(filename) == 0:
      print(data)
    else:
      with open(filename, "w") as f:
        f.write(data)

  def _export(self, code):
    filename = code
    tikzcode = self._context.render()
    data = json.dumps(self._context._picture)
    if filename.endswith(".png"):
      path = tikzimage(tikzcode)
      os.system(f"cp {path} {filename}")
    else:
      with open(filename, "w") as f:
        f.write(tikzcode)

  def _read_object(self, code):
    object_name = code
    with open(self._get_object_path(object_name)) as f:
      data = json.loads(f.read())
    with self._modify_picture():
      self._context.paste_data(data, *self._pointer.pos(), True)

  def _get_object_path(self, name):
    if not os.path.exists(self._object_path):
      os.mkdir(self._object_path)
    return os.path.join(self._object_path, f"{name}.json")

  def _save_command_history(self, history):
    path = os.path.join(self._object_path, "history")
    if not os.path.exists(self._object_path):
      os.mkdir(self._object_path)
    with open(path, "w") as f:
      f.write("\n".join(history))

  def _execute_python_code(self):
    with self._modify_picture():
      with open("/tmp/english2tikz.py") as f:
        code = f.read()
      selected_objects = self._selection.get_selected_id_objects()
      selected_paths = self._selection.paths()
      exec(code, locals())

  def _edit_python_code(self):
    if not os.path.exists("/tmp/english2tikz.py"):
      with open("/tmp/english2tikz.py", "w") as f:
        f.write(r"""# Available local variables:
# selected_objects: list, objects with ids
# selected_paths: list, paths
""")
    os.system("open -a 'Sublime Text' /tmp/english2tikz.py")

  def _execute_describeit_code(self):
    with self._modify_picture():
      with open("/tmp/english2tikz.desc") as f:
        code = f.read()
      ctx = self._context
      ctx._state["refered_to"] = self._selection.get_selected_objects()
      for i, id_ in enumerate(self._selection.ids()):
        code = code.replace(f"{{#{i}}}", id_)
      x, y = self._pointer.posstr()
      code = code.replace(f"{{#x}}", x)
      code = code.replace(f"{{#y}}", y)
      ctx.parse(code)

  def _edit_describeit_code(self):
    if not os.path.exists("/tmp/english2tikz.desc"):
      with open("/tmp/english2tikz.desc", "w") as f:
        f.write("### Write the describe it code here ###")
    os.system("open -a 'Sublime Text' /tmp/english2tikz.desc")

  def _view(self):
    tikzcode = self._context.render()
    self._canvas_manager.preview(tikzimage(tikzcode))
