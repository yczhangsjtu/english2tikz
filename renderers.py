from .utils import colors, dump_options


class Renderer(object):
  def match(self, obj):
    raise Exception("'match' cannot be invoked directly")

  def render(self, obj):
    raise Exception("'render' cannot be invoked directly")


class BoxRenderer(Renderer):
  whitelist = set([
    "color", "line.width", "rounded.corners", "fill", "xshift", "yshift",
    "scale", "rotate", "circle", "inner.sep",
  ] + colors)
  directions = set([
    "above", "below", "left", "right",
    "below.left", "below.right",
    "above.left", "above.right",
  ])
  anchors = set([
    "south", "north", "south.west", "south.east",
    "east", "west", "north.west", "north.east", "center",
  ])
  def match(self, obj):
    return "type" in obj and obj["type"] == "box"
  
  def prepare_options(obj):
    ret = {name.replace(".", " "): value
           for name, value in obj.items()
           if name in BoxRenderer.whitelist}
    for direction in BoxRenderer.directions:
      if direction in obj:
        if "distance" in obj:
          distance = obj["distance"].replace(".and.", " and ")
          ret[direction.replace(".", " ")] = f"{distance} of {obj[direction]}"
        else:
          ret[direction.replace(".", " ")] = f"of {obj[direction]}"
    if "anchor" in obj:
      ret["anchor"] = obj["anchor"].replace(".", " ")
    if "at" in obj:
      if "at.anchor" in obj:
        ret["at"] = f"({obj['at']}.{obj['at.anchor'].replace('.', ' ')})"
      else:
        if not isinstance(obj["at"], str):
          if IntersectionRenderer().match(obj["at"]):
            at = IntersectionRenderer().render(obj["at"])
          elif CoordinateRenderer().match(obj["at"]):
            at = "{{{}}}".format(CoordinateRenderer().render(obj["at"]))
          else:
            raise Exception(f"Unsupported node location: {obj['at']}")
        else:
          at = f"({obj['at']})"
        ret["at"] = at
    if "width" in obj:
      ret["minimum width"] = obj["width"]
    if "height" in obj:
      ret["minimum height"] = obj["height"]
    if "inner sep" not in ret and ("text" not in obj or obj["text"] == ""):
      ret["inner sep"] = "0"
    return ret
  
  def render(self, obj):
    options = BoxRenderer.prepare_options(obj)
    if len(options) > 0:
      return r"\node[draw, {options}] ({id}) {{{text}}};".format(
        **obj,
        options=dump_options(options),
      )
    return r"\node[draw] ({id}) {{{text}}};".format(**obj)


class TextRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "text"
  
  def render(self, obj):
    options = BoxRenderer.prepare_options(obj)
    if "draw" in obj:
      options["draw"] = obj["draw"]
    if len(options) > 0:
      return r"\node[{options}] ({id}) {{{text}}};".format(
        **obj,
        options=dump_options(options),
      )
    return r"\node ({id}) {{{text}}};".format(**obj)


class PathRenderer(Renderer):
  def __init__(self, context):
    self._context = context
    
  def match(self, obj):
    return "type" in obj and obj["type"] == "path"
  
  def render(self, obj):
    options = BoxRenderer.prepare_options(obj)
    if "draw" in obj:
      options["draw"] = obj["draw"]
    if "arrow" in obj:
      options["->"] = True
    if "stealth" in obj:
      options["-stealth"] = True
    if "reversed.arrow" in obj:
      options["<-"] = True
    if "reversed.stealth" in obj:
      options["stealth-"] = True
    if "double.arrow" in obj:
      options["<->"] = True
    if "double.stealth" in obj:
      options["stealth-stealth"] = True
    if "dashed" in obj:
      options["dashed"] = True
    return r"\path[{}] {};".format(
      dump_options(options),
      " ".join(
        [self._context._render(item) for item in obj["items"]]
      )
    )


class NodeNameRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "nodename"
  
  def render(self, obj):
    if "anchor" in obj:
      return f"({obj['name']}.{obj['anchor'].replace('.', ' ')})"
    return f"({obj['name']})"


class LineRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "line"
  
  def render(self, obj):
    ret = ["--"]
    if "annotates" in obj:
      for annotate in obj["annotates"]:
        options = BoxRenderer.prepare_options(annotate)
        if "sloped" in annotate:
          options["sloped"] = annotate["sloped"]
        if "midway" in annotate:
          options["midway"] = annotate["midway"]
        if "above" in annotate:
          options["above"] = annotate["above"]
        if len(options) > 0:
          ret.append(r"node[{options}] ({id}) {{{text}}}".format(
            **annotate, options=dump_options(options)))
        else:
          ret.append(r"node ({id}) {{{text}}}".format(**annotate))
    return " ".join(ret)


class IntersectionRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "intersection"
  
  def render(self, obj):
    if "anchor1" in obj:
      x = f"{obj['name1']}.{obj['anchor1'].replace('.', ' ')}"
    else:
      x = f"{obj['name1']}"
      
    if "anchor2" in obj:
      y = f"{obj['name2']}.{obj['anchor2'].replace('.', ' ')}"
    else:
      y = f"{obj['name2']}"
    
    return f"({x} |- {y})"


  
class CoordinateRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "coordinate"
  
  def render(self, obj):
    if 'relative' in obj and obj['relative']:
      return f"++({obj['x']},{obj['y']})"
    return f"({obj['x']},{obj['y']})"


class PointRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "point"
  
  def render(self, obj):
    return f"coordinate ({obj['id']})"


class RectangleRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "rectangle"

  def render(self, obj):
    return "rectangle"
