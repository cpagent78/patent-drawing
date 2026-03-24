"""
edge_router.py — Self-Contained Orthogonal Edge Router
USPTO Patent Drawing Engine — Research7

Features:
  1. Rounded Corner Rendering   — Bezier (CURVE3) arcs at waypoints
  2. Orthogonal Path Calculation — horizontal/vertical segments only
  3. Obstacle Avoidance         — segment-box intersection → reroute
  4. Channel Offset              — shared channels auto-offset to prevent overlap
  5. Arrowhead (Path-based)      — direct Path/PathPatch, not annotate()

Usage:
    from edge_router import EdgeRouter

    router = EdgeRouter(corner_radius=0.08)
    router.add_obstacle(1.0, 5.0, 3.0, 6.0)  # (x1, y1, x2, y2) bottom-left + top-right

    waypoints = router.route(
        src_pt=(2.0, 9.0), dst_pt=(2.0, 3.0),
        src_side='bottom', dst_side='top'
    )
    router.draw(ax, waypoints, color='black', lw=1.3, arrowhead=True)
"""

import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.path as mpath


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _unit(a, b):
    """Unit vector from a→b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy)
    if d < 1e-12:
        return (0.0, 0.0)
    return (dx / d, dy / d)


def _seg_intersects_rect(p1, p2, rx1, ry1, rx2, ry2, margin=0.03):
    """
    Return True if segment p1→p2 passes through rectangle [rx1,ry1,rx2,ry2]
    (expanded by margin).
    Uses Cohen-Sutherland / parametric clipping.
    """
    # Expand rect by margin
    rx1 -= margin; ry1 -= margin
    rx2 += margin; ry2 += margin

    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1

    t_min, t_max = 0.0, 1.0

    def clip(p, q):
        nonlocal t_min, t_max
        if p == 0:
            return q >= 0
        if p < 0:
            r = q / p
            if r > t_max:
                return False
            if r > t_min:
                t_min = r
        else:
            r = q / p
            if r < t_min:
                return False
            if r < t_max:
                t_max = r
        return True

    if not clip(-dx, x1 - rx1): return False
    if not clip( dx, rx2 - x1): return False
    if not clip(-dy, y1 - ry1): return False
    if not clip( dy, ry2 - y1): return False
    return t_min < t_max


def _path_intersects_obstacle(pts, rx1, ry1, rx2, ry2, margin=0.03):
    """Check if any segment of pts intersects the given obstacle rectangle."""
    for i in range(len(pts) - 1):
        if _seg_intersects_rect(pts[i], pts[i+1], rx1, ry1, rx2, ry2, margin):
            return True
    return False


def _remove_duplicates(pts):
    """Remove consecutive duplicate/near-duplicate points."""
    if not pts:
        return pts
    result = [pts[0]]
    for p in pts[1:]:
        if _dist(result[-1], p) > 1e-6:
            result.append(p)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# EdgeRouter
# ─────────────────────────────────────────────────────────────────────────────

class EdgeRouter:
    """
    Self-contained orthogonal edge router with:
    - Rounded corner Bezier rendering
    - Obstacle avoidance (axis-aligned rerouting)
    - Channel offset (prevent overlap on shared channels)
    - Path-based arrowhead (no annotate())
    """

    # Arrowhead geometry (inches)
    ARROW_HEAD_LENGTH = 0.10
    ARROW_HEAD_WIDTH  = 0.055

    def __init__(self, corner_radius: float = 0.08):
        self.corner_radius = corner_radius
        self.obstacles: list = []    # list of (x1,y1,x2,y2)
        # Channel tracking: maps channel_key → list of offset values already used
        # For vertical channels: key = ('V', round(x,4))
        # For horizontal channels: key = ('H', round(y,4))
        self._channel_usage: dict = {}
        self._channel_offset_step = 0.12   # inches between parallel overlapping edges

    # ── Obstacle registration ─────────────────────────────────────────────────

    def add_obstacle(self, x1: float, y1: float, x2: float, y2: float):
        """Register a node bounding box as an obstacle for routing."""
        self.obstacles.append((
            min(x1, x2), min(y1, y2),
            max(x1, x2), max(y1, y2)
        ))

    def clear_obstacles(self):
        self.obstacles.clear()

    def clear_channels(self):
        self._channel_usage.clear()

    def reset(self):
        self.clear_obstacles()
        self.clear_channels()

    # ── Orthogonal routing ────────────────────────────────────────────────────

    def route(self, src_pt: tuple, dst_pt: tuple,
              src_side: str = 'bottom', dst_side: str = 'top',
              prefer_side: str = 'left') -> list:
        """
        Compute orthogonal waypoints from src_pt to dst_pt.

        src_side / dst_side: 'top' | 'bottom' | 'left' | 'right'
            The direction from which the edge exits / enters the node.

        prefer_side: 'left' | 'right'
            When a simple straight path hits an obstacle, which side to detour around.

        Returns:
            list of (x, y) tuples — the orthogonal waypoints (including endpoints).
        """
        sx, sy = src_pt
        ex, ey = dst_pt

        # Build candidate path based on src/dst sides
        pts = self._build_initial_path(sx, sy, ex, ey, src_side, dst_side)

        # Apply obstacle avoidance
        pts = self._avoid_obstacles(pts, prefer_side)

        # Apply channel offset to prevent overlap
        pts = self._apply_channel_offset(pts, src_side, dst_side)

        return _remove_duplicates(pts)

    def _build_initial_path(self, sx, sy, ex, ey, src_side, dst_side) -> list:
        """Build the initial (possibly naive) orthogonal path."""
        # Exit direction from src
        STUB = 0.20   # minimum stub length before first turn

        src_exits = {
            'bottom': (sx, sy - STUB),
            'top':    (sx, sy + STUB),
            'left':   (sx - STUB, sy),
            'right':  (sx + STUB, sy),
        }
        dst_entries = {
            'top':    (ex, ey + STUB),
            'bottom': (ex, ey - STUB),
            'right':  (ex + STUB, ey),
            'left':   (ex - STUB, ey),
        }

        p_src_exit  = src_exits.get(src_side, (sx, sy - STUB))
        p_dst_entry = dst_entries.get(dst_side, (ex, ey + STUB))

        # Determine primary routing
        # Top→Bottom / Bottom→Top: vertical primary
        # Left→Right / Right→Left: horizontal primary
        vertical_exits   = {'top', 'bottom'}
        horizontal_exits = {'left', 'right'}

        if src_side in vertical_exits and dst_side in vertical_exits:
            # Both vertical: direct or Z-path
            pts = self._route_vv(sx, sy, ex, ey, src_side, dst_side, p_src_exit, p_dst_entry)
        elif src_side in horizontal_exits and dst_side in horizontal_exits:
            # Both horizontal: direct or Z-path
            pts = self._route_hh(sx, sy, ex, ey, src_side, dst_side, p_src_exit, p_dst_entry)
        elif src_side in vertical_exits and dst_side in horizontal_exits:
            # L-path: vertical then horizontal
            pts = self._route_vh(sx, sy, ex, ey, src_side, dst_side, p_src_exit, p_dst_entry)
        else:
            # L-path: horizontal then vertical
            pts = self._route_hv(sx, sy, ex, ey, src_side, dst_side, p_src_exit, p_dst_entry)

        return pts

    def _route_vv(self, sx, sy, ex, ey, src_side, dst_side, p0, p1) -> list:
        """Both exits vertical (top/bottom). Produces U or Z path."""
        # Direct: src exits vertically, dst enters vertically
        # If src_side=bottom and dst_side=top: normal down-flow
        #   path: src → (sx, mid_y) → (ex, mid_y) → dst
        # If src_side=bottom and dst_side=bottom: U-path (loop)
        #   path: src → down → left/right → up → dst
        # If src_side=top and dst_side=bottom: U-path going up

        pts_x0, pts_y0 = p0
        pts_x1, pts_y1 = p1

        # Flow going "with" the exit direction: straight Z or direct
        if src_side == 'bottom' and dst_side == 'top':
            if ey < sy:   # dst is below src → normal downward flow
                mid_y = (pts_y0 + pts_y1) / 2
                return [(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)]
            else:  # dst is above src → need to go around
                # Go down, then across, then up
                below_y = min(pts_y0, pts_y1) - 0.20
                return [(sx, sy), (sx, below_y), (ex, below_y), (ex, ey)]
        elif src_side == 'top' and dst_side == 'bottom':
            mid_y = (pts_y0 + pts_y1) / 2
            return [(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)]
        elif src_side == 'bottom' and dst_side == 'bottom':
            # U-path downward
            below_y = min(pts_y0, pts_y1) - 0.10
            return [(sx, sy), (sx, below_y), (ex, below_y), (ex, ey)]
        elif src_side == 'top' and dst_side == 'top':
            # U-path upward
            above_y = max(pts_y0, pts_y1) + 0.10
            return [(sx, sy), (sx, above_y), (ex, above_y), (ex, ey)]
        else:
            mid_y = (pts_y0 + pts_y1) / 2
            return [(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)]

    def _route_hh(self, sx, sy, ex, ey, src_side, dst_side, p0, p1) -> list:
        """Both exits horizontal."""
        pts_x0, pts_y0 = p0
        pts_x1, pts_y1 = p1

        if src_side == 'right' and dst_side == 'left':
            mid_x = (pts_x0 + pts_x1) / 2
            return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]
        elif src_side == 'left' and dst_side == 'right':
            mid_x = (pts_x0 + pts_x1) / 2
            return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]
        elif src_side == 'right' and dst_side == 'right':
            right_x = max(pts_x0, pts_x1) + 0.10
            return [(sx, sy), (right_x, sy), (right_x, ey), (ex, ey)]
        elif src_side == 'left' and dst_side == 'left':
            left_x = min(pts_x0, pts_x1) - 0.10
            return [(sx, sy), (left_x, sy), (left_x, ey), (ex, ey)]
        else:
            mid_x = (pts_x0 + pts_x1) / 2
            return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]

    def _route_vh(self, sx, sy, ex, ey, src_side, dst_side, p0, p1) -> list:
        """Source vertical, dest horizontal — L-path."""
        # Go vertically to dest y-level, then horizontally
        return [(sx, sy), (sx, ey), (ex, ey)]

    def _route_hv(self, sx, sy, ex, ey, src_side, dst_side, p0, p1) -> list:
        """Source horizontal, dest vertical — L-path."""
        return [(sx, sy), (ex, sy), (ex, ey)]

    # ── Obstacle avoidance ────────────────────────────────────────────────────

    def _avoid_obstacles(self, pts: list, prefer_side: str = 'left') -> list:
        """
        If any segment of pts intersects an obstacle, reroute around it.
        Simple iterative approach: fix one collision at a time, up to 5 passes.
        """
        for _ in range(5):
            new_pts = self._single_avoidance_pass(pts, prefer_side)
            if new_pts == pts:
                break
            pts = _remove_duplicates(new_pts)
        return pts

    def _single_avoidance_pass(self, pts: list, prefer_side: str) -> list:
        """One pass of obstacle avoidance: fix first collision found."""
        MARGIN = 0.06  # clearance from obstacle edge

        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i+1]
            for (ox1, oy1, ox2, oy2) in self.obstacles:
                if _seg_intersects_rect(p1, p2, ox1, oy1, ox2, oy2, MARGIN):
                    # Reroute this segment around the obstacle
                    bypass = self._compute_bypass(p1, p2, ox1, oy1, ox2, oy2,
                                                  MARGIN, prefer_side)
                    if bypass:
                        new_pts = pts[:i] + bypass + pts[i+2:]
                        return _remove_duplicates(new_pts)
        return pts

    def _compute_bypass(self, p1, p2, ox1, oy1, ox2, oy2,
                        margin: float, prefer_side: str) -> list:
        """
        Compute a bypass path around obstacle [ox1,oy1,ox2,oy2].
        Returns list of points replacing the segment p1→p2.
        """
        x1, y1 = p1
        x2, y2 = p2
        MARGIN = margin

        is_vertical   = abs(x2 - x1) < 0.001
        is_horizontal = abs(y2 - y1) < 0.001

        if is_vertical:
            # Going vertically: go around left or right
            if prefer_side == 'left':
                bx = ox1 - MARGIN
            else:
                bx = ox2 + MARGIN
            return [(x1, y1), (bx, y1), (bx, y2), (x2, y2)]

        elif is_horizontal:
            # Going horizontally: go around above or below
            if prefer_side == 'left':  # 'left' means 'above' for horizontal
                by = oy2 + MARGIN
            else:
                by = oy1 - MARGIN
            return [(x1, y1), (x1, by), (x2, by), (x2, y2)]

        else:
            # Diagonal (shouldn't happen in orthogonal routing, but fallback)
            if prefer_side == 'left':
                bx = ox1 - MARGIN
                return [(x1, y1), (bx, y1), (bx, y2), (x2, y2)]
            else:
                bx = ox2 + MARGIN
                return [(x1, y1), (bx, y1), (bx, y2), (x2, y2)]

    # ── Channel offset ────────────────────────────────────────────────────────

    def _apply_channel_offset(self, pts: list, src_side: str, dst_side: str) -> list:
        """
        Detect if this path shares a vertical or horizontal channel with a
        previously registered path, and offset accordingly to prevent overlap.

        Channel = the middle segments (not the endpoints stubs).
        """
        if len(pts) < 3:
            return pts

        new_pts = list(pts)

        for i in range(1, len(new_pts) - 1):
            seg_start = new_pts[i - 1]
            seg_end   = new_pts[i]
            is_vert = abs(seg_end[0] - seg_start[0]) < 0.001
            is_horiz = abs(seg_end[1] - seg_start[1]) < 0.001

            if is_vert:
                key = ('V', round(new_pts[i][0], 3))
                offset = self._get_channel_offset(key)
                if offset != 0.0:
                    # Shift this vertical segment (and connecting points) laterally
                    # Adjust all points that share this x coordinate (interior only)
                    new_pts = self._shift_vertical_channel(new_pts, new_pts[i][0], offset, i)
                    break  # re-evaluate after shift

            elif is_horiz:
                key = ('H', round(new_pts[i][1], 3))
                offset = self._get_channel_offset(key)
                if offset != 0.0:
                    new_pts = self._shift_horizontal_channel(new_pts, new_pts[i][1], offset, i)
                    break

        return new_pts

    def _get_channel_offset(self, key) -> float:
        """
        Register usage of a channel key. Return the offset to apply for this edge.
        First user: offset=0; second: +step; third: -step; fourth: +2*step, etc.
        """
        if key not in self._channel_usage:
            self._channel_usage[key] = []
        usages = self._channel_usage[key]
        n = len(usages)
        if n == 0:
            offset = 0.0
        elif n % 2 == 1:
            offset = self._channel_offset_step * ((n + 1) // 2)
        else:
            offset = -self._channel_offset_step * (n // 2)
        usages.append(offset)
        return offset

    def _shift_vertical_channel(self, pts, orig_x, offset, seg_idx) -> list:
        """Shift points at orig_x (interior) laterally by offset."""
        new_x = orig_x + offset
        new_pts = []
        for i, (px, py) in enumerate(pts):
            if i == 0 or i == len(pts) - 1:
                new_pts.append((px, py))
            elif abs(px - orig_x) < 0.001:
                new_pts.append((new_x, py))
            else:
                new_pts.append((px, py))
        # Fix connecting horizontal segments
        result = []
        for i, (px, py) in enumerate(new_pts):
            if i == 0 or i == len(new_pts) - 1:
                result.append((px, py))
                continue
            prev = new_pts[i - 1] if i > 0 else (px, py)
            nxt  = new_pts[i + 1] if i < len(new_pts) - 1 else (px, py)
            # If previous and next are on different x/y, we may need an elbow insert
            result.append((px, py))
        return result

    def _shift_horizontal_channel(self, pts, orig_y, offset, seg_idx) -> list:
        """Shift points at orig_y (interior) vertically by offset."""
        new_y = orig_y + offset
        new_pts = []
        for i, (px, py) in enumerate(pts):
            if i == 0 or i == len(pts) - 1:
                new_pts.append((px, py))
            elif abs(py - orig_y) < 0.001:
                new_pts.append((px, new_y))
            else:
                new_pts.append((px, py))
        return new_pts

    # ── Path construction (rounded corners) ──────────────────────────────────

    def make_path(self, waypoints: list) -> mpath.Path:
        """
        Convert waypoints → matplotlib Path with rounded corners.
        Uses quadratic Bezier (CURVE3) at each interior corner.

        At corner B (between A and C):
          - LINE_TO  B - unit(A→B) * r
          - CURVE3 control=B, end=B + unit(B→C) * r
        Then LINE_TO next segment start...

        Returns a matplotlib.path.Path object.
        """
        pts = _remove_duplicates(waypoints)
        n = len(pts)

        if n < 2:
            if n == 1:
                verts = [pts[0], pts[0]]
                codes = [mpath.Path.MOVETO, mpath.Path.LINETO]
            else:
                return mpath.Path([(0, 0)], [mpath.Path.MOVETO])
            return mpath.Path(verts, codes)

        if n == 2:
            verts = [pts[0], pts[1]]
            codes = [mpath.Path.MOVETO, mpath.Path.LINETO]
            return mpath.Path(verts, codes)

        # n >= 3: rounded corners at interior points
        verts = []
        codes = []
        r = self.corner_radius

        # Start
        verts.append(pts[0])
        codes.append(mpath.Path.MOVETO)

        for i in range(1, n - 1):
            A = pts[i - 1]
            B = pts[i]
            C = pts[i + 1]

            # Unit vectors
            uAB = _unit(A, B)
            uBC = _unit(B, C)

            # Distance clamp: can't use more than half the segment length
            dist_AB = _dist(A, B)
            dist_BC = _dist(B, C)
            radius = min(r, dist_AB / 2, dist_BC / 2)

            # Arc entry point (on segment A→B, radius before B)
            arc_entry = (B[0] - uAB[0] * radius, B[1] - uAB[1] * radius)
            # Arc exit point (on segment B→C, radius after B)
            arc_exit  = (B[0] + uBC[0] * radius, B[1] + uBC[1] * radius)

            # Line to arc entry
            verts.append(arc_entry)
            codes.append(mpath.Path.LINETO)

            # Quadratic Bezier: control=B, end=arc_exit
            verts.append(B)           # control point
            codes.append(mpath.Path.CURVE3)
            verts.append(arc_exit)    # end point
            codes.append(mpath.Path.CURVE3)

        # Final line to last point
        verts.append(pts[-1])
        codes.append(mpath.Path.LINETO)

        return mpath.Path(verts, codes)

    # ── Arrowhead ─────────────────────────────────────────────────────────────

    def make_arrowhead(self, tip: tuple, direction: tuple,
                       length: float = None, width: float = None) -> mpath.Path:
        """
        Build a filled triangle arrowhead Path.

        tip: (x, y) — tip of the arrowhead (= dst point on box boundary)
        direction: (dx, dy) — unit vector pointing TOWARD the tip
        length: arrow head length in inches
        width: arrow head half-width in inches
        """
        length = length or self.ARROW_HEAD_LENGTH
        width  = width  or self.ARROW_HEAD_WIDTH

        dx, dy = direction
        d = math.hypot(dx, dy)
        if d < 1e-12:
            return mpath.Path([(0, 0)], [mpath.Path.MOVETO])
        ux, uy = dx / d, dy / d

        # Base center (back from tip)
        bx = tip[0] - ux * length
        by = tip[1] - uy * length

        # Perpendicular vector
        px, py = -uy, ux

        # Three vertices of the triangle
        left  = (bx + px * width, by + py * width)
        right = (bx - px * width, by - py * width)

        verts = [tip, left, right, tip]
        codes = [
            mpath.Path.MOVETO,
            mpath.Path.LINETO,
            mpath.Path.LINETO,
            mpath.Path.CLOSEPOLY,
        ]
        return mpath.Path(verts, codes)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, ax, waypoints: list,
             color: str = 'black', lw: float = 1.3,
             arrowhead: bool = True,
             arrowhead_start: bool = False,
             linestyle: str = '-',
             zorder_line: int = 4,
             zorder_arrow: int = 13) -> None:
        """
        Render the path to ax.

        waypoints: list of (x,y) tuples from route() or manual
        arrowhead: draw filled arrowhead at destination (end)
        arrowhead_start: also draw arrowhead at source (for bidir)
        """
        pts = _remove_duplicates(waypoints)
        if len(pts) < 2:
            return

        # 1. Build and draw the main path (excluding last stub inside arrowhead)
        path = self.make_path(pts)
        patch = mpatches.PathPatch(
            path,
            facecolor='none',
            edgecolor=color,
            linewidth=lw,
            linestyle=linestyle,
            capstyle='round',
            joinstyle='round',
            zorder=zorder_line
        )
        ax.add_patch(patch)

        # 2. Draw arrowhead at end
        if arrowhead and len(pts) >= 2:
            tip = pts[-1]
            direction = _unit(pts[-2], pts[-1])
            if direction != (0.0, 0.0):
                ah_path = self.make_arrowhead(tip, direction)
                ah_patch = mpatches.PathPatch(
                    ah_path,
                    facecolor=color,
                    edgecolor=color,
                    linewidth=0,
                    zorder=zorder_arrow
                )
                ax.add_patch(ah_patch)

        # 3. Draw arrowhead at start (bidir)
        if arrowhead_start and len(pts) >= 2:
            tip = pts[0]
            direction = _unit(pts[1], pts[0])
            if direction != (0.0, 0.0):
                ah_path = self.make_arrowhead(tip, direction)
                ah_patch = mpatches.PathPatch(
                    ah_path,
                    facecolor=color,
                    edgecolor=color,
                    linewidth=0,
                    zorder=zorder_arrow
                )
                ax.add_patch(ah_patch)

    def draw_label(self, ax, waypoints: list, text: str,
                   fontsize: float = 9.0, color: str = 'black',
                   offset_x: float = 0.10, offset_y: float = 0.06,
                   ha: str = 'left') -> None:
        """
        Place a text label near the middle segment of the route.
        """
        pts = _remove_duplicates(waypoints)
        if len(pts) < 2 or not text:
            return

        # Find best segment: longest horizontal or vertical segment (interior)
        best_idx = 0
        best_len = 0.0
        for i in range(len(pts) - 1):
            seg_len = _dist(pts[i], pts[i+1])
            if seg_len > best_len:
                best_len = seg_len
                best_idx = i

        mx = (pts[best_idx][0] + pts[best_idx+1][0]) / 2
        my = (pts[best_idx][1] + pts[best_idx+1][1]) / 2

        # Determine segment orientation
        dx = pts[best_idx+1][0] - pts[best_idx][0]
        dy = pts[best_idx+1][1] - pts[best_idx][1]
        if abs(dy) > abs(dx):
            # Vertical segment: label to the right
            label_x = mx + offset_x
            label_y = my + offset_y
        else:
            # Horizontal segment: label above
            label_x = mx
            label_y = my + offset_y

        ax.text(
            label_x, label_y, text,
            ha=ha, va='center',
            fontsize=fontsize, color=color,
            bbox=dict(facecolor='white', edgecolor='none', pad=1.5),
            zorder=20
        )


# ─────────────────────────────────────────────────────────────────────────────
# Integration helper: register all nodes from patent_figure
# ─────────────────────────────────────────────────────────────────────────────

def build_router_from_figure(fig_nodes: dict, corner_radius: float = 0.08) -> 'EdgeRouter':
    """
    Create an EdgeRouter pre-loaded with all node bounding boxes as obstacles.

    fig_nodes: dict of {node_id: FigNode} where FigNode has .box_ref (BoxRef)
    """
    router = EdgeRouter(corner_radius=corner_radius)
    for nd in fig_nodes.values():
        if nd.box_ref is not None:
            b = nd.box_ref
            router.add_obstacle(b.left, b.bot, b.right, b.top)
    return router


# ─────────────────────────────────────────────────────────────────────────────
# Quick standalone test
# ─────────────────────────────────────────────────────────────────────────────

def _test_basic():
    """Render basic test: 2-pt, L-shape, Z-shape, with rounded corners."""
    import matplotlib
    matplotlib.use('Agg')

    fig, axes = plt.subplots(1, 3, figsize=(12, 5))
    fig.patch.set_facecolor('white')

    router = EdgeRouter(corner_radius=0.10)

    for ax in axes:
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 6)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('white')

    # 2-pt straight
    ax = axes[0]
    ax.set_title('2-point (straight)', fontsize=10)
    router.draw(ax, [(0.5, 5.0), (0.5, 1.0)], color='black', lw=1.3)
    ax.text(0.8, 3.0, 'straight\ndown', fontsize=8)

    # L-shape (2 segments)
    ax = axes[1]
    ax.set_title('3-point (L-shape)', fontsize=10)
    pts = [(0.5, 5.0), (3.5, 5.0), (3.5, 1.0)]
    router.draw(ax, pts, color='black', lw=1.3)
    for p in pts:
        ax.plot(*p, 'ro', ms=4, zorder=15)
    ax.text(1.5, 5.2, 'horizontal', fontsize=8)
    ax.text(3.55, 3.0, 'down', fontsize=8)

    # Z-shape (3 segments)
    ax = axes[2]
    ax.set_title('4-point (Z-shape)', fontsize=10)
    pts = [(0.5, 5.0), (0.5, 3.0), (3.5, 3.0), (3.5, 1.0)]
    router.draw(ax, pts, color='black', lw=1.3)
    for p in pts:
        ax.plot(*p, 'ro', ms=4, zorder=15)

    plt.tight_layout()
    return fig


if __name__ == '__main__':
    fig = _test_basic()
    out = os.path.expanduser('~/.openclaw/skills/patent-drawing/research7/test_basic.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Saved: {out}")
