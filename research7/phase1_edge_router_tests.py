"""
Phase 1: EdgeRouter Basic Rendering Tests
Tests: 2-pt straight, L-shape, Z-shape, rounded corners comparison,
       bidir arrows, obstacle avoidance, channel offset.
"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from edge_router import EdgeRouter, _remove_duplicates

OUT = os.path.expanduser('~/.openclaw/skills/patent-drawing/research7')

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Path shapes (straight, L, Z, U)
# ─────────────────────────────────────────────────────────────────────────────

def test1_path_shapes():
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    fig.suptitle('Phase 1 — EdgeRouter Path Shapes', fontsize=12, fontweight='bold')
    fig.patch.set_facecolor('white')

    tests = [
        # (title, waypoints)
        ('Straight down\n(2-pt)',
         [(2.0, 5.0), (2.0, 1.0)]),
        ('Straight right\n(2-pt)',
         [(0.5, 3.0), (3.5, 3.0)]),
        ('L-shape\n(3-pt)',
         [(0.5, 5.0), (3.5, 5.0), (3.5, 1.0)]),
        ('L-shape inv\n(3-pt)',
         [(3.5, 5.0), (0.5, 5.0), (0.5, 1.0)]),
        ('Z-shape\n(4-pt)',
         [(0.5, 5.0), (0.5, 3.0), (3.5, 3.0), (3.5, 1.0)]),
        ('Z-shape rev\n(4-pt)',
         [(3.5, 5.0), (3.5, 3.0), (0.5, 3.0), (0.5, 1.0)]),
        ('U-shape\n(4-pt loop)',
         [(1.5, 5.0), (0.3, 5.0), (0.3, 1.0), (1.5, 1.0)]),
        ('5-point\n(complex)',
         [(0.5, 5.0), (0.5, 4.0), (3.5, 4.0), (3.5, 2.0), (2.0, 2.0), (2.0, 1.0)]),
    ]

    router = EdgeRouter(corner_radius=0.12)

    for idx, (title, pts) in enumerate(tests):
        ax = axes[idx // 4][idx % 4]
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 6)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('#FAFAFA')
        ax.set_title(title, fontsize=9)

        # Draw with rounded corners
        router.draw(ax, pts, color='#1a1a2e', lw=1.5)

        # Mark waypoints
        for i, p in enumerate(pts):
            color = 'green' if i == 0 else ('red' if i == len(pts)-1 else 'blue')
            ax.plot(*p, 'o', color=color, ms=5, zorder=20)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase1_path_shapes.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Corner radius comparison
# ─────────────────────────────────────────────────────────────────────────────

def test2_corner_radius():
    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    fig.suptitle('Phase 1 — Corner Radius Comparison', fontsize=12, fontweight='bold')
    fig.patch.set_facecolor('white')

    radii = [0.0, 0.05, 0.12, 0.25]
    titles = ['r=0 (sharp)', 'r=0.05"', 'r=0.12"', 'r=0.25"']

    pts_list = [
        [(0.5, 5.0), (0.5, 3.0), (3.5, 3.0), (3.5, 1.0)],  # Z-shape
        [(0.5, 5.0), (3.5, 5.0), (3.5, 3.0), (0.5, 3.0), (0.5, 1.0)],  # S-shape
    ]

    colors = ['#1a1a2e', '#e74c3c']

    for i, (r, title) in enumerate(zip(radii, titles)):
        ax = axes[i]
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 6)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('#FAFAFA')
        ax.set_title(f'{title}', fontsize=10)

        router = EdgeRouter(corner_radius=r)

        for j, pts in enumerate(pts_list):
            router.draw(ax, pts, color=colors[j], lw=1.5)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase1_corner_radius.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Arrowhead quality
# ─────────────────────────────────────────────────────────────────────────────

def test3_arrowheads():
    fig, axes = plt.subplots(1, 3, figsize=(12, 5))
    fig.suptitle('Phase 1 — Arrowhead Directions', fontsize=12, fontweight='bold')
    fig.patch.set_facecolor('white')

    router = EdgeRouter(corner_radius=0.08)

    # Test 1: 8 directions
    ax = axes[0]
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('8 arrow directions', fontsize=9)
    cx, cy = 2.0, 2.0
    import math
    for angle_deg in range(0, 360, 45):
        angle = math.radians(angle_deg)
        ex = cx + 1.2 * math.cos(angle)
        ey = cy + 1.2 * math.sin(angle)
        # For diagonal: short line
        router.draw(ax, [(cx, cy), (ex, ey)], color='#1a1a2e', lw=1.3)

    # Test 2: Bidir arrows
    ax = axes[1]
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 6)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Bidirectional arrows', fontsize=9)

    # Horizontal bidir
    router.draw(ax, [(0.5, 5.0), (3.5, 5.0)], color='#1a1a2e', lw=1.3,
                arrowhead=True, arrowhead_start=True)
    ax.text(2.0, 5.2, 'bidir horizontal', ha='center', fontsize=8)

    # Vertical bidir
    router.draw(ax, [(2.0, 4.0), (2.0, 1.5)], color='#e74c3c', lw=1.3,
                arrowhead=True, arrowhead_start=True)
    ax.text(2.2, 2.7, 'bidir\nvertical', ha='left', fontsize=8)

    # Elbow bidir
    router.draw(ax, [(0.5, 3.0), (0.5, 1.0), (3.5, 1.0)], color='#2ecc71', lw=1.3,
                arrowhead=True, arrowhead_start=True)

    # Test 3: Labels
    ax = axes[2]
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 6)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Labels on arrows', fontsize=9)

    pts1 = [(0.5, 5.0), (0.5, 3.0), (3.5, 3.0), (3.5, 1.0)]
    router.draw(ax, pts1, color='black', lw=1.3)
    router.draw_label(ax, pts1, 'Yes', fontsize=9)

    pts2 = [(3.5, 5.0), (3.5, 4.0), (0.5, 4.0), (0.5, 1.0)]
    router.draw(ax, pts2, color='#e74c3c', lw=1.3)
    router.draw_label(ax, pts2, 'No', fontsize=9)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase1_arrowheads.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: route() function — auto orthogonal routing
# ─────────────────────────────────────────────────────────────────────────────

def test4_auto_routing():
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Phase 1 — Automatic Orthogonal Routing', fontsize=12, fontweight='bold')
    fig.patch.set_facecolor('white')

    tests = [
        ('bottom → top\n(normal flow)',
         (2.0, 5.5), (2.0, 1.5), 'bottom', 'top'),
        ('bottom → top\n(offset)',
         (1.0, 5.5), (3.0, 1.5), 'bottom', 'top'),
        ('right → left\n(horizontal)',
         (0.5, 3.0), (3.5, 3.0), 'right', 'left'),
        ('bottom → left\n(L-path)',
         (2.0, 5.0), (3.5, 2.0), 'bottom', 'left'),
        ('right → top\n(L-path)',
         (0.5, 2.0), (3.0, 5.0), 'right', 'top'),
        ('bottom → bottom\n(U-loop)',
         (1.5, 5.0), (2.5, 1.5), 'bottom', 'bottom'),
    ]

    router = EdgeRouter(corner_radius=0.10)

    for idx, (title, src, dst, ss, ds) in enumerate(tests):
        ax = axes[idx // 3][idx % 3]
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 6)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('#FAFAFA')
        ax.set_title(title, fontsize=9)

        pts = router.route(src, dst, src_side=ss, dst_side=ds)
        router.draw(ax, pts, color='#1a1a2e', lw=1.5)

        # Mark src (green), dst (red)
        ax.plot(*src, 's', color='green', ms=7, zorder=20)
        ax.plot(*dst, 's', color='red', ms=7, zorder=20)
        ax.text(src[0]+0.1, src[1], 'SRC', fontsize=7, color='green')
        ax.text(dst[0]+0.1, dst[1], 'DST', fontsize=7, color='red')

    plt.tight_layout()
    path = os.path.join(OUT, 'phase1_auto_routing.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Obstacle avoidance
# ─────────────────────────────────────────────────────────────────────────────

def draw_box(ax, x1, y1, x2, y2, label='', color='#ADD8E6'):
    from matplotlib.patches import FancyBboxPatch
    w, h = x2 - x1, y2 - y1
    rect = mpatches.FancyBboxPatch((x1, y1), w, h,
        boxstyle='square,pad=0', linewidth=1.2,
        edgecolor='#333333', facecolor=color, zorder=5)
    ax.add_patch(rect)
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2, label, ha='center', va='center',
                fontsize=8, zorder=6)


def test5_obstacle_avoidance():
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle('Phase 1 — Obstacle Avoidance', fontsize=12, fontweight='bold')
    fig.patch.set_facecolor('white')

    # Test A: arrow tries to go through a box in the middle
    ax = axes[0]
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 8)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Vertical path blocked by box', fontsize=9)

    # Source and destination boxes
    draw_box(ax, 1.5, 6.5, 3.5, 7.5, 'Source\n100')
    draw_box(ax, 1.5, 0.5, 3.5, 1.5, 'Dest\n200')
    # Obstacle in middle
    draw_box(ax, 1.5, 3.5, 3.5, 4.5, 'Obstacle\n150', color='#FFD700')

    router = EdgeRouter(corner_radius=0.10)
    router.add_obstacle(1.5, 3.5, 3.5, 4.5)

    # Path without avoidance (for comparison — gray)
    pts_naive = [(2.5, 6.5), (2.5, 1.5)]
    router_naive = EdgeRouter(corner_radius=0.0)
    router_naive.draw(ax, pts_naive, color='#CCCCCC', lw=1.0, linestyle='--')
    ax.text(2.7, 4.0, 'naive\n(blocked)', fontsize=7, color='#999999')

    # Path with avoidance
    pts = router.route((2.5, 6.5), (2.5, 1.5), src_side='bottom', dst_side='top',
                       prefer_side='right')
    router.draw(ax, pts, color='#1a1a2e', lw=1.5)
    ax.text(3.8, 4.0, 'routed\n(avoided)', fontsize=7, color='#1a1a2e')

    # Test B: horizontal path blocked
    ax = axes[1]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Horizontal path blocked by box', fontsize=9)

    draw_box(ax, 0.5, 2.0, 1.5, 3.0, 'Src\n100')
    draw_box(ax, 6.5, 2.0, 7.5, 3.0, 'Dst\n200')
    draw_box(ax, 3.5, 1.5, 4.5, 3.5, 'Block\n150', color='#FFD700')

    router2 = EdgeRouter(corner_radius=0.10)
    router2.add_obstacle(3.5, 1.5, 4.5, 3.5)

    pts_naive2 = [(1.5, 2.5), (6.5, 2.5)]
    router_naive.draw(ax, pts_naive2, color='#CCCCCC', lw=1.0, linestyle='--')

    pts2 = router2.route((1.5, 2.5), (6.5, 2.5), src_side='right', dst_side='left',
                         prefer_side='right')
    router2.draw(ax, pts2, color='#1a1a2e', lw=1.5)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase1_obstacle_avoidance.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Channel offset
# ─────────────────────────────────────────────────────────────────────────────

def test6_channel_offset():
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle('Phase 1 — Channel Offset (prevent overlap)', fontsize=12, fontweight='bold')
    fig.patch.set_facecolor('white')

    # Test A: Multiple loop-back arrows sharing same vertical channel
    ax = axes[0]
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 8)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('3 loop-backs: without offset', fontsize=9)

    # Without offset — all same channel x
    router0 = EdgeRouter(corner_radius=0.08)
    paths = [
        [(2.5, 7.0), (1.5, 7.0), (1.5, 5.0), (2.5, 5.0)],
        [(2.5, 5.0), (1.5, 5.0), (1.5, 3.0), (2.5, 3.0)],
        [(2.5, 3.0), (1.5, 3.0), (1.5, 1.0), (2.5, 1.0)],
    ]
    colors = ['#e74c3c', '#3498db', '#2ecc71']
    for pts, c in zip(paths, colors):
        router0.draw(ax, pts, color=c, lw=1.5)
        ax.plot(*pts[0], 's', color=c, ms=5, zorder=15)
        ax.plot(*pts[-1], 's', color=c, ms=5, zorder=15)

    ax = axes[1]
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 8)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('3 loop-backs: with channel offset', fontsize=9)

    # With offset router — use route() which tracks channels
    router1 = EdgeRouter(corner_radius=0.08)
    # Register obstacles so they use the left channel
    nodes_y = [(6.5, 7.5), (4.5, 5.5), (2.5, 3.5), (0.5, 1.5)]
    for y1, y2 in nodes_y:
        router1.add_obstacle(1.8, y1, 3.2, y2)
        draw_box(ax, 1.8, y1, 3.2, y2, '', '#E8F4FD')

    # Manual offset: stagger channel_x
    offsets = [0.0, 0.18, 0.36]
    base_x = 1.5
    src_pts = [(2.5, 6.5), (2.5, 4.5), (2.5, 2.5)]
    dst_pts = [(2.5, 5.5), (2.5, 3.5), (2.5, 1.5)]
    for i, (src, dst, c) in enumerate(zip(src_pts, dst_pts, colors)):
        cx = base_x - offsets[i]
        pts = [src, (src[0], src[1]-0.2), (cx, src[1]-0.2),
               (cx, dst[1]+0.2), (dst[0], dst[1]+0.2), dst]
        router1.draw(ax, pts, color=c, lw=1.5)

    plt.tight_layout()
    path = os.path.join(OUT, 'phase1_channel_offset.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {path}")


if __name__ == '__main__':
    print("Running Phase 1 tests...")
    test1_path_shapes()
    test2_corner_radius()
    test3_arrowheads()
    test4_auto_routing()
    test5_obstacle_avoidance()
    test6_channel_offset()
    print("All Phase 1 tests complete.")
