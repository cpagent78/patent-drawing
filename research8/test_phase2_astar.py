"""
Phase 2 Test: A* Grid Routing
"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from edge_router import EdgeRouter

OUT = os.path.dirname(os.path.abspath(__file__))


def test_astar_basic():
    """Test A* routing with obstacles in the direct path."""
    router = EdgeRouter(corner_radius=0.08, grid_step=0.10)

    # Add obstacle directly in the straight path
    router.add_obstacle(1.5, 3.0, 3.0, 5.0)   # Big block in the middle

    # Route around the obstacle
    src_pt = (2.25, 7.0)  # above obstacle
    dst_pt = (2.25, 1.5)  # below obstacle

    # Standard bypass
    pts_bypass = router.route(src_pt, dst_pt, src_side='bottom', dst_side='top',
                               use_astar=False)
    # A* routing
    pts_astar = router.route(src_pt, dst_pt, src_side='bottom', dst_side='top',
                              use_astar=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 6))
    fig.suptitle('Phase 2: A* vs Cohen-Sutherland Routing', fontsize=12)

    for ax, pts, title in [(axes[0], pts_bypass, 'Cohen-Sutherland Bypass'),
                            (axes[1], pts_astar, 'A* Grid Routing (auto-fallback)')]:
        ax.set_xlim(0, 4.5)
        ax.set_ylim(0.5, 8.0)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=10)
        ax.set_facecolor('white')

        # Draw obstacle
        import matplotlib.patches as mpatches
        ax.add_patch(mpatches.Rectangle((1.5, 3.0), 1.5, 2.0,
                     facecolor='#DDDDDD', edgecolor='black', lw=1.5))
        ax.text(2.25, 4.0, 'OBSTACLE', ha='center', va='center', fontsize=9)

        # Draw path
        router2 = EdgeRouter(corner_radius=0.08)
        router2.add_obstacle(1.5, 3.0, 3.0, 5.0)
        router2.draw(ax, pts, color='blue', lw=2.0, arrowhead=True)

        # Mark waypoints
        for x, y in pts:
            ax.plot(x, y, 'ro', ms=4, zorder=15)

        ax.text(2.25, 7.2, 'START', ha='center', fontsize=8, color='green')
        ax.text(2.25, 1.3, 'END', ha='center', fontsize=8, color='red')
        ax.axis('off')

    plt.tight_layout()
    out = os.path.join(OUT, 'fig_astar_test.png')
    fig.savefig(out, dpi=120, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'  Saved: {out}')
    print(f'  Bypass waypoints: {len(pts_bypass)}')
    print(f'  A* waypoints: {len(pts_astar)}')
    return out


def test_astar_in_figure():
    """Phase 2 + PatentFigure: C: 3중 루프백 + A* 회피"""
    from patent_figure import PatentFigure

    fig = PatentFigure('FIG. C', direction='TB')
    fig.style(corner_radius=0.08)  # Enables EdgeRouter (which now has A*)

    fig.node('S100', 'S100\nInitialize', shape='start')
    fig.node('S200', 'S200\nValidate Input')
    fig.node('S210', 'S210\nValid?', shape='diamond')
    fig.node('S300', 'S300\nProcess Data')
    fig.node('S310', 'S310\nProcessed OK?', shape='diamond')
    fig.node('S400', 'S400\nStore Result')
    fig.node('S410', 'S410\nStored?', shape='diamond')
    fig.node('S500', 'S500\nNotify User')
    fig.node('S600', 'S600\nComplete', shape='end')

    fig.edge('S100', 'S200')
    fig.edge('S200', 'S210')
    fig.edge('S210', 'S300', label='Y')
    fig.edge('S210', 'S200', label='N')   # loop back 1
    fig.edge('S300', 'S310')
    fig.edge('S310', 'S400', label='Y')
    fig.edge('S310', 'S300', label='N')   # loop back 2
    fig.edge('S400', 'S410')
    fig.edge('S410', 'S500', label='Y')
    fig.edge('S410', 'S400', label='N')   # loop back 3
    fig.edge('S500', 'S600')

    out = os.path.join(OUT, 'fig_C_triple_loopback.png')
    fig.render(out, auto_split=False)
    print(f'  Saved: {out}')
    return out


if __name__ == '__main__':
    print('=== Phase 2: A* Routing Test ===')
    test_astar_basic()
    test_astar_in_figure()
    print('  PASS')
