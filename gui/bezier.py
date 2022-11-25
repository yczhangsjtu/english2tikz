"""
Modified from
https://git.sr.ht/~torresjrjr/Bezier.py/tree/bc87b14eaa226f8fb68d2925fb4f37c3344418c1/item/Bezier.py
Modified to avoid using numpy
Bezier, a module for creating Bezier curves.
Version 1.1, from < BezierCurveFunction-v1.ipynb > on 2019-05-02
"""


class Bezier():
  def TwoPoints(t, P1, P2):
    assert len(P1) == 2
    assert len(P2) == 2
    assert isinstance(P1[0], float) or isinstance(P1[0], int)
    assert isinstance(P1[1], float) or isinstance(P1[1], int)
    """
    Returns a point between P1 and P2, parametised by t.
    """

    Q1 = [(1 - t) * e1 + t * e2 for e1, e2 in zip(P1, P2)]
    assert len(Q1) == 2
    assert isinstance(Q1[0], float) or isinstance(Q1[0], int)
    return Q1

  def Points(t, *points):
    """
    Returns a list of points interpolated by the Bezier process
    """
    newpoints = []
    for i in range(0, len(points) - 1):
      point = Bezier.TwoPoints(t, points[i], points[i + 1])
      assert isinstance(point, list)
      assert len(point) == 2
      assert isinstance(point[0], float) or isinstance(point[0], int)
      assert isinstance(point[1], float) or isinstance(point[1], int)
      newpoints.append(point)
    assert isinstance(newpoints, list)
    assert isinstance(newpoints[0], list)
    assert isinstance(newpoints[0][0], float) or isinstance(
        newpoints[0][1], int)
    return newpoints

  def Point(t, *points):
    """
    Returns a point interpolated by the Bezier process
    """
    newpoints = points
    while len(newpoints) > 1:
      newpoints = Bezier.Points(t, *newpoints)
    assert len(newpoints) == 1, f"Got new points = {newpoints}"
    assert isinstance(newpoints[0], list), f"Got newpoints[0] = {newpoints[0]}"
    assert len(newpoints[0]) == 2, f"Got newpoints[0] = {newpoints[0]}"
    assert isinstance(newpoints[0][0], float) or isinstance(
        newpoints[0][0], int), f"Got type {type(newpoints[0][0])}"
    return newpoints[0]

  def Curve(t_values, *points):
    """
    Returns a point interpolated by the Bezier process
    """
    return [Bezier.Point(t, *points) for t in t_values]

  def generate_line_segments(*points, steps=100):
    t_values = [i/steps for i in range(steps+1)]
    curve = Bezier.Curve(t_values, *points)
    return [(x, y) for x, y in curve]
