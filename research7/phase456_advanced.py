"""
Phase 4+5+6: Advanced EdgeRouter features and visual quality validation.
- Phase 4: Obstacle avoidance on real patent figures
- Phase 5: Channel offset for multiple loopbacks
- Phase 6: Visual quality validation across figure types
"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from edge_router import EdgeRouter, _remove_duplicates, _seg_intersects_rect

OUT = os.path.expanduser('~/.openclaw/skills/patent-drawing/research7')


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Obstacle avoidance — demonstrate arrow rerouting
# ─────────────────────────────────────────────────────────────────────────────

def draw_box_patch(ax, x, y, w, h, text='', color='#E8F4FD', lw=1.2):
    rect = mpatches.FancyBboxPatch((x, y), w, h,
        boxstyle='square,pad=0', linewidth=lw,
        edgecolor='#333333', facecolor=color, zorder=5)
    ax.add_patch(rect)
    if text:
        ax.text(x+w/2, y+h/2, text, ha='center', va='center',
                fontsize=7, zorder=6, fontfamily='monospace')


def test_phase4_obstacle_avoidance():
    """Show arrows being rerouted around obstacles."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 14))
    fig.suptitle('Phase 4 — Obstacle Avoidance: Before vs After',
                 fontsize=13, fontweight='bold')
    fig.patch.set_facecolor('white')

    # Scenario 1: Vertical arrow blocked by middle box
    for col, use_avoidance in enumerate([False, True]):
        ax = axes[0][col]
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 9)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('white')
        title = 'WITH avoidance' if use_avoidance else 'WITHOUT avoidance'
        ax.set_title(f'Vertical path — {title}', fontsize=9)

        # Boxes layout
        boxes = [
            (1.5, 7.5, 2.0, 0.7, '100\nSource'),
            (1.5, 3.5, 2.0, 0.7, '150\nObstacle', '#FFE4B5'),
            (1.5, 0.5, 2.0, 0.7, '200\nDestination'),
        ]
        for bx, by, bw, bh, lbl, *opt_color in boxes:
            color = opt_color[0] if opt_color else '#E8F4FD'
            draw_box_patch(ax, bx, by, bw, bh, lbl, color)

        # Arrow: from bottom of src to top of dst
        src_pt = (2.5, 7.5)
        dst_pt = (2.5, 1.2)

        router = EdgeRouter(corner_radius=0.08)
        if use_avoidance:
            router.add_obstacle(1.5, 3.5, 3.5, 4.2)  # obstacle box
            color_arr = '#1a1a2e'
        else:
            color_arr = '#e74c3c'

        pts = router.route(src_pt, dst_pt, src_side='bottom', dst_side='top',
                           prefer_side='right')
        router.draw(ax, pts, color=color_arr, lw=1.5)

        # Show waypoints
        for i, p in enumerate(pts):
            c = 'green' if i == 0 else ('red' if i == len(pts)-1 else 'blue')
            ax.plot(*p, 'o', color=c, ms=4, zorder=20)

        if use_avoidance:
            ax.text(3.7, 3.8, '↩ rerouted\naround box', fontsize=7,
                    color='#1a1a2e', ha='left')
        else:
            ax.text(2.7, 3.8, '⚠ passes\nthrough!', fontsize=7,
                    color='#e74c3c', ha='left')

    # Scenario 2: Two arrows, same path — second gets offset
    for col, use_offset in enumerate([False, True]):
        ax = axes[1][col]
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 9)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('white')
        title = 'WITH channel offset' if use_offset else 'WITHOUT channel offset'
        ax.set_title(f'Shared channel — {title}', fontsize=9)

        # Boxes
        src_y = 7.5; dst_y = 0.5
        draw_box_patch(ax, 1.2, src_y, 2.6, 0.7, '100\nSource A + B')
        draw_box_patch(ax, 1.2, dst_y, 2.6, 0.7, '200\nDest A + B')
        # Channel on left side
        channel_x = 0.5

        # Two arrows sharing same left channel
        pts_base1 = [(1.2, src_y + 0.35), (channel_x, src_y + 0.35),
                     (channel_x, dst_y + 0.35), (1.2, dst_y + 0.35)]
        pts_base2 = [(1.2, src_y + 0.25), (channel_x, src_y + 0.25),
                     (channel_x, dst_y + 0.25), (1.2, dst_y + 0.25)]

        if use_offset:
            # Offset second arrow
            OFFSET = 0.18
            pts1 = pts_base1
            pts2 = [(p[0] - OFFSET, p[1]) for p in pts_base2]
        else:
            pts1 = pts_base1
            pts2 = pts_base2

        router = EdgeRouter(corner_radius=0.08)
        router.draw(ax, pts1, color='#e74c3c', lw=1.5)
        router.draw(ax, pts2, color='#3498db', lw=1.5)

        if use_offset:
            ax.text(0.1, 4.0, 'offset →', fontsize=7, color='#333333', ha='left')
        else:
            ax.text(0.6, 4.0, '⚠ overlap', fontsize=7, color='#e74c3c', ha='left')

    plt.tight_layout()
    path = os.path.join(OUT, 'phase4_obstacle_avoidance.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Channel offset stress test (3 parallel loopbacks)
# ─────────────────────────────────────────────────────────────────────────────

def test_phase5_channel_offset():
    """3 loopbacks with progressively staggered channels."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    fig.suptitle('Phase 5 — Channel Offset: Triple Loopback',
                 fontsize=13, fontweight='bold')
    fig.patch.set_facecolor('white')

    BOX_W, BOX_H = 2.0, 0.6
    cx = 2.8
    ys = [7.5, 5.8, 4.1, 2.4, 0.7]
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for col, use_offset in enumerate([False, True]):
        ax = axes[col]
        ax.set_xlim(-0.2, 5.2)
        ax.set_ylim(0, 9)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('white')
        title = 'WITH offsets' if use_offset else 'WITHOUT offsets (overlap)'
        ax.set_title(f'3 loopback arrows — {title}', fontsize=10)

        # Draw 5 boxes
        for i, y in enumerate(ys):
            draw_box_patch(ax, cx - BOX_W/2, y, BOX_W, BOX_H,
                           f'S{(i+1)*100}\nNode {i+1}', '#E8F4FD')

        router = EdgeRouter(corner_radius=0.10)

        # 3 loopbacks: (from box i+1 → box i) via left channel
        # base_x = 1.5 (first), with offsets going further left
        base_x = 1.5
        for i in range(3):
            src_y = ys[i+1]
            dst_y = ys[i]
            offset = i * 0.22 if use_offset else 0.0
            ch_x = base_x - offset

            # Exit from left side of src box
            src_pt = (cx - BOX_W/2, src_y + BOX_H/2)
            dst_pt = (cx - BOX_W/2, dst_y + BOX_H/2)

            pts = [
                src_pt,
                (ch_x, src_pt[1]),
                (ch_x, dst_pt[1]),
                dst_pt,
            ]
            router.draw(ax, pts, color=colors[i], lw=1.6)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase5_channel_offset.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Visual quality validation
# ─────────────────────────────────────────────────────────────────────────────

def test_phase6_quality():
    """Generate final quality comparison figures using PatentFigure API."""
    from patent_figure import PatentFigure

    # 6A: Simple flow — default vs r=0.08
    for suffix, radius in [('_default', None), ('_r08', 0.08)]:
        pf = PatentFigure('FIG. 1')
        if radius:
            pf.style(corner_radius=radius)
        pf.node('100', '100\nUser Request', shape='start')
        pf.node('110', '110\nAuthenticate')
        pf.node('120', '120\nAuthorized?', shape='diamond')
        pf.node('130', '130\nProcess Request')
        pf.node('140', '140\nReturn Error')
        pf.node('150', '150\nReturn Response', shape='end')

        pf.edge('100', '110')
        pf.edge('110', '120')
        pf.edge('120', '130', label='Yes')
        pf.edge('120', '140', label='No')
        pf.edge('130', '150')
        pf.edge('140', '110')  # loop-back

        out = os.path.join(OUT, f'phase6A_simple_flow{suffix}.png')
        pf.render(out)
        print(f"Saved: {out}")

    # 6B: LR block diagram — default vs r=0.08
    for suffix, radius in [('_default', None), ('_r08', 0.08)]:
        pf = PatentFigure('FIG. 2', direction='LR')
        if radius:
            pf.style(corner_radius=radius)

        pf.node('100', '100\nClient')
        pf.node('200', '200\nLoad\nBalancer')
        pf.node('300', '300\nApp Server\nA')
        pf.node('310', '310\nApp Server\nB')
        pf.node('400', '400\nDatabase')

        pf.edge('100', '200')
        pf.edge('200', '300')
        pf.edge('200', '310')
        pf.edge('300', '400')
        pf.edge('310', '400')
        pf.edge('300', '310', bidir=True)

        out = os.path.join(OUT, f'phase6B_lr_diagram{suffix}.png')
        pf.render(out)
        print(f"Saved: {out}")

    # 6C: Deep flow with multiple loopbacks
    for suffix, radius in [('_default', None), ('_r08', 0.08)]:
        pf = PatentFigure('FIG. 3')
        if radius:
            pf.style(corner_radius=radius)

        pf.node('100', '100\nStart', shape='start')
        pf.node('200', '200\nInit Phase')
        pf.node('210', '210\nCheck Config', shape='diamond')
        pf.node('220', '220\nLoad Config')
        pf.node('300', '300\nProcess Phase')
        pf.node('310', '310\nValidate Input', shape='diamond')
        pf.node('320', '320\nTransform Data')
        pf.node('400', '400\nOutput Phase')
        pf.node('500', '500\nEnd', shape='end')

        pf.edge('100', '200')
        pf.edge('200', '210')
        pf.edge('210', '300', label='OK')
        pf.edge('210', '220', label='Missing')
        pf.edge('220', '210')      # loop-back 1
        pf.edge('300', '310')
        pf.edge('310', '320', label='Valid')
        pf.edge('310', '300', label='Invalid')  # loop-back 2
        pf.edge('320', '400')
        pf.edge('400', '500')

        out = os.path.join(OUT, f'phase6C_deep_flow{suffix}.png')
        pf.render(out)
        print(f"Saved: {out}")


if __name__ == '__main__':
    print("Running Phase 4+5+6 tests...")
    test_phase4_obstacle_avoidance()
    test_phase5_channel_offset()
    test_phase6_quality()
    print("All Phase 4+5+6 tests complete.")
