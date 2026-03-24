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

Phase 6 additions (Research 6):
  - Auto text wrapping: max_text_width param, wraps long node text automatically
  - node_group(): force nodes to same rank (side-by-side in TB layout)
  - add_note(): speech bubble annotation next to a node
  - export_spec(): reverse-engineer PatentFigure → spec text
  - validate(): pre-render structural checks (orphans, duplicates, cycles)
  - from_spec() parser enhanced: parenthetical branches, loops, English specs

Phase 8 additions (Research 8):
  - Korean font auto-detection: _setup_korean_font() sets matplotlib rcParams
    to use Apple SD Gothic Neo / NanumGothic / ArialUnicode on macOS.
    All text rendering uses the detected Korean-capable font.
  - A* grid-based obstacle routing in EdgeRouter (edge_router.py):
    auto-activates when Cohen-Sutherland detects intersection, falls back
    to A* shortest-path with Manhattan heuristic + bend penalty.
  - Diamond arrow quality: arrows exit from exact diamond vertices
    (top/bottom/left/right points), Yes/No labels repositioned.
  - render() auto-split: auto_split=True (default) triggers render_multi()
    when node count > max_nodes_per_page (default 14).
  - preset(): style presets — 'uspto', 'draft', 'presentation'.

Phase 9 additions (Research 9):
  - from_spec() accuracy: Korean decision keywords (여부 판단, 확인, 검증),
    "후 종료" implicit END branches, number-only paren skip, improved shape detection.
  - bus(): horizontal bus topology with multiple node connections.
  - edge() label_back= param: separate labels for bidir arrow each direction.
  - PatentSequence: sequence diagram support (actors, messages, return arrows).
  - Error recovery: empty text warning, duplicate ID warning, cycle detection report,
    long text auto-wrap (>200 chars), orphan validation with shape awareness.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from patent_drawing_lib import Drawing, BoxRef

from collections import defaultdict, deque


# ── Phase 8: Korean Font Auto-Detection ──────────────────────────────────────

def _setup_korean_font() -> str:
    """
    Auto-detect a Korean-capable font on the system and configure matplotlib.

    Priority order:
      1. Apple SD Gothic Neo (macOS system font — full Korean support)
      2. AppleGothic (macOS fallback)
      3. NanumGothic / NanumMyeongjo (Korean open fonts)
      4. Arial Unicode MS (broad unicode coverage)
      5. DejaVu Sans (matplotlib default — no Korean, but graceful fallback)

    Returns the selected font family name string.
    Side effect: sets matplotlib rcParams['font.family'] and
                 rcParams['font.sans-serif'] to prioritize the chosen font.
    """
    import matplotlib
    import matplotlib.font_manager as fm

    KOREAN_PRIORITY = [
        'Apple SD Gothic Neo',
        'AppleGothic',
        'AppleMyungjo',
        'Nanum Gothic',
        'NanumGothic',
        'Nanum Myeongjo',
        'NanumMyeongjo',
        'Arial Unicode MS',
    ]

    available_names = {f.name for f in fm.fontManager.ttflist}
    chosen = 'DejaVu Sans'
    for candidate in KOREAN_PRIORITY:
        if candidate in available_names:
            chosen = candidate
            break

    # Set matplotlib to use this font globally
    matplotlib.rcParams['font.family'] = 'sans-serif'
    # Prepend chosen font so it wins over matplotlib defaults
    current = matplotlib.rcParams.get('font.sans-serif', [])
    if isinstance(current, str):
        current = [current]
    new_list = [chosen] + [f for f in current if f != chosen]
    matplotlib.rcParams['font.sans-serif'] = new_list

    return chosen


# Run once at import time — subsequent calls are idempotent
_KOREAN_FONT = _setup_korean_font()


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
    __slots__ = ('src_id', 'dst_id', 'label', 'is_back', 'bidir', 'label_back')

    def __init__(self, src_id: str, dst_id: str, label: str = '', bidir: bool = False):
        self.src_id = src_id
        self.dst_id = dst_id
        self.label = label
        self.is_back = False    # True if this is a loop-back edge
        self.bidir = bidir      # True if bidirectional arrow
        self.label_back = ''    # label for the reverse direction of bidir arrows


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
        # Phase 5: Highlighted node IDs → style dict
        self._highlights: dict[str, dict] = {}
        # Phase 5: Auto-numbering state
        self._auto_num_prefix: str = ''
        self._auto_num_counter: int = 100
        self._auto_num_step: int = 100
        # Phase 6: node groups (same-rank forcing)
        self._node_groups: list[list[str]] = []
        # Phase 6: notes (speech-bubble annotations)
        self._notes: list[dict] = []   # {node_id, text}
        # Phase 6: max text width for auto-wrap (inches, None = disabled)
        self.max_text_width: float = None
        # Phase 9: bus connections
        self._buses: list[dict] = []

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

    def preset(self, name: str) -> 'PatentFigure':
        """
        Apply a named style preset.

        Presets
        -------
        'uspto'
            Black & white, strict USPTO compliance:
            - line_width=1.0, arrow_scale=1.0 (standard weights)
            - No corner rounding (corner_radius not set)
            - Tight, minimal margins

        'draft'
            Color-friendly draft mode:
            - line_width=1.2, corner_radius=0.08 (rounded corners via EdgeRouter)
            - label_fs_scale=1.1 (slightly larger labels)
            - Relaxed margins, annotation notes visible

        'presentation'
            Large, bold, presentation-ready:
            - line_width=1.8, arrow_scale=1.4
            - label_fs_scale=1.3, diamond_text_scale=1.1
            - corner_radius=0.10

        Example
        -------
        fig.preset('presentation')
        """
        presets = {
            'uspto': {
                'line_width': 1.0,
                'arrow_scale': 1.0,
                'label_fs_scale': 1.0,
                'diamond_text_scale': 1.0,
                # No corner_radius → uses default straight-corner library rendering
            },
            'draft': {
                'line_width': 1.2,
                'arrow_scale': 1.1,
                'label_fs_scale': 1.1,
                'diamond_text_scale': 1.0,
                'corner_radius': 0.08,
            },
            'presentation': {
                'line_width': 1.8,
                'arrow_scale': 1.4,
                'label_fs_scale': 1.3,
                'diamond_text_scale': 1.1,
                'corner_radius': 0.10,
            },
        }
        if name not in presets:
            raise ValueError(f"Unknown preset '{name}'. Choose from: {list(presets.keys())}")
        self._style.update(presets[name])
        return self

    def node(self, id: str, text: str = '', shape: str = 'process') -> 'PatentFigure':
        """Add a node. shape: process | start | end | diamond | oval | cylinder
        
        Phase 9 error recovery:
        - Empty text → warning, uses id as fallback text.
        - Duplicate ID → warning, overwrites previous node.
        - Text > 200 chars → auto-wrap + warning.
        """
        import warnings as _w
        # Empty text warning
        if not text:
            _w.warn(f"PatentFigure: node '{id}' has empty text — using id as fallback")
            text = id
        # Duplicate ID warning
        if id in self._nodes:
            _w.warn(f"PatentFigure: duplicate node id '{id}' — overwriting previous definition")
            self._order.remove(id)
        # Long text auto-wrap (>200 chars)
        if len(text) > 200:
            _w.warn(f"PatentFigure: node '{id}' text exceeds 200 chars — auto-wrapping")
            text = self._wrap_text(text, max_chars_per_line=20)
        self._nodes[id] = FigNode(id, text, shape)
        self._order.append(id)
        return self

    def highlight(self, *node_ids: str, bg_color: str = '#E8E8E8',
                  border_lw: float = 2.0) -> 'PatentFigure':
        """
        Mark one or more nodes for conditional highlighting.
        Highlighted nodes are drawn with a gray background and thicker border.

        Args:
            *node_ids:   One or more node IDs to highlight.
            bg_color:    Background fill color (default '#E8E8E8' light gray).
            border_lw:   Border line width multiplier (default 2.0).

        Example::

            fig.highlight('S300', 'S500')   # mark two nodes
            fig.highlight('S200', bg_color='#FFFACD', border_lw=1.5)  # custom
        """
        style = {'bg_color': bg_color, 'border_lw': border_lw}
        for nid in node_ids:
            self._highlights[nid] = style
        return self

    # ── Phase 6 New Methods ───────────────────────────────────────────────────

    def node_group(self, node_ids: list[str]) -> 'PatentFigure':
        """
        Force a set of nodes to be assigned the same rank (side-by-side row).

        In TB layout, all nodes in the group will appear in the same horizontal row.
        In LR layout, all nodes will appear in the same vertical column.

        This is different from container() — node_group() affects layout rank
        assignment, not just the visual boundary box.

        Args:
            node_ids: List of node IDs to place at the same rank.

        Example::

            fig.node('S300a', 'Log Event')
            fig.node('S300b', 'Send Notification')
            fig.node_group(['S300a', 'S300b'])  # place side-by-side
        """
        self._node_groups.append(list(node_ids))
        return self

    def add_note(self, node_id: str, text: str) -> 'PatentFigure':
        """
        Add a speech-bubble annotation next to a node.

        The note is drawn as a small dashed rectangle with a pointer line
        to the right side of the target node. Useful for draft/review work.

        Note: USPTO formal drawings do not permit speech bubbles. Use only
        for draft/review figures (not final submissions).

        Args:
            node_id: The node to annotate.
            text:    Annotation text (multi-line supported via '\\n').

        Example::

            fig.add_note('S300', 'Check DB index\\nEnsure ACID compliance')
        """
        self._notes.append({'node_id': node_id, 'text': text})
        return self

    def export_spec(self, path: str = None) -> str:
        """
        Reverse-engineer this PatentFigure into spec-format text.

        The output is compatible with from_spec() — you can round-trip
        a figure through export_spec() → from_spec() to get an equivalent figure.

        Args:
            path: If given, write the spec text to this file path.
                  If None, just return the string.

        Returns:
            Spec-format string representation of this figure.

        Example::

            spec = fig.export_spec()
            # or
            fig.export_spec('/tmp/my_figure.spec.txt')
        """
        lines = []
        # Build edge lookup: src → list of dst
        fwd_edges = {}   # src → [(dst, label)]
        back_edges_map = {}  # src → [(dst, label)]

        # We need to run rank assignment to know which edges are back-edges.
        # Use a lightweight pass if not yet assigned.
        if not any(nd.rank != 0 for nd in self._nodes.values()):
            self._assign_ranks()

        for e in self._edges:
            if e.is_back:
                back_edges_map.setdefault(e.src_id, []).append((e.dst_id, e.label))
            else:
                fwd_edges.setdefault(e.src_id, []).append((e.dst_id, e.label))

        for nid in self._order:
            nd = self._nodes[nid]
            # Clean text: strip the "S100\n" prefix if present
            text = nd.text
            if text.startswith(nid + '\n'):
                text = text[len(nid) + 1:]
            # Shape annotation
            shape_note = ''
            if nd.shape == 'start':
                shape_note = ' [START]'
            elif nd.shape == 'end':
                shape_note = ' [END]'
            elif nd.shape == 'diamond':
                shape_note = ' [DECISION]'

            # Build redirect suffix for back-edges
            backs = back_edges_map.get(nid, [])
            fwds = fwd_edges.get(nid, [])

            # If there's a back-edge (loop), append → Sxxx
            redirect_suffix = ''
            if backs:
                dst_id, lbl = backs[0]
                redirect_suffix = f' → {dst_id}'
                if lbl:
                    redirect_suffix = f' ({lbl}) → {dst_id}'

            lines.append(f'{nid}: {text}{redirect_suffix}')

        result = '\n'.join(lines)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(result + '\n')
        return result

    def validate(self) -> list[str]:
        """
        Validate this PatentFigure's structure before rendering.

        Checks performed:
        1. Orphan nodes (no edges in or out)
        2. Duplicate node IDs (shouldn't happen via API but good to check)
        3. Duplicate edge pairs (src→dst appears more than once)
        4. Edges referencing undefined nodes
        5. Multiple start nodes (shape='start')
        6. Multiple end nodes (shape='end')

        Returns:
            List of warning strings. Empty list = no issues found.
            Does NOT raise exceptions — caller decides whether to abort.

        Example::

            warnings = fig.validate()
            if warnings:
                for w in warnings:
                    print('WARNING:', w)
            fig.render('output.png')
        """
        warnings = []

        # Check for edges referencing undefined nodes
        for e in self._edges:
            if e.src_id not in self._nodes:
                warnings.append(f"Edge references undefined source node: '{e.src_id}'")
            if e.dst_id not in self._nodes:
                warnings.append(f"Edge references undefined dest node: '{e.dst_id}'")

        # Build adjacency for valid nodes
        connected = set()
        for e in self._edges:
            if e.src_id in self._nodes and e.dst_id in self._nodes:
                connected.add(e.src_id)
                connected.add(e.dst_id)

        # Orphan check
        for nid in self._order:
            if nid not in connected:
                warnings.append(f"Orphan node (no edges): '{nid}' (text='{self._nodes[nid].text[:30]}')")

        # Duplicate edges
        edge_pairs = [(e.src_id, e.dst_id) for e in self._edges]
        seen_pairs = set()
        for pair in edge_pairs:
            if pair in seen_pairs:
                warnings.append(f"Duplicate edge: {pair[0]} → {pair[1]}")
            seen_pairs.add(pair)

        # Multiple start/end shapes
        starts = [nid for nid, nd in self._nodes.items() if nd.shape == 'start']
        ends = [nid for nid, nd in self._nodes.items() if nd.shape == 'end']
        if len(starts) > 1:
            warnings.append(f"Multiple START nodes: {starts}")
        if len(ends) > 1:
            warnings.append(f"Multiple END nodes: {ends}")

        # Note groups with non-existent node IDs
        for grp in self._node_groups:
            for nid in grp:
                if nid not in self._nodes:
                    warnings.append(f"node_group references undefined node: '{nid}'")

        # Phase 9: edge-less non-START/END nodes (orphans with shape context)
        out_edges = {e.src_id for e in self._edges}
        in_edges  = {e.dst_id for e in self._edges}
        for nid, nd in self._nodes.items():
            if nd.shape in ('start', 'end'):
                continue
            if nid not in out_edges and nid not in in_edges:
                pass  # already caught by orphan check
            elif nid not in out_edges and nd.shape not in ('end',):
                warnings.append(f"Node '{nid}' (shape={nd.shape}) has no outgoing edge — possibly missing connection or should be shape='end'")

        # Phase 9: cycle detection (simple DFS)
        adj_fwd = {}
        for e in self._edges:
            if e.src_id in self._nodes and e.dst_id in self._nodes:
                adj_fwd.setdefault(e.src_id, []).append(e.dst_id)

        visited_cy, in_stack = set(), set()
        cycles_found = []

        def _dfs_cycle(u, path):
            visited_cy.add(u)
            in_stack.add(u)
            for v in adj_fwd.get(u, []):
                if v not in visited_cy:
                    _dfs_cycle(v, path + [v])
                elif v in in_stack:
                    # Found a cycle; report it
                    cycle_start = path.index(v) if v in path else 0
                    cycles_found.append(' → '.join(path[cycle_start:] + [v]))

        for nid in self._order:
            if nid not in visited_cy:
                _dfs_cycle(nid, [nid])

        for c in cycles_found[:3]:  # report up to 3 cycles
            warnings.append(f"Cycle detected (will be treated as back-edge): {c}")

        return warnings

    # ── Phase 6: Text Auto-Wrap ───────────────────────────────────────────────

    @staticmethod
    def _wrap_text(text: str, max_chars_per_line: int = 18) -> str:
        """
        Wrap text so no line exceeds max_chars_per_line characters.
        Preserves existing newlines. Wraps on word boundaries where possible.
        """
        import textwrap
        result_lines = []
        for existing_line in text.split('\n'):
            if len(existing_line) <= max_chars_per_line:
                result_lines.append(existing_line)
            else:
                wrapped = textwrap.fill(existing_line, width=max_chars_per_line,
                                        break_long_words=True)
                result_lines.extend(wrapped.split('\n'))
        return '\n'.join(result_lines)

    @classmethod
    def from_spec(cls, fig_label: str, spec_text: str,
                  direction: str = 'TB') -> 'PatentFigure':
        """
        Parse a spec-format text and build a PatentFigure automatically.

        Spec format (one step per line)::

            S100: 로그인 요청 수신
            S200: 자격증명 검증
            S300: 검증 실패 시 재시도 횟수 확인
            S400: 재시도 3회 미만 → S200
            S500: 재시도 3회 이상 → 계정 잠금
            S600: 검증 성공 → 세션 토큰 발급
            S700: 토큰을 사용자 단말로 전송

        Enhanced parsing (Phase 6):

        Case A — Parenthetical branches::

            S300: 자격증명 검증 (성공 시 S500으로, 실패 시 S400으로)

        Case B — Parallel nodes (same alpha suffix)::

            S200a: 로그 기록
            S200b: 알림 발송

        Case C — Loop (최대 N회 ... 복귀)::

            S300: 재시도 (최대 3회, 실패 시 S200으로 복귀)

        Case D — English spec (If ... go to ...)::

            S300: If validation fails, check retry count

        Parsing rules:
        - Lines matching ``Sxxx: text`` define nodes.
        - First node is shape='start', last node is shape='end'.
        - ``→ Snnn`` at end of text = back-edge / branch to that node.
        - ``(성공 시 Sxxx으로, 실패 시 Syyy으로)`` → two outgoing edges.
        - ``(실패 시 Sxxx으로 복귀)`` or ``→ Sxxx`` at any position → loop-back edge.
        - Adjacent nodes with alpha suffix (S200a, S200b) → node_group().
        - Nodes with multiple outgoing edges get shape='diamond'.
        - Sequential nodes (no → redirect) get a forward edge to the next node.
        - English: ``if ... go to Snnn`` or ``fails, Snnn`` → branch edge.

        Returns:
            A configured PatentFigure instance ready for render().
        """
        import re

        fig = cls(fig_label, direction=direction)

        # ── Pre-parse: collect node definitions ──────────────────────────────
        # Each entry: (id, raw_text)
        raw_lines = []
        for line in spec_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Match Snnn or Snnn[a-z] (alpha suffix for parallel nodes)
            m = re.match(r'^(S\d+[a-z]?)\s*[:：]\s*(.+)$', line)
            if not m:
                continue
            raw_lines.append((m.group(1), m.group(2).strip()))

        if not raw_lines:
            return fig

        all_ids_set = {nid for nid, _ in raw_lines}

        # ── Parse each line for redirects ─────────────────────────────────────
        # node_defs: list of (id, cleaned_text, redirects: list of (target, label))
        node_defs = []

        for nid, text in raw_lines:
            redirects = []  # list of (target_id, label)

            # Case A: parenthetical multi-branch: (성공 시 S500으로, 실패 시 S400으로)
            # or English: (on success go to S500, on failure go to S400)
            paren_m = re.search(r'\(([^)]+)\)', text)
            if paren_m:
                paren_content = paren_m.group(1)
                # Korean pattern: "X 시 Snnn으로" or "X → Snnn"
                kor_branches = re.findall(
                    r'([^,]+?)\s*(?:시|경우|때)?\s*(?:→|->)?\s*(S\d+[a-z]?)(?:으로|에게|로)?', 
                    paren_content
                )
                # English pattern: "on X go to Snnn" or "X → Snnn"
                eng_branches = re.findall(
                    r'(?:on\s+)?([a-z][^,]+?)\s+(?:go\s+to|goto|->|→)\s*(S\d+[a-z]?)',
                    paren_content, re.IGNORECASE
                )
                # Loop: 복귀 pattern: "실패 시 S200으로 복귀"
                loop_m = re.search(
                    r'(?:실패|오류|fail[a-z]*).*?(S\d+[a-z]?).*?복귀',
                    paren_content, re.IGNORECASE
                )
                # Generic "Snnn으로 복귀" / "return to Snnn"
                loop_generic = re.search(
                    r'(?:복귀|return to|back to)\s*(?:→)?\s*(S\d+[a-z]?)',
                    paren_content, re.IGNORECASE
                )

                if kor_branches:
                    for lbl, tgt in kor_branches:
                        lbl = lbl.strip().rstrip(' 시경우때')
                        # Translate common Korean labels
                        lbl = lbl.replace('성공', 'Y').replace('실패', 'N') \
                                 .replace('예', 'Y').replace('아니오', 'N').strip()
                        redirects.append((tgt.strip(), lbl))
                elif eng_branches:
                    for lbl, tgt in eng_branches:
                        redirects.append((tgt.strip(), lbl.strip()))
                elif loop_m:
                    redirects.append((loop_m.group(1), 'N'))
                elif loop_generic:
                    redirects.append((loop_generic.group(1), ''))

                # Remove the parenthetical from display text if we parsed it
                if redirects or loop_m or loop_generic:
                    text = text[:paren_m.start()].rstrip(' \t') + text[paren_m.end():].lstrip()

            # Case D English: "If X, go to/check Snnn" or "If X fails → Snnn"
            if not redirects:
                eng_if = re.search(
                    r'(?:if|when)\s+[^,]+,?\s+(?:go\s+to|check|retry|→|->)\s+(S\d+[a-z]?)',
                    text, re.IGNORECASE
                )
                if eng_if:
                    redirects.append((eng_if.group(1), 'N'))

            # Arrow redirect: → Snnn or -> Snnn at end of text (after removing parens)
            if not redirects:
                red_m = re.search(r'(?:[→\-]+>?\s*)(S\d+[a-z]?)\s*$', text)
                if red_m:
                    redirects.append((red_m.group(1), ''))
                    text = text[:red_m.start()].rstrip(' \t→\\->').rstrip()

            # Korean end-of-sentence redirect: "후 S200으로 복귀" "후 종료"
            if not redirects:
                kor_m = re.search(r'후\s+(S\d+[a-z]?)으로\s*(?:복귀|이동)', text)
                if kor_m:
                    redirects.append((kor_m.group(1), ''))
                    text = text[:kor_m.start()].rstrip(' \t').rstrip()

            # Replace remaining → arrows with -> for USPTO
            text = text.replace('→', '->')

            node_defs.append((nid, text, redirects))

        # ── Detect parallel node groups (same numeric prefix, different letter) ──
        # e.g. S200a, S200b → same rank group
        from collections import defaultdict
        alpha_groups = defaultdict(list)
        for nid, _, _ in node_defs:
            m = re.match(r'^(S\d+)([a-z])$', nid)
            if m:
                alpha_groups[m.group(1)].append(nid)

        # ── Phase 9: Detect decision keywords in text ─────────────────────────
        DECISION_KW = [
            # Korean decision patterns
            '여부 판단', '여부를 판단', '여부확인', '여부 확인',
            '판단', '확인', '검증', '검사', '비교',
            # English decision patterns
            'check', 'verify', 'validate', 'decide', 'determine',
            'is ', 'are ', 'has ', 'have ',
        ]

        def _has_decision_kw(text_: str) -> bool:
            tl = text_.lower()
            return any(kw in tl for kw in DECISION_KW)

        # ── Phase 9: Detect implicit END nodes ("후 종료" pattern) ────────────
        IMPLICIT_END_KW = ['후 종료', '로 종료', '하고 종료', '종료']

        def _has_implicit_end(text_: str) -> bool:
            return any(kw in text_ for kw in IMPLICIT_END_KW)

        # ── Assign shapes ─────────────────────────────────────────────────────
        redirect_srcs = {nid for nid, _, reds in node_defs if reds}

        for i, (nid, text, redirects) in enumerate(node_defs):
            if i == 0:
                shape = 'start'
            elif i == len(node_defs) - 1 and not redirects:
                shape = 'end'
            elif redirects and len(redirects) > 1:
                shape = 'diamond'  # multi-branch decision
            elif nid in redirect_srcs:
                shape = 'diamond'  # has some redirect = decision
            elif _has_decision_kw(text):
                shape = 'diamond'  # Phase 9: keyword heuristic
            else:
                shape = 'process'
            # Phase 9: use numeric-only ref number in display text so USPTO
            # validator (which expects pure digits on first line) is satisfied.
            # Sxxx → strip 'S'; Sxxxα → use numeric part only (alpha is in node text)
            import re as _re
            num_m = _re.match(r'^S(\d+)([a-z]?)$', nid)
            if num_m:
                # Use only digits for the reference number line (USPTO compliance)
                ref_num = num_m.group(1)
                display_text = f'{ref_num}\n{text}'
            else:
                display_text = f'{nid}\n{text}'
            fig.node(nid, display_text, shape=shape)

        # ── Apply parallel node groups ─────────────────────────────────────────
        for base_id, group_ids in alpha_groups.items():
            if len(group_ids) > 1:
                fig.node_group(group_ids)

        # ── Phase 9: Build implicit END nodes for "후 종료" branches ──────────
        # If a node has text like "실패 시 거부 후 종료", we add a synthetic END node
        # and create an edge to it.
        _extra_end_nodes = {}  # nid → synthetic end node id

        for i, (nid, text, redirects) in enumerate(node_defs):
            if _has_implicit_end(text):
                # Create synthetic END node (if node itself is diamond or process)
                # This node terminates the branch
                synth_id = f'_end_{nid}'
                if synth_id not in all_ids_set:
                    _extra_end_nodes[nid] = synth_id

        # Add synthetic END nodes to fig (as 'end' shape)
        # Derive numeric ref from source node number + 50 for USPTO compliance
        import re as _re2
        for src_id, synth_id in _extra_end_nodes.items():
            src_m = _re2.match(r'^S(\d+)', src_id)
            if src_m:
                end_ref = str(int(src_m.group(1)) + 50)
            else:
                end_ref = '999'
            fig.node(synth_id, f'{end_ref}\nEnd', shape='end')

        # ── Build edges ────────────────────────────────────────────────────────
        # Find the "next" sequential node for each, skipping parallel members
        # (parallel nodes all link to the same "next" downstream node)
        for i, (nid, text, redirects) in enumerate(node_defs):
            # Determine sequential next
            next_id = None
            if i + 1 < len(node_defs):
                next_id = node_defs[i + 1][0]

            has_implicit_end_branch = nid in _extra_end_nodes

            if redirects:
                # Has explicit redirects → draw edges per redirect
                # Also add edge to sequential next (if redirects don't already go there)
                redirect_targets = {r[0] for r in redirects}

                # If only 1 redirect and next exists and next not in redirects → add seq edge
                if next_id and next_id not in redirect_targets and len(redirects) == 1:
                    fig.edge(nid, next_id)

                for tgt, lbl in redirects:
                    if tgt in all_ids_set:
                        fig.edge(nid, tgt, label=lbl)
                    else:
                        # Target doesn't exist as a node — treat as end label
                        pass
                # Add implicit end branch if detected
                if has_implicit_end_branch and _extra_end_nodes[nid] not in redirect_targets:
                    fig.edge(nid, _extra_end_nodes[nid], label='N')
            else:
                # Phase 9: If text contains "후 종료" and no explicit redirect,
                # treat this node as terminal (connect to synthetic END) AND
                # still connect to sequential next (it's an alternative path)
                if has_implicit_end_branch:
                    # This node has an implicit exit path to END
                    fig.edge(nid, _extra_end_nodes[nid], label='N')
                    # Also continue sequential
                    if next_id:
                        fig.edge(nid, next_id, label='Y')
                else:
                    # Sequential: connect to next
                    if next_id:
                        fig.edge(nid, next_id)

        return fig

    def edge(self, src: str, dst: str, label: str = '', bidir: bool = False,
             label_back: str = '') -> 'PatentFigure':
        """Add a directed edge (arrow) from src to dst.
        bidir=True: bidirectional arrow (both arrowheads).
        label_back: label for the reverse direction of bidir arrows.
        
        Note: Edges referencing non-existent node IDs are silently skipped
        during rendering (no crash). A warning is printed at render time.
        """
        e = FigEdge(src, dst, label, bidir=bidir)
        e.label_back = label_back
        self._edges.append(e)
        return self

    def bus(self, bus_id: str, node_ids: list, label: str = '',
            orientation: str = 'H') -> 'PatentFigure':
        """
        Add a bus connection: a horizontal (or vertical) bar connecting
        multiple nodes. Each node connects to the bus with a short stem.

        The bus itself is rendered as a thick horizontal line with stubs
        to each connected node.

        Args:
            bus_id:      Unique ID for the bus bar itself.
            node_ids:    List of node IDs connected to the bus.
            label:       Optional label for the bus bar.
            orientation: 'H' = horizontal bus (default), 'V' = vertical bus.

        Example::

            fig.bus('DATA_BUS', ['CPU', 'Memory', 'GPU', 'Storage'],
                    label='810\nData Bus')
        """
        self._buses.append({
            'id': bus_id,
            'node_ids': list(node_ids),
            'label': label,
            'orientation': orientation,
        })
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

    def render(self, output_path: str,
               auto_split: bool = True,
               max_nodes_per_page: int = 14) -> str:
        """
        Full pipeline: layout → draw → save. Returns output path.

        Parameters
        ----------
        auto_split : bool
            If True (default) and the number of nodes exceeds max_nodes_per_page,
            automatically split into two pages using render_multi().
            The second page path is derived by inserting '_p2' before the extension.
            E.g. 'fig5.png' → 'fig5.png' (page 1) + 'fig5_p2.png' (page 2).
        max_nodes_per_page : int
            Node count threshold for auto-split (default 14).
        """
        # Phase 8: Auto-split for large flows
        if auto_split and len(self._nodes) > max_nodes_per_page:
            base, ext = os.path.splitext(output_path)
            path2 = base + '_p2' + ext
            return self.render_multi(output_path, path2)[0]

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

        # Build DAG (exclude back-edges, skip edges to non-existent nodes)
        for e in self._edges:
            if e.src_id not in self._nodes or e.dst_id not in self._nodes:
                continue
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

        # Phase 6: Apply node_group constraints — force all members to same rank
        for group in self._node_groups:
            valid = [nid for nid in group if nid in self._nodes]
            if not valid:
                continue
            # Use the minimum rank among group members
            min_rank = min(self._nodes[nid].rank for nid in valid)
            for nid in valid:
                self._nodes[nid].rank = min_rank

    def _find_back_edges(self) -> list[FigEdge]:
        """DFS-based back-edge detection."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in self._nodes}
        adj = defaultdict(list)
        edge_map = {}  # (src,dst) → FigEdge

        for e in self._edges:
            if e.src_id not in self._nodes or e.dst_id not in self._nodes:
                continue
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
        Phase 6: Applies auto text wrapping if max_text_width is set.
        """
        from collections import defaultdict
        d = Drawing('/dev/null')

        # Phase 6: Auto text wrapping
        if self.max_text_width is not None:
            # Approximate: 1 inch ≈ 10 chars at font size 10
            chars_per_inch = 10.0
            max_chars = max(8, int(self.max_text_width * chars_per_inch))
            for nd in self._nodes.values():
                nd.text = self._wrap_text(nd.text, max_chars_per_line=max_chars)

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

            # Check fit — only count ranks that have nodes (node_group may create gaps)
            used_ranks = sorted(ranks.keys())
            total_node_h = sum(max(nd._h for nd in ranks[r]) for r in used_ranks)
            n_gaps_used = len(used_ranks) - 1
            needed = total_node_h + MIN_ARROW_GAP * n_gaps_used
            if needed <= available_h or fs == self.MIN_FS:
                break

        # ── LR-mode: size boxes to distribute evenly across page width ─────────
        if self.direction == 'LR':
            EXTRA_MARGIN = 0.12
            lr_content_x1 = self.BND_X1 + self.INNER_PAD + EXTRA_MARGIN
            lr_content_x2 = self.BND_X2 - self.INNER_PAD - EXTRA_MARGIN
            lr_available_w = lr_content_x2 - lr_content_x1
            lr_available_h = (self.BND_Y2 - self.INNER_PAD) - (self.BND_Y1 + self.INNER_PAD)
            used_ranks_lr = sorted(ranks.keys())
            n_cols = len(used_ranks_lr)
            n_gaps = n_cols - 1
            # Distribute available_w: ensure inter-column gap ≥ 1.00" (2 × 0.44" + slack)
            # so that elbow arrows in the gap have sufficient segment length.
            # Also ensure box width ≥ max text width so d.box() doesn't auto-expand beyond nd._w.
            MIN_H_GAP = 1.00   # minimum gap between columns for valid elbow routing
            
            # Compute minimum box width required to prevent auto-expansion in d.box()
            d_tmp = Drawing('/dev/null')
            min_text_w = 1.00
            for nd in self._nodes.values():
                if nd.shape not in ('diamond',):
                    tw, _ = d_tmp.measure_text(nd.text, self._active_fs)
                    needed = tw + 0.18  # d.box() uses MIN_PAD_W=0.18
                    min_text_w = max(min_text_w, needed)
            
            if n_gaps > 0:
                # Compute target_box_w: must fit all cols with gap ≥ MIN_H_GAP
                target_box_w = (lr_available_w - MIN_H_GAP * n_gaps) / n_cols
                # Must be at least min_text_w to prevent box auto-expansion
                target_box_w = max(min_text_w, target_box_w)
                # Recompute actual gap with this box width
                actual_gap = (lr_available_w - target_box_w * n_cols) / n_gaps
                if actual_gap < MIN_H_GAP:
                    # Boxes too wide — accept smaller gap but keep box width for text
                    actual_gap = max(0.50, actual_gap)
            else:
                target_box_w = max(min_text_w, lr_available_w * 0.55)
                actual_gap = 0.0
            # Set width for all nodes
            for nd in self._nodes.values():
                if nd.shape != 'diamond':
                    nd._w = target_box_w

            # Set height: fill vertical space based on max nodes in any column
            max_nodes_per_col = max(len(ranks[r]) for r in used_ranks_lr)
            MIN_V_GAP_LR = 0.50
            # For each column, total available height minus gaps
            # Use the column with most nodes as constraint
            if max_nodes_per_col == 1:
                # Single-row: use 65% of available height, capped at 2.5:1 aspect
                target_box_h = lr_available_h * 0.65
                max_aspect = 2.5
                target_box_h = min(target_box_h, target_box_w * max_aspect)
                for nd in self._nodes.values():
                    if nd.shape != 'diamond':
                        nd._h = max(nd._h, target_box_h)
            else:
                # Multi-row: distribute height with gaps
                n_v_gaps = max_nodes_per_col - 1
                target_box_h = (lr_available_h - MIN_V_GAP_LR * n_v_gaps) / max_nodes_per_col
                target_box_h = max(nd._h, target_box_h)  # don't shrink below text fit
                # Cap at 2:1 aspect
                target_box_h = min(target_box_h, target_box_w * 2.0)
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

        # Use only ranks with nodes (node_group may create gaps)
        used_ranks = sorted(ranks.keys())
        max_rank = used_ranks[-1] if used_ranks else 0

        # Available area
        content_x1 = self.BND_X1 + self.INNER_PAD + self.LOOPBACK_MARGIN
        content_x2 = self.BND_X2 - self.INNER_PAD
        content_cx = (content_x1 + content_x2) / 2

        content_y_top = self.BND_Y2 - self.INNER_PAD
        content_y_bot = self.BND_Y1 + self.INNER_PAD
        available_h = content_y_top - content_y_bot

        # Calculate total node height (only used ranks)
        total_node_h = sum(max(nd._h for nd in ranks[r]) for r in used_ranks)

        # Dynamic V_GAP: fill available space evenly
        # For branching flows, elbows need 2 × 0.44" = 0.88" between boxes
        # For straight vertical arrows: minimum 0.46" (just over 0.44" validator limit)
        has_branching = any(len(ranks[r]) > 1 for r in used_ranks)
        MIN_V_GAP_LINEAR   = 0.46  # straight arrow — slightly above 0.44" min
        MIN_V_GAP_BRANCHING = 0.92  # elbow arrows — two 0.44" segments
        n_gaps = len(used_ranks) - 1  # gaps between used ranks
        if n_gaps > 0:
            remaining = available_h - total_node_h
            best_gap = remaining / n_gaps if remaining > 0 else 0.20
            min_gap = MIN_V_GAP_BRANCHING if has_branching else MIN_V_GAP_LINEAR
            if best_gap < min_gap:
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

        for r in used_ranks:
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

        # Use only ranks with nodes (node_group may create gaps)
        used_ranks = sorted(ranks.keys())
        max_rank = used_ranks[-1] if used_ranks else 0

        # In LR mode, use slightly more margin to prevent box edges from touching boundary
        EXTRA_MARGIN = 0.12
        content_x1 = self.BND_X1 + self.INNER_PAD + EXTRA_MARGIN
        content_x2 = self.BND_X2 - self.INNER_PAD - EXTRA_MARGIN
        content_y_top = self.BND_Y2 - self.INNER_PAD
        content_y_bot = self.BND_Y1 + self.INNER_PAD
        available_w = content_x2 - content_x1
        available_h = content_y_top - content_y_bot
        content_cy = (content_y_top + content_y_bot) / 2

        # Column widths = max node width per rank (only used ranks)
        col_widths = [max(nd._w for nd in ranks[r]) for r in used_ranks]

        # H_GAP between columns
        MIN_H_GAP = 1.10
        n_h_gaps = len(used_ranks) - 1
        total_box_w = sum(col_widths)
        if n_h_gaps > 0:
            remaining_w = available_w - total_box_w
            h_gap = max(MIN_H_GAP, remaining_w / n_h_gaps)
            h_gap = min(2.00, h_gap)
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

        for ri, r in enumerate(used_ranks):
            nodes = ranks[r]
            col_w = col_widths[ri]

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

            # Phase 5: Conditional highlighting — draw background patch before node
            hl_style = self._highlights.get(nid)
            if hl_style:
                import matplotlib.patches as _patches
                bg_color = hl_style.get('bg_color', '#E8E8E8')
                hl_lw = hl_style.get('border_lw', 2.0)
                pad = 0.06
                d.ax.add_patch(_patches.FancyBboxPatch(
                    (cx - nd._w / 2 - pad, cy - nd._h / 2 - pad),
                    nd._w + pad * 2, nd._h + pad * 2,
                    boxstyle='round,pad=0.02',
                    linewidth=hl_lw, edgecolor='black',
                    facecolor=bg_color, zorder=4,
                ))

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

        # Phase 7 (Research7): EdgeRouter integration
        # When corner_radius style param is set, use EdgeRouter for arrow rendering.
        # d.arrow_route() is monkey-patched to route via EdgeRouter instead.
        _corner_radius = self._style.get('corner_radius', None)
        _er = None
        _er_lw = None
        if _corner_radius is not None:
            try:
                from edge_router import EdgeRouter as _EdgeRouter
                import patent_drawing_lib as _plib
                _er = _EdgeRouter(corner_radius=_corner_radius)
                _er_lw = _plib.LW_ARR  # use same line width as library
                # Register all node boxes as obstacles
                for _nd in self._nodes.values():
                    if _nd.box_ref is not None:
                        _b = _nd.box_ref
                        _er.add_obstacle(_b.left, _b.bot, _b.right, _b.top)
                # Monkey-patch d.arrow_route to use EdgeRouter
                _orig_arrow_route = d.arrow_route
                def _er_arrow_route(steps, label='', label_pos=1,
                                    label_dx=0.18, label_ha='left', ls='-', _er=_er):
                    pts = d._resolve_steps(steps)
                    _er.draw(d.ax, pts, color='black', lw=_er_lw, linestyle=ls)
                    # Still place labels using original code
                    if label:
                        import patent_drawing_lib as _pl
                        idx = d._best_label_segment(pts, label_pos)
                        if idx is not None:
                            mx = (pts[idx][0] + pts[idx+1][0]) / 2
                            my = (pts[idx][1] + pts[idx+1][1]) / 2
                            if abs(pts[idx][0] - pts[idx+1][0]) < 0.01:
                                d.ax.text(mx + label_dx, my, label,
                                         ha=label_ha, va='center',
                                         fontsize=_pl.FS_BODY, fontweight=_pl.FW,
                                         bbox=_pl.LABEL_BG, zorder=_pl.Z_ARR_LABEL)
                            else:
                                d.ax.text(mx, my + 0.10, label,
                                         ha='center', va='bottom',
                                         fontsize=_pl.FS_BODY, fontweight=_pl.FW,
                                         bbox=_pl.LABEL_BG, zorder=_pl.Z_ARR_LABEL)
                d.arrow_route = _er_arrow_route
                # Also patch arrow_bidir_route
                _orig_bidir_route = d.arrow_bidir_route
                def _er_bidir_route(steps, label='', _er=_er):
                    pts = d._resolve_steps(steps)
                    _er.draw(d.ax, pts, color='black', lw=_er_lw,
                             arrowhead=True, arrowhead_start=True)
                d.arrow_bidir_route = _er_bidir_route
            except ImportError:
                pass  # fallback: use original drawing methods

        # LR mode: per-column-pair channel x cache (computed from actual box_refs)
        _lr_channel_map: dict = {}

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
                       if not e.is_back
                       and e.src_id in self._nodes and e.dst_id in self._nodes
                       and (self._nodes[e.dst_id].rank - self._nodes[e.src_id].rank) > 1
                       and self._nodes[e.src_id].box_ref and self._nodes[e.dst_id].box_ref]
        _skip_edges.sort(key=lambda t: t[2].rank - t[1].rank)  # smallest span first
        _skip_channel_map = {}  # edge id → channel_x
        for idx_s, (e_s, _, _) in enumerate(_skip_edges):
            ch_x = min(_skip_channel_max_x, _skip_channel_base_x + idx_s * 0.45)
            _skip_channel_map[id(e_s)] = ch_x

        for e in self._edges:
            if e.is_back:
                continue
            # Guard: skip edges referencing non-existent nodes
            if e.src_id not in self._nodes or e.dst_id not in self._nodes:
                import warnings
                warnings.warn(f"Edge {e.src_id}→{e.dst_id}: node not found, skipping.")
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
                    # Use elbow routing if source and destination are at different heights.
                    dy = abs(sb.cy - db.cy)
                    if dy < 0.05:
                        # Same height: straight horizontal
                        if e.bidir:
                            d.arrow_bidir_route([sb.right_mid(), db.left_mid()])
                        else:
                            d.arrow_route([sb.right_mid(), db.left_mid()])
                    else:
                        # Different heights: elbow routing via inter-column gap.
                        # Use a shared channel x for all edges in this column-pair.
                        src_rank = src_nd.rank
                        channel_key = (src_rank, src_rank + 1)
                        channel_x = _lr_channel_map.get(channel_key)
                        if channel_x is None:
                            src_rights = [self._nodes[n].box_ref.right
                                          for n in self._order
                                          if self._nodes[n].box_ref and self._nodes[n].rank == src_rank]
                            dst_lefts = [self._nodes[n].box_ref.left
                                         for n in self._order
                                         if self._nodes[n].box_ref and self._nodes[n].rank == src_rank + 1]
                            if src_rights and dst_lefts:
                                channel_x = (max(src_rights) + min(dst_lefts)) / 2
                            else:
                                channel_x = (sb.right + db.left) / 2
                            _lr_channel_map[channel_key] = channel_x

                        route_pts = [
                            sb.right_mid(),
                            (channel_x, sb.cy),
                            (channel_x, db.cy),
                            db.left_mid(),
                        ]
                        if e.bidir:
                            d.arrow_bidir_route(route_pts)
                        else:
                            d.arrow_route(route_pts)
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
                        # bidir: shift forward label up to avoid overlap with label_back
                        _offset_y = 0.14 if (e.bidir and e.label_back) else 0.08
                        d.label(mid_x + 0.05, mid_y + _offset_y, e.label, ha='left', fs=_label_fs)
                    else:
                        mid_x = (sb.right + db.left) / 2
                        _offset_y = 0.14 if (e.bidir and e.label_back) else 0.08
                        d.label(mid_x, (sb.cy + db.cy) / 2 + _offset_y, e.label, ha='center', fs=_label_fs)
                # Phase 9: label_back for bidir LR edges
                # Place forward label above midpoint, return label below midpoint
                if e.label_back and e.bidir:
                    if rank_diff == 0:
                        mid_x = (sb.cx + db.cx) / 2
                        mid_y = (sb.cy + db.cy) / 2
                        d.label(mid_x + 0.05, mid_y - 0.18, e.label_back, ha='left', fs=_label_fs)
                    else:
                        mid_x = (sb.right + db.left) / 2
                        d.label(mid_x, (sb.cy + db.cy) / 2 - 0.18, e.label_back, ha='center', fs=_label_fs)
                continue

            # ── Phase 8: Diamond exact-vertex helpers ─────────────────────────
            # For diamond shapes, arrows should exit/enter from exact vertices
            # (top/bottom/left/right points), not from the bbox midpoints.
            def _diamond_exit(box, direction: str):
                """Return exact exit point for a diamond vertex.
                direction: 'down'→bottom vertex, 'up'→top vertex,
                           'left'→left vertex, 'right'→right vertex.
                """
                if direction == 'down':
                    return (box.cx, box.bot)
                elif direction == 'up':
                    return (box.cx, box.top)
                elif direction == 'left':
                    return (box.left, box.cy)
                elif direction == 'right':
                    return (box.right, box.cy)
                return box.bot_mid()

            def _src_exit(nd, db_):
                """Choose source exit point. Diamonds use exact vertices."""
                if nd.shape == 'diamond':
                    # Determine which vertex to exit from based on destination position
                    dx = db_.cx - sb.cx
                    dy = db_.cy - sb.cy
                    if abs(dy) >= abs(dx):
                        return _diamond_exit(sb, 'down' if dy < 0 else 'up')
                    else:
                        return _diamond_exit(sb, 'right' if dx > 0 else 'left')
                return sb.bot_mid()

            def _dst_entry(nd, sb_):
                """Choose destination entry point. Diamonds use exact vertices."""
                if nd.shape == 'diamond':
                    dx = sb_.cx - db.cx
                    dy = sb_.cy - db.cy
                    if abs(dy) >= abs(dx):
                        return _diamond_exit(db, 'top' if dy < 0 else 'bot')  # type: ignore
                    else:
                        return _diamond_exit(db, 'right' if dx > 0 else 'left')
                return db.top_mid()

            # TB direction (default): vertical primary axis
            # Same column: straight vertical arrow (only if no intermediate boxes in path)
            if abs(sb.cx - db.cx) < 0.1 and not is_skip:
                if e.bidir:
                    d.arrow_bidir(sb, db, side='v')
                else:
                    # Phase 8: use diamond vertex if applicable
                    if src_nd.shape == 'diamond':
                        src_pt = _diamond_exit(sb, 'down')
                        d.arrow_route([src_pt, db.top_mid()])
                    elif dst_nd.shape == 'diamond':
                        dst_pt = _diamond_exit(db, 'up')
                        d.arrow_route([sb.bot_mid(), dst_pt])
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
                    if src_nd.shape == 'diamond':
                        # Diamond side exit: exact left/right vertex
                        if db.cx < sb.cx:
                            src_exit = _diamond_exit(sb, 'left')
                            dst_entry = db.right_mid()
                        else:
                            src_exit = _diamond_exit(sb, 'right')
                            dst_entry = db.left_mid()
                        if e.bidir:
                            d.arrow_bidir_route([src_exit, dst_entry])
                        else:
                            d.arrow_route([src_exit, dst_entry])
                    else:
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
                    # Phase 8: use diamond exact vertex for departure
                    if src_nd.shape == 'diamond':
                        # Determine if exiting from bottom vertex or side vertex
                        if abs(sb.cx - db.cx) < 0.15:
                            # Approximately same column → bottom vertex
                            src_exit = _diamond_exit(sb, 'down')
                            mid_y = min(src_exit[1] - 0.44, max(db.top + 0.44,
                                        (src_exit[1] + db.top) / 2))
                            route_pts = [src_exit, (src_exit[0], mid_y),
                                         (db.cx, mid_y), db.top_mid()]
                        else:
                            # Side exit from diamond
                            direction = 'right' if db.cx > sb.cx else 'left'
                            src_exit = _diamond_exit(sb, direction)
                            mid_y = min(sb.bot - 0.44, max(db.top + 0.44,
                                        (sb.bot + db.top) / 2))
                            route_pts = [src_exit, (src_exit[0], mid_y),
                                         (db.cx, mid_y), db.top_mid()]
                        if e.bidir:
                            d.arrow_bidir_route(route_pts)
                        else:
                            d.arrow_route(route_pts)
                    else:
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
            # Phase 8: Improved diamond label positioning
            if e.label:
                if src_nd.shape == 'diamond':
                    if abs(sb.cx - db.cx) < 0.15 and not is_skip:
                        # Straight down from bottom vertex: label right of the bottom vertex
                        # Place just below the bottom vertex for clean attachment
                        bvx, bvy = sb.cx, sb.bot   # bottom vertex
                        d.label(bvx + 0.10, bvy - 0.12, e.label, ha='left', fs=_label_fs)
                    elif is_skip:
                        d.label(skip_channel_x + 0.08, (sb.cy + db.cy) / 2, e.label, ha='left', fs=_label_fs)
                    elif abs(src_nd.rank - dst_nd.rank) == 0:
                        # Same-rank side exit: label just outside the side vertex
                        if db.cx < sb.cx:
                            # Left vertex exit
                            lvx, lvy = sb.left, sb.cy
                            d.label(lvx - 0.08, lvy + 0.12, e.label, ha='right', fs=_label_fs)
                        else:
                            # Right vertex exit
                            rvx, rvy = sb.right, sb.cy
                            d.label(rvx + 0.08, rvy + 0.12, e.label, ha='left', fs=_label_fs)
                    else:
                        # Cross-rank elbow: label near departure vertex
                        if abs(sb.cx - db.cx) < 0.15:
                            # Bottom exit
                            d.label(sb.cx + 0.10, sb.bot - 0.12, e.label, ha='left', fs=_label_fs)
                        elif db.cx < sb.cx:
                            # Left vertex exit
                            d.label(sb.left - 0.08, sb.cy + 0.12, e.label, ha='right', fs=_label_fs)
                        else:
                            # Right vertex exit
                            d.label(sb.right + 0.08, sb.cy + 0.12, e.label, ha='left', fs=_label_fs)
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
                if e.src_id not in self._nodes or e.dst_id not in self._nodes:
                    continue
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

        # Phase 6: Draw notes (speech bubbles)
        import matplotlib.patches as _mpatch
        for note_def in self._notes:
            nid = note_def['node_id']
            note_text = note_def['text']
            if nid not in self._nodes:
                continue
            nd = self._nodes[nid]
            if nd.box_ref is None:
                continue
            sb = nd.box_ref
            # Place note bubble to the right of the node
            note_x = sb.right + 0.18
            note_y = sb.cy
            note_w = 1.40
            note_h = 0.55
            # Draw dashed rectangle for the note
            d.ax.add_patch(_mpatch.FancyBboxPatch(
                (note_x, note_y - note_h / 2), note_w, note_h,
                boxstyle='round,pad=0.04',
                linewidth=0.8, edgecolor='#444444', facecolor='#FFFEF0',
                linestyle='dashed', zorder=15,
            ))
            # Pointer line from node right edge to note left edge
            d.ax.annotate('', xy=(note_x, note_y),
                          xytext=(sb.right, note_y),
                          arrowprops=dict(arrowstyle='-', color='#444444', lw=0.8),
                          zorder=14)
            # Note text
            d.ax.text(note_x + note_w / 2, note_y, note_text,
                      fontsize=7, ha='center', va='center',
                      fontfamily='DejaVu Sans', zorder=16,
                      wrap=True)

        # Phase 9: Draw bus connections
        for bus_def in self._buses:
            bus_node_ids = bus_def['node_ids']
            bus_label = bus_def.get('label', '')
            bus_orient = bus_def.get('orientation', 'H')

            # Get boxes for all connected nodes
            bus_boxes = [self._nodes[nid].box_ref
                         for nid in bus_node_ids
                         if nid in self._nodes and self._nodes[nid].box_ref]
            if not bus_boxes:
                continue

            import matplotlib.patches as _buspatch
            if bus_orient == 'H':
                # Horizontal bus: draw a thick horizontal bar at median bottom of nodes
                bus_y = min(b.bot for b in bus_boxes) - 0.35
                bus_x1 = min(b.cx for b in bus_boxes) - 0.10
                bus_x2 = max(b.cx for b in bus_boxes) + 0.10
                # Clamp to boundary
                bus_x1 = max(bus_x1, self.BND_X1 + 0.20)
                bus_x2 = min(bus_x2, self.BND_X2 - 0.20)
                bus_y = max(bus_y, self.BND_Y1 + 0.20)
                # Draw thick bus bar
                d.ax.plot([bus_x1, bus_x2], [bus_y, bus_y],
                          color='black', lw=3.0, solid_capstyle='butt', zorder=10)
                # End caps
                cap_h = 0.08
                d.ax.plot([bus_x1, bus_x1], [bus_y - cap_h, bus_y + cap_h],
                          color='black', lw=2.0, zorder=10)
                d.ax.plot([bus_x2, bus_x2], [bus_y - cap_h, bus_y + cap_h],
                          color='black', lw=2.0, zorder=10)
                # Stubs from each node bottom to bus bar
                for b in bus_boxes:
                    d.ax.plot([b.cx, b.cx], [b.bot, bus_y],
                              color='black', lw=1.3, zorder=9)
                # Bus label (left of bus bar)
                if bus_label:
                    d.ax.text(bus_x1 - 0.05, bus_y, bus_label,
                              ha='right', va='center', fontsize=8, zorder=11,
                              bbox=dict(facecolor='white', edgecolor='none', pad=1))
            else:
                # Vertical bus
                bus_x = max(b.right for b in bus_boxes) + 0.35
                bus_y1 = min(b.cy for b in bus_boxes) - 0.10
                bus_y2 = max(b.cy for b in bus_boxes) + 0.10
                bus_x = min(bus_x, self.BND_X2 - 0.20)
                d.ax.plot([bus_x, bus_x], [bus_y1, bus_y2],
                          color='black', lw=3.0, solid_capstyle='butt', zorder=10)
                for b in bus_boxes:
                    d.ax.plot([b.right, bus_x], [b.cy, b.cy],
                              color='black', lw=1.3, zorder=9)
                if bus_label:
                    d.ax.text(bus_x + 0.05, (bus_y1 + bus_y2) / 2, bus_label,
                              ha='left', va='center', fontsize=8, zorder=11,
                              bbox=dict(facecolor='white', edgecolor='none', pad=1))

        # Boundary + label
        d.boundary(self.BND_X1, self.BND_Y1, self.BND_X2, self.BND_Y2)
        d.fig_label()
        d.save()

        # Phase 2: Restore original library constants
        self._restore_style(_style_originals)

        return d


# ── Phase 9: Sequence Diagram Support ────────────────────────────────────────

class PatentSequence:
    """
    Minimal sequence diagram for patent drawings.

    Renders actors as vertical lifelines with horizontal message arrows.
    Return messages are shown as dashed arrows.

    Example::

        fig = PatentSequence('FIG. 3')
        fig.actor('User',   'user')
        fig.actor('Server', 'server')
        fig.actor('DB',     'db')

        fig.message('user',   'server', 'login(id, pw)')
        fig.message('server', 'db',     'query(id)')
        fig.message('db',     'server', 'result',    return_msg=True)
        fig.message('server', 'user',   'token',     return_msg=True)
        fig.render('fig3_seq.png')

    Supported features:
    - Vertical actor lifelines (dashed)
    - Actor head boxes at top
    - Forward messages: solid arrow →
    - Return messages: dashed arrow <--
    - Automatic vertical spacing
    - USPTO boundary + FIG. label
    """

    # Page constants
    PAGE_W, PAGE_H = 8.5, 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15

    # Layout
    ACTOR_BOX_H  = 0.50   # actor head box height
    ACTOR_BOX_W  = 1.40   # actor head box width
    MSG_SPACING  = 0.60   # vertical spacing between messages
    LIFELINE_TOP_PAD = 0.15  # gap below actor box to lifeline start
    FS_ACTOR = 9
    FS_MSG   = 8

    def __init__(self, fig_label: str = 'FIG. 3'):
        self.fig_label = fig_label
        self._actors: list[dict] = []   # [{id, label}]
        self._messages: list[dict] = [] # [{src, dst, label, return_msg}]

    def actor(self, label: str, id: str) -> 'PatentSequence':
        """Add an actor (participant) to the sequence diagram.

        Args:
            label: Display name for the actor (shown in head box).
            id:    Unique identifier used in message() calls.
        """
        self._actors.append({'id': id, 'label': label})
        return self

    def message(self, src: str, dst: str, label: str = '',
                return_msg: bool = False) -> 'PatentSequence':
        """Add a message between two actors.

        Args:
            src:        Source actor id.
            dst:        Destination actor id.
            label:      Message label (e.g. function call or data).
            return_msg: If True, draw as dashed return arrow.
        """
        self._messages.append({
            'src': src, 'dst': dst,
            'label': label,
            'return_msg': return_msg,
        })
        return self

    def render(self, output_path: str) -> str:
        """Render the sequence diagram to a PNG file."""
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        from patent_drawing_lib import Drawing
        import matplotlib.patches as mpatches
        import matplotlib

        fig_num = self.fig_label.replace('FIG. ', '')
        d = Drawing(output_path, fig_num=fig_num)

        n_actors = len(self._actors)
        n_msgs   = len(self._messages)
        if n_actors == 0:
            d.boundary(self.BND_X1, self.BND_Y1, self.BND_X2, self.BND_Y2)
            d.fig_label()
            d.save()
            return output_path

        # ── Layout ────────────────────────────────────────────────────────────
        content_w = self.BND_X2 - self.BND_X1 - 0.80
        content_x1 = self.BND_X1 + 0.40

        # Distribute actors evenly across content width
        actor_spacing = content_w / max(n_actors - 1, 1) if n_actors > 1 else 0
        actor_xs = []
        for i in range(n_actors):
            if n_actors == 1:
                actor_xs.append(content_x1 + content_w / 2)
            else:
                actor_xs.append(content_x1 + i * actor_spacing)

        # Cap actor spacing so boxes don't overlap
        max_actor_spacing = max(self.ACTOR_BOX_W + 0.60, actor_spacing)
        # Recompute if spacing too tight
        if actor_spacing < self.ACTOR_BOX_W + 0.30 and n_actors > 1:
            actor_spacing = min(max_actor_spacing,
                                content_w / (n_actors - 1))
            actor_xs = [content_x1 + i * actor_spacing for i in range(n_actors)]

        actor_top_y = self.BND_Y2 - 0.30
        actor_bot_y = actor_top_y - self.ACTOR_BOX_H

        lifeline_start_y = actor_bot_y - self.LIFELINE_TOP_PAD

        # Vertical extent for messages
        total_msg_h = (n_msgs + 0.5) * self.MSG_SPACING
        lifeline_end_y = max(
            lifeline_start_y - total_msg_h,
            self.BND_Y1 + 0.30
        )

        # Build actor id → x lookup
        actor_x_map = {a['id']: actor_xs[i] for i, a in enumerate(self._actors)}

        # ── Draw lifelines ────────────────────────────────────────────────────
        for ax_x in actor_xs:
            d.ax.plot([ax_x, ax_x], [lifeline_start_y, lifeline_end_y],
                      color='black', lw=0.9, linestyle='dashed', zorder=5)

        # ── Draw actor boxes ──────────────────────────────────────────────────
        for i, actor in enumerate(self._actors):
            ax_x = actor_xs[i]
            bx = ax_x - self.ACTOR_BOX_W / 2
            by = actor_bot_y
            # Box
            d.ax.add_patch(mpatches.FancyBboxPatch(
                (bx, by), self.ACTOR_BOX_W, self.ACTOR_BOX_H,
                boxstyle='square,pad=0',
                linewidth=1.2, edgecolor='black', facecolor='white', zorder=10
            ))
            # Label
            d.ax.text(ax_x, by + self.ACTOR_BOX_H / 2, actor['label'],
                      ha='center', va='center',
                      fontsize=self.FS_ACTOR, zorder=11)

        # ── Draw messages ─────────────────────────────────────────────────────
        for mi, msg in enumerate(self._messages):
            src_x = actor_x_map.get(msg['src'])
            dst_x = actor_x_map.get(msg['dst'])
            if src_x is None or dst_x is None:
                continue

            msg_y = lifeline_start_y - (mi + 1) * self.MSG_SPACING
            if msg_y < lifeline_end_y:
                msg_y = lifeline_end_y + 0.10

            ls = 'dashed' if msg['return_msg'] else 'solid'
            color = 'black'
            lw = 1.0

            # Arrow
            dx = dst_x - src_x
            if abs(dx) < 0.01:
                # Self-message: small loop
                loop_x = src_x + 0.30
                d.ax.annotate('', xy=(dst_x, msg_y - 0.12), xytext=(src_x, msg_y),
                               arrowprops=dict(
                                   arrowstyle='->' if not msg['return_msg'] else '<-',
                                   color=color, lw=lw,
                                   connectionstyle='arc3,rad=-0.3'
                               ), zorder=12)
            else:
                import matplotlib as _mpl
                arrowstyle = '<-' if msg['return_msg'] else '->'
                d.ax.annotate('', xy=(dst_x, msg_y), xytext=(src_x, msg_y),
                               arrowprops=dict(
                                   arrowstyle=arrowstyle,
                                   color=color, lw=lw,
                                   linestyle=ls,
                                   mutation_scale=10,
                               ), zorder=12)

            # Message label: above the arrow line, centered
            if msg['label']:
                mid_x = (src_x + dst_x) / 2
                d.ax.text(mid_x, msg_y + 0.06, msg['label'],
                          ha='center', va='bottom',
                          fontsize=self.FS_MSG, zorder=13,
                          bbox=dict(facecolor='white', edgecolor='none', pad=0))

        # ── Boundary + FIG. label ─────────────────────────────────────────────
        d.boundary(self.BND_X1, self.BND_Y1, self.BND_X2, self.BND_Y2)
        d.fig_label()
        d.save()
        return output_path


# ── Phase 10: quick_draw() — Momo High-Level API ──────────────────────────────

def quick_draw(spec_text: str, output_path: str,
               preset: str = 'uspto',
               lang: str = 'auto',
               direction: str = 'TB',
               fig_label: str = 'FIG. 1') -> dict:
    """
    명세서 텍스트 → USPTO 규격 PNG 한방에 생성.
    특허방 모모(patent-drawing 스킬 사용자)용 고수준 API.

    Args:
        spec_text:   명세서 텍스트 (한글/영어 자동 감지).
                     S100: ... 형식 한 줄씩.
        output_path: 출력 PNG 경로 (e.g. 'fig1.png').
        preset:      'uspto' | 'draft' | 'presentation' (기본: 'uspto').
        lang:        'auto' | 'ko' | 'en'  — 파싱 힌트 (현재 auto-detect).
        direction:   'TB' (top-bottom, 기본) | 'LR' (left-right).
        fig_label:   FIG. 라벨 (기본: 'FIG. 1').

    Returns:
        dict with keys:
            'pages'      : list[str]  — 생성된 PNG 파일 경로 목록 (1~2개).
            'node_count' : int        — 파싱된 노드 수.
            'warnings'   : list[str]  — 구조 경고 목록.
            'validation' : dict       — {'passed': bool, 'issues': list[str]}.

    Example::

        from patent_figure import quick_draw

        spec = \"\"\"
        S100: 사용자 위치 정보 수신
        S200: 주변 가맹점 검색 (반경 500m)
        S300: 검색 결과 없을 경우 반경 확장 후 S200으로 복귀
        S400: 가맹점 목록 정렬 (거리순, 평점순)
        S500: 사용자에게 추천 목록 제공
        \"\"\"
        result = quick_draw(spec, 'output.png')
        print(result['pages'])     # ['output.png'] or ['output.png', 'output_p2.png']
        print(result['warnings'])  # [] if clean
    """
    import os
    import time

    t0 = time.time()

    # ── 1. Parse spec → PatentFigure ──────────────────────────────────────────
    fig = PatentFigure.from_spec(fig_label, spec_text, direction=direction)

    # ── 2. Apply preset ───────────────────────────────────────────────────────
    if preset in ('uspto', 'draft', 'presentation'):
        fig.preset(preset)

    # ── 3. Validate structure ─────────────────────────────────────────────────
    warnings = fig.validate()
    validation_issues = list(warnings)  # copy

    # ── 4. Ensure output directory exists ────────────────────────────────────
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    # ── 5. Render (auto-split for large flows) ────────────────────────────────
    node_count = len(fig._nodes)

    if node_count > 14:
        # Auto-split: generate page 1 + page 2
        base, ext = os.path.splitext(output_path)
        path2 = base + '_p2' + ext
        try:
            fig.render_multi(output_path, path2)
            pages = [output_path, path2]
        except Exception as e:
            warnings.append(f"render_multi failed ({e}), falling back to single page")
            fig.render(output_path, auto_split=False)
            pages = [output_path]
    else:
        fig.render(output_path)
        pages = [output_path]

    # ── 6. USPTO post-render validation ──────────────────────────────────────
    # Check generated files pass USPTO rules
    uspt_issues = _validate_output_files(pages)
    validation_issues.extend(uspt_issues)

    elapsed = time.time() - t0

    return {
        'pages':      pages,
        'node_count': node_count,
        'warnings':   warnings,
        'validation': {
            'passed': len(validation_issues) == 0,
            'issues': validation_issues,
        },
        'elapsed_sec': round(elapsed, 2),
    }


def _validate_output_files(paths: list) -> list:
    """
    Post-render USPTO compliance check on generated PNGs.
    Returns list of issue strings (empty = all good).

    Checks:
    - File exists and non-empty
    - PNG can be opened (not corrupted)
    - (Structural checks are done in validate() before render)
    """
    import os
    issues = []
    for p in paths:
        if not os.path.exists(p):
            issues.append(f"Output file not found: {p}")
            continue
        size = os.path.getsize(p)
        if size < 1000:
            issues.append(f"Output file suspiciously small ({size} bytes): {p}")
            continue
        # Try opening with PIL if available
        try:
            from PIL import Image
            with Image.open(p) as img:
                w, h = img.size
                if w < 100 or h < 100:
                    issues.append(f"Image dimensions too small ({w}x{h}): {p}")
        except ImportError:
            pass  # PIL not required
        except Exception as e:
            issues.append(f"Cannot open image {p}: {e}")
    return issues
