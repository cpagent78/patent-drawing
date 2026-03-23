"""
patent_figure.py — Declarative Patent Figure Engine
USPTO-compliant patent drawing with zero manual coordinates.

Usage:
    from patent_figure import PatentFigure

    fig = PatentFigure('FIG. 6')
    fig.node('S400', 'Visit offline shop', shape='start')
    fig.node('S402', 'Shopping in store')
    fig.node('S404', 'Ordering a camera')
    fig.node('S410', 'Paying?', shape='diamond')
    fig.node('S416', 'Payment complete', shape='end')

    fig.edge('S400', 'S402')
    fig.edge('S410', 'S412', label='Yes')
    fig.edge('S410', 'S404', label='No')   # loop-back auto-detected

    fig.render('fig6.png')

Shapes: 'process' (default), 'start', 'end', 'diamond', 'oval', 'cylinder'
Layout: automatic top-to-bottom with back-edge detection + side-channel routing.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from patent_drawing_lib import Drawing, BoxRef

from collections import defaultdict, deque


# ── Node / Edge data ──────────────────────────────────────────────────────────

class FigNode:
    """A node in the figure."""
    __slots__ = ('id', 'text', 'shape', 'rank', 'box_ref', '_w', '_h')

    def __init__(self, id: str, text: str, shape: str = 'process'):
        self.id = id
        self.text = text
        self.shape = shape      # process | start | end | diamond | oval | cylinder
        self.rank = 0
        self.box_ref = None     # filled after layout
        self._w = 0.0
        self._h = 0.0


class FigEdge:
    """An edge (arrow) between two nodes."""
    __slots__ = ('src_id', 'dst_id', 'label', 'is_back')

    def __init__(self, src_id: str, dst_id: str, label: str = ''):
        self.src_id = src_id
        self.dst_id = dst_id
        self.label = label
        self.is_back = False    # True if this is a loop-back edge


# ── Patent Figure Engine ──────────────────────────────────────────────────────

class PatentFigure:
    """
    Declarative patent figure builder.
    Nodes + edges → automatic layout → USPTO-compliant PNG.
    """

    # USPTO page constants (portrait 8.5" × 11")
    PAGE_W = 8.5
    PAGE_H = 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15
    INNER_PAD = 0.40

    # Layout constants
    H_GAP = 0.50           # horizontal gap for same-rank nodes
    LOOPBACK_MARGIN = 0.55 # left margin for loop-back channel
    DIAMOND_W = 2.20       # diamond width
    DIAMOND_H = 1.10       # diamond height
    BOX_PAD_X = 0.22       # text padding inside boxes
    BOX_PAD_Y = 0.14
    DEFAULT_FS = 8         # default font size (patent-scale)

    def __init__(self, fig_label: str = 'FIG. 1', orientation: str = 'portrait'):
        self.fig_label = fig_label
        self.orientation = orientation
        self._nodes: dict[str, FigNode] = {}   # id → FigNode
        self._edges: list[FigEdge] = []
        self._order: list[str] = []            # insertion order

    def node(self, id: str, text: str, shape: str = 'process') -> 'PatentFigure':
        """Add a node. shape: process | start | end | diamond | oval | cylinder"""
        self._nodes[id] = FigNode(id, text, shape)
        self._order.append(id)
        return self

    def edge(self, src: str, dst: str, label: str = '') -> 'PatentFigure':
        """Add a directed edge (arrow) from src to dst."""
        self._edges.append(FigEdge(src, dst, label))
        return self

    # ── Main render pipeline ──────────────────────────────────────────────────

    def render(self, output_path: str) -> str:
        """Full pipeline: layout → draw → save. Returns output path."""
        self._assign_ranks()
        self._measure_nodes()
        positions = self._compute_positions()
        self._draw(output_path, positions)
        return output_path

    # ── Step 1: Rank assignment with back-edge detection ──────────────────────

    def _assign_ranks(self):
        """
        Assign ranks (layers) via modified Kahn's algorithm.
        Detects back-edges (cycles) and marks them for side-channel routing.
        """
        # Build adjacency
        adj = defaultdict(list)      # src → [dst_ids]
        in_deg = defaultdict(int)

        # First pass: detect back-edges via DFS
        back_edges = self._find_back_edges()
        back_set = {(e.src_id, e.dst_id) for e in back_edges}

        # Build DAG (exclude back-edges)
        for e in self._edges:
            if (e.src_id, e.dst_id) in back_set:
                e.is_back = True
                continue
            adj[e.src_id].append(e.dst_id)
            in_deg[e.dst_id] += 1

        # Kahn's on DAG
        queue = deque()
        for nid in self._order:
            if in_deg[nid] == 0:
                queue.append(nid)

        rank = {}
        while queue:
            nid = queue.popleft()
            if nid not in rank:
                rank[nid] = 0
            for dst_id in adj[nid]:
                rank[dst_id] = max(rank.get(dst_id, 0), rank[nid] + 1)
                in_deg[dst_id] -= 1
                if in_deg[dst_id] == 0:
                    queue.append(dst_id)

        # Assign to nodes
        for nid, nd in self._nodes.items():
            nd.rank = rank.get(nid, 0)

    def _find_back_edges(self) -> list[FigEdge]:
        """DFS-based back-edge detection."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in self._nodes}
        adj = defaultdict(list)
        edge_map = {}  # (src,dst) → FigEdge

        for e in self._edges:
            adj[e.src_id].append(e.dst_id)
            edge_map[(e.src_id, e.dst_id)] = e

        back = []

        def dfs(u):
            color[u] = GRAY
            for v in adj[u]:
                if v not in color:
                    continue
                if color[v] == GRAY:  # back edge!
                    back.append(edge_map[(u, v)])
                elif color[v] == WHITE:
                    dfs(v)
            color[u] = BLACK

        for nid in self._order:
            if color[nid] == WHITE:
                dfs(nid)

        return back

    # ── Step 2: Measure node sizes ────────────────────────────────────────────

    def _measure_nodes(self):
        """Compute width/height for each node based on text + shape."""
        # Use a temporary Drawing for text measurement
        d = Drawing('/dev/null')
        fs = self.DEFAULT_FS

        for nd in self._nodes.values():
            if nd.shape == 'diamond':
                nd._w = self.DIAMOND_W
                nd._h = self.DIAMOND_H
            else:
                tw, th = d.measure_text(nd.text, fs)
                nd._w = tw + self.BOX_PAD_X * 2
                nd._h = max(th + self.BOX_PAD_Y * 2, 0.45)
                nd._w = max(nd._w, 1.60)

        # Unify widths for process/start/end boxes (not diamonds)
        box_nodes = [nd for nd in self._nodes.values() if nd.shape != 'diamond']
        if box_nodes:
            max_w = max(nd._w for nd in box_nodes)
            for nd in box_nodes:
                nd._w = max_w

        # ── Fix: scale down node sizes if total height exceeds available area ──
        # Available vertical height for content
        content_y_top = self.BND_Y2 - self.INNER_PAD
        content_y_bot = self.BND_Y1 + self.INNER_PAD
        available_h = content_y_top - content_y_bot

        # Group by rank to count ranks (ranks not yet assigned — skip for now)
        # This is called AFTER _assign_ranks, so ranks are set
        from collections import defaultdict
        ranks = defaultdict(list)
        for nd in self._nodes.values():
            ranks[nd.rank].append(nd)
        max_rank = max(ranks.keys()) if ranks else 0

        # Total min height: sum of row heights with min gap
        MIN_GAP = 0.25
        total_min_h = sum(max(nd._h for nd in ranks[r]) for r in range(max_rank + 1))
        total_min_h += MIN_GAP * max_rank

        if total_min_h > available_h:
            # Scale factor: reduce box heights proportionally
            scale = available_h / total_min_h * 0.92   # 8% extra margin
            for nd in self._nodes.values():
                nd._h *= scale
                nd._h = max(nd._h, 0.35)  # absolute minimum 0.35"

        # ── Fix: scale down node widths if wide rows exceed available width ──
        content_x1 = self.BND_X1 + self.INNER_PAD + self.LOOPBACK_MARGIN
        content_x2 = self.BND_X2 - self.INNER_PAD
        available_w = content_x2 - content_x1

        # Find the widest rank
        for r, nodes in ranks.items():
            if len(nodes) > 1:
                total_row_w = sum(nd._w for nd in nodes) + self.H_GAP * (len(nodes) - 1)
                if total_row_w > available_w:
                    scale_w = available_w / total_row_w * 0.95
                    for nd in nodes:
                        nd._w *= scale_w
                        nd._w = max(nd._w, 0.80)  # absolute minimum 0.80"

    # ── Step 3: Position calculation ──────────────────────────────────────────

    def _compute_positions(self) -> dict[str, tuple[float, float]]:
        """
        Compute (cx, cy) for each node.
        Top-to-bottom layout, centered horizontally.
        """
        # Group by rank
        ranks = defaultdict(list)
        for nid in self._order:
            nd = self._nodes[nid]
            ranks[nd.rank].append(nd)

        max_rank = max(ranks.keys()) if ranks else 0

        # Available area
        content_x1 = self.BND_X1 + self.INNER_PAD + self.LOOPBACK_MARGIN
        content_x2 = self.BND_X2 - self.INNER_PAD
        content_cx = (content_x1 + content_x2) / 2

        content_y_top = self.BND_Y2 - self.INNER_PAD
        content_y_bot = self.BND_Y1 + self.INNER_PAD
        available_h = content_y_top - content_y_bot

        # Calculate total node height
        total_node_h = 0
        for r in range(max_rank + 1):
            nodes = ranks[r]
            row_h = max(nd._h for nd in nodes)
            total_node_h += row_h

        # Dynamic V_GAP: fill available space evenly
        # For branching flows, elbows need 2 × 0.44" = 0.88" between boxes
        # to avoid "too short" validator warnings.
        # Detect if this layout has branching (some ranks have > 1 node)
        has_branching = any(len(ranks[r]) > 1 for r in range(max_rank + 1))
        # For single-column linear flows, straight arrows only need 0.44"
        # For branching, elbow arrows need 0.88" minimum
        MIN_V_GAP = 0.92 if has_branching else 0.48
        n_gaps = max_rank  # gaps between ranks
        if n_gaps > 0:
            remaining = available_h - total_node_h
            if remaining <= 0:
                # Space constrained (deep flow) — use computed scale-down gap
                v_gap = max(0.20, remaining / n_gaps) if remaining > 0 else 0.20
            elif remaining / n_gaps < MIN_V_GAP:
                # Not enough space for ideal gap — compress to fit
                v_gap = max(0.20, remaining / n_gaps)
            else:
                v_gap = min(0.90, max(MIN_V_GAP, remaining / n_gaps))
        else:
            v_gap = 0.55

        total_h = total_node_h + v_gap * n_gaps

        # Clamp total_h to available_h to prevent overflow
        if total_h > available_h:
            if n_gaps > 0:
                v_gap = max(0.20, (available_h - total_node_h) / n_gaps)
            total_h = total_node_h + v_gap * n_gaps

        # Start y (top of content, going down) — clamped to boundary
        start_y = min(content_y_top, (content_y_top + content_y_bot) / 2 + total_h / 2)

        positions = {}
        cur_y = start_y

        for r in range(max_rank + 1):
            nodes = ranks[r]
            row_h = max(nd._h for nd in nodes)

            if len(nodes) == 1:
                # Single node: center horizontally
                nd = nodes[0]
                cx = content_cx
                cy = cur_y - row_h / 2
                positions[nd.id] = (cx, cy)
            else:
                # Multiple nodes: spread horizontally
                total_w = sum(nd._w for nd in nodes) + self.H_GAP * (len(nodes) - 1)
                start_x = content_cx - total_w / 2
                for nd in nodes:
                    cx = start_x + nd._w / 2
                    cy = cur_y - row_h / 2
                    positions[nd.id] = (cx, cy)
                    start_x += nd._w + self.H_GAP

            cur_y -= row_h + v_gap

        return positions

    # ── Step 4: Draw everything ───────────────────────────────────────────────

    def _draw(self, output_path: str, positions: dict):
        """Create Drawing, render all nodes and edges, save."""
        d = Drawing(output_path, fig_num=self.fig_label.replace('FIG. ', ''))

        fs = self.DEFAULT_FS

        # Draw nodes
        for nid in self._order:
            nd = self._nodes[nid]
            cx, cy = positions[nid]

            if nd.shape in ('start', 'end'):
                x = cx - nd._w / 2
                y = cy - nd._h / 2
                nd.box_ref = d.rounded_rect(x, y, nd._w, nd._h, nd.text, fs=fs, radius=0.20)
            elif nd.shape == 'diamond':
                nd.box_ref = d.decision_diamond(cx, cy, nd._w, nd._h, nd.text, fs=fs)
            elif nd.shape == 'oval':
                nd.box_ref = d.oval(cx, cy, nd._w, nd._h, nd.text, fs=fs)
            elif nd.shape == 'cylinder':
                x = cx - nd._w / 2
                y = cy - nd._h / 2
                nd.box_ref = d.database_cylinder(x, y, nd._w, nd._h, nd.text, fs=fs)
            else:  # process (default box)
                x = cx - nd._w / 2
                y = cy - nd._h / 2
                nd.box_ref = d.box(x, y, nd._w, nd._h, nd.text, fs=fs)

        # Draw forward edges (straight/elbow arrows)
        # For skip-rank edges (rank diff > 1), route via side channel to avoid
        # passing through intermediate boxes.
        all_right_edges = max(
            (nd.box_ref.right for nd in self._nodes.values() if nd.box_ref), 
            default=self.BND_X2 - self.INNER_PAD
        )
        skip_channel_x = all_right_edges + 0.35  # right side channel for skip edges

        for e in self._edges:
            if e.is_back:
                continue
            src_nd = self._nodes[e.src_id]
            dst_nd = self._nodes[e.dst_id]
            sb = src_nd.box_ref
            db = dst_nd.box_ref

            if sb is None or db is None:
                continue

            rank_diff = dst_nd.rank - src_nd.rank

            # Check if this edge skips over intermediate nodes
            is_skip = rank_diff > 1

            # Same column: straight vertical arrow (only if no intermediate boxes in path)
            if abs(sb.cx - db.cx) < 0.1 and not is_skip:
                d.arrow_v(sb, db)
            elif is_skip:
                # Skip-rank: route via right side channel to avoid crossing intermediate boxes
                d.arrow_route([
                    sb.right_mid(),
                    ('right_to', skip_channel_x),
                    ('up_to' if sb.cy < db.cy else 'down_to', db.cy),
                    db.right_mid(),
                ])
            else:
                # Elbow: down from src, horizontal, down to dst
                if abs(src_nd.rank - dst_nd.rank) == 0:
                    # Same-rank: horizontal exit from side (left or right) of src
                    if db.cx < sb.cx:
                        d.arrow_route([sb.left_mid(), db.right_mid()])
                    else:
                        d.arrow_route([sb.right_mid(), db.left_mid()])
                elif abs(src_nd.rank - dst_nd.rank) == 1:
                    # Adjacent rank: standard elbow — ensure minimum 0.44" segments
                    # by using at least 0.44" below src and above dst
                    mid_y = min(sb.bot - 0.44, max(db.top + 0.44, (sb.bot + db.top) / 2))
                    d.arrow_route([
                        sb.bot_mid(),
                        (sb.cx, mid_y),
                        (db.cx, mid_y),
                        db.top_mid(),
                    ])
                else:
                    # Multi-rank: handled by skip-rank logic above (shouldn't reach here)
                    mid_y = (sb.bot + db.top) / 2
                    d.arrow_route([
                        sb.bot_mid(),
                        (sb.cx, mid_y),
                        (db.cx, mid_y),
                        db.top_mid(),
                    ])

            # Edge label (Yes/No)
            if e.label:
                if src_nd.shape == 'diamond':
                    if abs(sb.cx - db.cx) < 0.1 and not is_skip:
                        # Straight down label
                        d.label(sb.cx + 0.12, sb.bot - 0.08, e.label, ha='left', fs=fs)
                    elif is_skip:
                        d.label(skip_channel_x + 0.08, (sb.cy + db.cy) / 2, e.label, ha='left', fs=fs)
                    elif abs(src_nd.rank - dst_nd.rank) == 0:
                        # Same-rank side exit: label on diamond side
                        if db.cx < sb.cx:
                            d.label(sb.left - 0.08, sb.cy + 0.10, e.label, ha='right', fs=fs)
                        else:
                            d.label(sb.right + 0.08, sb.cy + 0.10, e.label, ha='left', fs=fs)
                    else:
                        # Cross-rank elbow: label on diamond side at departure
                        if db.cx < sb.cx:
                            d.label(sb.left - 0.08, sb.cy + 0.10, e.label, ha='right', fs=fs)
                        else:
                            d.label(sb.right + 0.08, sb.cy + 0.10, e.label, ha='left', fs=fs)
                else:
                    if is_skip:
                        d.label(skip_channel_x + 0.08, (sb.cy + db.cy) / 2, e.label, ha='left', fs=fs)
                    else:
                        mid_y = (sb.bot + db.top) / 2
                        d.label(sb.cx + 0.12, mid_y, e.label, ha='left', fs=fs)

        # Draw back-edges (loop-back through left channel)
        back_edges = [e for e in self._edges if e.is_back]
        if back_edges:
            # Find leftmost node boundary — boundary itself is the limit
            all_lefts = [nd.box_ref.left for nd in self._nodes.values() if nd.box_ref]
            base_x = min(all_lefts) if all_lefts else self.BND_X1 + self.INNER_PAD
            # Clamp: channel must remain inside boundary (with margin)
            min_channel_x = self.BND_X1 + 0.10

            for i, e in enumerate(back_edges):
                src_nd = self._nodes[e.src_id]
                dst_nd = self._nodes[e.dst_id]
                sb = src_nd.box_ref
                db = dst_nd.box_ref

                if sb is None or db is None:
                    continue

                # Route: src bottom-left corner → left channel → up → dst left_mid
                # Use bottom-left of src box for departure (avoids overlapping label positions)
                channel_x = max(min_channel_x, base_x - 0.40 - i * 0.28)

                # For diamonds, exit from the bottom (straight down first, then left)
                # For boxes, exit from the left_mid
                if src_nd.shape == 'diamond':
                    d.arrow_route([
                        sb.bot_mid(),
                        (sb.cx, sb.bot - 0.20),
                        ('left_to', channel_x),
                        ('up_to', db.cy),
                        db.left_mid(),
                    ])
                else:
                    d.arrow_route([
                        sb.left_mid(),
                        ('left_to', channel_x),
                        ('up_to', db.cy),
                        db.left_mid(),
                    ])

                # Label: place it near the source departure, offset from channel
                if e.label:
                    if src_nd.shape == 'diamond':
                        d.label(sb.cx - 0.12, sb.bot - 0.12, e.label, ha='right', fs=fs)
                    else:
                        d.label(channel_x - 0.08, sb.cy + 0.10, e.label, ha='right', fs=fs)

        # Boundary + label
        d.boundary(self.BND_X1, self.BND_Y1, self.BND_X2, self.BND_Y2)
        d.fig_label()
        d.save()
        return d
