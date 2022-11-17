import os
from hashlib import sha256


def escape_for_latex(text):
  text = text.replace("\n", "\\\\")
  return text


def text_to_latex_image_path(text, color="black"):
  code = sha256(bytes(text, "utf8")).hexdigest()
  if color != "black":
    code = sha256(bytes(code + color, "utf8")).hexdigest()
  if not os.path.exists("view"):
    os.mkdir("view")
  if not os.path.isdir("view"):
    raise Exception("view is not a directory")
  if os.path.exists(f"view/{code}.png"):
    return f"view/{code}.png"
  cwd = os.getcwd()
  if color is None:
    color = "black"
  with open("/tmp/tmp.tex", "w") as f:
    f.write(r"""
\documentclass[varwidth=\maxdimen]{standalone}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{xcolor}
\begin{document}
\Huge
\textcolor{%s}{%s}
\end{document}
""" % (color, escape_for_latex(text)))
  ret = os.system("cd /tmp && pdflatex tmp.tex 1> /dev/null 2> /dev/null")
  if ret != 0:
    raise Exception(f"Error compiling latex: {text}")
  ret = os.system("convert /tmp/tmp.pdf /tmp/tmp.png 1> /dev/null 2> /dev/null")
  if ret != 0:
    raise Exception(f"Error converting pdf to png in processing: {text}")
  ret = os.system(f"cp /tmp/tmp.png view/{code}.png")
  if ret != 0:
    raise Exception(f"Error copying png to view: {text}")
  return f"view/{code}.png"
