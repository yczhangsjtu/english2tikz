import os
from hashlib import sha256


def text_to_latex_image_path(text):
  code = sha256(bytes(text, "utf8")).hexdigest()
  if not os.path.exists("view"):
    os.mkdir("view")
  if not os.path.isdir("view"):
    raise Exception("view is not a directory")
  if os.path.exists(f"view/{code}.png"):
    return f"view/{code}.png"
  cwd = os.getcwd()
  with open("/tmp/tmp.tex", "w") as f:
    f.write(r"""
\documentclass{standalone}
\begin{document}
\Huge
%s
\end{document}
""" % text)
  ret = os.system("cd /tmp && pdflatex tmp.tex &> /dev/null")
  if ret != 0:
    raise Exception(f"Error compiling latex: {text}")
  ret = os.system("convert /tmp/tmp.pdf /tmp/tmp.png &> /dev/null")
  if ret != 0:
    raise Exception(f"Error converting pdf to png in processing: {text}")
  ret = os.system(f"cp /tmp/tmp.png view/{code}.png")
  if ret != 0:
    raise Exception(f"Error copying png to view: {text}")
  return f"view/{code}.png"
