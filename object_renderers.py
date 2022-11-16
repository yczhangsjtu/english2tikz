class ObjectRenderer(object):
  def match(self, obj):
    raise Exception("'match' cannot be invoked directly")

  def render(self, context, obj):
    raise Exception("'render' cannot be invoked directly")


class SupportMultipleRenderer(object):
  pass


class BoxObjectRenderer(ObjectRenderer, SupportMultipleRenderer):
  def match(self, obj):
    return obj == "box"

  def render(self, context, obj):
    return {
        "id": context.getid(),
        "type": "box",
        "text": "",
    }


class TreeObjectRenderer(ObjectRenderer):
  def match(self, obj):
    return isinstance(obj, dict) and "type" in obj and obj["type"] == "tree"

  def render(self, context, obj):
    ret = [{
        "id": context.getid(),
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
            "id": context.getid(),
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


class GridObjectRenderer(ObjectRenderer):
  def match(self, obj):
    return isinstance(obj, dict) and "type" in obj and obj["type"] == "grid"

  def render(self, context, obj):
    h, w, v_align, h_align = obj["rows"], obj["cols"], obj["v_align"], obj["h_align"]
    nodes = [[
        {
            "type": "text",
            "id": context.getid(),
            "text": f"grid-{i}-{j}",
        } for j in range(w)
    ] for i in range(h)]
    nodes[0][0]["origin"] = True
    nodes[0][0]["first.row"] = True
    nodes[0][0]["first.col"] = True
    for i in range(h):
      for j in range(w):
        nodes[i][j]["row"] = i
        nodes[i][j]["col"] = j
        if i == h - 1:
          nodes[i][j]["last.row"] = True
        if j == w - 1:
          nodes[i][j]["last.col"] = True
        if i % 2 == 0:
          nodes[i][j]["even.row"] = True
        else:
          nodes[i][j]["even.row"] = False
        if j % 2 == 0:
          nodes[i][j]["even.col"] = True
        else:
          nodes[i][j]["even.col"] = False
        if i == 0 and j > 0:
          nodes[i][j]["at"] = nodes[i][j-1]["id"]
          nodes[i][j]["first.row"] = True
          if v_align == "top":
            nodes[i][j]["anchor"] = "north.west"
            nodes[i][j]["at.anchor"] = "north.east"
          elif v_align == "center":
            nodes[i][j]["anchor"] = "west"
            nodes[i][j]["at.anchor"] = "east"
          elif v_align == "bottom":
            nodes[i][j]["anchor"] = "south.west"
            nodes[i][j]["at.anchor"] = "south.east"
        elif i > 0 and j == 0:
          nodes[i][j]["at"] = nodes[i-1][j]["id"]
          nodes[i][j]["first.col"] = True
          if h_align == "left":
            nodes[i][j]["anchor"] = "north.west"
            nodes[i][j]["at.anchor"] = "south.west"
          elif h_align == "center":
            nodes[i][j]["anchor"] = "north"
            nodes[i][j]["at.anchor"] = "south"
          elif h_align == "right":
            nodes[i][j]["anchor"] = "north.east"
            nodes[i][j]["at.anchor"] = "south.east"
        elif i > 0 and j > 0:
          nodes[i][j]["at"] = {
              "type": "intersection",
              "name1": nodes[0][j]["id"],
              "name2": nodes[i][0]["id"],
          }
          if h_align == "left":
            nodes[i][j]["at"]["anchor1"] = "west"
          elif h_align == "center":
            nodes[i][j]["at"]["anchor1"] = "center"
          elif h_align == "right":
            nodes[i][j]["at"]["anchor1"] = "east"

          if v_align == "top":
            nodes[i][j]["at"]["anchor2"] = "north"
          elif v_align == "center":
            nodes[i][j]["at"]["anchor2"] = "center"
          elif v_align == "bottom":
            nodes[i][j]["at"]["anchor2"] = "south"

          if v_align == "top":
            if h_align == "left":
              nodes[i][j]["anchor"] = "north.west"
            elif h_align == "center":
              nodes[i][j]["anchor"] = "north"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "north.east"
          elif v_align == "center":
            if h_align == "left":
              nodes[i][j]["anchor"] = "west"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "east"
          elif v_align == "bottom":
            if h_align == "left":
              nodes[i][j]["anchor"] = "south.west"
            elif h_align == "center":
              nodes[i][j]["anchor"] = "south"
            elif h_align == "right":
              nodes[i][j]["anchor"] = "south.east"
    return [node for row in nodes for node in row]
