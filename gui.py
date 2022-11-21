import tkinter as tk
import argparse
import os
from english2tikz.gui.canvas_manager import CanvasManager


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

  cm = CanvasManager(root, canvas, screen_width, screen_height)
  if args.filename is not None:
    filename = args.filename
    cm.filename = filename
    if os.path.exists(filename):
      cm._read(("command", filename))

  root.title("Vim Draw")
  root.minsize(screen_width, screen_height)
  root.configure(bg="white")
  root.mainloop()
