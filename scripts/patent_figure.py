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
    fig.edge('S402', 'S403', bidir=True)   # bidirectional arrow

    # Container grouping (drawn as dashed box after layout)
    fig.container('grp1', ['S402', 'S404'], label='310\nProcessing Group')

    fig.render('fig6.png')

Shapes: 'process' (default), 'start', 'end', 'diamond', 'oval', 'cylinder'
Layout: automatic top-to-bottom with back-edge detection + side-channel routing.
  orientation='TB' (default) — top-to-bottom flowchart
  orientation='LR' — left-to-right block diagram style (Phase 3 addition)

Phase 3 additions:
  - container(): dashed group box around nodes (labeled)
  - bidir=True in edge(): bidirectional arrow
  - orientation='LR': horizontal left-to-right layout
  - Deep flow short arrow fix: MIN_V_GAP enforced ≥ 0.44"
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
    __slots__ = ('src_id', 'dst_id', 'label', 'is_back', 'bidir')

    def __init__(self, src_id: str, dst_id: str, label: str = '', bidir: bool = False):
        self.src_id = src_id
        self.dst_id = dst_id
        self.label = label
        self.is_back = False    # True if this is a loop-back edge
        self.bidir = bidir      # True if bidirectional arrow


class FigContainer:
    """A labeled dashed group box around a set of nodes."""
    __slots__ = ('id', 'node_ids', 'label', 'pad')

    def __init__(self, id: str, node_ids: list, label: str = '', pad: float = 0.12):
        self.id = id
        self.node_ids = node_ids
        self.label = label
        self.pad = pad


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
    DEFAULT_FS = 10        # default font size (patent-scale, matches USPTO §1.84(p)(3) min)
    MIN_FS = 8             # minimum font size (for deep/dense flows)

    def __init__(self, fig_label: str = 'FIG. 1', orientation: str = 'portrait',
                 direction: str = 'TB'):
        self.fig_label = fig_label
        self.orientation = orientation
        self.direction = direction  # 'TB' (top-bottom) or 'LR' (left-right)
        self._nodes: dict[str, FigNode] = {}   # id → FigNode
        self._edges: list[FigEdge] = []
        self._containers: list[FigContainer] = []
        self._order: list[str] = []            # insertion order
        # Phase 2: Style parameters (None = use library defaults)
        self._style: dict = {}

    def style(self, **kwargs) -> 'PatentFigure':
        """
        Set visual style parameters for the figure.

        Parameters
        ----------
        line_width : float
            Line width multiplier for boxes and arrows (default 1.0).
            E.g. line_width=1.5 makes lines 50% thicker.
        arrow_scale : float
            Arrowhead size multiplier (default 1.0 = mutation_scale 12).
            E.g. arrow_scale=1.5 makes arrowheads 50% larger.
        label_fs_scale : float
            Font size multiplier for edge labels (Yes/No, etc.) (default 1.0).
            Applied on top of the auto-computed node font size.
        diamond_text_scale : float
            Font size multiplier for text inside diamond shapes (default 1.0).
            Useful when diamond text is long and needs to be smaller.
        text_align : str
            Text alignment inside boxes: 'center' (default) or 'left'.
            NOTE: patent_drawing_lib always uses 'center'; setting 'left' here
            is noted but has limited effect without lib-level changes.

        Example
        -------
        fig.style(line_width=1.3, arrow_scale=1.2, label_fs_scale=1.1)
        """
        self._style.update(kwargs)
        return self

    def node(self, id: str, text: str, shape: str = 'process') -> 'PatentFigure':
        """Add a node. shape: process | start | end | diamond | oval | cylinder"""
        self._nodes[id] = FigNode(id, text, shape)
        self._order.append(id)
        return self

    def edge(self, src: str, dst: str, label: str = '', bidir: bool = False) -> 'PatentFigure':
        """Add a directed edge (arrow) from src to dst.
        bidir=True: bidirectional arrow (both arrowheads).
        """
        self._edges.append(FigEdge(src, dst, label, bidir=bidir))
        return self

    def container(self, id: str, node_ids: list, label: str = '',
                  pad: float = 0.14) -> 'PatentFigure':
        """
        Add a labeled dashed group box around the given node IDs.
        Drawn after layout — the box auto-sizes to enclose all listed nodes.

        Args:
            id:       unique container ID
            node_ids: list of node IDs to enclose
            label:    optional label (e.g. reference number + name)
            pad:      extra padding around enclosed nodes (inches)
        """
        self._containers.append(FigContainer(id, node_ids, label, pad))
        return self

    # ── Main render pipeline ──────────────────────────────────────────────────

    def render(self, output_path: str) -> str:
        """Full pipeline: layout → draw → save. Returns output path."""
        self._assign_ranks()
        self._measure_nodes()
        if self.direction == 'LR':
            positions = self._compute_positions_lr()
        else:
            positions = self._compute_positions()
        self._draw(output_path, positions)
        return output_path

    def render_multi(self, *output_paths: str, split_at: int = None) -> list[str]:
        """
        Split a deep flow into multiple pages and render each as a separate PNG.

        For flows with 9+ nodes (or when split_at is specified), automatically
        splits the node list into roughly equal halves and renders each half
        as a separate figure. A connector label (A) is added at the bottom of
        the first figure and the top of the second to indicate continuation.

        Args:
            *output_paths: One output path per page (e.g. 'fig5a.png', 'fig5b.png').
                           Currently supports exactly 2 pages.
            split_at:      Optional index at which to split (0-based into self._order).
                           Defaults to len(nodes) // 2.

        Returns:
            List of output paths that were written.

        Example::

            fig = PatentFigure('FIG. 5A')
            # Add 12 nodes + edges ...
            fig.render_multi('fig5a.png', 'fig5b.png')
        """
        if len(output_paths) < 2:
            raise ValueError("render_multi requires at least 2 output paths")
        if len(output_paths) > 2:
            raise NotImplementedError("render_multi currently supports 2-page split only")

        n = len(self._order)
        idx = split_at if split_at is not None else n // 2

        first_ids  = set(self._order[:idx])
        second_ids = set(self._order[idx:])

        # ── Page A ────────────────────────────────────────────────────────────
        label_a = self.fig_label.replace('FIG.', 'FIG.').rstrip()
        # Use "A" suffix if label doesn't already end with a letter
        if not label_a[-1].isalpha():
            label_a += 'A'
        fig_a = PatentFigure(label_a, orientation=self.orientation, direction=self.direction)
        for nid in self._order[:idx]:
            nd = self._nodes[nid]
            fig_a.node(nid, nd.text, shape=nd.shape)
        # Only edges between nodes in first half
        for e in self._edges:
            if e.src_id in first_ids and e.dst_id in first_ids:
                fig_a.edge(e.src_id, e.dst_id, label=e.label, bidir=e.bidir)
        # Add connector node at bottom
        _conn_id = '__cont_a__'
        fig_a.node(_conn_id, '(A)\nCont\'d', shape='end')
        # Connect last node of first half to connector
        last_id = self._order[idx - 1]
        fig_a.edge(last_id, _conn_id)
        for cont in self._containers:
            cont_ids_a = [cid for cid in cont.node_ids if cid in first_ids]
            if cont_ids_a:
                fig_a.container(cont.id, cont_ids_a, label=cont.label, pad=cont.pad)
        fig_a.render(output_paths[0])

        # ── Page B ────────────────────────────────────────────────────────────
        label_b = self.fig_label.rstrip()
        if not label_b[-1].isalpha():
            label_b += 'B'
        else:
            label_b = label_b[:-1] + 'B'
        fig_b = PatentFigure(label_b, orientation=self.orientation, direction=self.direction)
        # Add connector node at top
        _conn_id_b = '__cont_b__'
        fig_b.node(_conn_id_b, '(A)\nCont\'d', shape='start')
        for nid in self._order[idx:]:
            nd = self._nodes[nid]
            fig_b.node(nid, nd.text, shape=nd.shape)
        # Connect connector to first node of second half
        first_id_b = self._order[idx]
        fig_b.edge(_conn_id_b, first_id_b)
        # Only edges between nodes in second half
        for e in self._edges:
            if e.src_id in second_ids and e.dst_id in second_ids:
                fig_b.edge(e.src_id, e.dst_id, label=e.label, bidir=e.bidir)
        for cont in self._containers:
            cont_ids_b = [cid for cid in cont.node_ids if cid in second_ids]
            if cont_ids_b:
                fig_b.container(cont.id + '_b', cont_ids_b, label=cont.label, pad=cont.pad)
        fig_b.render(output_paths[1])

        return list(output_paths[:2])

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
        """Compute width/height for each node based on text + shape.

        Uses font-size scaling to ensure deep flows fit on a single page.
        Box sizes reflect what patent_drawing_lib will ACTUALLY draw.
        """
        from collections import defaultdict
        d = Drawing('/dev/null')

        # Available area
        content_y_top = self.BND_Y2 - self.INNER_PAD
        content_y_bot = self.BND_Y1 + self.INNER_PAD
        available_h = content_y_top - content_y_bot

        # Build rank groups
        ranks = defaultdict(list)
        for nd in self._nodes.values():
            ranks[nd.rank].append(nd)
        max_rank = max(ranks.keys()) if ranks else 0

        MIN_ARROW_GAP = 0.46   # minimum gap for visible arrows

        # Try decreasing font sizes until the flow fits
        for fs in range(self.DEFAULT_FS, self.MIN_FS - 1, -1):
            self._active_fs = fs

            for nd in self._nodes.values():
                if nd.shape == 'diamond':
                    # Scale diamond proportionally with font
                    scale_f = fs / self.DEFAULT_FS
                    nd._w = max(self.DIAMOND_W * scale_f, 1.20)
                    nd._h = max(self.DIAMOND_H * scale_f, 0.60)
                else:
                    tw, th = d.measure_text(nd.text, fs)
                    # Match patent_drawing_lib's minimum padding
                    pad_w = 0.24 if nd.shape in ('start', 'end') else 0.18
                    pad_h = 0.14
                    # Our width: text + padding + extra pad for margins
                    nd._w = max(tw + pad_w + self.BOX_PAD_X, 1.40)
                    # Our height: must match library minimum (text + pad)
                    nd._h = max(th + pad_h, 0.35)

            # Unify widths for non-diamond boxes
            box_nodes = [nd for nd in self._nodes.values() if nd.shape != 'diamond']
            if box_nodes:
                max_w = max(nd._w for nd in box_nodes)
                for nd in box_nodes:
                    nd._w = max_w

            # Check fit
            total_node_h = sum(max(nd._h for nd in ranks[r]) for r in range(max_rank + 1))
            needed = total_node_h + MIN_ARROW_GAP * max_rank
            if needed <= available_h or fs == self.MIN_FS:
                break

        # ── LR-mode: size boxes to distribute evenly across page width ─────────
        if self.direction == 'LR':
            EXTRA_MARGIN = 0.12
            lr_content_x1 = self.BND_X1 + self.INNER_PAD + EXTRA_MARGIN
            lr_content_x2 = self.BND_X2 - self.INNER_PAD - EXTRA_MARGIN
            lr_available_w = lr_content_x2 - lr_content_x1
            lr_available_h = (self.BND_Y2 - self.INNER_PAD) - (self.BND_Y1 + self.INNER_PAD)
            n_cols = max_rank + 1
            n_gaps = max_rank
            # Distribute available_w: target 40% gaps, 60% boxes
            # But also ensure min gap of 0.50"
            MIN_H_GAP = 0.50
            if n_gaps > 0:
                target_gap = max(MIN_H_GAP, lr_available_w * 0.38 / n_gaps)
                target_box_w = (lr_available_w - target_gap * n_gaps) / n_cols
                target_box_w = max(1.00, target_box_w)
            else:
                target_box_w = lr_available_w * 0.50
            # Recalculate gap with actual box width
            if n_gaps > 0:
                actual_gap = (lr_available_w - target_box_w * n_cols) / n_gaps
                actual_gap = max(MIN_H_GAP, actual_gap)
            else:
                actual_gap = 0.0
            # Set width for all nodes
            for nd in self._nodes.values():
                if nd.shape != 'diamond':
                    nd._w = target_box_w
            # Set height: for single-row LR, use 55% of page height,
            # capped at 2:1 height-to-width ratio for natural proportions
            max_nodes_per_col = max(len(ranks[r]) for r in range(max_rank + 1))
            if max_nodes_per_col == 1:
                target_box_h = lr_available_h * 0.55
                max_aspect = 2.0   # max height = 2× width for landscape blocks
                target_box_h = min(target_box_h, target_box_w * max_aspect)
                for nd in self._nodes.values():
                    if nd.shape != 'diamond':
                        nd._h = max(nd._h, target_box_h)
            return  # skip TB-specific width check below

        # ── Scale widths if any row is too wide ──────────────────────────────
        content_x1 = self.BND_X1 + self.INNER_PAD + self.LOOPBACK_MARGIN
        content_x2 = self.BND_X2 - self.INNER_PAD
        available_w = content_x2 - content_x1

        for r, nodes in ranks.items():
            if len(nodes) > 1:
                total_row_w = sum(nd._w for nd in nodes) + self.H_GAP * (len(nodes) - 1)
                if total_row_w > available_w:
                    scale_w = available_w / total_row_w * 0.95
                    for nd in nodes:
                        nd._w *= scale_w
                        nd._w = max(nd._w, 0.80)

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
        # For straight vertical arrows: minimum 0.46" (just over 0.44" validator limit)
        has_branching = any(len(ranks[r]) > 1 for r in range(max_rank + 1))
        MIN_V_GAP_LINEAR   = 0.46  # straight arrow — slightly above 0.44" min
        MIN_V_GAP_BRANCHING = 0.92  # elbow arrows — two 0.44" segments
        n_gaps = max_rank  # gaps between ranks
        if n_gaps > 0:
            remaining = available_h - total_node_h
            best_gap = remaining / n_gaps if remaining > 0 else 0.20
            min_gap = MIN_V_GAP_BRANCHING if has_branching else MIN_V_GAP_LINEAR
            if best_gap < min_gap:
                # Not enough room for minimum gap — we need to shrink boxes
                # but do NOT modify nd._h here (that's _measure_nodes' job).
                # Just accept the best gap we can get.
                # The _measure_nodes() already tried to pre-shrink boxes;
                # if it's still not enough, it's geometrically impossible on one page.
                pass
            # Cap maximum gap — allow up to 1.50" for sparse flows to fill the page
            v_gap = min(1.50, max(0.20, best_gap))
        else:
            v_gap = 0.80

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

    # ── Step 3b: LR (left-to-right) Position Calculation ─────────────────────

    def _compute_positions_lr(self) -> dict[str, tuple[float, float]]:
        """
        Horizontal layout: nodes arranged left-to-right by rank.
        Each rank is a column. Multiple nodes in same rank stacked vertically.
        """
        from collections import defaultdict
        ranks = defaultdict(list)
        for nid in self._order:
            nd = self._nodes[nid]
            ranks[nd.rank].append(nd)

        max_rank = max(ranks.keys()) if ranks else 0

        # In LR mode, use slightly more margin to prevent box edges from touching boundary
        EXTRA_MARGIN = 0.12
        content_x1 = self.BND_X1 + self.INNER_PAD + EXTRA_MARGIN
        content_x2 = self.BND_X2 - self.INNER_PAD - EXTRA_MARGIN
        content_y_top = self.BND_Y2 - self.INNER_PAD
        content_y_bot = self.BND_Y1 + self.INNER_PAD
        available_w = content_x2 - content_x1
        available_h = content_y_top - content_y_bot
        content_cy = (content_y_top + content_y_bot) / 2

        # Column widths = max node width per rank
        col_widths = [max(nd._w for nd in ranks[r]) for r in range(max_rank + 1)]

        # H_GAP between columns
        # Box widths are pre-computed in _measure_nodes for LR mode.
        # Recalculate gap based on actual col_widths to match.
        MIN_H_GAP = 0.50
        n_h_gaps = max_rank
        total_box_w = sum(col_widths)
        if n_h_gaps > 0:
            remaining_w = available_w - total_box_w
            h_gap = max(MIN_H_GAP, remaining_w / n_h_gaps)
            h_gap = min(1.50, h_gap)
        else:
            h_gap = 0.80

        # V_GAP between nodes in same column
        MIN_V_GAP = 0.46

        # Total content width — must stay within available_w
        total_content_w = sum(col_widths) + h_gap * n_h_gaps
        # If still overflows (floating point), clamp h_gap
        if total_content_w > available_w and n_h_gaps > 0:
            h_gap = (available_w - total_box_w) / n_h_gaps * 0.98
            h_gap = max(0.10, h_gap)
            total_content_w = sum(col_widths) + h_gap * n_h_gaps

        # Center content horizontally within available area
        start_x = content_x1 + max(0.0, (available_w - total_content_w) / 2)

        positions = {}
        cur_x = start_x

        for r in range(max_rank + 1):
            nodes = ranks[r]
            col_w = col_widths[r]

            # Stack nodes vertically in this column
            total_col_h = sum(nd._h for nd in nodes)
            n_v_gaps = len(nodes) - 1
            if n_v_gaps > 0:
                remaining_h = available_h - total_col_h
                v_gap = max(MIN_V_GAP, min(1.20, remaining_h / n_v_gaps))
            else:
                v_gap = 0.0
            total_col_content_h = total_col_h + v_gap * n_v_gaps
            col_start_y = content_cy + total_col_content_h / 2

            cur_y = col_start_y
            for nd in nodes:
                cx = cur_x + col_w / 2
                cy = cur_y - nd._h / 2
                positions[nd.id] = (cx, cy)
                cur_y -= nd._h + v_gap

            cur_x += col_w + h_gap

        return positions

    # ── Step 4: Draw everything ───────────────────────────────────────────────

    def _apply_style(self):
        """
        Phase 2: Apply style overrides to patent_drawing_lib module constants.
        Returns a dict of original values for restoration.
        """
        import patent_drawing_lib as _lib
        originals = {}
        if not self._style:
            return originals

        lw_mult = self._style.get('line_width', 1.0)
        if lw_mult != 1.0:
            originals['LW_BOX'] = _lib.LW_BOX
            originals['LW_ARR'] = _lib.LW_ARR
            _lib.LW_BOX = _lib.LW_BOX * lw_mult
            _lib.LW_ARR = _lib.LW_ARR * lw_mult

        return originals

    def _restore_style(self, originals: dict):
        """Restore patent_drawing_lib constants after rendering."""
        import patent_drawing_lib as _lib
        for k, v in originals.items():
            setattr(_lib, k, v)

    def _draw(self, output_path: str, positions: dict):
        """Create Drawing, render all nodes and edges, save."""
        fig_num = self.fig_label.replace('FIG. ', '')

        # Phase 2: Apply style overrides
        _style_originals = self._apply_style()

        d = Drawing(output_path, fig_num=fig_num)

        # Use the font size determined by _measure_nodes (may be smaller for deep flows)
        fs = getattr(self, '_active_fs', self.DEFAULT_FS)

        # Phase 2: Apply font size scales from style
        arrow_scale = self._style.get('arrow_scale', 1.0)
        label_fs_scale = self._style.get('label_fs_scale', 1.0)
        diamond_text_scale = self._style.get('diamond_text_scale', 1.0)

        _orig_fs = fs
        _label_fs = max(6, int(fs * label_fs_scale))
        _diamond_fs = max(6, int(fs * diamond_text_scale))

        # Patch arrow mutation_scale if arrow_scale != 1.0
        # We do this by monkey-patching the render method temporarily
        if arrow_scale != 1.0:
            import patent_drawing_lib as _lib
            _orig_ms = 12  # default mutation_scale in library
            _new_ms = int(_orig_ms * arrow_scale)
            # Store for use in _render_route patching (via closure)
            d._patent_arrow_scale = arrow_scale
            d._patent_mutation_scale = _new_ms

        # Draw nodes
        for nid in self._order:
            nd = self._nodes[nid]
            cx, cy = positions[nid]

            if nd.shape in ('start', 'end'):
                x = cx - nd._w / 2
                y = cy - nd._h / 2
                nd.box_ref = d.rounded_rect(x, y, nd._w, nd._h, nd.text, fs=fs, radius=0.20)
            elif nd.shape == 'diamond':
                nd.box_ref = d.decision_diamond(cx, cy, nd._w, nd._h, nd.text, fs=_diamond_fs)
            elif nd.shape == 'oval':
                nd.box_ref = d.oval(cx, cy, nd._w, nd._h, nd.text, fs=fs)
            elif nd.shape == 'cylinder':
                # database_cylinder takes cx, cy (center), not x, y (bottom-left)
                nd.box_ref = d.database_cylinder(cx, cy, nd._w, nd._h, nd.text, fs=fs)
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
        # Base right channel x — first skip uses +0.50 (≥ 0.44" min segment)
        # Each additional skip edge gets its own lane (+0.45" per lane) for clear visual separation
        _skip_channel_base_x = all_right_edges + 0.50
        # Clamp to boundary
        _skip_channel_max_x = self.BND_X2 - 0.10
        # Index skip edges so each gets its own channel lane
        # Sort by rank span (smallest span = innermost/closest channel)
        _skip_edges = [(e, self._nodes[e.src_id], self._nodes[e.dst_id])
                       for e in self._edges
                       if not e.is_back and (self._nodes[e.dst_id].rank - self._nodes[e.src_id].rank) > 1
                       and self._nodes[e.src_id].box_ref and self._nodes[e.dst_id].box_ref]
        _skip_edges.sort(key=lambda t: t[2].rank - t[1].rank)  # smallest span first
        _skip_channel_map = {}  # edge id → channel_x
        for idx_s, (e_s, _, _) in enumerate(_skip_edges):
            ch_x = min(_skip_channel_max_x, _skip_channel_base_x + idx_s * 0.45)
            _skip_channel_map[id(e_s)] = ch_x

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
            # Per-edge skip channel (fan-out to avoid overlap)
            skip_channel_x = _skip_channel_map.get(id(e), _skip_channel_base_x)

            # LR direction: use horizontal primary axis
            if self.direction == 'LR':
                # In LR layout: same-rank nodes are in the same column (vertically stacked)
                # Cross-rank edges go left→right
                if rank_diff == 0:
                    # Same rank (same column): vertical direct or side routing
                    if abs(sb.cy - db.cy) > 0.1:
                        if db.cy < sb.cy:
                            d.arrow_route([sb.bot_mid(), db.top_mid()])
                        else:
                            d.arrow_route([sb.top_mid(), db.bot_mid()])
                    else:
                        d.arrow_route([sb.right_mid(), db.left_mid()])
                elif rank_diff == 1:
                    # Adjacent column: right → left of next box
                    if e.bidir:
                        d.arrow_bidir_route([sb.right_mid(), db.left_mid()])
                    else:
                        d.arrow_route([sb.right_mid(), db.left_mid()])
                else:
                    # Skip-rank LR: route via top channel
                    skip_channel_y = min(
                        b.bot for b in [self._nodes[nid].box_ref
                                        for nid in self._order
                                        if self._nodes[nid].box_ref]
                    ) - 0.35
                    skip_channel_y = max(skip_channel_y, self.BND_Y1 + 0.20)
                    d.arrow_route([
                        sb.top_mid(),
                        ('up_to', skip_channel_y),
                        ('right_to', db.cx),
                        db.top_mid(),
                    ])

                if e.label:
                    if rank_diff == 0:
                        mid_x = (sb.cx + db.cx) / 2
                        mid_y = (sb.cy + db.cy) / 2
                        d.label(mid_x + 0.05, mid_y + 0.08, e.label, ha='left', fs=_label_fs)
                    else:
                        mid_x = (sb.right + db.left) / 2
                        d.label(mid_x, (sb.cy + db.cy) / 2 + 0.08, e.label, ha='center', fs=_label_fs)
                continue

            # TB direction (default): vertical primary axis
            # Same column: straight vertical arrow (only if no intermediate boxes in path)
            if abs(sb.cx - db.cx) < 0.1 and not is_skip:
                if e.bidir:
                    d.arrow_bidir(sb, db, side='v')
                else:
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
                        if e.bidir:
                            d.arrow_bidir_route([sb.left_mid(), db.right_mid()])
                        else:
                            d.arrow_route([sb.left_mid(), db.right_mid()])
                    else:
                        if e.bidir:
                            d.arrow_bidir_route([sb.right_mid(), db.left_mid()])
                        else:
                            d.arrow_route([sb.right_mid(), db.left_mid()])
                elif abs(src_nd.rank - dst_nd.rank) == 1:
                    # Adjacent rank: standard elbow — ensure minimum 0.44" segments
                    # by using at least 0.44" below src and above dst
                    mid_y = min(sb.bot - 0.44, max(db.top + 0.44, (sb.bot + db.top) / 2))
                    route_pts = [
                        sb.bot_mid(),
                        (sb.cx, mid_y),
                        (db.cx, mid_y),
                        db.top_mid(),
                    ]
                    if e.bidir:
                        d.arrow_bidir_route(route_pts)
                    else:
                        d.arrow_route(route_pts)
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
                        d.label(sb.cx + 0.12, sb.bot - 0.08, e.label, ha='left', fs=_label_fs)
                    elif is_skip:
                        d.label(skip_channel_x + 0.08, (sb.cy + db.cy) / 2, e.label, ha='left', fs=_label_fs)
                    elif abs(src_nd.rank - dst_nd.rank) == 0:
                        # Same-rank side exit: label on diamond side
                        if db.cx < sb.cx:
                            d.label(sb.left - 0.08, sb.cy + 0.10, e.label, ha='right', fs=_label_fs)
                        else:
                            d.label(sb.right + 0.08, sb.cy + 0.10, e.label, ha='left', fs=_label_fs)
                    else:
                        # Cross-rank elbow: label on diamond side at departure
                        if db.cx < sb.cx:
                            d.label(sb.left - 0.08, sb.cy + 0.10, e.label, ha='right', fs=_label_fs)
                        else:
                            d.label(sb.right + 0.08, sb.cy + 0.10, e.label, ha='left', fs=_label_fs)
                else:
                    if is_skip:
                        d.label(skip_channel_x + 0.08, (sb.cy + db.cy) / 2, e.label, ha='left', fs=_label_fs)
                    else:
                        mid_y = (sb.bot + db.top) / 2
                        d.label(sb.cx + 0.12, mid_y, e.label, ha='left', fs=_label_fs)

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
                # i=0: innermost (closest) channel; i=1: outer channel (further left)
                # 0.40" initial offset + 0.35" per extra loop ensures visible separation
                channel_x = max(min_channel_x, base_x - 0.40 - i * 0.35)

                # For diamonds, exit from the bottom (straight down first, then left)
                # For boxes, exit from the left_mid
                if src_nd.shape == 'diamond':
                    # Ensure minimum 0.44" downward segment before turning left
                    down_y = sb.bot - max(0.50, (sb.bot - db.cy) * 0.15)
                    d.arrow_route([
                        sb.bot_mid(),
                        (sb.cx, down_y),
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
                        d.label(sb.cx - 0.12, sb.bot - 0.12, e.label, ha='right', fs=_label_fs)
                    else:
                        d.label(channel_x - 0.08, sb.cy + 0.10, e.label, ha='right', fs=_label_fs)

        # Draw containers (dashed group boxes)
        for cont in self._containers:
            # Compute bounding box of contained nodes
            ref_boxes = [self._nodes[nid].box_ref for nid in cont.node_ids
                         if nid in self._nodes and self._nodes[nid].box_ref]
            if not ref_boxes:
                continue
            pad = cont.pad
            min_x = min(b.left for b in ref_boxes) - pad
            min_y = min(b.bot  for b in ref_boxes) - pad
            max_x = max(b.right for b in ref_boxes) + pad
            max_y = max(b.top  for b in ref_boxes) + pad
            w = max_x - min_x
            h = max_y - min_y
            # Draw as dashed rectangle
            rect = d.ax.add_patch(
                __import__('matplotlib').patches.FancyBboxPatch(
                    (min_x, min_y), w, h,
                    boxstyle='square,pad=0',
                    linewidth=1.0, edgecolor='black', facecolor='none',
                    linestyle='dashed', zorder=3
                )
            )
            # Label: place above the container top edge (outside the box)
            if cont.label:
                # Use first line of label as main text (reference number)
                label_lines = cont.label.split('\n')
                label_text = cont.label
                # Place label just above the dashed box top edge
                label_y = max_y + 0.04
                d.ax.text((min_x + max_x) / 2, label_y, label_text,
                          fontsize=7, ha='center', va='bottom',
                          fontfamily='DejaVu Sans',
                          zorder=21,
                          bbox=dict(facecolor='white', edgecolor='none', pad=1))

        # Boundary + label
        d.boundary(self.BND_X1, self.BND_Y1, self.BND_X2, self.BND_Y2)
        d.fig_label()
        d.save()

        # Phase 2: Restore original library constants
        self._restore_style(_style_originals)

        return d
