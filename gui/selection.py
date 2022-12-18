from english2tikz.utils import *
from english2tikz.errors import *
from english2tikz.gui.object_utils import *


class Selection(object):
  def __init__(self, context):
    self._context = context
    self.clear()

  def clear(self):
    self._selected_ids = []
    self._selected_paths = []
    self._selected_path_position_index = 0
    self._selected_path_position = None
    self._jump_to_select_index = 0
    self._selected_anchor = None

  def picture(self):
    return self._context._picture

  def get_id(self, index):
    return self._selected_ids[index]

  def get_object(self, index):
    return self._context.find_object_by_id(self.get_id(index))

  def get_path(self, index):
    return self._selected_paths[index]

  def get_single_path(self):
    assert len(self._selected_paths) == 1
    return self._selected_paths[0]
  
  def get_single_node(self):
    return self._context.find_object_by_id(self.get_single_id())

  def get_single_object(self):
    if self.single_id() and not self.has_path():
      return self._context.find_object_by_id(self.get_single_id())
    if not self.has_id() and self.single_path():
      path = self.get_single_path()
      if self._selected_path_position is not None:
        return path["items"][self._selected_path_position]
      return path
    return None

  def get_selected_objects_common_description(self):
    objs = self.get_selected_objects()
    if len(objs) == 0:
      return {}
    if len(objs) == 1:
      obj = objs[0]
      if is_type(obj, "path") and self.is_in_path_position_mode():
        obj = obj["items"][self._selected_path_position]
      return self._get_object_description(obj)
    descs = [self._get_object_description(obj) for obj in objs]
    return common_part(descs)

  def _get_object_description(self, obj):
    keys = list(obj.keys())
    if is_type(obj, "path"):
      keys = remove_if_in(keys, "items")
      desc = {key: obj[key] for key in keys}
      desc["#items"] = str(len(obj["items"]))
      desc["#segments"] = str(count_path_segment_items(obj))
      desc["#positions"] = str(count_path_position_items(obj))
    elif is_type(obj, "box"):
      desc = {key: obj[key] for key in keys}
      desc["draw"] = True
    elif is_type(obj, "text"):
      desc = {key: obj[key] for key in keys}
    else:
      desc = {key: obj[key] for key in keys}

    return desc

  def ids(self):
    return self._selected_ids

  def paths(self):
    return self._selected_paths

  def has_ids(self, n):
    return self.num_ids() == n

  def has_id(self):
    return self.num_ids() > 0

  def has_paths(self, n):
    return self.num_paths() == n

  def has_path(self):
    return self.num_paths() > 0

  def single_id(self):
    return self.has_ids(1)

  def single_path(self):
    return self.has_paths(1)

  def get_single_id(self):
    assert len(self._selected_ids) == 1
    return self._selected_ids[0]

  def get_two_ids(self):
    assert len(self._selected_ids) == 2
    return self._selected_ids[0], self._selected_ids[1]

  def get_path_items(self):
    return self.get_single_path()["items"]

  def get_selected_path_item(self):
    return self.get_single_path()["items"][self._selected_path_position]

  def set_selected_path_item(self, item):
    assert self.is_in_path_position_mode()
    self.get_path_items()[self._selected_path_position] = item

  def previous_line(self):
    return previous_line(self.get_path_items(), self._selected_path_position)

  def next_line(self):
    return next_line(self.get_path_items(), self._selected_path_position)

  def get_path_position(self):
    assert self.is_in_path_position_mode()
    return self.get_path_items()[self._selected_path_position]

  def get_node_anchor(self):
    assert self.is_in_node_anchor_mode()
    return create_nodename(self.get_single_id(), self._selected_anchor)
  
  def selected_node_anchor(self, id_):
    if self.is_in_node_anchor_mode() and self.get_single_id() == id_:
      return self._selected_anchor
    return None
  
  def num_ids(self):
    return len(self._selected_ids)

  def num_paths(self):
    return len(self._selected_paths)

  def num_selected(self):
    return self.num_ids() + self.num_paths()

  def is_in_path_position_mode(self):
    if self._selected_path_position is not None:
      assert len(self._selected_ids) == 0
      assert len(self._selected_paths) == 1
      return True
    return False
  
  def is_in_node_anchor_mode(self):
    if self._selected_anchor is not None:
      assert len(self._selected_ids) == 1
      assert len(self._selected_paths) == 0
      return True
    return False

  def empty(self):
    return not self.has_id() and not self.has_path()

  def nonempty(self):
    return self.has_id() or self.has_path()

  def deselect(self):
    if self.is_in_path_position_mode():
      self._selected_path_position = None
      return True
    elif self.is_in_node_anchor_mode():
      self._selected_anchor = None
      return True
    elif self.nonempty():
      self.clear()
      return True
    return False

  def selected(self, obj_or_id):
    if isinstance(obj_or_id, str):
      return self.selected_id(obj_or_id)
    id_ = obj_or_id.get("id")
    if id_:
      return self.selected_id(id_)
    assert is_type(obj_or_id, "path")
    return self.selected_path(obj_or_id)

  def selected_position(self, index):
    return (self.is_in_path_position_mode() and
            self._selected_path_position == index)

  def selected_id(self, id_):
    return id_ in self._selected_ids

  def selected_path(self, path):
    return path in self._selected_paths

  def update(self, mode, *items):
    if mode == "clear":
      self.select(*items)
    elif mode == "exclude":
      self.exclude(*items)
    elif mode == "intersect":
      self.intersect(*items)
    elif mode == "toggle":
      self.toggle(*items)
    elif mode == "merge":
      self.include(*items)
    else:
      raise ValueError(f"Unknown mode {mode}")

  def select(self, *items):
    self.clear()
    self.include(*items)

  def toggle(self, *items):
    for item in items:
      if isinstance(item, str):
        self._selected_ids = toggle_element(self._selected_ids, item)
        self._selected_path_position = None
      elif is_type(item, "box") or is_type(item, "text"):
        self._selected_ids = toggle_element(self._selected_ids, item["id"])
        self._selected_path_position = None
      elif is_type(item, "path"):
        self._selected_paths = toggle_element(self._selected_paths, item)
        self._selected_path_position = None
      else:
        raise ValueError(f"Invalid item {item}")

  def include(self, *items):
    for item in items:
      if isinstance(item, str):
        append_if_not_in(self._selected_ids, item)
        self._selected_path_position = None
      elif is_type(item, "box") or is_type(item, "text"):
        append_if_not_in(self._selected_ids, item["id"])
        self._selected_path_position = None
      elif is_type(item, "path"):
        append_if_not_in(self._selected_paths, item)
        self._selected_path_position = None
      else:
        raise ValueError(f"Invalid item {item}")

  def exclude(self, *items):
    for item in items:
      if isinstance(item, str):
        self._selected_ids = remove_if_in(self._selected_ids, item)
        self._selected_path_position = None
      elif is_type(item, "box") or is_type(item, "text"):
        self._selected_ids = remove_if_in(self._selected_ids, item["id"])
        self._selected_path_position = None
      elif is_type(item, "path"):
        self._selected_paths = remove_if_in(self._selected_paths, item)
        self._selected_path_position = None
      else:
        raise ValueError(f"Invalid item {item}")

  def intersect(self, *items):
    items = [item for item in items if self.selected(item)]
    self.clear()
    for item in items:
      if isinstance(item, str):
        self._selected_ids.append(item)
      elif is_type(item, "box") or is_type(item, "text"):
        self._selected_ids.append(item["id"])
      elif is_type(item, "path"):
        self._selected_paths.append(item)
      else:
        raise ValueError(f"Invalid item {item}")

  def get_selected_id_objects(self):
    return [self._context.find_object_by_id(id_) for id_ in self.ids()]

  def get_selected_objects(self):
    ret = self.get_selected_id_objects() + self._selected_paths
    ret = [obj for obj in ret if obj is not None]
    return ret

  def jump_to_next_selected(self, by):
    if self.has_id():
      self._jump_to_select_index += self.num_ids() + by
      self._jump_to_select_index %= self.num_ids()
      return True
    elif self.single_path():
      self._selected_path_position_index += by
      self._select_path_position()
    else:
      self._jump_to_select_index = 0
    return False
  
  def shift_selected_anchor(self, direction):
    assert self.is_in_node_anchor_mode()
    self._selected_anchor = shift_anchor(self._selected_anchor, direction)

  def id_to_jump(self):
    return self._selected_ids[self._jump_to_select_index]

  def _select_path_position(self):
    if not self.single_path() or self.has_id():
      return

    position_items = get_path_position_items(self.get_single_path())

    if len(position_items) > 0:
      self._selected_path_position_index += len(position_items)
      self._selected_path_position_index %= len(position_items)
      self._selected_path_position = position_items[
          self._selected_path_position_index][0]
  
  def _select_anchor(self):
    if not self.single_id() or self.has_path():
      return
    self._selected_anchor = "center"

  def search(self, positionals=[], **kwargs):
    self.clear()
    filters = []
    for v in positionals:
      filters.append(("text", v))

    for key, value in kwargs.items():
      if len(key) == 0:
        raise ErrorMessage("Does not support empty search key")
      if value is True:
        filters.append((None, key))
      elif len(value) == 0:
        """
        In this case, the value is not filtered. This is a key filter,
        i.e., find objects with the given key
        """
        filters.append((key, None))
      else:
        filters.append((key, value))

    if len(filters) == 0:
      raise ErrorMessage("No filter given")

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

  def select_path(self, path):
    self.clear()
    self._selected_paths = [path]
  
  def select_path_and_index(self, path, index):
    self.clear()
    self._selected_paths = [path]
    self._selected_path_position = index
  
  def select_node_and_anchor(self, nodename):
    self.clear()
    self._selected_ids = [nodename["name"]]
    self._selected_anchor = nodename.get("anchor", "center")