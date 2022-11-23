from english2tikz import DescribeIt
from english2tikz.latex import tikzimage
di = DescribeIt()
di.parse(r"""
there.is.a.tree.with.branches.2.2.2.1.1.1.1
  with.texts "$\mathsf{H}$"
    "$\mathsf{h0}$" "$\mathsf{h1}$"
    "$\mathsf{h00}$" "$\mathsf{h01}$" "$\mathsf{h10}$" "$\mathsf{h11}$"
    "$a$" "$b$" "$c$" "$d$"
  with.names "root" "h0" "h1" "h00" "h01" "h10" "h11" "a" "b" "c" "d"
for.all.text with.tree without.tree.layer=3
  set.draw set.rounded.corners
for.all.text where.tree.role=left with.tree.layer=1
  set.xshift=-0.6cm
for.all.text where.tree.role=right with.tree.layer=1
  set.xshift=0.6cm
for.all.text where.tree.role=left with.tree.layer=2
  set.xshift=-0.08cm
for.all.text where.tree.role=right with.tree.layer=2
  set.xshift=0.08cm
for.all.text where.tree.layer=1
  set.yshift=-0.2cm
for.all.text where.tree.layer=2
  set.yshift=-0.2cm
for.all.text where.tree.layer=3
  set.yshift=-0.5cm
for.all.text where.name=root set.fill=blue!20
draw from.root.south point.to.h0
draw from.root.south point.to.h1
draw from.h0.south point.to.h00
draw from.h0.south point.to.h01
draw from.h1.south point.to.h10
draw from.h1.south point.to.h11
for.all.path set.blue
draw with.dashed from.h00 point.to.a
draw with.dashed from.h01 point.to.b
draw with.dashed from.h10 point.to.c
draw with.dashed from.h11 point.to.d
there.is.a.4.by.4.grid.aligned.center.right with.texts
  "A" "B" "Long" "D"
  "E" "F" "G" "H"
  "$\begin{array}{c}J\\V\end{array}$" "J" "K" "L"
  "M" "N" "O" "P"
  with.draw with.width=0.8cm with.height=0.8cm
for.all.text where.origin set.below.of.a by.0.5cm
for.all.text where.even.row set.fill=green!20
for.all.text with.text "P" set.red
for.all.text with.row=1 with.col=1 set.fill=green!50!black
""")
tikz = di.render()
tikzimage(tikz)
