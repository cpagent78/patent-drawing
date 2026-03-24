"""
Phase 2: Side-by-side comparison — Old annotate() vs EdgeRouter
Generates same diagram twice using both methods.
"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import math

from edge_router import EdgeRouter

OUT = os.path.expanduser('~/.openclaw/skills/patent-drawing/research7')

# ── Drawing constants (matching patent_drawing_lib) ────────────────────────
LW_ARR   = 1.3
LW_BOX   = 1.5
FS_BODY  = 10
BOX_EDGE = 'black'
Z_ARROW     = 4
Z_ARROWHEAD = 13
Z_BOX_FILL  = 10
Z_BOX_EDGE  = 11
Z_BOX_TEXT  = 12

def draw_rect_box(ax, x, y, w, h, text, fs=10):
    """Draw a simple patent-style rectangle box."""
    from matplotlib.patches import FancyBboxPatch
    rect = FancyBboxPatch((x, y), w, h,
        boxstyle='square,pad=0',
        linewidth=LW_BOX, edgecolor=BOX_EDGE,
        facecolor='white', zorder=Z_BOX_FILL)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fs, zorder=Z_BOX_TEXT, fontfamily='monospace')
    return (x, y, w, h)  # (x, y, w, h) box spec

def box_center(b): return (b[0]+b[2]/2, b[1]+b[3]/2)
def box_top(b): return (b[0]+b[2]/2, b[1]+b[3])
def box_bot(b): return (b[0]+b[2]/2, b[1])
def box_left(b): return (b[0], b[1]+b[3]/2)
def box_right(b): return (b[0]+b[2], b[1]+b[3]/2)

def draw_diamond(ax, cx, cy, w, h, text, fs=9):
    import numpy as np
    verts = np.array([
        [cx, cy + h/2],  # top
        [cx + w/2, cy],  # right
        [cx, cy - h/2],  # bottom
        [cx - w/2, cy],  # left
        [cx, cy + h/2],  # close
    ])
    from matplotlib.patches import Polygon
    poly = Polygon(verts[:-1], closed=True,
                   linewidth=LW_BOX, edgecolor=BOX_EDGE,
                   facecolor='white', zorder=Z_BOX_FILL)
    ax.add_patch(poly)
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fs,
            zorder=Z_BOX_TEXT, fontfamily='monospace')
    return (cx - w/2, cy - h/2, w, h)


# ─────────────────────────────────────────────────────────────────────────────
# OLD METHOD: annotate() / ax.plot()
# ─────────────────────────────────────────────────────────────────────────────

def draw_old_arrow(ax, pts):
    """Old method: plot segments + annotate for arrowhead."""
    n = len(pts)
    if n < 2:
        return
    OVERSHOOT = 0.02
    for i in range(n - 2):
        x0, y0 = pts[i]
        x1, y1 = pts[i+1]
        if i + 2 < n:
            nx, ny = pts[i+2]
            dx = nx - x1; dy = ny - y1
            dist = max((dx**2+dy**2)**0.5, 1e-9)
            ox = x1 + dx/dist*OVERSHOOT
            oy = y1 + dy/dist*OVERSHOOT
        else:
            ox, oy = x1, y1
        ax.plot([x0, ox], [y0, oy], color=BOX_EDGE, lw=LW_ARR,
                solid_capstyle='round', zorder=Z_ARROW)
    ax.annotate('', xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle='->', color=BOX_EDGE,
                                shrinkA=0, shrinkB=0, lw=LW_ARR,
                                mutation_scale=12),
                zorder=Z_ARROWHEAD)


# ─────────────────────────────────────────────────────────────────────────────
# Comparison Test A: Flowchart (FIG.6-style)
# ─────────────────────────────────────────────────────────────────────────────

def test_A_flowchart():
    """FIG.6-style flowchart: old vs EdgeRouter."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 10))
    fig.suptitle('Phase 2A — Flowchart: annotate() vs EdgeRouter', 
                 fontsize=13, fontweight='bold')
    fig.patch.set_facecolor('white')

    # Layout (same for both)
    BOX_W, BOX_H = 2.2, 0.65
    DIA_W, DIA_H = 2.0, 1.0
    cx = 3.5       # center x
    page_h = 9.5
    y_gap = 1.1

    ys = [page_h - i * y_gap for i in range(7)]

    # Box specs (x, y, w, h)
    b_start = (cx - BOX_W/2, ys[0] - BOX_H/2, BOX_W, BOX_H)
    b_s400  = (cx - BOX_W/2, ys[1] - BOX_H/2, BOX_W, BOX_H)
    b_s402  = (cx - BOX_W/2, ys[2] - BOX_H/2, BOX_W, BOX_H)
    b_dia   = (cx - DIA_W/2, ys[3] - DIA_H/2, DIA_W, DIA_H)
    b_s410y = (cx - BOX_W/2, ys[4] - BOX_H/2, BOX_W, BOX_H)
    b_s404  = (cx + DIA_W/2 + 0.2, ys[3] - BOX_H/2, BOX_W, BOX_H)  # right branch
    b_end   = (cx - BOX_W/2, ys[5] - BOX_H/2, BOX_W, BOX_H)

    def draw_diagram(ax, use_edgerouter):
        ax.set_xlim(0.5, 7)
        ax.set_ylim(3.0, 10.5)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('white')
        method = 'EdgeRouter' if use_edgerouter else 'annotate()'
        ax.set_title(f'Method: {method}', fontsize=11, fontweight='bold',
                     color='#1a1a2e' if use_edgerouter else '#888888')
        ax.text(0.5, 0.98, method, transform=ax.transAxes,
                ha='left', va='top', fontsize=9,
                color='#1a1a2e' if use_edgerouter else '#888888',
                fontweight='bold')

        # Draw boxes
        draw_rect_box(ax, *b_start, 'S400\nVisit offline shop', fs=8)
        draw_rect_box(ax, *b_s400,  'S402\nShopping in store', fs=8)
        draw_rect_box(ax, *b_s402,  'S404\nOrdering a camera', fs=8)
        draw_diamond(ax, cx, ys[3], DIA_W, DIA_H, 'S410\nPaying?', fs=8)
        draw_rect_box(ax, *b_s410y, 'S412\nProcess payment', fs=8)
        draw_rect_box(ax, *b_s404,  'S406\nNo pay\nprocess', fs=8)
        draw_rect_box(ax, *b_end,   'S416\nPayment complete', fs=8)

        # Edge routes (same waypoints for both methods)
        edges = [
            # start → s400
            [box_bot(b_start), box_top(b_s400)],
            # s400 → s402
            [box_bot(b_s400), box_top(b_s402)],
            # s402 → diamond top
            [box_bot(b_s402), (cx, ys[3] + DIA_H/2)],
            # diamond bottom → s410y top (Yes)
            [(cx, ys[3] - DIA_H/2), box_top(b_s410y)],
            # s410y → end
            [box_bot(b_s410y), box_top(b_end)],
        ]

        # Right branch: diamond right → s404
        dia_right = (cx + DIA_W/2, ys[3])
        s404_left = box_left(b_s404)
        edges_elbow = [
            [dia_right, s404_left],
        ]

        # Loop-back: s404 → s402 via left channel
        s404_bot = box_bot(b_s404)
        s402_right = box_right(b_s402)
        loop_pts = [
            s404_bot,
            (s404_bot[0], ys[2]),
            (s402_right[0] + 0.20, ys[2]),
            s402_right,
        ]

        if use_edgerouter:
            router = EdgeRouter(corner_radius=0.08)
            for pts in edges:
                router.draw(ax, pts, color='black', lw=LW_ARR)
            for pts in edges_elbow:
                router.draw(ax, pts, color='black', lw=LW_ARR)
            router.draw(ax, loop_pts, color='#e74c3c', lw=LW_ARR)
            # Labels
            ax.text(cx + 0.15, ys[3] - 0.15, 'Yes', fontsize=8, color='black')
            ax.text(cx + DIA_W/2 + 0.05, ys[3] + 0.10, 'No', fontsize=8, color='black')
        else:
            for pts in edges:
                draw_old_arrow(ax, pts)
            for pts in edges_elbow:
                draw_old_arrow(ax, pts)
            draw_old_arrow(ax, loop_pts)
            ax.text(cx + 0.15, ys[3] - 0.15, 'Yes', fontsize=8, color='black')
            ax.text(cx + DIA_W/2 + 0.05, ys[3] + 0.10, 'No', fontsize=8, color='black')

    draw_diagram(axes[0], use_edgerouter=False)
    draw_diagram(axes[1], use_edgerouter=True)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase2A_flowchart_compare.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Comparison Test B: Loopback arrows (old joint gap vs rounded)
# ─────────────────────────────────────────────────────────────────────────────

def test_B_loopback():
    """Loopback arrows: highlight the joint gap fix."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle('Phase 2B — Loopback Arrows: annotate() vs EdgeRouter',
                 fontsize=13, fontweight='bold')
    fig.patch.set_facecolor('white')

    def draw_loopbacks(ax, use_edgerouter):
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 9)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('white')
        method = 'EdgeRouter' if use_edgerouter else 'annotate()'
        ax.set_title(f'{method}', fontsize=11, fontweight='bold')

        # 4 stacked boxes + 3 loopback arrows
        BOX_W, BOX_H = 1.8, 0.6
        cx = 2.5
        ys = [7.8, 5.8, 3.8, 1.8]
        boxes = [(cx - BOX_W/2, y - BOX_H/2, BOX_W, BOX_H) for y in ys]
        labels = ['S100\nStart', 'S200\nProcess A', 'S300\nProcess B', 'S400\nEnd']

        for b, lbl in zip(boxes, labels):
            draw_rect_box(ax, *b, lbl, fs=8)

        # 3 loopback routes (using different channel x offsets)
        CHANNEL_X = [1.2, 0.8, 0.4]
        router = EdgeRouter(corner_radius=0.10)

        for i in range(3):
            src_b = boxes[i+1]   # from lower box
            dst_b = boxes[i]     # to upper box

            # Route: src left → channel → up → dst left
            src_pt = box_left(src_b)
            dst_pt = box_left(dst_b)
            cx_ch = CHANNEL_X[i]

            pts = [
                src_pt,
                (cx_ch, src_pt[1]),
                (cx_ch, dst_pt[1]),
                dst_pt
            ]

            c = ['#e74c3c', '#3498db', '#2ecc71'][i]
            if use_edgerouter:
                router.draw(ax, pts, color=c, lw=1.5)
            else:
                draw_old_arrow(ax, pts)
                # Note: old method uses ax.plot which can leave gaps at corners

        if not use_edgerouter:
            ax.text(2.5, 0.3, '⚠ corner gap visible (OVERSHOOT fix)',
                    ha='center', fontsize=7, color='#888888')
        else:
            ax.text(2.5, 0.3, '✓ smooth rounded corners',
                    ha='center', fontsize=7, color='#2ecc71')

    draw_loopbacks(axes[0], False)
    draw_loopbacks(axes[1], True)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase2B_loopback_compare.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Comparison Test C: Corner detail zoom
# ─────────────────────────────────────────────────────────────────────────────

def test_C_corner_zoom():
    """Zoom in on a single corner: old (sharp) vs different radii."""
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    fig.suptitle('Phase 2C — Corner Quality Zoom: annotate() vs EdgeRouter r=0.0/0.08/0.15',
                 fontsize=11, fontweight='bold')
    fig.patch.set_facecolor('white')

    radii = [None, 0.0, 0.08, 0.15]
    titles = ['Old annotate()\n(OVERSHOOT)', 'EdgeRouter r=0\n(sharp)', 
              'EdgeRouter r=0.08\n(subtle)', 'EdgeRouter r=0.15\n(smooth)']

    # Zoomed-in Z-shape corner
    pts = [(1.0, 3.5), (1.0, 2.0), (3.0, 2.0), (3.0, 0.5)]

    for i, (r, title) in enumerate(zip(radii, titles)):
        ax = axes[i]
        ax.set_xlim(0.3, 3.7)
        ax.set_ylim(0.0, 4.0)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('#FAFAFA')
        ax.set_title(title, fontsize=9)

        # Draw guideline grid
        ax.axhline(2.0, color='#E0E0E0', lw=0.5, zorder=1)
        ax.axvline(1.0, color='#E0E0E0', lw=0.5, zorder=1)
        ax.axvline(3.0, color='#E0E0E0', lw=0.5, zorder=1)

        if r is None:
            # Old method
            draw_old_arrow(ax, pts)
        else:
            router = EdgeRouter(corner_radius=r)
            router.draw(ax, pts, color='#1a1a2e', lw=2.0)

        # Mark waypoints
        for p in pts:
            ax.plot(*p, 'o', color='#e74c3c', ms=4, zorder=20, alpha=0.5)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase2C_corner_zoom.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Run all comparisons
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Running Phase 2 comparison tests...")
    test_A_flowchart()
    test_B_loopback()
    test_C_corner_zoom()
    print("All Phase 2 tests complete.")
