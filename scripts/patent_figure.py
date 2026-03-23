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
    DIAMOND_W = 2.60       # diamond width
    DIAMOND_H = 1.30       # diamond height
    BOX_PAD_X = 0.30       # text padding inside boxes
    BOX_PAD_Y = 0.20

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

        for nd in self._nodes.values():
            if nd.shape == 'diamond':
                nd._w = self.DIAMOND_W
                nd._h = self.DIAMOND_H
            else:
                tw, th = d.measure_text(nd.text)
                nd._w = tw + self.BOX_PAD_X * 2
                nd._h = max(th + self.BOX_PAD_Y * 2, 0.55)
                # Minimum width for aesthetics
                nd._w = max(nd._w, 2.00)

        # Unify widths for process/start/end boxes (not diamonds)
        box_nodes = [nd for nd in self._nodes.values() if nd.shape != 'diamond']
        if box_nodes:
            max_w = max(nd._w for nd in box_nodes)
            for nd in box_nodes:
                nd._w = max_w

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
        n_gaps = max_rank  # gaps between ranks
        if n_gaps > 0:
            v_gap = min(0.55, max(0.25, (available_h - total_node_h) / n_gaps))
        else:
            v_gap = 0.55

        total_h = total_node_h + v_gap * n_gaps

        # Start y (top of content, going down)
        start_y = (content_y_top + content_y_bot) / 2 + total_h / 2

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

        # Draw nodes
        for nid in self._order:
            nd = self._nodes[nid]
            cx, cy = positions[nid]

            if nd.shape in ('start', 'end'):
                x = cx - nd._w / 2
                y = cy - nd._h / 2
                nd.box_ref = d.rounded_rect(x, y, nd._w, nd._h, nd.text, radius=0.25)
            elif nd.shape == 'diamond':
                nd.box_ref = d.decision_diamond(cx, cy, nd._w, nd._h, nd.text)
            elif nd.shape == 'oval':
                nd.box_ref = d.oval(cx, cy, nd._w, nd._h, nd.text)
            elif nd.shape == 'cylinder':
                x = cx - nd._w / 2
                y = cy - nd._h / 2
                nd.box_ref = d.database_cylinder(x, y, nd._w, nd._h, nd.text)
            else:  # process (default box)
                x = cx - nd._w / 2
                y = cy - nd._h / 2
                nd.box_ref = d.box(x, y, nd._w, nd._h, nd.text)

        # Draw forward edges (straight/elbow arrows)
        for e in self._edges:
            if e.is_back:
                continue
            src_nd = self._nodes[e.src_id]
            dst_nd = self._nodes[e.dst_id]
            sb = src_nd.box_ref
            db = dst_nd.box_ref

            if sb is None or db is None:
                continue

            # Same column: straight vertical arrow
            if abs(sb.cx - db.cx) < 0.1:
                d.arrow_v(sb, db)
            else:
                # Elbow: down from src, horizontal, down to dst
                mid_y = (sb.bot + db.top) / 2
                d.arrow_route([
                    sb.bot_mid(),
                    (sb.cx, mid_y),
                    (db.cx, mid_y),
                    db.top_mid(),
                ])

            # Edge label (Yes/No)
            if e.label:
                src_cx, src_cy = positions[e.src_id]
                dst_cx, dst_cy = positions[e.dst_id]

                if src_nd.shape == 'diamond':
                    # Label near the diamond exit point
                    if abs(sb.cx - db.cx) < 0.1:
                        # Vertical exit (bottom)
                        d.label(sb.cx + 0.15, sb.bot - 0.12, e.label, ha='left')
                    else:
                        # Horizontal exit
                        if db.cx < sb.cx:
                            d.label(sb.left - 0.10, sb.cy + 0.12, e.label, ha='right')
                        else:
                            d.label(sb.right + 0.10, sb.cy + 0.12, e.label, ha='left')
                else:
                    # Generic: label at midpoint
                    mid_y = (sb.bot + db.top) / 2
                    d.label(sb.cx + 0.15, mid_y, e.label, ha='left')

        # Draw back-edges (loop-back through left channel)
        back_edges = [e for e in self._edges if e.is_back]
        if back_edges:
            # Find leftmost node boundary
            all_lefts = [nd.box_ref.left for nd in self._nodes.values() if nd.box_ref]
            base_x = min(all_lefts) if all_lefts else self.BND_X1 + self.INNER_PAD

            for i, e in enumerate(back_edges):
                src_nd = self._nodes[e.src_id]
                dst_nd = self._nodes[e.dst_id]
                sb = src_nd.box_ref
                db = dst_nd.box_ref

                if sb is None or db is None:
                    continue

                # Route: src left_mid → left → up → dst left_mid
                channel_x = base_x - 0.45 - i * 0.30

                d.arrow_route([
                    sb.left_mid(),
                    ('left_to', channel_x),
                    ('up_to', db.cy),
                    db.left_mid(),
                ])

                # Label at branch point
                if e.label:
                    d.label(sb.left - 0.10, sb.cy + 0.12, e.label, ha='right')

        # Boundary + label
        d.boundary(self.BND_X1, self.BND_Y1, self.BND_X2, self.BND_Y2)
        d.fig_label()
        d.save()
        return d
