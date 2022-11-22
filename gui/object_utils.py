from english2tikz.utils import *


def draw_border(obj):
  return get_default(obj, "draw", False) or is_type(obj, "box")


def get_draw_color(obj):
  return get_default(obj, "color", "black") if draw_border(obj) else ""


def get_text_color(obj):
  text_color = get_default(obj, "text.color")
  text_color = get_default(obj, "color") if text_color is None else text_color
  text_color = "black" if text_color is None else text_color
  return text_color
