import os
from hashlib import sha256
from english2tikz.errors import *


def escape_for_latex(text):
  text = text.replace("\n", "\\\\")
  return text


def text_to_latex_image_path(text, color="black", text_width=None):
  code = sha256(bytes(text, "utf8")).hexdigest()
  if color != "black":
    code = sha256(bytes(code + color, "utf8")).hexdigest()
  if text_width is not None:
    code = sha256(bytes(code + text_width, "utf8")).hexdigest()
  if not os.path.exists("view"):
    os.mkdir("view")
  if not os.path.isdir("view"):
    raise IOError("view is not a directory")
  if os.path.exists(f"view/{code}.png"):
    return f"view/{code}.png"
  cwd = os.getcwd()
  if color is None:
    color = "black"
  with open("/tmp/tmp.tex", "w") as f:
    f.write(r"""
\documentclass[varwidth=%s]{standalone}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{xcolor}
\begin{document}
\textcolor{%s}{%s}
\end{document}
""" % (r"\maxdimen" if text_width is None else text_width,
       color, escape_for_latex(text)))
  ret = os.system("cd /tmp && pdflatex tmp.tex 1> /dev/null 2> /dev/null")
  if ret != 0:
    raise SystemError(f"Error compiling latex: {text}")
  ret = os.system(
      r"convert -density 600 /tmp/tmp.pdf /tmp/tmp.png "
      r"1> /dev/null 2> /dev/null")
  if ret != 0:
    raise SystemError(f"Error converting pdf to png in processing: {text}")
  ret = os.system(f"cp /tmp/tmp.png view/{code}.png")
  if ret != 0:
    raise SystemError(f"Error copying png to view: {text}")
  return f"view/{code}.png"


def tikzimage(code):
  if not os.path.exists("view"):
    os.mkdir("view")
  if not os.path.isdir("view"):
    raise IOError("view is not a directory")
  cwd = os.getcwd()
  with open("/tmp/tmp.tex", "w") as f:
    f.write(r"""
\documentclass[varwidth=\maxdimen]{standalone}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{positioning}
\begin{document}
%s
\end{document}
""" % code)
  ret = os.system("cd /tmp && pdflatex tmp.tex 1> /dev/null 2> /dev/null")
  if ret != 0:
    raise SystemError(f"Error compiling latex:\n{code}")
  ret = os.system(
      r"convert -density 600 /tmp/tmp.pdf /tmp/tmp.png "
      r"1> /dev/null 2> /dev/null")
  if ret != 0:
    raise SystemError(f"Error converting pdf to png in processing:\n{code}")
  ret = os.system(f"cp /tmp/tmp.png view/view.png")
  if ret != 0:
    raise SystemError(f"Error copying png to view:\n{code}")
  return f"view/view.png"
