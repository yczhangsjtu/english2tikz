import tkinter as tk
import argparse
import os
from english2tikz.gui.editor import Editor


screen_width, screen_height = 1200, 750


if __name__ == "__main__":
  root = tk.Tk()
  canvas = tk.Canvas(root, bg="white",
                     width=screen_width,
                     height=screen_height)
  canvas.pack()
  parser = argparse.ArgumentParser(prog="vimdraw")
  parser.add_argument('filename', nargs='?')
  args = parser.parse_args()

  editor = Editor(root, canvas, screen_width, screen_height)
  if args.filename is not None:
    filename = args.filename
    editor.filename = filename
    if os.path.exists(filename):
      editor._read(filename)

  root.title("Vim Draw")
  root.minsize(screen_width, screen_height)
  root.configure(bg="white")
  root.mainloop()
