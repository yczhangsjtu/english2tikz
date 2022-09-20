from .utils import getid


class ObjectRenderer(object):
  def match(self, obj):
    raise Exception("'match' cannot be invoked directly")
  
  def render(self, obj):
    raise Exception("'render' cannot be invoked directly")


class BoxObjectRenderer(ObjectRenderer):
  def match(self, obj):
    return obj == "box"
  
  def render(self, obj):
    return {
      "id": getid(),
      "type": "box",
      "text": "",
    }


class TreeObjectRenderer(ObjectRenderer):
  def match(self, obj):
    return isinstance(obj, dict) and "type" in obj and obj["type"] == "tree"
  
  def render(self, obj):
    ret = [{
      "id": getid(),
      "type": "text",
      "text": "root",
      "tree.role": "root",
      "tree.layer": 0,
      "tree": True,
    }]
    index = 0
    branches = obj["branches"]
    for branch in branches:
      curr = ret[index]
      curr_id = curr["id"]
      for i in range(branch):
        node = {
          "id": getid(),
          "type": "text",
          "text": f"node-{index}-{i}",
          "tree.layer": curr["tree.layer"] + 1,
          "tree": True,
        }
        if branch % 2 == 0 and i == 0:
          node["anchor"] = "north.east"
          node["at"] = curr_id
          node["at.anchor"] = "south"
          node["tree.role"] = "left"
        elif branch % 2 == 0 and i == 1:
          node["anchor"] = "north.west"
          node["at"] = curr_id
          node["at.anchor"] = "south"
          node["tree.role"] = "right"
        elif branch % 2 == 1 and i == 0:
          node["anchor"] = "north"
          node["at"] = curr_id
          node["at.anchor"] = "south"
          node["tree.role"] = "center"
        elif (branch % 2 == 0 and i % 2 == 0) or (branch % 2 == 1 and i % 2 == 1):
          node["anchor"] = "east"
          node["at"] = ret[-2]["id"] if i > 1 else ret[-1]["id"]
          node["at.anchor"] = "west"
          node["tree.role"] = "left"
        else:
          node["anchor"] = "west"
          node["at"] = ret[-2]["id"]
          node["at.anchor"] = "east"
          node["tree.role"] = "right"
        ret.append(node)
      index += 1
    return ret
