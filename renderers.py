from english2tikz.utils import colors, dump_options
from english2tikz.latex import escape_for_latex
from english2tikz.errors import *
from english2tikz.gui.image_utils import extract_image_path


class Renderer(object):
  def match(self, obj):
    raise ConfigurationError("'match' cannot be invoked directly")

  def render(self, obj):
    raise ConfigurationError("'render' cannot be invoked directly")


class BoxRenderer(Renderer):
  whitelist = set([
      "color", "line.width", "rounded.corners", "fill", "xshift", "yshift",
      "scale", "rotate", "circle", "inner.sep", "shape", "dashed", "font",
      "text.width", "sloped", "align"
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
        if isinstance(obj[direction], str):
          if "distance" in obj:
            distance = obj["distance"].replace(".and.", " and ")
            ret[direction.replace(
                ".", " ")] = f"{distance} of {obj[direction]}"
          else:
            ret[direction.replace(".", " ")] = f"of {obj[direction]}"
        else:
          ret[direction.replace(".", " ")] = True
        break
    for annotate_pos in LineRenderer.annotate_positions:
      if annotate_pos in obj:
        ret[annotate_pos.replace(".", " ")] = obj[annotate_pos]
        break
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
            raise ValueError(f"Unsupported node location: {obj['at']}")
        else:
          at = f"({obj['at']})"
        ret["at"] = at
    if "width" in obj:
      ret["minimum width"] = obj["width"]
    if "height" in obj:
      ret["minimum height"] = obj["height"]
    if "inner sep" not in ret and ("text" not in obj or obj["text"] == ""):
      ret["inner sep"] = "0"
    if "text.color" in obj:
      ret["text"] = obj["text.color"]
    return ret

  def render(self, obj):
    options = BoxRenderer.prepare_options(obj)
    text = obj.get("text")
    img_path = extract_image_path(text)
    if len(options) > 0:
      return r"\node[draw, {options}] ({id}) {{{escaped_text}}};".format(
          **obj,
          escaped_text=escape_for_latex(text) if img_path is None
                       else r"\includegraphics{%s}" % img_path,
          options=dump_options(options),
      )
    return r"\node[draw] ({id}) {{{escaped_text}}};".format(**obj,
        escaped_text=escape_for_latex(text) if img_path is None
                      else r"\includegraphics{%s}" % img_path,)


class TextRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "text"

  def render(self, obj):
    if "in_path" in obj:
      prefix, postfix = "node", ""
    else:
      prefix, postfix = r"\node", ";"
    options = BoxRenderer.prepare_options(obj)
    text = obj.get("text")
    img_path = extract_image_path(text)
    if "draw" in obj:
      options["draw"] = obj["draw"]
    if len(options) > 0:
      return r"{prefix}[{options}] ({id}) {{{escaped_text}}}{postfix}".format(
          **obj,
          escaped_text=escape_for_latex(text) if img_path is None
                       else r"\includegraphics{%s}" % img_path,
          prefix=prefix,
          postfix=postfix,
          options=dump_options(options),
      )
    return r"{prefix} ({id}) {{{escaped_text}}}{postfix}".format(
        **obj,
        escaped_text=escape_for_latex(text) if img_path is None
                     else r"\includegraphics{%s}" % img_path,
        prefix=prefix, postfix=postfix)


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
    if "inner.sep" not in obj and "inner sep" in options:
      del options["inner sep"]
    return r"\path[{}] {};".format(
        dump_options(options),
        " ".join(
            [self._context._render(item) for item in obj["items"]]
        )
    )


class BraceRenderer(Renderer):
  def __init__(self, context):
    self._context = context

  def match(self, obj):
    return "type" in obj and obj["type"] == "brace"

  def render(self, obj):
    options = BoxRenderer.prepare_options(obj)
    options["draw"] = True
    options["decorate"] = True
    options["decoration"] = "{brace}"
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
    options = {}
    if "xshift" in obj:
      options["xshift"] = obj["xshift"]
    if "yshift" in obj:
      options["yshift"] = obj["yshift"]
    if len(options) > 0:
      options = dump_options(options)
      if "anchor" in obj:
        return f"([{options}] {obj['name']}.{obj['anchor'].replace('.', ' ')})"
      return f"([{options}] {obj['name']})"
    else:
      if "anchor" in obj:
        return f"({obj['name']}.{obj['anchor'].replace('.', ' ')})"
      return f"({obj['name']})"


class LineRenderer(Renderer):
  annotate_positions = set([
      "midway", "pos",
      "near.end", "near.start",
      "very.near.end", "very.near.start",
      "at.end", "at.start"
  ])

  def __init__(self, context):
    self._context = context

  def match(self, obj):
    return "type" in obj and obj["type"] in ["line", "to", "edge"]

  def render(self, obj):
    options = {}
    if "out" in obj:
      options["out"] = obj["out"]
    if "in" in obj:
      options["in"] = obj["in"]
    if "opacity" in obj:
      options["opacity"] = obj["opacity"]

    if len(options) > 0:
      if obj["type"] == "edge":
        ret = ["edge [{}]".format(dump_options(options))]
      else:
        ret = ["to [{}]".format(dump_options(options))]
    elif obj["type"] == "to":
      ret = ["to"]
    elif obj["type"] == "edge":
      ret = ["edge"]
    else:
      ret = ["--"]

    if "annotates" in obj:
      for annotate in obj["annotates"]:
        ret.append(self._context._render(annotate))
    return " ".join(ret)


class VerticalHorizontalRenderer(Renderer):
  def __init__(self, context):
    self._context = context

  def match(self, obj):
    return "type" in obj and obj["type"] == "vertical.horizontal"

  def render(self, obj):
    ret = ["|-"]

    if "annotates" in obj:
      for annotate in obj["annotates"]:
        ret.append(self._context._render(annotate))
    return " ".join(ret)


class HorizontalVerticalRenderer(Renderer):
  def __init__(self, context):
    self._context = context

  def match(self, obj):
    return "type" in obj and obj["type"] == "horizontal.vertical"

  def render(self, obj):
    ret = ["-|"]

    if "annotates" in obj:
      for annotate in obj["annotates"]:
        ret.append(self._context._render(annotate))
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


class CycleRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "cycle"

  def render(self, obj):
    return 'cycle'


class PointRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "point"

  def render(self, obj):
    options = {}
    if "midway" in obj:
      options["midway"] = True
    if len(options) > 0:
      return f"coordinate[{dump_options(options)}] ({obj['id']})"
    else:
      return f"coordinate ({obj['id']})"


class RectangleRenderer(Renderer):
  def match(self, obj):
    return "type" in obj and obj["type"] == "rectangle"

  def render(self, obj):
    return "rectangle"


class ArcRenderer(Renderer):
  def __init__(self, context):
    self._context = context

  def match(self, obj):
    return "type" in obj and obj["type"] == "arc"

  def render(self, obj):
    start = obj['start']
    end = obj['end']
    radius = obj['radius']
    ret = [f"arc ({start}:{end}:{radius})"]

    if "annotates" in obj:
      for annotate in obj["annotates"]:
        ret.append(self._context._render(annotate))

    return " ".join(ret)
