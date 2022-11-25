from PIL import Image
from PIL import ImageTk
from english2tikz.utils import *


"""
Used to keep a reference to the images to prevent the garbage
collector from collecting the images
"""
image_references = {}


def get_image_from_path(path, scale, id_, angle=0, recreate=False):
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
  img = img.resize((int(w * scale), int(h * scale)))
  if angle != 0:
    img = img.rotate(angle % 360, expand=True)
  image = ImageTk.PhotoImage(img)
  image_references[(path, scale, id_, angle)] = image
  return image
