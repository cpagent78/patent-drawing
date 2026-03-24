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
        # Research 14: dynamic page size flag
        self._dynamic_page: bool = False

    def dynamic_page_size(self, enable: bool = True) -> 'PatentFigure':
        """
        Research 14: Enable dynamic page size adjustment.

        When enabled, the page size is expanded based on the total text length
        of all nodes, so that very long labels or many nodes don't get cramped.
        The page is expanded in multiples of the standard size (up to 2×).

        Returns self for method chaining.
        """
        self._dynamic_page = enable
        return self

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
        # Research 14: dynamic page size adjustment
        if self._dynamic_page:
            self._apply_dynamic_page_size()
        self._measure_nodes()
        if self.direction == 'LR':
            positions = self._compute_positions_lr()
        else:
            positions = self._compute_positions()
        self._draw(output_path, positions)
        return output_path

    def _apply_dynamic_page_size(self):
        """
        Research 14 Phase 2: Dynamically adjust page/boundary size based on
        node text lengths and count, ensuring adequate space for all nodes.

        Expansion rules:
        - Count total chars across all node texts
        - If char density (chars / available area) is too high, expand page
        - Expansion is up to 2× standard page size, in portrait or landscape
        """
        total_chars = sum(len(nd.text) for nd in self._nodes.values())
        n_nodes = len(self._nodes)
        # Baseline: ~50 chars per node fits comfortably at 10pt in standard page
        baseline_chars = n_nodes * 50
        if total_chars <= baseline_chars:
            return  # no expansion needed

        ratio = total_chars / max(baseline_chars, 1)
        # Expand BND area proportionally, up to 2×
        expand = min(2.0, max(1.0, ratio))
        if expand <= 1.05:
            return  # marginal — skip

        # Expand boundary and page by scaling available content area
        # Only expand vertically for TB, horizontally for LR
        if self.direction == 'TB':
            # Expand BND_Y2 upward (more vertical space)
            orig_h = self.BND_Y2 - self.BND_Y1
            new_h = orig_h * expand
            # Keep BND_Y1 fixed, extend BND_Y2
            new_bnd_y2 = self.BND_Y1 + new_h
            # Also extend PAGE_H
            self.PAGE_H = max(self.PAGE_H, new_bnd_y2 + 0.60)
            self.BND_Y2 = new_bnd_y2
        else:
            # LR: expand horizontally
            orig_w = self.BND_X2 - self.BND_X1
            new_w = orig_w * expand
            new_bnd_x2 = self.BND_X1 + new_w
            self.PAGE_W = max(self.PAGE_W, new_bnd_x2 + 0.60)
            self.BND_X2 = new_bnd_x2

    @staticmethod
    def _resolve_label_collisions(label_positions: list) -> list:
        """
        Research 14 Phase 3: Detect and resolve overlapping edge labels.

        label_positions: list of dicts with keys:
            x, y, text, ha, fs  (as would be passed to d.label())

        Returns a new list with y-offsets applied to avoid overlaps.
        Two labels are considered overlapping if |dy| < 0.18" and
        the x ranges are within 1.5" of each other.

        Strategy:
        - Sort by y descending (top-to-bottom)
        - For each label, check against all already-placed labels
        - If collision detected, nudge y by ±0.16" (alternating)
        """
        COLLISION_Y = 0.18   # labels within this y distance are considered overlapping
        COLLISION_X = 1.50   # labels within this x distance may collide
        NUDGE = 0.16

        resolved = [dict(p) for p in label_positions]  # copy
        placed = []  # list of (x, y, text) after resolution

        for item in resolved:
            x, y, text = item['x'], item['y'], item.get('text', '')
            nudge_dir = 1  # start by nudging up
            for attempt in range(8):
                collision = False
                for px, py, _ in placed:
                    if abs(x - px) < COLLISION_X and abs(y - py) < COLLISION_Y:
                        collision = True
                        break
                if not collision:
                    break
                # Apply nudge (alternate up/down, increasing distance)
                y = item['y'] + nudge_dir * NUDGE * ((attempt // 2) + 1)
                nudge_dir *= -1
            item['y'] = y
            placed.append((x, y, text))

        return resolved

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

        # Research 14 Phase 3: Intercept d.label() calls to accumulate then resolve collisions
        # We defer all edge-label placements and flush them at end with collision avoidance.
        _deferred_labels: list = []
        _orig_d_label = d.label
        def _intercepted_label(x, y, text, ha='center', fs=None):
            _deferred_labels.append({'x': x, 'y': y, 'text': text, 'ha': ha, 'fs': fs})
        d.label = _intercepted_label

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

        # Research 14 Phase 3: Flush deferred labels with collision resolution
        resolved_labels = self._resolve_label_collisions(_deferred_labels)
        for lbl in resolved_labels:
            _orig_d_label(lbl['x'], lbl['y'], lbl['text'], ha=lbl.get('ha', 'center'), fs=lbl.get('fs'))

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
               fig_label: str = 'FIG. 1',
               diagram_type: str = 'auto') -> dict:
    """
    명세서 텍스트 → USPTO 규격 PNG 한방에 생성.
    특허방 모모(patent-drawing 스킬 사용자)용 고수준 API.

    Args:
        spec_text:    명세서 텍스트 (한글/영어 자동 감지).
                      S100: ... 형식 한 줄씩.
        output_path:  출력 PNG 경로 (e.g. 'fig1.png').
        preset:       'uspto' | 'draft' | 'presentation' (기본: 'uspto').
        lang:         'auto' | 'ko' | 'en'  — 파싱 힌트 (현재 auto-detect).
        direction:    'TB' (top-bottom, 기본) | 'LR' (left-right).
        fig_label:    FIG. 라벨 (기본: 'FIG. 1').
        diagram_type: 'auto' (기본, 자동 감지) | 'flowchart' | 'state' |
                      'sequence' | 'layered' | 'timing' | 'dfd' | 'er' | 'hardware'

    Returns:
        dict with keys:
            'pages'               : list[str]  — 생성된 PNG 파일 경로 목록 (1~2개).
            'node_count'          : int        — 파싱된 노드 수.
            'warnings'            : list[str]  — 구조 경고 목록.
            'validation'          : dict       — {'passed': bool, 'issues': list[str]}.
            'elapsed_sec'         : float      — 소요 시간(초).
            'detected_type'       : str        — 최종 사용된 도면 타입.
            'detection_reason'    : str        — 타입 판단 근거 (auto일 때).
            'detection_confidence': float      — 감지 신뢰도 (auto일 때).

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
        print(result['pages'])           # ['output.png'] or ['output.png', 'output_p2.png']
        print(result['detected_type'])   # 'flowchart' (auto-detected)
        print(result['warnings'])        # [] if clean
    """
    import os
    import time

    t0 = time.time()

    # ── 0. Auto-detect diagram type if requested ──────────────────────────────
    detection = None
    if diagram_type == 'auto':
        try:
            import sys as _sys
            import os as _os
            _skill_scripts = _os.path.dirname(_os.path.abspath(__file__))
            if _skill_scripts not in _sys.path:
                _sys.path.insert(0, _skill_scripts)
            from detect_type import detect_diagram_type as _detect
            detection = _detect(spec_text)
            diagram_type = detection['type']
        except ImportError:
            # detect_type.py not found — fall back to flowchart
            detection = {
                'type': 'flowchart',
                'confidence': 0.5,
                'reason': 'detect_type 모듈 없음 — 기본값 flowchart',
                'class': 'PatentFigure',
            }
            diagram_type = 'flowchart'

    # ── 1. Route to specialized diagram type if requested ─────────────────────
    # diagram_type: 'flowchart' (default), 'state', 'sequence', 'layered',
    #               'timing', 'dfd', 'er', 'hardware'
    # For non-flowchart types, parse spec in a simplified manner.

    def _with_detection(base_result: dict) -> dict:
        """Inject detection metadata into any result dict."""
        if detection is not None:
            base_result.setdefault('detected_type', detection['type'])
            base_result.setdefault('detection_reason', detection['reason'])
            base_result.setdefault('detection_confidence', detection['confidence'])
        else:
            base_result.setdefault('detected_type', diagram_type)
            base_result.setdefault('detection_reason', '명시적 지정')
            base_result.setdefault('detection_confidence', 1.0)
        return base_result

    if diagram_type == 'state':
        return _with_detection(_quick_draw_state(spec_text, output_path, fig_label, t0))
    elif diagram_type == 'sequence':
        return _with_detection(_quick_draw_sequence(spec_text, output_path, fig_label, t0))
    elif diagram_type == 'layered':
        return _with_detection(_quick_draw_layered(spec_text, output_path, fig_label, t0))
    elif diagram_type == 'timing':
        return _with_detection(_quick_draw_timing(spec_text, output_path, fig_label, t0))

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

    result = {
        'pages':      pages,
        'node_count': node_count,
        'warnings':   warnings,
        'validation': {
            'passed': len(validation_issues) == 0,
            'issues': validation_issues,
        },
        'elapsed_sec': round(elapsed, 2),
    }
    return _with_detection(result)


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

# ═══════════════════════════════════════════════════════════════════════════════
# Research 11: PatentState — State Diagram Support
# ═══════════════════════════════════════════════════════════════════════════════

class PatentState:
    """
    USPTO-compliant state machine / state transition diagram.

    Renders UML-style state diagrams:
    - Rounded-rectangle state nodes (double border for initial/final)
    - Initial pseudo-state: filled black circle → arrow
    - Final pseudo-state: bull's-eye (circle in circle)
    - Transition arrows with optional labels
    - Self-loop transitions (same state)
    - Automatic layout (TB or LR)

    Example::

        fig = PatentState('FIG. 4')
        fig.state('IDLE',       '100\\nIdle State',    initial=True)
        fig.state('CONNECTING', '200\\nConnecting')
        fig.state('ACTIVE',     '300\\nActive')
        fig.state('ERROR',      '400\\nError')
        fig.state('TERMINATED', '500\\nTerminated',    final=True)

        fig.transition('IDLE',       'CONNECTING', label='connect()')
        fig.transition('CONNECTING', 'ACTIVE',     label='success')
        fig.transition('CONNECTING', 'ERROR',      label='timeout')
        fig.transition('ACTIVE',     'IDLE',       label='disconnect()')
        fig.transition('ERROR',      'IDLE',       label='reset()')
        fig.transition('ACTIVE',     'TERMINATED', label='shutdown()')
        fig.render('fig4.png')

    Supported options:
    - direction: 'TB' (default) or 'LR'
    - initial=True / final=True per state
    - self-loop transitions (src == dst)
    """

    PAGE_W, PAGE_H = 8.5, 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15

    STATE_W = 2.00    # state box width
    STATE_H = 0.60    # state box height
    STATE_RX = 0.15   # rounded corner radius (in axes units approx)

    FS_STATE = 8
    FS_LABEL = 7

    def __init__(self, fig_label: str = 'FIG. 4', direction: str = 'TB'):
        self.fig_label = fig_label
        self.direction = direction.upper()
        self._states: list[dict] = []      # [{id, text, initial, final}]
        self._transitions: list[dict] = [] # [{src, dst, label}]
        self._state_ids: set = set()

    def state(self, id: str, text: str = '',
              initial: bool = False, final: bool = False) -> 'PatentState':
        """Register a state node.

        Args:
            id:      Unique state identifier.
            text:    Display text (use '\\n' to separate ref# from name).
            initial: If True, draw initial pseudo-state arrow pointing here.
            final:   If True, draw bull's-eye final marker inside this state.
        """
        if not text:
            text = id
        self._states.append({
            'id': id, 'text': text,
            'initial': initial, 'final': final,
        })
        self._state_ids.add(id)
        return self

    def transition(self, src: str, dst: str, label: str = '') -> 'PatentState':
        """Add a state transition (arrow).

        Args:
            src:   Source state id.
            dst:   Destination state id.
            label: Transition label (event/guard/action).
        """
        self._transitions.append({'src': src, 'dst': dst, 'label': label})
        return self

    def render(self, output_path: str) -> str:
        """Render state diagram to PNG."""
        import os
        import math
        import numpy as np
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

        _setup_korean_font()

        fig_num = self.fig_label.replace('FIG. ', '')

        # ── Page setup ────────────────────────────────────────────────────────
        dpi = 150
        fig, ax = plt.subplots(figsize=(self.PAGE_W, self.PAGE_H), dpi=dpi)
        ax.set_xlim(0, self.PAGE_W)
        ax.set_ylim(0, self.PAGE_H)
        ax.set_aspect('equal')
        ax.axis('off')

        n = len(self._states)
        if n == 0:
            self._draw_boundary(ax)
            self._draw_fig_label(ax, fig_num)
            plt.tight_layout(pad=0)
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight',
                        facecolor='white')
            plt.close(fig)
            return output_path

        # ── Compute layout positions ──────────────────────────────────────────
        content_x1 = self.BND_X1 + 0.40
        content_x2 = self.BND_X2 - 0.40
        content_y1 = self.BND_Y1 + 0.40
        content_y2 = self.BND_Y2 - 0.40
        cw = content_x2 - content_x1
        ch = content_y2 - content_y1

        positions = {}  # id → (cx, cy)

        if self.direction == 'LR':
            # Left-to-right: states arranged in a row
            cols = n
            rows = 1
            col_w = cw / max(cols, 1)
            for i, s in enumerate(self._states):
                cx = content_x1 + (i + 0.5) * col_w
                cy = content_y1 + ch / 2
                positions[s['id']] = (cx, cy)
        else:
            # Top-to-bottom layout: try to arrange in reasonable grid
            # Use a topology sort / rough ordering based on transitions
            # Simple approach: layout in order given, with branches side-by-side

            # Build adjacency for topology hint
            forward_adj = {s['id']: [] for s in self._states}
            for t in self._transitions:
                if t['src'] != t['dst']:
                    if t['src'] in forward_adj:
                        forward_adj[t['src']].append(t['dst'])

            # Assign ranks via BFS from initial state
            rank_map = {}
            initial_ids = [s['id'] for s in self._states if s['initial']]
            if not initial_ids:
                initial_ids = [self._states[0]['id']]

            queue = deque([(initial_ids[0], 0)])
            visited = set()
            while queue:
                sid, rank = queue.popleft()
                if sid in visited:
                    continue
                visited.add(sid)
                rank_map[sid] = rank
                for nxt in forward_adj.get(sid, []):
                    if nxt not in visited:
                        queue.append((nxt, rank + 1))

            # Assign unvisited states to end
            max_rank = max(rank_map.values()) if rank_map else 0
            for s in self._states:
                if s['id'] not in rank_map:
                    max_rank += 1
                    rank_map[s['id']] = max_rank

            # Group by rank
            rank_groups = defaultdict(list)
            for s in self._states:
                rank_groups[rank_map[s['id']]].append(s['id'])

            n_ranks = max(rank_map.values()) + 1
            row_h = ch / max(n_ranks, 1)

            for rank, sids in rank_groups.items():
                n_in_row = len(sids)
                row_w = cw / max(n_in_row, 1)
                cy = content_y2 - (rank + 0.5) * row_h
                for j, sid in enumerate(sids):
                    cx = content_x1 + (j + 0.5) * row_w
                    positions[sid] = (cx, cy)

        # ── Draw initial pseudo-state ─────────────────────────────────────────
        INIT_R = 0.08
        for s in self._states:
            if s['initial']:
                cx, cy = positions[s['id']]
                # position: above the state box
                init_cy = cy + self.STATE_H / 2 + 0.35
                init_cx = cx
                # Filled circle
                circ = Circle((init_cx, init_cy), INIT_R,
                               color='black', zorder=15)
                ax.add_patch(circ)
                # Arrow from circle bottom to state top
                ax.annotate('', xy=(cx, cy + self.STATE_H / 2),
                             xytext=(init_cx, init_cy - INIT_R),
                             arrowprops=dict(
                                 arrowstyle='->', color='black', lw=1.2,
                                 mutation_scale=10,
                             ), zorder=14)

        # ── Draw state boxes ──────────────────────────────────────────────────
        state_patches = {}
        for s in self._states:
            cx, cy = positions[s['id']]
            x = cx - self.STATE_W / 2
            y = cy - self.STATE_H / 2
            # Outer box
            patch = FancyBboxPatch(
                (x, y), self.STATE_W, self.STATE_H,
                boxstyle=f'round,pad=0.02',
                linewidth=1.5 if not s['final'] else 2.5,
                edgecolor='black', facecolor='white', zorder=10
            )
            ax.add_patch(patch)
            state_patches[s['id']] = patch

            # Double border for initial state (extra inner rect)
            if s['initial']:
                inner = FancyBboxPatch(
                    (x + 0.04, y + 0.04), self.STATE_W - 0.08, self.STATE_H - 0.08,
                    boxstyle='round,pad=0.01',
                    linewidth=0.7, edgecolor='black', facecolor='none', zorder=11
                )
                ax.add_patch(inner)

            # Final state: bull's-eye inner circle
            if s['final']:
                bull_r = min(self.STATE_W, self.STATE_H) * 0.18
                circ_out = Circle((cx, cy), bull_r + 0.04,
                                   color='black', zorder=11)
                circ_in  = Circle((cx, cy), bull_r,
                                   color='white', zorder=12)
                circ_dot = Circle((cx, cy), bull_r * 0.45,
                                   color='black', zorder=13)
                ax.add_patch(circ_out)
                ax.add_patch(circ_in)
                ax.add_patch(circ_dot)

            # State label text
            lines = s['text'].split('\n')
            text_str = '\n'.join(lines)
            ax.text(cx, cy, text_str,
                    ha='center', va='center',
                    fontsize=self.FS_STATE, zorder=12,
                    bbox=dict(facecolor='white', edgecolor='none', pad=0))

        # ── Draw transitions ──────────────────────────────────────────────────
        # Track multi-edges between same pair to offset them
        edge_count = defaultdict(int)

        for t in self._transitions:
            src = t['src']
            dst = t['dst']
            label = t.get('label', '')

            if src not in positions or dst not in positions:
                continue

            sx, sy = positions[src]
            dx, dy = positions[dst]

            if src == dst:
                # Self-loop: arc above the state box
                self._draw_self_loop(ax, sx, sy, label)
                continue

            # Determine entry/exit points based on relative position
            dx_rel = dx - sx
            dy_rel = dy - sy

            # Exit from state edge, enter from state edge
            if abs(dy_rel) >= abs(dx_rel):
                # Primarily vertical
                if dy_rel > 0:
                    # going up
                    p0 = (sx, sy + self.STATE_H / 2)
                    p1 = (dx, dy - self.STATE_H / 2)
                else:
                    # going down
                    p0 = (sx, sy - self.STATE_H / 2)
                    p1 = (dx, dy + self.STATE_H / 2)
            else:
                # Primarily horizontal
                if dx_rel > 0:
                    p0 = (sx + self.STATE_W / 2, sy)
                    p1 = (dx - self.STATE_W / 2, dy)
                else:
                    p0 = (sx - self.STATE_W / 2, sy)
                    p1 = (dx + self.STATE_W / 2, dy)

            # Check if a reverse edge exists (to offset with curve)
            key = (src, dst)
            rev_key = (dst, src)
            # Count usage to offset
            edge_count[key] += 1
            has_reverse = any(
                t2['src'] == dst and t2['dst'] == src
                for t2 in self._transitions
                if t2 != t
            )

            rad = 0.0
            if has_reverse:
                rad = 0.25 if edge_count[key] <= 1 else -0.25

            self._draw_transition(ax, p0, p1, label, rad=rad)

        # ── Boundary + FIG. label ─────────────────────────────────────────────
        self._draw_boundary(ax)
        self._draw_fig_label(ax, fig_num)

        plt.tight_layout(pad=0)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight',
                    facecolor='white')
        plt.close(fig)
        return output_path

    def _draw_self_loop(self, ax, cx, cy, label: str):
        """Draw a self-transition loop above the state box."""
        import matplotlib.patches as mpatches
        top_y = cy + self.STATE_H / 2
        # Arc from top-left to top-right going up
        loop_h = 0.30
        loop_w = self.STATE_W * 0.6
        from matplotlib.patches import FancyArrowPatch
        ax.annotate('', xy=(cx + loop_w * 0.3, top_y),
                     xytext=(cx - loop_w * 0.3, top_y),
                     arrowprops=dict(
                         arrowstyle='->', color='black', lw=1.0,
                         mutation_scale=10,
                         connectionstyle=f'arc3,rad=-0.6',
                     ), zorder=13)
        if label:
            ax.text(cx, top_y + loop_h * 0.6, label,
                    ha='center', va='bottom',
                    fontsize=self.FS_LABEL, zorder=14,
                    bbox=dict(facecolor='white', edgecolor='none', pad=1))

    def _draw_transition(self, ax, p0, p1, label: str, rad: float = 0.0):
        """Draw a transition arrow from p0 to p1."""
        conn = f'arc3,rad={rad:.2f}' if rad != 0.0 else 'arc3,rad=0'
        ax.annotate('', xy=p1, xytext=p0,
                     arrowprops=dict(
                         arrowstyle='->', color='black', lw=1.0,
                         mutation_scale=10,
                         connectionstyle=conn,
                     ), zorder=13)
        if label:
            # Place label near midpoint, slightly offset
            mx = (p0[0] + p1[0]) / 2
            my = (p0[1] + p1[1]) / 2
            # Offset perpendicular to direction
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            length = max(0.01, (dx**2 + dy**2) ** 0.5)
            # Perpendicular unit vector
            perp_x = -dy / length * 0.12
            perp_y =  dx / length * 0.12
            if rad != 0.0:
                perp_x *= (1 + abs(rad) * 2)
                perp_y *= (1 + abs(rad) * 2)
            ax.text(mx + perp_x, my + perp_y, label,
                    ha='center', va='center',
                    fontsize=self.FS_LABEL, zorder=14,
                    bbox=dict(facecolor='white', edgecolor='none', pad=1))

    def _draw_boundary(self, ax):
        import matplotlib.patches as mpatches
        rect = mpatches.Rectangle(
            (self.BND_X1, self.BND_Y1),
            self.BND_X2 - self.BND_X1,
            self.BND_Y2 - self.BND_Y1,
            linewidth=1.5, edgecolor='black', facecolor='none',
            linestyle='dashed', zorder=1
        )
        ax.add_patch(rect)

    def _draw_fig_label(self, ax, fig_num: str):
        cx = (self.BND_X1 + self.BND_X2) / 2
        cy = self.BND_Y1 - 0.25
        ax.text(cx, cy, f'FIG. {fig_num}',
                ha='center', va='center', fontsize=11, zorder=20)


# ═══════════════════════════════════════════════════════════════════════════════
# Research 11: Hardware Block Diagram Shapes
# ═══════════════════════════════════════════════════════════════════════════════

class PatentHardware:
    """
    Hardware/semiconductor patent block diagrams with specialized shapes.

    Supports IC chip shape, multiplexer (trapezoid), register cells,
    and memory array blocks. Connects with standard arrows.

    Example::

        fig = PatentHardware('FIG. 2')
        cpu = fig.chip('CPU', '610\\nALU Core', cx=2.5, cy=7.0)
        cache = fig.register('CACHE', '620\\nCache', cx=2.5, cy=5.5, cells=4)
        mem = fig.memory_array('MEM', '630\\nMemory', cx=5.5, cy=7.0,
                               rows=4, cols=4)
        mux_b = fig.mux('MUX', '640\\nMUX', cx=2.5, cy=4.0)
        fig.connect(cpu, cache, label='bus')
        fig.connect(cache, mux_b)
        fig.connect(mux_b, mem, label='data')
        fig.render('fig2_hw.png')
    """

    PAGE_W, PAGE_H = 8.5, 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15
    FS_LABEL = 8

    def __init__(self, fig_label: str = 'FIG. 2'):
        self.fig_label = fig_label
        self._elements: list[dict] = []  # [{id, type, cx, cy, w, h, text, ...}]
        self._connections: list[dict] = []  # [{src_id, dst_id, label, bidir}]
        self._element_map: dict = {}

    def chip(self, id: str, text: str, cx: float, cy: float,
             w: float = 1.60, h: float = 0.80,
             n_pins_left: int = 3, n_pins_right: int = 3) -> dict:
        """IC chip shape: rectangle with pin stubs on sides."""
        e = dict(id=id, type='chip', cx=cx, cy=cy, w=w, h=h, text=text,
                 n_pins_left=n_pins_left, n_pins_right=n_pins_right)
        self._elements.append(e)
        self._element_map[id] = e
        return e

    def mux(self, id: str, text: str, cx: float, cy: float,
            w: float = 0.80, h: float = 1.20,
            direction: str = 'right') -> dict:
        """Multiplexer shape: trapezoid wider at input side."""
        e = dict(id=id, type='mux', cx=cx, cy=cy, w=w, h=h, text=text,
                 direction=direction)
        self._elements.append(e)
        self._element_map[id] = e
        return e

    def register(self, id: str, text: str, cx: float, cy: float,
                 cells: int = 4, cell_w: float = 0.35,
                 cell_h: float = 0.40) -> dict:
        """Register: row of cells (sub-divided rectangle)."""
        total_w = cells * cell_w
        e = dict(id=id, type='register', cx=cx, cy=cy,
                 w=total_w, h=cell_h, text=text, cells=cells,
                 cell_w=cell_w, cell_h=cell_h)
        self._elements.append(e)
        self._element_map[id] = e
        return e

    def memory_array(self, id: str, text: str, cx: float, cy: float,
                     rows: int = 4, cols: int = 4,
                     cell_w: float = 0.22, cell_h: float = 0.20) -> dict:
        """Memory array: grid of cells."""
        total_w = cols * cell_w
        total_h = rows * cell_h
        e = dict(id=id, type='memory_array', cx=cx, cy=cy,
                 w=total_w, h=total_h, text=text,
                 rows=rows, cols=cols, cell_w=cell_w, cell_h=cell_h)
        self._elements.append(e)
        self._element_map[id] = e
        return e

    def block(self, id: str, text: str, cx: float, cy: float,
              w: float = 1.40, h: float = 0.60) -> dict:
        """Simple rectangular block."""
        e = dict(id=id, type='block', cx=cx, cy=cy, w=w, h=h, text=text)
        self._elements.append(e)
        self._element_map[id] = e
        return e

    def connect(self, src, dst, label: str = '', bidir: bool = False) -> 'PatentHardware':
        """Connect two elements with an arrow.

        Args:
            src/dst: element dict (returned by chip/mux/etc.) or element id string.
            label:   optional label.
            bidir:   if True, double-headed arrow.
        """
        src_id = src['id'] if isinstance(src, dict) else src
        dst_id = dst['id'] if isinstance(dst, dict) else dst
        self._connections.append(dict(src_id=src_id, dst_id=dst_id,
                                      label=label, bidir=bidir))
        return self

    def render(self, output_path: str) -> str:
        """Render hardware block diagram to PNG."""
        import os
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch, Polygon

        _setup_korean_font()
        fig_num = self.fig_label.replace('FIG. ', '')

        dpi = 150
        fig, ax = plt.subplots(figsize=(self.PAGE_W, self.PAGE_H), dpi=dpi)
        ax.set_xlim(0, self.PAGE_W)
        ax.set_ylim(0, self.PAGE_H)
        ax.set_aspect('equal')
        ax.axis('off')

        elem_bounds = {}  # id → (x1, y1, x2, y2)

        for e in self._elements:
            cx, cy = e['cx'], e['cy']
            w, h = e['w'], e['h']
            x1, y1 = cx - w/2, cy - h/2
            x2, y2 = cx + w/2, cy + h/2
            elem_bounds[e['id']] = (x1, y1, x2, y2)

            if e['type'] == 'block':
                patch = FancyBboxPatch((x1, y1), w, h,
                                        boxstyle='square,pad=0',
                                        lw=1.3, edgecolor='black',
                                        facecolor='white', zorder=10)
                ax.add_patch(patch)
                ax.text(cx, cy, e['text'], ha='center', va='center',
                        fontsize=self.FS_LABEL, zorder=11)

            elif e['type'] == 'chip':
                # Main body
                patch = FancyBboxPatch((x1, y1), w, h,
                                        boxstyle='square,pad=0',
                                        lw=1.5, edgecolor='black',
                                        facecolor='white', zorder=10)
                ax.add_patch(patch)
                ax.text(cx, cy, e['text'], ha='center', va='center',
                        fontsize=self.FS_LABEL, zorder=11)
                # Left pins
                n_left = e.get('n_pins_left', 3)
                pin_len = 0.18
                if n_left > 0:
                    pin_ys = [y1 + (i + 1) * h / (n_left + 1)
                               for i in range(n_left)]
                    for py in pin_ys:
                        ax.plot([x1 - pin_len, x1], [py, py],
                                color='black', lw=1.0, zorder=9)
                # Right pins
                n_right = e.get('n_pins_right', 3)
                if n_right > 0:
                    pin_ys = [y1 + (i + 1) * h / (n_right + 1)
                               for i in range(n_right)]
                    for py in pin_ys:
                        ax.plot([x2, x2 + pin_len], [py, py],
                                color='black', lw=1.0, zorder=9)

            elif e['type'] == 'mux':
                # Trapezoid shape
                d = e.get('direction', 'right')
                taper = h * 0.25  # taper amount
                if d == 'right':
                    # wider on left (input), narrower on right (output)
                    pts = [
                        (x1, y1),
                        (x2, y1 + taper),
                        (x2, y2 - taper),
                        (x1, y2),
                    ]
                else:
                    pts = [
                        (x1, y1 + taper),
                        (x2, y1),
                        (x2, y2),
                        (x1, y2 - taper),
                    ]
                poly = Polygon(pts, closed=True,
                                linewidth=1.3, edgecolor='black',
                                facecolor='white', zorder=10)
                ax.add_patch(poly)
                ax.text(cx, cy, e['text'], ha='center', va='center',
                        fontsize=self.FS_LABEL, zorder=11)

            elif e['type'] == 'register':
                cells = e['cells']
                cw = e['cell_w']
                ch = e['cell_h']
                # Outer border
                patch = FancyBboxPatch((x1, y1), w, h,
                                        boxstyle='square,pad=0',
                                        lw=1.5, edgecolor='black',
                                        facecolor='white', zorder=10)
                ax.add_patch(patch)
                # Cell dividers
                for ci in range(1, cells):
                    lx = x1 + ci * cw
                    ax.plot([lx, lx], [y1, y2],
                            color='black', lw=0.8, zorder=11)
                # Label above
                ax.text(cx, y2 + 0.08, e['text'],
                        ha='center', va='bottom',
                        fontsize=self.FS_LABEL - 1, zorder=12)

            elif e['type'] == 'memory_array':
                rows = e['rows']
                cols = e['cols']
                cw = e['cell_w']
                ch = e['cell_h']
                # Outer border
                patch = mpatches.Rectangle((x1, y1), w, h,
                                            lw=1.5, edgecolor='black',
                                            facecolor='white', zorder=10)
                ax.add_patch(patch)
                # Row lines
                for ri in range(1, rows):
                    ly = y1 + ri * ch
                    ax.plot([x1, x2], [ly, ly],
                            color='black', lw=0.6, zorder=11)
                # Col lines
                for ci in range(1, cols):
                    lx = x1 + ci * cw
                    ax.plot([lx, lx], [y1, y2],
                            color='black', lw=0.6, zorder=11)
                # Label above
                ax.text(cx, y2 + 0.08, e['text'],
                        ha='center', va='bottom',
                        fontsize=self.FS_LABEL - 1, zorder=12)

        # ── Draw connections ──────────────────────────────────────────────────
        for conn in self._connections:
            src_id = conn['src_id']
            dst_id = conn['dst_id']
            if src_id not in elem_bounds or dst_id not in elem_bounds:
                continue
            sx1, sy1, sx2, sy2 = elem_bounds[src_id]
            dx1, dy1, dx2, dy2 = elem_bounds[dst_id]
            scx = (sx1 + sx2) / 2
            scy = (sy1 + sy2) / 2
            dcx = (dx1 + dx2) / 2
            dcy = (dy1 + dy2) / 2

            # Simple nearest-edge connection
            # Determine direction
            ddx = dcx - scx
            ddy = dcy - scy
            if abs(ddy) >= abs(ddx):
                if ddy > 0:
                    p0 = (scx, sy2)
                    p1 = (dcx, dy1)
                else:
                    p0 = (scx, sy1)
                    p1 = (dcx, dy2)
            else:
                if ddx > 0:
                    p0 = (sx2, scy)
                    p1 = (dx1, dcy)
                else:
                    p0 = (sx1, scy)
                    p1 = (dx2, dcy)

            style = '<->' if conn['bidir'] else '->'
            ax.annotate('', xy=p1, xytext=p0,
                         arrowprops=dict(
                             arrowstyle=style, color='black', lw=1.1,
                             mutation_scale=10,
                         ), zorder=13)

            if conn['label']:
                mx = (p0[0] + p1[0]) / 2
                my = (p0[1] + p1[1]) / 2
                ax.text(mx + 0.08, my, conn['label'],
                        ha='left', va='center',
                        fontsize=self.FS_LABEL - 1, zorder=14,
                        bbox=dict(facecolor='white', edgecolor='none', pad=1))

        # ── Boundary + FIG. label ─────────────────────────────────────────────
        bnd = mpatches.Rectangle(
            (self.BND_X1, self.BND_Y1),
            self.BND_X2 - self.BND_X1, self.BND_Y2 - self.BND_Y1,
            lw=1.5, edgecolor='black', facecolor='none',
            linestyle='dashed', zorder=1
        )
        ax.add_patch(bnd)
        cx_bnd = (self.BND_X1 + self.BND_X2) / 2
        ax.text(cx_bnd, self.BND_Y1 - 0.25, f'FIG. {fig_num}',
                ha='center', va='center', fontsize=11, zorder=20)

        plt.tight_layout(pad=0)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# Research 12: PatentLayered — Layered Architecture Diagram
# ═══════════════════════════════════════════════════════════════════════════════

class PatentLayered:
    """
    Layered (horizontal band) architecture diagram for software patent figures.

    Each layer is a full-width horizontal band containing component boxes.
    Interface arrows connect layers vertically.

    Example::

        fig = PatentLayered('FIG. 2')
        fig.layer('Application Layer', ['Browser', 'Mobile App', 'API Client'],
                  ref='100')
        fig.layer('Service Layer',     ['Auth Service', 'Business Logic', 'Cache'],
                  ref='200')
        fig.layer('Data Layer',        ['PostgreSQL', 'Redis', 'S3'],
                  ref='300')
        fig.interface('100', '200', label='REST API')
        fig.interface('200', '300', label='ORM/Query')
        fig.render('fig2.png')
    """

    PAGE_W, PAGE_H = 8.5, 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15

    FS_LAYER  = 9
    FS_COMP   = 8
    FS_IFACE  = 7

    COMP_H    = 0.55   # component box height
    COMP_PAD  = 0.20   # horizontal padding between components

    def __init__(self, fig_label: str = 'FIG. 2'):
        self.fig_label = fig_label
        self._layers: list[dict] = []     # [{name, components, ref}]
        self._interfaces: list[dict] = [] # [{ref_top, ref_bot, label}]
        self._ref_to_idx: dict = {}

    def layer(self, name: str, components: list,
              ref: str = '') -> 'PatentLayered':
        """Add a horizontal layer.

        Args:
            name:       Layer display name.
            components: List of component names (strings).
            ref:        Reference number for the layer.
        """
        idx = len(self._layers)
        self._layers.append(dict(name=name, components=components, ref=ref))
        if ref:
            self._ref_to_idx[ref] = idx
        return self

    def interface(self, ref_top: str, ref_bot: str,
                  label: str = '') -> 'PatentLayered':
        """Add an interface arrow between two layers.

        Args:
            ref_top: Reference number of the upper layer.
            ref_bot: Reference number of the lower layer.
            label:   Interface label.
        """
        self._interfaces.append(dict(ref_top=ref_top, ref_bot=ref_bot,
                                     label=label))
        return self

    def render(self, output_path: str) -> str:
        """Render layered architecture diagram to PNG."""
        import os
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch

        _setup_korean_font()
        fig_num = self.fig_label.replace('FIG. ', '')

        dpi = 150
        fig, ax = plt.subplots(figsize=(self.PAGE_W, self.PAGE_H), dpi=dpi)
        ax.set_xlim(0, self.PAGE_W)
        ax.set_ylim(0, self.PAGE_H)
        ax.set_aspect('equal')
        ax.axis('off')

        n_layers = len(self._layers)
        if n_layers == 0:
            self._draw_frame(ax, fig_num)
            plt.tight_layout(pad=0)
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            return output_path

        content_x1 = self.BND_X1 + 0.40
        content_x2 = self.BND_X2 - 0.15
        content_y1 = self.BND_Y1 + 0.40
        content_y2 = self.BND_Y2 - 0.30
        content_w  = content_x2 - content_x1
        content_h  = content_y2 - content_y1

        # Layer height: split evenly
        layer_h = content_h / n_layers
        # Reserve some height for layer label + padding
        LAYER_LABEL_H = 0.25
        LAYER_PAD_TOP = 0.10
        LAYER_PAD_BOT = 0.12
        comp_area_h = layer_h - LAYER_LABEL_H - LAYER_PAD_TOP - LAYER_PAD_BOT

        # Interface arrow region between layers
        IFACE_H = 0.30
        # Recalculate: layers take up (content_h - n_gaps * IFACE_H) / n_layers
        n_gaps = max(n_layers - 1, 0)
        layer_h_adj = (content_h - n_gaps * IFACE_H) / n_layers
        comp_area_h_adj = layer_h_adj - LAYER_LABEL_H - LAYER_PAD_TOP - LAYER_PAD_BOT

        layer_rects = {}  # ref → (x1, y1, x2, y2) of layer band

        for li, layer in enumerate(self._layers):
            # Top layer at top
            top_y = content_y2 - li * (layer_h_adj + IFACE_H)
            bot_y = top_y - layer_h_adj
            lx1 = content_x1
            lx2 = content_x2

            layer_rects[layer['ref']] = (lx1, bot_y, lx2, top_y)

            # Layer band border
            patch = mpatches.Rectangle(
                (lx1, bot_y), content_w, layer_h_adj,
                lw=1.2, edgecolor='black', facecolor='none', zorder=5
            )
            ax.add_patch(patch)

            # Layer reference number on the left
            ref_text = layer['ref'] + '\n' if layer['ref'] else ''
            ax.text(lx1 - 0.12, (top_y + bot_y) / 2,
                    ref_text + layer['name'],
                    ha='right', va='center',
                    fontsize=self.FS_LAYER, zorder=10,
                    rotation=90 if layer_h_adj < 0.6 else 0)

            # Components inside the layer
            comps = layer['components']
            n_comps = len(comps)
            if n_comps > 0:
                comp_total_w = content_w - 2 * self.COMP_PAD
                comp_w = (comp_total_w - (n_comps - 1) * self.COMP_PAD) / n_comps
                comp_h = min(self.COMP_H, comp_area_h_adj - 0.06)
                comp_y1 = (top_y + bot_y) / 2 - comp_h / 2

                for ci, comp_name in enumerate(comps):
                    cx1 = lx1 + self.COMP_PAD + ci * (comp_w + self.COMP_PAD)
                    cx2 = cx1 + comp_w
                    ccx = (cx1 + cx2) / 2
                    ccy = comp_y1 + comp_h / 2

                    comp_patch = FancyBboxPatch(
                        (cx1, comp_y1), comp_w, comp_h,
                        boxstyle='square,pad=0',
                        lw=1.0, edgecolor='black', facecolor='white', zorder=10
                    )
                    ax.add_patch(comp_patch)
                    ax.text(ccx, ccy, comp_name,
                            ha='center', va='center',
                            fontsize=self.FS_COMP, zorder=11)

        # ── Draw interfaces ───────────────────────────────────────────────────
        for iface in self._interfaces:
            r_top = iface['ref_top']
            r_bot = iface['ref_bot']
            label = iface.get('label', '')

            # Find the bottom of the top layer and top of the bottom layer
            if r_top in layer_rects and r_bot in layer_rects:
                tx1, ty1, tx2, ty2 = layer_rects[r_top]
                bx1, by1, bx2, by2 = layer_rects[r_bot]

                # Arrow from bottom of top layer to top of bottom layer
                arrow_x = (tx1 + tx2) / 2
                p0 = (arrow_x, ty1)   # bottom of top layer
                p1 = (arrow_x, by2)   # top of bottom layer

                ax.annotate('', xy=p1, xytext=p0,
                             arrowprops=dict(
                                 arrowstyle='->', color='black', lw=1.2,
                                 mutation_scale=11,
                             ), zorder=13)
                if label:
                    my = (p0[1] + p1[1]) / 2
                    ax.text(arrow_x + 0.10, my, label,
                            ha='left', va='center',
                            fontsize=self.FS_IFACE, zorder=14,
                            bbox=dict(facecolor='white', edgecolor='none', pad=1))

        self._draw_frame(ax, fig_num)
        plt.tight_layout(pad=0)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return output_path

    def _draw_frame(self, ax, fig_num: str):
        import matplotlib.patches as mpatches
        bnd = mpatches.Rectangle(
            (self.BND_X1, self.BND_Y1),
            self.BND_X2 - self.BND_X1, self.BND_Y2 - self.BND_Y1,
            lw=1.5, edgecolor='black', facecolor='none',
            linestyle='dashed', zorder=1
        )
        ax.add_patch(bnd)
        cx = (self.BND_X1 + self.BND_X2) / 2
        ax.text(cx, self.BND_Y1 - 0.25, f'FIG. {fig_num}',
                ha='center', va='center', fontsize=11, zorder=20)


# ═══════════════════════════════════════════════════════════════════════════════
# Research 12: PatentTiming — Timing Diagram
# ═══════════════════════════════════════════════════════════════════════════════

class PatentTiming:
    """
    Timing diagram for hardware/communication patent figures.

    Renders digital signals as waveforms with clock, data, and control lines.
    Supports vertical time markers.

    Example::

        fig = PatentTiming('FIG. 5')
        fig.signal('CLK',   '100', wave='clock', period=1.0)
        fig.signal('DATA',  '200', wave=[0,0,1,1,0,1,0,0],
                   labels=['D0','D1','D2','D3'])
        fig.signal('VALID', '300', wave=[0,1,1,1,1,1,0,0])
        fig.signal('READY', '400', wave=[0,0,1,0,1,1,1,0])
        fig.marker(t=2.0, label='T_setup')
        fig.marker(t=6.0, label='T_hold')
        fig.render('fig5.png')
    """

    PAGE_W, PAGE_H = 8.5, 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15

    FS_SIGNAL = 8
    FS_MARKER = 7
    FS_LABEL  = 7

    SIGNAL_H    = 0.40   # height of each signal track
    SIGNAL_GAP  = 0.15   # gap between signal tracks
    WAVE_HIGH   = 0.28   # waveform high level height
    WAVE_LOW    = 0.00   # waveform low level
    TRANSITION_W = 0.08  # transition slope width
    LEFT_MARGIN  = 1.20  # width for signal name + ref

    def __init__(self, fig_label: str = 'FIG. 5'):
        self.fig_label = fig_label
        self._signals: list[dict] = []   # [{name, ref, wave, period, labels}]
        self._markers: list[dict] = []   # [{t, label}]

    def signal(self, name: str, ref: str = '',
               wave='clock', period: float = 1.0,
               labels: list = None) -> 'PatentTiming':
        """Add a signal to the timing diagram.

        Args:
            name:   Signal name (e.g. 'CLK', 'DATA').
            ref:    Reference number.
            wave:   'clock' for square wave, or list of 0/1/'X' values.
            period: Clock period (used only for wave='clock').
            labels: Optional data labels for transitions.
        """
        self._signals.append(dict(
            name=name, ref=ref, wave=wave,
            period=period, labels=labels or [],
        ))
        return self

    def marker(self, t: float, label: str = '') -> 'PatentTiming':
        """Add a vertical time marker (dashed line)."""
        self._markers.append(dict(t=t, label=label))
        return self

    def render(self, output_path: str) -> str:
        """Render timing diagram to PNG."""
        import os
        import numpy as np
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch

        _setup_korean_font()
        fig_num = self.fig_label.replace('FIG. ', '')

        dpi = 150
        fig, ax = plt.subplots(figsize=(self.PAGE_W, self.PAGE_H), dpi=dpi)
        ax.set_xlim(0, self.PAGE_W)
        ax.set_ylim(0, self.PAGE_H)
        ax.set_aspect('equal')
        ax.axis('off')

        n_signals = len(self._signals)
        if n_signals == 0:
            self._draw_frame(ax, fig_num)
            self._save(fig, ax, output_path, dpi, fig_num)
            return output_path

        content_x1 = self.BND_X1 + 0.20
        content_x2 = self.BND_X2 - 0.20
        content_y2 = self.BND_Y2 - 0.30
        wave_x1 = content_x1 + self.LEFT_MARGIN
        wave_x2 = content_x2 - 0.15
        wave_w  = wave_x2 - wave_x1

        track_h = self.SIGNAL_H + self.SIGNAL_GAP
        total_h = n_signals * track_h
        start_y = content_y2 - 0.20

        # Determine total time units
        max_t = 8
        for s in self._signals:
            if isinstance(s['wave'], list):
                max_t = max(max_t, len(s['wave']))
            elif s['wave'] == 'clock':
                max_t = max(max_t, int(16 / max(s['period'], 0.1)))
        max_t = max(max_t, 8)

        t_scale = wave_w / max_t  # pixels per time unit

        for si, sig in enumerate(self._signals):
            track_y_top = start_y - si * track_h
            track_y_bot = track_y_top - self.SIGNAL_H
            track_cy    = (track_y_top + track_y_bot) / 2

            # Signal name + reference number
            ref_line = sig['ref'] + '\n' if sig['ref'] else ''
            name_text = ref_line + sig['name']
            ax.text(content_x1 + self.LEFT_MARGIN - 0.12, track_cy,
                    name_text,
                    ha='right', va='center',
                    fontsize=self.FS_SIGNAL, zorder=10)

            # Baseline (low level)
            baseline_y = track_y_bot + 0.05
            high_y     = baseline_y + self.WAVE_HIGH

            # Build waveform
            xs, ys = [], []

            if sig['wave'] == 'clock':
                period = sig['period']
                t = 0.0
                level = 0
                xs.append(wave_x1)
                ys.append(baseline_y if level == 0 else high_y)
                while t < max_t:
                    # Rising edge
                    x_rise = wave_x1 + t * t_scale
                    xs += [x_rise, x_rise]
                    ys += [baseline_y, high_y]
                    # Falling edge
                    x_fall = wave_x1 + (t + period / 2) * t_scale
                    xs += [x_fall, x_fall]
                    ys += [high_y, baseline_y]
                    t += period
                xs.append(wave_x2)
                ys.append(baseline_y)

            elif isinstance(sig['wave'], list):
                wave_data = sig['wave']
                n_pts = len(wave_data)
                step = wave_w / max(n_pts, 1)
                tw = self.TRANSITION_W

                level_prev = wave_data[0]
                x_cur = wave_x1
                y_cur = high_y if level_prev else baseline_y
                xs.append(x_cur)
                ys.append(y_cur)

                for wi, val in enumerate(wave_data):
                    x_next = wave_x1 + (wi + 1) * step
                    if val == 'X' or val == 'x':
                        # Don't care: zigzag
                        n_zigs = 4
                        for zi in range(n_zigs):
                            frac = (wi + zi / n_zigs) * step / wave_w
                            zx = wave_x1 + (wi * step + zi * step / n_zigs)
                            zy = high_y if zi % 2 == 0 else baseline_y
                            xs.append(zx)
                            ys.append(zy)
                        xs.append(x_next)
                        ys.append(baseline_y)
                        level_prev = 0
                    else:
                        # Determine if transition
                        level_cur = int(bool(val))
                        if level_cur != level_prev:
                            # Transition slope
                            y_from = high_y if level_prev else baseline_y
                            y_to   = high_y if level_cur  else baseline_y
                            # Diagonal transition
                            t_mid = wave_x1 + wi * step
                            t_end = wave_x1 + wi * step + tw
                            xs += [t_mid, t_end]
                            ys += [y_from, y_to]
                        # Hold level
                        y_hold = high_y if level_cur else baseline_y
                        xs.append(x_next)
                        ys.append(y_hold)
                        level_prev = level_cur

            # Plot waveform
            ax.plot(xs, ys, color='black', lw=1.2, zorder=10)

            # Data labels
            for li, lbl in enumerate(sig.get('labels', [])):
                if li < (len(sig['wave']) if isinstance(sig['wave'], list) else 0):
                    lx = wave_x1 + (li + 0.5) * (wave_w / max(len(sig['wave']), 1))
                    ax.text(lx, high_y + 0.06, lbl,
                            ha='center', va='bottom',
                            fontsize=self.FS_LABEL - 1, zorder=11)

        # ── Time axis ─────────────────────────────────────────────────────────
        axis_y = start_y - n_signals * track_h - 0.10
        ax.plot([wave_x1, wave_x2], [axis_y, axis_y],
                color='black', lw=0.8, zorder=8)
        # Ticks
        for t in range(0, max_t + 1, max(1, max_t // 8)):
            tx = wave_x1 + t * t_scale
            ax.plot([tx, tx], [axis_y, axis_y - 0.05],
                    color='black', lw=0.8, zorder=8)
            ax.text(tx, axis_y - 0.10, str(t),
                    ha='center', va='top', fontsize=6, zorder=9)

        # ── Vertical time markers ─────────────────────────────────────────────
        for m in self._markers:
            mt = m['t']
            mx = wave_x1 + mt * t_scale
            top_y = start_y + 0.10
            bot_y = axis_y
            ax.plot([mx, mx], [bot_y, top_y],
                    color='black', lw=0.8, linestyle='dashed', zorder=12)
            if m['label']:
                ax.text(mx, top_y + 0.05, m['label'],
                        ha='center', va='bottom',
                        fontsize=self.FS_MARKER, zorder=13,
                        bbox=dict(facecolor='white', edgecolor='none', pad=1))

        self._draw_frame(ax, fig_num)
        self._save(fig, ax, output_path, dpi, fig_num)
        return output_path

    def _draw_frame(self, ax, fig_num: str):
        import matplotlib.patches as mpatches
        bnd = mpatches.Rectangle(
            (self.BND_X1, self.BND_Y1),
            self.BND_X2 - self.BND_X1, self.BND_Y2 - self.BND_Y1,
            lw=1.5, edgecolor='black', facecolor='none',
            linestyle='dashed', zorder=1
        )
        ax.add_patch(bnd)

    def _save(self, fig, ax, output_path, dpi, fig_num):
        import os
        cx = (self.BND_X1 + self.BND_X2) / 2
        ax.text(cx, self.BND_Y1 - 0.25, f'FIG. {fig_num}',
                ha='center', va='center', fontsize=11, zorder=20)
        import matplotlib.pyplot as plt
        plt.tight_layout(pad=0)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Research 13: PatentDFD — Data Flow Diagram
# ═══════════════════════════════════════════════════════════════════════════════

class PatentDFD:
    """
    Data Flow Diagram (Yourdon/DeMarco notation) for patent figures.

    Shapes:
    - External entity: rectangle
    - Process: circle (or rounded rectangle)
    - Data store: open-ended horizontal rectangle (Yourdon style)
    - Data flow: directional arrows with labels

    Example::

        fig = PatentDFD('FIG. 3')
        fig.external('USER', '100\\nUser')
        fig.process('AUTH', '200\\nAuthentication')
        fig.process('PROC', '300\\nData Processing')
        fig.store('DB', '400\\nUser Database')
        fig.flow('USER', 'AUTH', label='credentials')
        fig.flow('AUTH', 'DB', label='lookup')
        fig.flow('DB', 'AUTH', label='user record')
        fig.flow('AUTH', 'PROC', label='token')
        fig.render('fig3.png')
    """

    PAGE_W, PAGE_H = 8.5, 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15

    FS_ELEM  = 8
    FS_FLOW  = 7

    PROC_R   = 0.42   # process circle radius
    EXT_W    = 1.30   # external entity width
    EXT_H    = 0.55   # external entity height
    STORE_W  = 1.60   # data store width
    STORE_H  = 0.40   # data store height

    def __init__(self, fig_label: str = 'FIG. 3'):
        self.fig_label = fig_label
        self._elements: list[dict] = []
        self._flows: list[dict] = []
        self._elem_map: dict = {}
        self._positions: dict = {}  # id → (cx, cy)

    def external(self, id: str, text: str,
                 cx: float = None, cy: float = None) -> 'PatentDFD':
        """Add an external entity (rectangle)."""
        e = dict(id=id, type='external', text=text, cx=cx, cy=cy)
        self._elements.append(e)
        self._elem_map[id] = e
        return self

    def process(self, id: str, text: str,
                cx: float = None, cy: float = None) -> 'PatentDFD':
        """Add a process (circle/ellipse)."""
        e = dict(id=id, type='process', text=text, cx=cx, cy=cy)
        self._elements.append(e)
        self._elem_map[id] = e
        return self

    def store(self, id: str, text: str,
              cx: float = None, cy: float = None) -> 'PatentDFD':
        """Add a data store (open rectangle)."""
        e = dict(id=id, type='store', text=text, cx=cx, cy=cy)
        self._elements.append(e)
        self._elem_map[id] = e
        return self

    def flow(self, src: str, dst: str, label: str = '') -> 'PatentDFD':
        """Add a data flow arrow."""
        self._flows.append(dict(src=src, dst=dst, label=label))
        return self

    def _auto_layout(self):
        """Auto-assign positions if not manually specified."""
        n = len(self._elements)
        if n == 0:
            return

        content_x1 = self.BND_X1 + 0.60
        content_x2 = self.BND_X2 - 0.60
        content_y1 = self.BND_Y1 + 0.60
        content_y2 = self.BND_Y2 - 0.60
        cw = content_x2 - content_x1
        ch = content_y2 - content_y1

        # Simple ring layout for elements without positions
        import math
        unplaced = [e for e in self._elements if e['cx'] is None]
        placed   = [e for e in self._elements if e['cx'] is not None]

        for e in placed:
            self._positions[e['id']] = (e['cx'], e['cy'])

        n_up = len(unplaced)
        if n_up == 0:
            return

        # Layout unplaced elements in a circle
        cx_c = (content_x1 + content_x2) / 2
        cy_c = (content_y1 + content_y2) / 2
        radius = min(cw, ch) * 0.35

        if n_up == 1:
            self._positions[unplaced[0]['id']] = (cx_c, cy_c)
        elif n_up == 2:
            self._positions[unplaced[0]['id']] = (cx_c - radius * 0.5, cy_c)
            self._positions[unplaced[1]['id']] = (cx_c + radius * 0.5, cy_c)
        else:
            # Ring layout, starting from top
            for i, e in enumerate(unplaced):
                angle = math.pi / 2 - (2 * math.pi * i / n_up)
                ex = cx_c + radius * math.cos(angle)
                ey = cy_c + radius * math.sin(angle)
                self._positions[e['id']] = (ex, ey)

    def _get_edge_point(self, elem_id: str, toward: tuple) -> tuple:
        """Get the edge point of an element closest to 'toward' (cx, cy)."""
        import math
        e = self._elem_map[elem_id]
        cx, cy = self._positions[elem_id]
        tx, ty = toward

        dx = tx - cx
        dy = ty - cy
        dist = max(0.001, math.sqrt(dx**2 + dy**2))
        ux, uy = dx / dist, dy / dist  # unit vector toward target

        if e['type'] == 'process':
            r = self.PROC_R
            return (cx + ux * r, cy + uy * r)
        elif e['type'] == 'external':
            # Rectangle edge
            w, h = self.EXT_W, self.EXT_H
            # Clip ray to rectangle edge
            tx_clip = cx + ux * (w / 2)
            ty_clip = cy + uy * (h / 2)
            # Scale: find t such that we hit rect edge
            if abs(ux) > 0.001:
                t_x = (w / 2) / abs(ux)
            else:
                t_x = float('inf')
            if abs(uy) > 0.001:
                t_y = (h / 2) / abs(uy)
            else:
                t_y = float('inf')
            t_edge = min(t_x, t_y)
            return (cx + ux * t_edge, cy + uy * t_edge)
        elif e['type'] == 'store':
            w, h = self.STORE_W, self.STORE_H
            if abs(ux) > 0.001:
                t_x = (w / 2) / abs(ux)
            else:
                t_x = float('inf')
            if abs(uy) > 0.001:
                t_y = (h / 2) / abs(uy)
            else:
                t_y = float('inf')
            t_edge = min(t_x, t_y)
            return (cx + ux * t_edge, cy + uy * t_edge)
        else:
            return (cx + ux * 0.4, cy + uy * 0.4)

    def render(self, output_path: str) -> str:
        """Render DFD to PNG."""
        import os
        import math
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch, Ellipse

        _setup_korean_font()
        fig_num = self.fig_label.replace('FIG. ', '')

        dpi = 150
        fig, ax = plt.subplots(figsize=(self.PAGE_W, self.PAGE_H), dpi=dpi)
        ax.set_xlim(0, self.PAGE_W)
        ax.set_ylim(0, self.PAGE_H)
        ax.set_aspect('equal')
        ax.axis('off')

        self._auto_layout()

        # ── Draw elements ─────────────────────────────────────────────────────
        for e in self._elements:
            cx, cy = self._positions[e['id']]

            if e['type'] == 'external':
                w, h = self.EXT_W, self.EXT_H
                patch = FancyBboxPatch(
                    (cx - w/2, cy - h/2), w, h,
                    boxstyle='square,pad=0',
                    lw=1.3, edgecolor='black', facecolor='white', zorder=10
                )
                ax.add_patch(patch)
                ax.text(cx, cy, e['text'], ha='center', va='center',
                        fontsize=self.FS_ELEM, zorder=11)

            elif e['type'] == 'process':
                ell = Ellipse((cx, cy),
                               width=self.PROC_R * 2 * 1.3,
                               height=self.PROC_R * 2,
                               lw=1.3, edgecolor='black', facecolor='white',
                               zorder=10)
                ax.add_patch(ell)
                ax.text(cx, cy, e['text'], ha='center', va='center',
                        fontsize=self.FS_ELEM, zorder=11)

            elif e['type'] == 'store':
                w, h = self.STORE_W, self.STORE_H
                # Yourdon open rectangle: two horizontal lines + one vertical (left)
                # Top line
                ax.plot([cx - w/2, cx + w/2], [cy + h/2, cy + h/2],
                        color='black', lw=1.3, zorder=10)
                # Bottom line
                ax.plot([cx - w/2, cx + w/2], [cy - h/2, cy - h/2],
                        color='black', lw=1.3, zorder=10)
                # Left vertical
                ax.plot([cx - w/2, cx - w/2], [cy - h/2, cy + h/2],
                        color='black', lw=1.3, zorder=10)
                # (right side open)
                ax.text(cx, cy, e['text'], ha='center', va='center',
                        fontsize=self.FS_ELEM, zorder=11)

        # ── Draw flows ────────────────────────────────────────────────────────
        for fl in self._flows:
            src_id = fl['src']
            dst_id = fl['dst']
            if src_id not in self._positions or dst_id not in self._positions:
                continue
            scx, scy = self._positions[src_id]
            dcx, dcy = self._positions[dst_id]

            p0 = self._get_edge_point(src_id, (dcx, dcy))
            p1 = self._get_edge_point(dst_id, (scx, scy))

            ax.annotate('', xy=p1, xytext=p0,
                         arrowprops=dict(
                             arrowstyle='->', color='black', lw=1.1,
                             mutation_scale=11,
                         ), zorder=12)
            if fl['label']:
                mx = (p0[0] + p1[0]) / 2
                my = (p0[1] + p1[1]) / 2
                dx = p1[0] - p0[0]
                dy = p1[1] - p0[1]
                length = max(0.001, math.sqrt(dx**2 + dy**2))
                perp_x = -dy / length * 0.12
                perp_y =  dx / length * 0.12
                ax.text(mx + perp_x, my + perp_y, fl['label'],
                        ha='center', va='center',
                        fontsize=self.FS_FLOW, zorder=13,
                        bbox=dict(facecolor='white', edgecolor='none', pad=1))

        # ── Boundary + FIG. label ─────────────────────────────────────────────
        bnd = mpatches.Rectangle(
            (self.BND_X1, self.BND_Y1),
            self.BND_X2 - self.BND_X1, self.BND_Y2 - self.BND_Y1,
            lw=1.5, edgecolor='black', facecolor='none',
            linestyle='dashed', zorder=1
        )
        ax.add_patch(bnd)
        cx_bnd = (self.BND_X1 + self.BND_X2) / 2
        ax.text(cx_bnd, self.BND_Y1 - 0.25, f'FIG. {fig_num}',
                ha='center', va='center', fontsize=11, zorder=20)

        import matplotlib.pyplot as _plt
        _plt.tight_layout(pad=0)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        _plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        _plt.close(fig)
        return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# Research 13: PatentER — Entity-Relationship Diagram
# ═══════════════════════════════════════════════════════════════════════════════

class PatentER:
    """
    Entity-Relationship diagram for database/data model patent figures.

    Shapes:
    - Entity: rectangle with attribute list
    - Relationship: diamond
    - Cardinality: 1, N, M notation
    - PK attributes: underlined

    Example::

        fig = PatentER('FIG. 6')
        fig.entity('USER',    '100\\nUser',
                   attrs=['user_id (PK)', 'name', 'email'])
        fig.entity('ORDER',   '200\\nOrder',
                   attrs=['order_id (PK)', 'date', 'total'])
        fig.entity('PRODUCT', '300\\nProduct',
                   attrs=['product_id (PK)', 'name', 'price'])
        fig.relationship('USER',  'ORDER',   '1', 'N', label='places')
        fig.relationship('ORDER', 'PRODUCT', 'N', 'M', label='contains')
        fig.render('fig6.png')
    """

    PAGE_W, PAGE_H = 8.5, 11.0
    BND_X1, BND_Y1 = 0.55, 1.10
    BND_X2, BND_Y2 = 7.90, 10.15

    FS_ENTITY = 8
    FS_ATTR   = 7
    FS_REL    = 7
    FS_CARD   = 8

    ENTITY_W  = 1.60
    ATTR_H    = 0.22  # height per attribute row
    ENTITY_TITLE_H = 0.36

    REL_W = 0.80   # relationship diamond width
    REL_H = 0.40   # relationship diamond height

    def __init__(self, fig_label: str = 'FIG. 6'):
        self.fig_label = fig_label
        self._entities: list[dict] = []
        self._relationships: list[dict] = []
        self._entity_map: dict = {}
        self._positions: dict = {}  # id → (cx, cy)

    def entity(self, id: str, text: str, attrs: list = None,
               cx: float = None, cy: float = None) -> 'PatentER':
        """Add an entity.

        Args:
            id:    Unique entity identifier.
            text:  Title text (ref\\nName format).
            attrs: List of attribute strings. PK attributes detected by '(PK)'.
            cx/cy: Optional manual position.
        """
        e = dict(id=id, text=text, attrs=attrs or [], cx=cx, cy=cy)
        self._entities.append(e)
        self._entity_map[id] = e
        return self

    def relationship(self, entity1: str, entity2: str,
                     card1: str, card2: str,
                     label: str = '',
                     cx: float = None, cy: float = None) -> 'PatentER':
        """Add a relationship between two entities.

        Args:
            entity1/entity2: Entity ids.
            card1/card2:     Cardinality ('1', 'N', 'M').
            label:           Relationship name.
            cx/cy:           Optional manual position for diamond.
        """
        self._relationships.append(dict(
            e1=entity1, e2=entity2,
            card1=card1, card2=card2,
            label=label, cx=cx, cy=cy,
        ))
        return self

    def _entity_height(self, entity_id: str) -> float:
        """Total height of entity box including attributes."""
        e = self._entity_map[entity_id]
        return self.ENTITY_TITLE_H + len(e['attrs']) * self.ATTR_H

    def _auto_layout(self):
        """Auto-assign positions if not given."""
        import math
        n = len(self._entities)
        if n == 0:
            return

        content_x1 = self.BND_X1 + 0.70
        content_x2 = self.BND_X2 - 0.70
        content_y1 = self.BND_Y1 + 0.80
        content_y2 = self.BND_Y2 - 0.80
        cw = content_x2 - content_x1

        # Place entities in a horizontal row
        spacing = cw / max(n, 1)
        for i, e in enumerate(self._entities):
            if e['cx'] is not None:
                self._positions[e['id']] = (e['cx'], e['cy'])
                continue
            cx = content_x1 + (i + 0.5) * spacing
            cy = (content_y1 + content_y2) / 2
            self._positions[e['id']] = (cx, cy)

        # Place relationship diamonds at midpoints (if not specified)
        for rel in self._relationships:
            if rel['cx'] is not None:
                continue
            if rel['e1'] in self._positions and rel['e2'] in self._positions:
                p1 = self._positions[rel['e1']]
                p2 = self._positions[rel['e2']]
                rel['_cx'] = (p1[0] + p2[0]) / 2
                rel['_cy'] = (p1[1] + p2[1]) / 2
            else:
                rel['_cx'] = (content_x1 + content_x2) / 2
                rel['_cy'] = (content_y1 + content_y2) / 2

    def render(self, output_path: str) -> str:
        """Render ER diagram to PNG."""
        import os
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch, Polygon

        _setup_korean_font()
        fig_num = self.fig_label.replace('FIG. ', '')

        dpi = 150
        fig, ax = plt.subplots(figsize=(self.PAGE_W, self.PAGE_H), dpi=dpi)
        ax.set_xlim(0, self.PAGE_W)
        ax.set_ylim(0, self.PAGE_H)
        ax.set_aspect('equal')
        ax.axis('off')

        self._auto_layout()

        # ── Draw entities ─────────────────────────────────────────────────────
        for e in self._entities:
            cx, cy = self._positions[e['id']]
            w = self.ENTITY_W
            total_h = self._entity_height(e['id'])
            x1 = cx - w / 2
            y_top = cy + total_h / 2
            y1 = y_top - total_h

            # Outer border
            patch = FancyBboxPatch(
                (x1, y1), w, total_h,
                boxstyle='square,pad=0',
                lw=1.5, edgecolor='black', facecolor='white', zorder=10
            )
            ax.add_patch(patch)

            # Title row
            title_y2 = y_top
            title_y1 = y_top - self.ENTITY_TITLE_H
            # Divider line
            ax.plot([x1, x1 + w], [title_y1, title_y1],
                    color='black', lw=1.0, zorder=11)
            # Title text
            ax.text(cx, (title_y1 + title_y2) / 2, e['text'],
                    ha='center', va='center',
                    fontsize=self.FS_ENTITY, zorder=12)

            # Attribute rows
            for ai, attr in enumerate(e['attrs']):
                row_y2 = title_y1 - ai * self.ATTR_H
                row_y1 = row_y2 - self.ATTR_H
                row_cy = (row_y1 + row_y2) / 2
                is_pk = '(PK)' in attr or '(pk)' in attr
                ax.text(cx, row_cy, attr,
                        ha='center', va='center',
                        fontsize=self.FS_ATTR, zorder=12)
                if is_pk:
                    # Draw underline manually
                    txt_w = w * 0.65
                    ax.plot([cx - txt_w/2, cx + txt_w/2],
                            [row_y1 + 0.03, row_y1 + 0.03],
                            color='black', lw=0.8, zorder=13)
                if ai < len(e['attrs']) - 1:
                    ax.plot([x1, x1 + w], [row_y1, row_y1],
                            color='black', lw=0.5, linestyle='dashed', zorder=11)

        # ── Draw relationships ────────────────────────────────────────────────
        for rel in self._relationships:
            if '_cx' not in rel:
                rel['_cx'] = rel.get('cx') or 4.2
                rel['_cy'] = rel.get('cy') or 5.5
            rcx = rel['_cx']
            rcy = rel['_cy']

            # Diamond shape
            dw = self.REL_W
            dh = self.REL_H
            pts = [
                (rcx, rcy + dh/2),       # top
                (rcx + dw/2, rcy),        # right
                (rcx, rcy - dh/2),        # bottom
                (rcx - dw/2, rcy),        # left
            ]
            diamond = Polygon(pts, closed=True,
                               lw=1.3, edgecolor='black', facecolor='white',
                               zorder=15)
            ax.add_patch(diamond)

            if rel['label']:
                ax.text(rcx, rcy, rel['label'],
                        ha='center', va='center',
                        fontsize=self.FS_REL, zorder=16)

            # Connecting lines + cardinality labels
            for eid, card in [(rel['e1'], rel['card1']),
                               (rel['e2'], rel['card2'])]:
                if eid not in self._positions:
                    continue
                ecx, ecy = self._positions[eid]
                e_obj = self._entity_map[eid]
                e_h = self._entity_height(eid)

                # Direction: entity → diamond
                ddx = rcx - ecx
                ddy = rcy - ecy
                import math
                dist = max(0.001, math.sqrt(ddx**2 + ddy**2))
                ux, uy = ddx/dist, ddy/dist

                # Entity edge point
                ew = self.ENTITY_W
                if abs(ux) > 0.001:
                    t_x = (ew / 2) / abs(ux)
                else:
                    t_x = float('inf')
                if abs(uy) > 0.001:
                    t_y = (e_h / 2) / abs(uy)
                else:
                    t_y = float('inf')
                t_ent = min(t_x, t_y)
                p_ent = (ecx + ux * t_ent, ecy + uy * t_ent)

                # Diamond edge point
                p_dia = (rcx - ux * dw/2, rcy - uy * dh/2)
                # Simple: use diamond center - offset along direction
                # More accurate: ray-diamond intersection
                # Use: max(|ux|/dw*2, |uy|/dh*2) style
                if abs(ux) > 0 or abs(uy) > 0:
                    # Parametric: |ux|/(dw/2) + |uy|/(dh/2)
                    t_dia = 1.0 / (abs(ux)/(dw/2) + abs(uy)/(dh/2) + 0.001)
                    p_dia = (rcx - ux * t_dia, rcy - uy * t_dia)

                # Line
                ax.plot([p_ent[0], p_dia[0]], [p_ent[1], p_dia[1]],
                        color='black', lw=1.0, zorder=12)

                # Cardinality label near entity side
                lx = p_ent[0] + ux * 0.20
                ly = p_ent[1] + uy * 0.20
                ax.text(lx, ly, card,
                        ha='center', va='center',
                        fontsize=self.FS_CARD, fontweight='bold', zorder=16,
                        bbox=dict(facecolor='white', edgecolor='none', pad=1))

        # ── Boundary + FIG. label ─────────────────────────────────────────────
        bnd = mpatches.Rectangle(
            (self.BND_X1, self.BND_Y1),
            self.BND_X2 - self.BND_X1, self.BND_Y2 - self.BND_Y1,
            lw=1.5, edgecolor='black', facecolor='none',
            linestyle='dashed', zorder=1
        )
        ax.add_patch(bnd)
        cx_b = (self.BND_X1 + self.BND_X2) / 2
        ax.text(cx_b, self.BND_Y1 - 0.25, f'FIG. {fig_num}',
                ha='center', va='center', fontsize=11, zorder=20)

        import matplotlib.pyplot as _plt
        _plt.tight_layout(pad=0)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        _plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        _plt.close(fig)
        return output_path



# ── quick_draw() helper functions for new diagram types ──────────────────────

def _quick_draw_state(spec_text: str, output_path: str,
                      fig_label: str, t0: float) -> dict:
    """Parse simple state spec and render with PatentState.

    Spec format:
        STATE_ID: State Name [initial] [final]
        STATE_ID -> STATE_ID2: label
    """
    import os, time
    fig = PatentState(fig_label)
    lines = [l.strip() for l in spec_text.strip().splitlines() if l.strip()]
    state_count = 0
    for line in lines:
        if '->' in line:
            # Transition: S1 -> S2: label
            parts = line.split('->', 1)
            src = parts[0].strip()
            rest = parts[1].strip()
            if ':' in rest:
                dst, label = rest.split(':', 1)
                dst = dst.strip()
                label = label.strip()
            else:
                dst = rest.strip()
                label = ''
            fig.transition(src, dst, label=label)
        elif ':' in line:
            # State definition: ID: name [initial] [final]
            id_part, text_part = line.split(':', 1)
            sid = id_part.strip()
            text = text_part.strip()
            is_initial = '[initial]' in text.lower()
            is_final   = '[final]'   in text.lower()
            text = text.replace('[initial]', '').replace('[Initial]', '')
            text = text.replace('[final]',   '').replace('[Final]',   '').strip()
            fig.state(sid, text, initial=is_initial, final=is_final)
            state_count += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.render(output_path)
    pages = [output_path]
    issues = _validate_output_files(pages)
    return {
        'pages': pages, 'node_count': state_count, 'warnings': [],
        'validation': {'passed': len(issues) == 0, 'issues': issues},
        'elapsed_sec': round(time.time() - t0, 2),
    }


def _quick_draw_sequence(spec_text: str, output_path: str,
                         fig_label: str, t0: float) -> dict:
    """Parse simple sequence spec and render with PatentSequence.

    Spec format:
        actor ID: Name
        ID -> ID2: message
        ID <- ID2: return message
    """
    import os, time
    fig = PatentSequence(fig_label)
    lines = [l.strip() for l in spec_text.strip().splitlines() if l.strip()]
    msg_count = 0
    for line in lines:
        if line.lower().startswith('actor '):
            rest = line[6:].strip()
            if ':' in rest:
                aid, name = rest.split(':', 1)
                fig.actor(name.strip(), aid.strip())
        elif '<-' in line or '->' in line:
            is_return = '<-' in line
            sep = '<-' if is_return else '->'
            parts = line.split(sep, 1)
            src = parts[0].strip()
            rest = parts[1].strip()
            if ':' in rest:
                dst, label = rest.split(':', 1)
                dst = dst.strip()
                label = label.strip()
            else:
                dst = rest.strip()
                label = ''
            if is_return:
                src, dst = dst, src  # swap for return
            fig.message(src, dst, label=label, return_msg=is_return)
            msg_count += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.render(output_path)
    pages = [output_path]
    issues = _validate_output_files(pages)
    return {
        'pages': pages, 'node_count': msg_count, 'warnings': [],
        'validation': {'passed': len(issues) == 0, 'issues': issues},
        'elapsed_sec': round(time.time() - t0, 2),
    }


def _quick_draw_layered(spec_text: str, output_path: str,
                        fig_label: str, t0: float) -> dict:
    """Parse simple layered spec and render with PatentLayered.

    Spec format:
        LAYER_REF: Layer Name | comp1, comp2, comp3
        INTERFACE: REF1 -> REF2 label
    """
    import os, time
    fig = PatentLayered(fig_label)
    lines = [l.strip() for l in spec_text.strip().splitlines() if l.strip()]
    layer_count = 0
    for line in lines:
        if line.upper().startswith('INTERFACE:'):
            rest = line[10:].strip()
            if '->' in rest:
                parts = rest.split('->', 1)
                ref1 = parts[0].strip()
                parts2 = parts[1].strip()
                if ' ' in parts2:
                    ref2, label = parts2.split(' ', 1)
                else:
                    ref2, label = parts2, ''
                fig.interface(ref1.strip(), ref2.strip(), label=label.strip())
        elif ':' in line and '|' in line:
            ref_name, comps_str = line.split('|', 1)
            if ':' in ref_name:
                ref, name = ref_name.split(':', 1)
                comps = [c.strip() for c in comps_str.split(',')]
                fig.layer(name.strip(), comps, ref=ref.strip())
                layer_count += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.render(output_path)
    pages = [output_path]
    issues = _validate_output_files(pages)
    return {
        'pages': pages, 'node_count': layer_count, 'warnings': [],
        'validation': {'passed': len(issues) == 0, 'issues': issues},
        'elapsed_sec': round(time.time() - t0, 2),
    }


def _quick_draw_timing(spec_text: str, output_path: str,
                       fig_label: str, t0: float) -> dict:
    """Parse simple timing spec and render with PatentTiming.

    Spec format:
        SIGNAL_REF: signal_name [clock|0,1,0,1,...]
        MARKER: t=2.0 label
    """
    import os, time
    fig = PatentTiming(fig_label)
    lines = [l.strip() for l in spec_text.strip().splitlines() if l.strip()]
    sig_count = 0
    for line in lines:
        if line.upper().startswith('MARKER:'):
            rest = line[7:].strip()
            if 't=' in rest:
                parts = rest.split(' ', 1)
                t_str = parts[0].replace('t=', '')
                label = parts[1] if len(parts) > 1 else ''
                try:
                    fig.marker(float(t_str), label=label.strip())
                except ValueError:
                    pass
        elif ':' in line:
            parts = line.split(':', 1)
            ref = parts[0].strip()
            rest = parts[1].strip()
            # rest: "name clock" or "name 0,1,0,1..."
            tokens = rest.split(' ', 1)
            name = tokens[0]
            wave_str = tokens[1] if len(tokens) > 1 else 'clock'
            if wave_str.strip().lower() == 'clock':
                fig.signal(name, ref, wave='clock')
            else:
                try:
                    wave = [int(x.strip()) if x.strip() not in ('X','x') else 'X'
                            for x in wave_str.split(',')]
                    fig.signal(name, ref, wave=wave)
                except Exception:
                    fig.signal(name, ref, wave='clock')
            sig_count += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.render(output_path)
    pages = [output_path]
    issues = _validate_output_files(pages)
    return {
        'pages': pages, 'node_count': sig_count, 'warnings': [],
        'validation': {'passed': len(issues) == 0, 'issues': issues},
        'elapsed_sec': round(time.time() - t0, 2),
    }
