import tkinter as tk
import string
import copy
import re
import json
import os
from english2tikz.describe_it import DescribeIt
from english2tikz.drawers import *
from english2tikz.utils import *

screen_width, screen_height = 1200, 750

class CanvasManager(object):
  def __init__(self, root, canvas, screen_width, screen_height, picture=None):
    self._canvas = canvas
    self._root = root
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
    self._error_msg = None
    self._grid_size_index = 0
    self._grid_sizes = [1, 0.5, 0.2, 0.1, 0.05]
    self._show_axes = True
    self._show_grid = True
    self._obj_to_edit_text = None
    self._editing_text = None
    self._editing_text_pos = None
    self._history = [self._context._picture]
    self._history_index = 0
    self._visual_start = None
    self._bounding_boxes = {}
    self._selected_ids = []
    self._selected_paths = []
    self._marks = []
    self._image_references = {}
    self._jump_to_select_index = 0
    self._selected_path_position_index = 0
    self._selected_path_position = None
    self._clipboard = []
    root.bind("<Key>", self.handle_key)
    self.draw()

  def _register_fundamental_drawers(self):
    self.register_drawer(BoxDrawer())
    self.register_drawer(PathDrawer())

  def register_drawer(self, drawer):
    assert isinstance(drawer, Drawer)
    self._drawers.append(drawer)

  def _before_change(self):
    self._history = self._history[:self._history_index+1]
    self._history[self._history_index] = copy.deepcopy(self._history[self._history_index])

  def _parse(self, code):
    self._before_change()
    self._context.parse(code)
    self._after_change()

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

  def _grid_size(self):
    return self._grid_sizes[self._grid_size_index]

  def _handle_key_in_command_mode(self, event):
    if event.char:
      self._command_line += event.char
    elif event.keysym == "Return":
      self._process_command(self._command_line)
      self._command_line = None
    elif event.keysym == "BackSpace":
      if len(self._command_line) > 0:
        self._command_line = self._command_line[:-1]
      else:
        self._command_line = None
    elif event.state == 4 and event.keysym in string.ascii_lowercase:
      """Ctrl + letter"""
      if event.keysym == "c":
        self._command_line = None

  def _handle_key_in_editing_mode(self, event):
    if event.char:
      self._editing_text += event.char
    elif event.keysym == "Return":
      self._editing_text += "\n"
    elif event.keysym == "BackSpace":
      if len(self._editing_text) > 0:
        self._editing_text = self._editing_text[:-1]
    elif event.state == 4 and event.keysym in string.ascii_lowercase:
      """Ctrl + letter"""
      if event.keysym == "c":
        if self._obj_to_edit_text is None:
          if len(self._editing_text) > 0:
            x, y = self._get_pointer_pos_str()
            self._parse(f"""there.is.text "{self._editing_text}" at.x.{x}.y.{y}
                            with.align=left""")
        else:
          self._before_change()
          self._obj_to_edit_text["text"] = self._editing_text
          self._after_change()
        self._editing_text = None
      elif event.keysym == "o":
        """
        It is very inconvenient to edit text in our tool, and I'm too lazy
        to implement a powerful text editor or using the tkinter text field.
        So press Ctrl+o to open an external editor for assistance.
        After editing it in the external editor, close the editor, and press
        Ctrl+r to load the text into our tool.
        """
        with open("/tmp/editing", "w") as f:
          f.write(self._editing_text)
        os.system(f"open -a 'Sublime Text' /tmp/editing")
      elif event.keysym == "r":
        try:
          with open("/tmp/editing") as f:
            self._editing_text = f.read()
        except Exception as e:
          self._error_msg = f"Failed to open editing text: {e}"

  def _handle_key_without_visual(self, event):
    if event.char == "a":
      if len(self._selected_ids) > 1:
        self._error_msg = "Cannot append to more than one objects"
      elif len(self._selected_ids) == 1:
        self._insert_text_following_id(self._selected_ids[0], "right")
    elif event.char == "I":
      if len(self._selected_ids) > 1:
        self._error_msg = "Cannot prepend to more than one objects"
      elif len(self._selected_ids) == 1:
        self._insert_text_following_id(self._selected_ids[0], "left")
    elif event.char == "o":
      if len(self._selected_ids) > 1:
        self._error_msg = "Cannot append to more than one objects"
      elif len(self._selected_ids) == 1:
        self._insert_text_following_id(self._selected_ids[0], "below")
    elif event.char == "O":
      if len(self._selected_ids) > 1:
        self._error_msg = "Cannot prepend to more than one objects"
      elif len(self._selected_ids) == 1:
        self._insert_text_following_id(self._selected_ids[0], "above")
    elif event.char == ">":
      self._shift_selected_objects(self._grid_size(), 0)
    elif event.char == "<":
      self._shift_selected_objects(-self._grid_size(), 0)
    elif event.char == "K":
      self._shift_selected_objects(0, self._grid_size())
    elif event.char == "J":
      self._shift_selected_objects(0, -self._grid_size())
    elif event.char == "u":
      self._undo()
    elif event.char == "D":
      self._before_change()
      if len(self._selected_ids) > 0:
        deleted_ids = []
        for id_ in self._selected_ids:
          self._delete_objects_related_to_id(id_, deleted_ids)
      if len(self._selected_paths) > 0:
        for path in self._selected_paths:
          self._delete_path(path)
      self._after_change()
      self._selected_paths = []
      self._selected_ids = []
      self._selected_path_position = None
    elif event.char == 'm':
      x, y = self._get_pointer_pos()
      self._marks.append(create_coordinate(x, y))
    elif event.char == 'y':
      self._clipboard = [id_ for id_ in self._selected_ids]
    elif event.char == 'p':
      self._paste()

  def _handle_key_only_visual(self, event):
    if event.char == "-":
      self._deselect_targets()
      self._visual_start = None
    elif event.char == "^":
      self._intersect_select_targets()
      self._visual_start = None

  def _handle_printable_char_in_normal_mode(self, event):
    if event.char == ":":
      self._command_line = ""
      self._error_msg = None
    elif event.char == "/":
      self._command_line = "search "
      self._error_msg = None
    elif event.char == "j":
      self._move_pointer(0, -1)
    elif event.char == "k":
      self._move_pointer(0, 1)
    elif event.char == "h":
      self._move_pointer(-1, 0)
    elif event.char == "l":
      self._move_pointer(1, 0)
    elif event.char == "w":
      self._move_pointer(round(1/self._grid_size()), 0)
    elif event.char == "b":
      self._move_pointer(-round(1/self._grid_size()), 0)
    elif event.char == "e":
      self._move_pointer(0, -round(1/self._grid_size()))
    elif event.char == "E":
      self._move_pointer(0, round(1/self._grid_size()))
    elif event.char == "n":
      self._jump_to_next_selected(1)
    elif event.char == "N":
      self._jump_to_next_selected(-1)
    elif event.char == "L":
      upper, lower, left, right = self._boundary_grids()
      self._pointery = lower
      self._move_pointer_into_screen()
    elif event.char == "H":
      upper, lower, left, right = self._boundary_grids()
      self._pointery = upper
      self._move_pointer_into_screen()
    elif event.char == "M":
      upper, lower, left, right = self._boundary_grids()
      self._pointery = int((upper + lower)/2)
      self._move_pointer_into_screen()
    elif event.char == "0":
      upper, lower, left, right = self._boundary_grids()
      self._pointerx = left
      self._move_pointer_into_screen()
    elif event.char == "$":
      upper, lower, left, right = self._boundary_grids()
      self._pointerx = right
      self._move_pointer_into_screen()
    elif event.char == "G":
      self._reset_pointer_to_origin()
    elif event.char == "i":
      if self._visual_start is not None:
        self._create_node_at_visual()
        self._visual_start = None
      elif len(self._selected_ids) > 1:
        self._error_msg = "Cannot edit more than one objects"
      elif len(self._selected_ids) == 1:
        self._start_edit_text(self._selected_ids[0])
      else:
        self._start_edit_text()
    elif event.char == "v":
      if self._visual_start is not None:
        self._select_targets(False)
        self._visual_start = None
      else:
        x, y = self._get_pointer_pos()
        self._visual_start = (x, y)
    elif self._visual_start is None:
      self._handle_key_without_visual(event)
    else:
      self._handle_key_only_visual(event)

  def _handle_ctrl_key_in_normal_mode(self, event):
    if event.keysym == "r":
      self._redo()
    elif event.keysym == "c":
      self._clear()
    elif event.keysym == "g":
      self._change_grid_size(1)
    elif event.keysym == "f":
      self._change_grid_size(-1)
    elif event.keysym == "e":
      self._centery -= 100
      self._reset_pointer_into_screen()
    elif event.keysym == "y":
      self._centery += 100
      self._reset_pointer_into_screen()
    elif event.keysym == "h":
      if self._visual_start is not None:
        return
      self._shift_selected_object_at_anchor("left")
    elif event.keysym == "j":
      if self._visual_start is not None:
        pass
      self._shift_selected_object_at_anchor("down")
    elif event.keysym == "k":
      if self._visual_start is not None:
        pass
      self._shift_selected_object_at_anchor("up")
    elif event.keysym == "l":
      if self._visual_start is not None:
        pass
      self._shift_selected_object_at_anchor("right")

  def _handle_key_in_normal_mode(self, event):
    if event.char:
      self._handle_printable_char_in_normal_mode(event)
    elif event.keysym == "Return":
      self._error_msg = None
      if self._visual_start is not None:
        self._select_targets()
        self._visual_start = None
    elif event.state == 4 and event.keysym in string.ascii_lowercase:
      self._handle_ctrl_key_in_normal_mode(event)

  def handle_key(self, event):
    if self._command_line is not None:
      self._handle_key_in_command_mode(event)
    else:
      if self._editing_text is not None:
        self._handle_key_in_editing_mode(event)
      else:
        self._handle_key_in_normal_mode(event)
    self.draw()

  def _clear(self):
    self._visual_start = None
    self._marks = []
    self._clear_selects()

  def _clear_selects(self):
    self._selected_ids = []
    self._selected_paths = []
    self._selected_path_position = None

  def _change_grid_size(self, by):
    x, y = self._get_pointer_pos()
    self._grid_size_index = bound_by(self._grid_size_index + by, 0, len(self._grid_sizes))
    self._pointerx, self._pointery = self._find_closest_pointer_grid_coord(x, y)
    self._move_pointer_into_screen()

  def _shift_object_at_anchor(self, id_, direction):
    obj = self._find_object_by_id(id_)
    if obj is None:
      return

    if get_default_of_type(obj, "at", str) is None:
      self._error_msg = f"Object {id_} is not anchored to another object"
      return

    obj["at.anchor"] = shift_anchor(
        get_default(obj, "at.anchor", "center"),
        direction)

  def _shift_selected_object_at_anchor(self, direction):
    for id_ in self._selected_ids:
      self._shift_object_at_anchor(id_, direction)

  def _jump_to_next_selected(self, by):
    if len(self._selected_ids) > 0:
      self._jump_to_select_index += len(self._selected_ids) + by
      self._jump_to_select_index %= len(self._selected_ids)
      self._jump_to_select()
    elif len(self._selected_paths) == 1:
      self._selected_path_position_index += by
      self._select_path_position()

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
    self._parse(f"there.is.a.box at.x.{x0}.y.{y0} sized.{w}.by.{h} with.anchor=south.west")
    self._obj_to_edit_text = self._context._picture[-1]
    self._editing_text = self._obj_to_edit_text["text"]

  def _start_edit_text(self, id_=None):
    if id_ is None:
      self._editing_text = ""
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

    self._editing_text = self._obj_to_edit_text["text"]
    self._editing_text_pos = get_anchor_pos(self._bounding_boxes[id_], "center")

  def _find_object_by_id(self, id_):
    for obj in self._context._picture:
      if "id" in obj and obj["id"] == id_:
        return obj
      if "items" in obj:
        items = obj["items"]
        for item in items:
          if "id" in item and item["id"] == id_:
            return item
          if "annotates" in item:
            for annotate in item["annotates"]:
              if "id" in annotate and annotate["id"] == id_:
                return annotate
    return None

  def _ensure_name_is_id(self, id_):
    obj = self._find_object_by_id(id_)
    if obj is not None:
      obj["name"] = id_

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
    self._editing_text = ""
    self._editing_text_pos = get_anchor_pos(
        self._bounding_boxes[self._selected_ids[0]],
        at_anchor)
    self._selected_ids = [self._obj_to_edit_text["id"]]

  def _shift_selected_objects(self, dx, dy):
    if len(self._selected_ids) > 0:
      self._before_change()
      for id_ in self._selected_ids:
        self._shift_object(id_, dx, dy)
      self._after_change()
    elif len(self._selected_paths) == 1 and self._selected_path_position is not None:
      self._before_change()
      self._shift_path_position(self._selected_paths[0],
                                self._selected_path_position,
                                dx, dy)
      self._after_change()

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
      return
    self._shift_dist(obj, "xshift", dx, "0")
    self._shift_dist(obj, "yshift", dy, "0")

  def _shift_path_position(self, path, index, dx, dy):
    item = path["items"][index]
    if is_type(item, "coordinate"):
      self._shift_dist(item, "x", dx)
      self._shift_dist(item, "y", dy)
      return
    if is_type(item, "nodename"):
      self._shift_dist(item, "xshift", dx)
      self._shift_dist(item, "yshift", dy)

  def _select_targets(self, clear=True):
    if clear:
      self._clear_selects()

    if self._visual_start is None:
      return

    x0, y0 = self._visual_start
    x1, y1 = self._get_pointer_pos()
    x0, x1 = order(x0, x1)
    y0, y1 = order(y0, y1)
    sel = (x0, y0, x1, y1)

    for id_, bb in self._bounding_boxes.items():
      x, y, width, height = bb
      if intersect(sel, (x, y, x+width, y+height)):
        append_if_not_in(self._selected_ids, id_)

    for type_, data, path in self._segments:
      if path in self._selected_paths:
        continue
      selector = get_default({
        "line": self._select_line,
        "rectangle": self._select_rect,
        "curve": self._select_curve,
      }, type_)
      if selector is None:
        raise Exception(f"Unknown segment type: {type_}")
      selector(sel, data, path)

  def _select_path(self, path, deselect=False, new_selected_paths=None):
    if new_selected_paths is not None:
      new_selected_paths.append(path)
    elif deselect:
      self._selected_paths = remove_if_in(self._selected_paths, path)
    else:
      self._selected_paths.append(path)
    self._selected_path_position = None

  def _select_line(self, bb, data, path, deselect=False, new_selected_paths=None):
    if rect_line_intersect(bb, data):
      self._select_path(path, deselect, new_selected_paths)

  def _select_rect(self, bb, data, path, deselect=False, new_selected_paths=None):
    if intersect(bb, data):
      self._select_path(path, deselect, new_selected_paths)

  def _select_curve(self, bb, data, path, deselect=False, new_selected_paths=None):
    eps = 0.1
    x0, y0, x1, y1 = bb
    for x, y in data:
      if is_bound_by(x, x0 - eps, x1 + eps) and is_bound_by(y, y0 - eps, y1 + eps):
        self._select_path(path, deselect, new_selected_paths)
        return

  def _deselect_targets(self):
    if self._visual_start is None:
      return
    x0, y0 = self._visual_start
    x1, y1 = self._get_pointer_pos()
    x0, x1 = order(x0, x1)
    y0, y1 = order(y0, y1)
    sel = (x0, y0, x1, y1)

    for id_, bb in self._bounding_boxes.items():
      x, y, width, height = bb
      if id_ in self._selected_ids and intersect((x0, y0, x1, y1), (x, y, x+width, y+height)):
        self._selected_ids = remove_if_in(self._selected_ids, id_)

    for type_, data, path in self._segments:
      if path not in self._selected_paths:
        continue
      selector = get_default({
        "line": self._select_line,
        "rectangle": self._select_rect,
        "curve": self._select_curve,
      }, type_)
      if selector is None:
        raise Exception(f"Unknown segment type: {type_}")
      selector(sel, data, path, deselect=True)

  def _intersect_select_targets(self):
    if self._visual_start is None:
      return
    x0, y0 = self._visual_start
    x1, y1 = self._get_pointer_pos()
    x0, x1 = order(x0, x1)
    y0, y1 = order(y0, y1)
    sel = (x0, y0, x1, y1)

    new_selected_ids = []
    for id_, bb in self._bounding_boxes.items():
      x, y, width, height = bb
      if id_ in self._selected_ids and intersect((x0, y0, x1, y1), (x, y, x+width, y+height)):
        new_selected_ids.append(id_)
    self._selected_ids = new_selected_ids

    new_selected_paths = []
    for type_, data, path in self._segments:
      if path not in self._selected_paths:
        continue
      selector = get_default({
        "line": self._select_line,
        "rectangle": self._select_rect,
        "curve": self._select_curve,
      }, type_)
      if selector is None:
        raise Exception(f"Unknown segment type: {type_}")
      selector(sel, data, path, deselect=True, new_selected_paths=new_selected_paths)
    self._selected_paths = new_selected_paths

  def _delete_objects_related_to_id(self, id_, deleted_ids = []):
    to_removes = [obj for obj in self._context._picture if self._related_to(obj, id_)]
    deleted_ids.append(id_)
    related_ids = [item["id"] for item in to_removes
                              if "id" in item and
                              item["id"] not in deleted_ids]
    self._context._picture = [obj for obj in self._context._picture
                                  if not self._related_to(obj, id_)]

    for obj in self._context._picture:
      if "items" in obj:
        for item in obj["items"]:
          if "annotates" in item:
            item["annotates"] = [annotate for annotate in item["annotates"]
                                          if "id" not in annotate or annotate["id"] != id_]
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
          if "id" in annotate and not "id" in affected_ids:
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

    old_to_new_id_dict = {}
    to_replace = []
    new_objects = []
    for id_ in self._clipboard:
      obj = self._find_object_by_id(id_)
      if obj is None:
        continue
      newobj = copy.deepcopy(obj)
      """
      This new object has conflict id with the original.
      Update it.
      """
      newid = self._context.getid()
      """
      Remember the relation between old and new ids, because
      if other copied objects rely on this, the reliance of them
      should also be updated.
      """
      old_to_new_id_dict[newobj["id"]] = newid

      newobj["id"] = newid

      x, y = self._get_pointer_pos()
      if get_default_of_type(newobj, "at", str, None) in self._clipboard:
        """
        If this object relies on another object that is also copied,
        update the reliance to the copied id, which may not be known yet.
        So postpone the replacement to the end of loop, when all the newids
        are settled.
        """
        to_replace.append(newobj)
      else:
        """
        Otherwise, simply put the copied object at the position of the pointer.
        """
        newobj["at"] = create_coordinate(x, y)
        del_if_has(newobj, "at.anchor")

      new_objects.append(newobj)

    """
    Now we have all newids ready, we can update the reliances.
    """
    for obj in to_replace:
      obj["at"] = old_to_new_id_dict[obj["at"]]

    self._before_change()
    for obj in new_objects:
      self._context._picture.append(obj)
    self._after_change()

  def _jump_to_select(self):
    id_ = self._selected_ids[self._jump_to_select_index]
    if id_ not in self._bounding_boxes:
      return
    bb = self._bounding_boxes[id_]
    x, y = get_anchor_pos(bb, "center")
    self._pointerx = round(x / self._grid_size())
    self._pointery = round(y / self._grid_size())
    self._reset_pointer_into_screen()

  def _select_path_position(self):
    if len(self._selected_paths) != 1:
      return

    path = self._selected_paths[0]
    position_items = [(i, item) for (i, item) in enumerate(path["items"])
                      if item["type"] in ["nodename", "coordinate", "intersection"]]

    if len(position_items) > 0:
      self._selected_path_position_index += len(position_items)
      self._selected_path_position_index %= len(position_items)
      self._selected_path_position = position_items[self._selected_path_position_index][0]

  def _get_pointer_pos(self):
    return self._pointerx * self._grid_size(), self._pointery * self._grid_size()

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

  def _reset_pointer_into_screen(self):
    screenx, screeny = self._get_pointer_screen_pos()
    screenx = bound_by(screenx, self._scale - 10, self._screen_width - self._scale + 10)
    screeny = bound_by(screeny, self._scale - 10, self._screen_height - self._scale + 10)
    x, y = reverse_map_point(screenx, screeny, self._coordinate_system())
    self._pointerx, self._pointery = self._find_closest_pointer_grid_coord(x, y)

  def _boundary_grids(self):
    x0, y0 = reverse_map_point(0, 0, self._coordinate_system())
    x1, y1 = reverse_map_point(self._screen_width,
                               self._screen_height,
                               self._coordinate_system())
    step_upper = int(y0 / self._grid_size())
    step_lower = int(y1 / self._grid_size())
    step_left  = int(x0 / self._grid_size())
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
    self._draw_pointer(self._canvas)
    self._draw_command(self._canvas)

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
        c.create_text(self._screen_width-3, y, text=text, anchor="se", fill=color)
    for i in range(step_left, step_right+1):
      x, y = map_point(self._grid_size() * i, 0, self._coordinate_system())
      c.create_line((x, 0, x, self._screen_height), fill="gray", dash=2)
      draw_text = i == self._pointerx or i % step == 0
      color = "red" if i == self._pointerx else "gray"
      if draw_text:
        text = "%g" % (i * self._grid_size())
        c.create_text(x, 0, text=text, anchor="nw", fill=color)
        c.create_text(x, self._screen_height, text=text, anchor="sw", fill=color)

  def _draw_axes(self, c):
    c.create_line((0, self._centery, self._screen_width, self._centery), fill="blue", width=1.5)
    c.create_line((self._centerx, 0, self._centerx, self._screen_height), fill="blue", width=1.5)

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
      "segments": [],
      "coordinate system": self._coordinate_system(),
      "selected ids": self._selected_ids,
      "selected paths": self._selected_paths,
      "selected path position": self._selected_path_position,
      "image references": self._image_references,
    }
    for obj in ctx._picture:
      self._draw_obj(c, obj, env)
    self._bounding_boxes = env["bounding box"]
    self._segments = env["segments"]

  def _draw_obj(self, c, obj, env):
    for drawer in self._drawers:
      if not drawer.match(obj):
        continue
      try:
        drawer.draw(c, obj, env)
      except Exception as e:
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
      x, y = get_anchor_pos(bb, get_default(mark, "anchor", "center"))
      if "anchor" in mark:
        """
        It's useless in tikz to shift a node name coordinate without specifying
        the anchor.
        """
        x += dist_to_num(get_default(mark, "xshift", 0))
        y += dist_to_num(get_default(mark, "yshift", 0))
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
      except:
        self._marks = self._marks[:i]
        return

      x, y = map_point(x, y, self._coordinate_system())
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
      c.create_oval(x-10, y-10, x+10, y+10, fill=fill, outline=outline)
      c.create_text(x, y, text=str(i), fill="black")

  def _draw_editing_text(self, c):
    x, y = map_point(*self._editing_text_pos, self._coordinate_system())
    if len(self._editing_text.strip()) == 0:
      c.create_line((x, y-10, x, y+10), fill="black", width=3)
    else:
      t = c.create_text(x, y, text=self._editing_text, fill="black")
      bg = c.create_rectangle(c.bbox(t), fill="white", outline="blue")
      c.tag_lower(bg, t)

  def _draw_pointer(self, c):
    if self._editing_text is not None:
      self._draw_editing_text(c)
      return
    x, y = map_point(self._pointerx * self._grid_size(), self._pointery * self._grid_size(),
                     self._coordinate_system())
    c.create_line((0, y, self._screen_width, y), fill="red", width=1)
    c.create_line((x, 0, x, self._screen_height), fill="red", width=1)
    c.create_oval(x-10, y-10, x+10, y+10, fill="red", outline="black")

  def _draw_command(self, c):
    if self._command_line is not None:
      c.create_rectangle((3, self._screen_height-15, self._screen_width, self._screen_height), fill="white", outline="black")
      c.create_text(5, self._screen_height, text=":"+self._command_line, anchor="sw", fill="black")
    elif self._error_msg is not None:
      c.create_rectangle((3, self._screen_height-15, self._screen_width, self._screen_height), fill="white", outline="black")
      c.create_text(5, self._screen_height, text=self._error_msg, anchor="sw", fill="red")

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
    nextid = self._context._state["nextid"] if "nextid" in self._context._state else 0
    return {
      "picture": self._context._picture,
      "nextid": nextid,
    }

  def load(self, data):
    if "picture" in data:
      self._context._picture = data["picture"]
    if "nextid" in data:
      self._context._state["nextid"] = data["nextid"]
    self._history = [self._context._picture]
    self.draw()

  def _process_command(self, cmd):
    try:
      tokens = self._tokenize(cmd)
      if len(tokens) == 0:
        raise Exception("Empty command")
      if tokens[0][0] != "command":
        raise Exception("Command does not start with command name")
      cmd_name = tokens[0][1]
      if cmd_name == "set":
        self._set(*tokens[1:])
      elif cmd_name == "make" or cmd_name == "mk":
        self._make(*tokens[1:])
      elif cmd_name == "cn" or cmd_name == "connect":
        self._connect(*tokens[1:])
      elif cmd_name == "grid" or cmd_name == "g":
        self._set_grid(*tokens[1:])
      elif cmd_name == "axes" or cmd_name == "a":
        self._set_axes(*tokens[1:])
      elif cmd_name == "mark" or cmd_name == "m":
        self._add_mark(*tokens[1:])
      elif cmd_name == "ann" or cmd_name == "annotate":
        self._annotate(*tokens[1:])
      elif cmd_name == "ch" or cmd_name == "chain":
        self._chain(*tokens[1:])
      elif cmd_name == "search" or cmd_name == "s":
        self._search(*tokens[1:])
      elif cmd_name == "w":
        print("%%drawjson\n"+json.dumps(self._save()))
      elif cmd_name == "q":
        self._root.after(1, self._root.destroy())
        self._end = True
    except Exception as e:
      self._error_msg = str(e)

  def _set(self, *args):
    if len(self._selected_ids) == 0 and len(self._selected_paths) == 0:
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

  def _set_selected_objects(self, key, value):
    self._before_change()
    for id_ in self._selected_ids:
      obj = self._find_object_by_id(id_)
      if obj is None:
        raise Exception(f"Cannot find object by id {id_}")
      if value == "False":
        if key in obj:
          del obj[key]
      else:
        obj[key] = value
    for path in self._selected_paths:
      if value == "False":
        if key in path:
          del path[key]
      else:
        path[key] = value
    self._after_change()

  def _make(self, *args):
    obj = "path"
    arrow = None
    for t, v in args:
      if t == "command":
        if v == "rect":
          obj = v
        elif v == "path":
          obj = v
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
          items.append({
            "type": "line",
          })
      path = {
        "type": "path",
        "draw": True,
        "items": items,
      }
      if arrow is not None:
        path[arrow] = True
      self._context._picture.append(path)
      self._after_change()

    elif obj == "rect":
      if self._visual_start is not None:
        self._before_change()
        x0, y0 = self._visual_start
        x1, y1 = self._get_pointer_pos()
        path = {
          "type": "path",
          "draw": True,
          "items": [
            {
              "type": "coordinate",
              "x": num_to_dist(x0),
              "y": num_to_dist(y0),
            },
            {
              "type": "rectangle",
            },
            {
              "type": "coordinate",
              "x": num_to_dist(x1),
              "y": num_to_dist(y1),
            },
          ]
        }
        self._context._picture.append(path)
        self._after_change()
      elif len(self._marks) == 2:
        self._before_change()
        path = {
          "type": "path",
          "draw": True,
          "items": [
            self._marks[0],
            {
              "type": "rectangle",
            },
            self._marks[1],
          ]
        }
        self._context._picture.append(path)
        self._after_change()
      else:
        raise Exception("Please set exactly two marks or draw a rect in visual mode")

    else:
      raise Exception("Unknown object type")

  def _connect(self, *args):
    if len(self._selected_paths) != 0:
      raise Exception("Cannot connect paths")
    if len(self._marks) == 0:
      if len(self._selected_ids) < 2:
        raise Exception("Should select at least two objects, or set at least one mark")
      arrow, annotates = "", ["" for i in range(len(self._selected_ids) - 1)]
      action = "line"
      pairs = [(0, i) for i in range(1, len(self._selected_ids))]
      anchors = ["" for i in range(len(self._selected_ids))]
      start_out, close_in = "", ""
      for t, v in args:
        if t == "command":
          if v == "->":
            arrow = "with.stealth"
          elif v == "<-":
            arrow = "with.reversed.stealth"
          elif v == "<->":
            arrow = "with.double.stealth"
          elif v == "h":
            action = "line.horizontal"
          elif v == "v":
            action = "line.vertical"
          elif v == "chain":
            pairs = [(i-1, i) for i in range(1, len(self._selected_ids))]
          elif v in anchor_list:
            for j in range(len(anchors)):
              if anchors[j] == "":
                anchors[j] = f".{v}"
                break
          elif v in short_anchor_dict:
            for j in range(len(anchors)):
              if anchors[j] == "":
                anchors[j] = f".{short_anchor_dict[v]}"
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
      for id_ in self._selected_ids:
        self._ensure_name_is_id(id_)
      for k, pair in enumerate(pairs):
        i, j = pair
        id1, id2 = self._selected_ids[i], self._selected_ids[j]
        anchor1, anchor2 = anchors[i], anchors[j]
        annotate = annotates[k]
        self._parse(f"draw {arrow} from.{id1}{anchor1} {action}.to.{id2}{anchor2} {start_out} {close_in} {annotate}")
    elif len(self._marks) == 1:
      if len(self._selected_ids) == 0:
        raise Exception("Should select at least one object")
      mark = self._marks[0]
      if mark["type"] == "coordinate":
        start_point = f"x.{mark['x']}.y.{mark['y']}"
      elif mark["type"] == "nodename":
        start_point = f"move.to.{mark['name']}"
        if "anchor" in mark:
          start_point += f".{mark['anchor']}"
        if "xshift" in mark or "yshift" in mark:
          xshift = mark["xshift"] if "xshift" in mark else "0"
          yshift = mark["yshift"] if "yshift" in mark else "0"
          start_point += f" x.{xshift}.y.{yshift}.relative"
      else:
        raise Exception(f"Unknown mark type: {mark['type']}")

      action, anchor = "line", ""
      start_out, close_in = "", ""
      annotates = []
      for t, v in args:
        if t == "command":
          if v == "->":
            arrow = "with.stealth"
          elif v == "<-":
            arrow = "with.reversed.stealth"
          elif v == "<->":
            arrow = "with.double.stealth"
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
      for id_ in self._selected_ids:
        self._ensure_name_is_id(id_)
        self._ensure_name_is_id(id_)
        self._parse(f"draw {arrow} {start_point} {action}.to.{id_}{anchor} {start_out} {close_in} {' '.join(annotates)}")

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
    mark = {
      "type": "coordinate",
      "x": f"{x:g}cm",
      "y": f"{y:g}cm",
    }
    to_del = None
    for t, v in args:
      if t == "command":
        if v in anchor_list or v in short_anchor_dict:
          if len(self._selected_ids) > 1:
            raise Exception("Cannot mark more than one object anchors")
          if len(self._selected_ids) == 0:
            raise Exception("Please select one object")
          id_ = self._selected_ids[0]
          self._ensure_name_is_id(id_)
          mark = {
            "type": "nodename",
            "name": id_,
            "anchor": v if v in anchor_list else short_anchor_dict[v],
          }
        elif v == "shift":
          if mark["type"] != "nodename":
            raise Exception("Please specify anchor before shift")
          anchor = mark["anchor"]
          bb = self._bounding_boxes[mark["name"]]
          pointerx, pointery = self._get_pointer_pos()
          anchorx, anchory = get_anchor_pos(bb, anchor)
          xshift = pointerx - anchorx
          yshift = pointery - anchory
          if xshift != 0:
            mark["xshift"] = f"{xshift:g}cm"
          if yshift != 0:
            mark["yshift"] = f"{yshift:g}cm"
        elif v == "relative" or v == "rel":
          if mark["type"] != "coordinate":
            raise Exception("Do not specify anchor")
          x0, y0 = self._get_mark_pos(len(self._marks)-1, {})
          pointerx, pointery = self._get_pointer_pos()
          xshift = pointerx - x0
          yshift = pointery - y0
          mark["x"] = f"{xshift:g}cm"
          mark["y"] = f"{yshift:g}cm"
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
        else:
          raise Exception(f"Unknown argument {v}")
    if to_del is not None:
      del self._marks[to_del]
    else:
      self._marks.append(mark)

  def _annotate(self, *args):
    if len(self._selected_paths) > 1:
      raise Exception("Cannot annotate more than one paths")
    if len(self._selected_paths) == 0:
      raise Exception("Please select one path")
    path = self._selected_paths[0]
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
    if len(self._selected_ids) < 2:
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
    for i in range(1, len(self._selected_ids)):
      id_ = self._selected_ids[i]
      obj = self._find_object_by_id(id_)
      obj["at"] = self._selected_ids[i-1]
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
    self._selected_ids = []
    self._selected_paths = []
    self._selected_path_position = None
    filters = []
    for t, v in args:
      if t == "command":
        index = v.find("=")
        if index >= 0:
          key, value = v[:index], v[index+1:]
          if len(key) == 0:
            raise Exception("Does not support empty search key")
          if len(value) == 0:
            """
            In this case, the value is not filtered. This is a key filter,
            i.e., find objects with the given key
            """
            value = None
          filters.append((key, value))
        else:
          """
          In this case, the key is not filtered
          """
          filters.append((None, v))
      elif t == "text":
        filters.append(("text", v))
    if len(filters) == 0:
      raise Exception("No filter given")

    for obj in self._context._picture:
      if satisfy_filters(obj, filters):
        if "id" in obj:
          self._selected_ids.append(obj["id"])
        elif "type" in obj and obj["type"] == "path":
          self._selected_paths.append(obj)
          self._selected_path_position = None
      if "items" in obj:
        for item in obj["items"]:
          if "annotates" in item:
            for annotate in item["annotates"]:
              if satisfy_filters(annotate, filters):
                if "id" in annotate:
                  self._selected_ids.append(annotate["id"])
        

if __name__ == "__main__":
  root = tk.Tk()
  canvas = tk.Canvas(root, bg="white", width=screen_width, height=screen_height)
  canvas.pack()

  CanvasManager(root, canvas, screen_width, screen_height)

  root.title("Vim Draw")
  root.minsize(screen_width, screen_height)
  root.configure(bg="white")
  root.mainloop()
