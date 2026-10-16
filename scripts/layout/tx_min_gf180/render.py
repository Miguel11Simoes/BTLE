"""Render a GDS with the GF180MCU layer properties: render.py GDS LYP OUT WIDTH [x1 y1 x2 y2 (um)] [layers]"""
import sys
import klayout.db as db
import klayout.lay as lay

gds, lyp, out, width = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
box = [float(v) for v in sys.argv[5:9]] if len(sys.argv) >= 9 else None
only = sys.argv[9].split(",") if len(sys.argv) >= 10 else None   # layer names to keep visible

v = lay.LayoutView()
v.load_layout(gds, True)
v.load_layer_props(lyp)
v.max_hier()
v.set_config("background-color", "#ffffff")
v.set_config("grid-visible", "false")
v.set_config("text-visible", "false")
if only:
    it = v.begin_layers()
    while not it.at_end():
        lp = it.current()
        name = lp.source or ""          # the GF180MCU .lyp names layers in the source: "Metal4 46/0@1"
        lp.visible = any(name.lower().startswith(o.lower() + " ") for o in only)
        v.set_layer_properties(it, lp)
        it.next()
if box:
    v.zoom_box(db.DBox(*box))
    height = int(width * (box[3] - box[1]) / (box[2] - box[0]))
else:
    v.zoom_fit()
    height = width
v.save_image(out, width, height)
print("saved", out, width, height)
