class MockCanvas(object):
  def create_text(self, *args, **kwargs):
    pass

  def create_arc(self, *args, **kwargs):
    pass

  def create_oval(self, *args, **kwargs):
    pass

  def create_rectangle(self, *args, **kwargs):
    pass

  def create_line(self, *args, **kwargs):
    pass

  def delete(self, *args, **kwargs):
    pass

  def bbox(self, *args, **kwargs):
    return 0, 0, 1, 1

  def tag_lower(self, *args, **kwargs):
    pass


class MockTk(object):
  def bind(self, *args, **kwargs):
    pass

  def after(self, *args, **kwargs):
    pass

  def destroy(self, *args, **kwargs):
    pass
