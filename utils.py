colors = [
  "red", "blue", "white", "black", "yellow", "orange", "green"
]


counter = 0


def getid():
  global counter
  ret = f"id{counter}"
  counter += 1
  return ret


def dump_options(o):
  return ", ".join([key if isinstance(value, bool) and value
                    else f"{key}={value}"
                    for key, value in o.items()])
