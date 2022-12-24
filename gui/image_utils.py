from PIL import Image
from PIL import ImageTk
from english2tikz.utils import *


"""
Used to keep a reference to the images to prevent the garbage
collector from collecting the images
"""
image_references = {}


def get_image_from_path(path, scale, id_, angle=0, recreate=False,
                        reset_size=None):
  global image_references
  """
  The id_ here is used to force creating a new image, because
  each image can appear in at most one place
  """
  if not recreate:
    image = image_references.get((path, scale, id_, angle))
    if image is not None:
      return image
  img = Image.open(path)
  img = img.convert("RGBA")
  w, h = img.size
  if reset_size is None:
    img = img.resize((int(w * scale), int(h * scale)))
  else:
    img = img.resize(reset_size)
  if angle != 0:
    img = img.rotate(angle % 360, expand=True)
  image = ImageTk.PhotoImage(img)
  image_references[(path, scale, id_, angle)] = image
  return image


def extract_image_path(text):
  if text.startswith("<img>") and text.endswith("</img>"):
    return text[5:-6]
  return None


def get_image_size(img_path):
  try:
    img = Image.open(img_path)
    w, h = img.size
    dpi = img.info.get("dpi", 72)
    return w, h, dpi
  except FileNotFoundError as e:
    return None, None, None