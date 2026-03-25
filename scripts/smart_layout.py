"""
SmartLayout v2 — Connection-aware automatic layout engine for patent drawings.
Uses simplified Sugiyama framework:
  rank assignment → crossing minimization → coordinate assignment → edge routing.

v2 improvements:
  - Multi-port: N arrows on same box face → auto-spread ports (no overlap)
  - Feedback arrows rendered as dashed lines (ls='--')
  - Elbow routing: _find_safe_via_y avoids box penetration
  - Feedback channel separation: each feedback arrow gets its own x lane
"""
import sys, os
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patent_drawing_lib import Drawing


class SmartLayout:
    """
    Usage:
        layout = SmartLayout('FIG. 2', orientation='landscape')
        layout.node('70', 'AI Agent Orchestration Unit')
        layout.node('80', 'Context Analysis Unit')
        layout.edge('70', '80')
        layout.render('fig2.png')
    """

    def __init__(self, fig_label, orientation='portrait', page='letter'):
        self.fig_label = fig_label
        self.fig_num = fig_label.replace('FIG. ', '').strip()
        self.orientation = orientation
        self.page = page
        self._nodes = {}       # id -> {text, shape, rank, order, cx, cy, w, h, box_ref}
        self._edges = []       # [{src, dst, label, feedback}]
        self._groups = []      # [{ids, direction}]
        self._rank_hints = {}  # id -> int or 'last'

        # Page dimensions
        if orientation == 'landscape':
            self.page_w, self.page_h = 11.0, 8.5
        else:
            self.page_w, self.page_h = 8.5, 11.0

        # Layout margins
        self.margin = 0.55
        self.content_left = self.margin + 0.45    # wider inner margin
        self.content_right = self.page_w - self.margin - 0.25
        self.content_top = self.page_h - self.margin - 0.75  # top inset (node center)
        self.content_bottom = self.margin + 0.90  # bottom: space for FIG label + margin

        # Layout parameters
        self.min_v_gap = 0.70       # minimum vertical gap between rank centers
        self.min_h_gap = 0.45       # minimum horizontal gap between nodes
        self.node_min_w = 1.40      # minimum node width
        self.node_h = 0.55          # node height (1-line)
        self.node_h2 = 0.80         # node height (2-line)
        self.feedback_reserve = 0.60  # width reserved on left for feedback channels
        self.feedback_lane_gap = 0.20  # x gap between feedback lanes

    def node(self, node_id, text, shape='box'):
        self._nodes[node_id] = {
            'text': text,
            'shape': shape,
            'rank': None, 'order': None,
            'cx': None, 'cy': None,
            'w': None, 'h': None,
            'box_ref': None,
        }

    def edge(self, src, dst, label='', feedback=False):
        self._edges.append({'src': src, 'dst': dst,
                            'label': label, 'feedback': feedback})

    def hint_group(self, node_ids, direction='horizontal'):
        self._groups.append({'ids': list(node_ids), 'direction': direction})

    def hint_rank(self, node_id, rank):
        self._rank_hints[node_id] = rank

    # ── Phase 1: Rank Assignment ──────────────────────────────────────────────

    def _assign_ranks(self):
        children = defaultdict(list)
        parents = defaultdict(list)
        for e in self._edges:
            if not e['feedback']:
                children[e['src']].append(e['dst'])
                parents[e['dst']].append(e['src'])

        all_ids = set(self._nodes.keys())
        has_parent = {e['dst'] for e in self._edges if not e['feedback']}
        roots = all_ids - has_parent
        if not roots:
            roots = {next(iter(all_ids))}

        # Longest-path ranking (BFS with relaxation)
        rank = {r: self._rank_hints.get(r, 0) for r in roots}
        queue = deque(roots)
        visited = set()

        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            for child in children[nid]:
                new_rank = rank[nid] + 1
                if child not in rank or new_rank > rank[child]:
                    rank[child] = new_rank
                    queue.append(child)

        # Unvisited nodes (isolated or orphan)
        max_rank = max(rank.values()) if rank else 0
        for nid in all_ids:
            if nid not in rank:
                rank[nid] = max_rank + 1

        # Apply explicit rank hints
        for nid, r in self._rank_hints.items():
            if nid not in all_ids:
                continue
            if r == 'last':
                rank[nid] = max(rank.values())
            else:
                rank[nid] = int(r)

        # Apply group hints: all group members share the maximum rank
        for g in self._groups:
            valid = [nid for nid in g['ids'] if nid in rank]
            if not valid:
                continue
            group_rank = max(rank[nid] for nid in valid)
            for nid in g['ids']:
                if nid in rank:
                    rank[nid] = group_rank

        for nid in self._nodes:
            self._nodes[nid]['rank'] = rank.get(nid, 0)

    # ── Phase 2: Ordering within ranks ───────────────────────────────────────

    def _order_within_ranks(self):
        ranks = defaultdict(list)
        for nid, info in self._nodes.items():
            ranks[info['rank']].append(nid)

        for r in ranks:
            ranks[r].sort()  # stable initial order

        children = defaultdict(list)
        parents = defaultdict(list)
        for e in self._edges:
            if not e['feedback']:
                children[e['src']].append(e['dst'])
                parents[e['dst']].append(e['src'])

        sorted_ranks = sorted(ranks.keys())

        for _pass in range(3):
            if _pass % 2 == 0:  # top-down
                for i in range(1, len(sorted_ranks)):
                    r = sorted_ranks[i]
                    prev_r = sorted_ranks[i - 1]
                    prev_order = {nid: idx for idx, nid in enumerate(ranks[prev_r])}
                    bary = {}
                    for nid in ranks[r]:
                        pars = [p for p in parents[nid] if p in prev_order]
                        bary[nid] = (sum(prev_order[p] for p in pars) / len(pars)
                                     if pars else ranks[r].index(nid))
                    ranks[r].sort(key=lambda n: bary.get(n, 0))
            else:  # bottom-up
                for i in range(len(sorted_ranks) - 2, -1, -1):
                    r = sorted_ranks[i]
                    next_r = sorted_ranks[i + 1]
                    next_order = {nid: idx for idx, nid in enumerate(ranks[next_r])}
                    bary = {}
                    for nid in ranks[r]:
                        chs = [c for c in children[nid] if c in next_order]
                        bary[nid] = (sum(next_order[c] for c in chs) / len(chs)
                                     if chs else ranks[r].index(nid))
                    ranks[r].sort(key=lambda n: bary.get(n, 0))

        # Group ordering: keep group members contiguous in declared order
        for g in self._groups:
            if g['direction'] == 'horizontal' and g['ids']:
                r = self._nodes[g['ids'][0]]['rank']
                if not all(self._nodes[nid]['rank'] == r for nid in g['ids'] if nid in self._nodes):
                    continue
                current = ranks[r]
                insert_pos = next((idx for idx, n in enumerate(current) if n in g['ids']), 0)
                others = [n for n in current if n not in g['ids']]
                members = [n for n in g['ids'] if n in self._nodes]
                ranks[r] = others[:insert_pos] + members + others[insert_pos:]

        for r, nodes in ranks.items():
            for idx, nid in enumerate(nodes):
                self._nodes[nid]['order'] = idx

        self._ranks = dict(ranks)

    # ── Phase 3: Coordinate Assignment ───────────────────────────────────────

    def _assign_coordinates(self):
        sorted_rank_keys = sorted(self._ranks.keys())
        n_ranks = len(sorted_rank_keys)

        avail_h = self.content_top - self.content_bottom
        has_feedback = any(e['feedback'] for e in self._edges)
        fb_reserve = self.feedback_reserve if has_feedback else 0
        content_left_adj = self.content_left + fb_reserve
        avail_w = self.content_right - content_left_adj

        # Vertical step between ranks: divide available height evenly
        if n_ranks > 1:
            v_step = avail_h / (n_ranks - 1)
        else:
            v_step = avail_h / 2

        for rank_idx, r in enumerate(sorted_rank_keys):
            nodes_in_rank = self._ranks[r]
            n = len(nodes_in_rank)

            # Center y of each rank (top → bottom)
            cy = self.content_top - rank_idx * v_step

            # Estimate node sizes
            for nid in nodes_in_rank:
                text = self._nodes[nid]['text']
                lines = text.split('\n')
                max_line = max(len(l) for l in lines)
                w = max(self.node_min_w, max_line * 0.115 + 0.40)
                h = self.node_h2 if len(lines) > 1 else self.node_h
                self._nodes[nid]['w'] = w
                self._nodes[nid]['h'] = h

            # Total width needed
            total_w = (sum(self._nodes[nid]['w'] for nid in nodes_in_rank)
                       + self.min_h_gap * max(0, n - 1))

            # Scale down if row too wide
            if total_w > avail_w and n > 0:
                scale = avail_w / total_w
                for nid in nodes_in_rank:
                    self._nodes[nid]['w'] = max(0.80, self._nodes[nid]['w'] * scale)
                total_w = (sum(self._nodes[nid]['w'] for nid in nodes_in_rank)
                           + self.min_h_gap * max(0, n - 1))

            # Center the row horizontally
            start_x = content_left_adj + (avail_w - total_w) / 2
            cx_cursor = start_x
            for nid in nodes_in_rank:
                w = self._nodes[nid]['w']
                self._nodes[nid]['cx'] = cx_cursor + w / 2
                self._nodes[nid]['cy'] = cy
                cx_cursor += w + self.min_h_gap

    # ── Phase 4: Edge Routing ─────────────────────────────────────────────────

    def _classify_edges(self):
        for e in self._edges:
            if e['feedback']:
                e['route_type'] = 'feedback'
                continue
            si = self._nodes[e['src']]
            di = self._nodes[e['dst']]
            if si['rank'] == di['rank']:
                e['route_type'] = 'horizontal'
            elif abs(si.get('cx', 0) - di.get('cx', 0)) < 0.05:
                e['route_type'] = 'vertical'
            else:
                e['route_type'] = 'elbow'

    # ── Multi-Port: port coordinate calculation ───────────────────────────────

    def _get_port(self, box_ref, side, total_ports, port_index):
        """
        box_ref의 side 면에서 port_index번째 접점 좌표.
        total_ports개가 균등 분산.

        예: top면에 3개 화살표
          - port 0: 25% 지점 (왼쪽)
          - port 1: 50% 지점 (중앙)
          - port 2: 75% 지점 (오른쪽)
        """
        margin = 0.15  # 가장자리에서 최소 거리
        if total_ports == 1:
            # 1개만이면 그냥 중앙
            if side == 'top':
                return (box_ref.cx, box_ref.top)
            elif side == 'bottom':
                return (box_ref.cx, box_ref.bot)
            elif side == 'left':
                return (box_ref.left, box_ref.cy)
            else:
                return (box_ref.right, box_ref.cy)

        if side in ('top', 'bottom'):
            avail = (box_ref.right - box_ref.left) - 2 * margin
            step = avail / (total_ports + 1)
            x = box_ref.left + margin + step * (port_index + 1)
            y = box_ref.top if side == 'top' else box_ref.bot
            return (x, y)
        else:  # left, right
            avail = (box_ref.top - box_ref.bot) - 2 * margin
            step = avail / (total_ports + 1)
            y = box_ref.bot + margin + step * (port_index + 1)
            x = box_ref.left if side == 'left' else box_ref.right
            return (x, y)

    def _build_port_assignments(self):
        """
        각 (box_id, side) 조합에 연결되는 엣지 목록을 수집하고
        port_index를 할당한다.
        반환: {edge_idx: {'src_pt': (x,y), 'dst_pt': (x,y)}}
        """
        # 1단계: 각 엣지가 어떤 면을 사용하는지 결정
        edge_faces = []  # [(src_face, dst_face)]
        for e in self._edges:
            if e['feedback']:
                edge_faces.append(('left', 'left'))
                continue
            rt = e.get('route_type', 'elbow')
            si = self._nodes[e['src']]
            di = self._nodes[e['dst']]
            if rt == 'horizontal':
                if si.get('cx', 0) <= di.get('cx', 0):
                    edge_faces.append(('right', 'left'))
                else:
                    edge_faces.append(('left', 'right'))
            elif rt == 'vertical':
                if si.get('cy', 0) >= di.get('cy', 0):
                    edge_faces.append(('bottom', 'top'))
                else:
                    edge_faces.append(('top', 'bottom'))
            else:  # elbow
                if si.get('cy', 0) >= di.get('cy', 0):
                    edge_faces.append(('bottom', 'top'))
                else:
                    edge_faces.append(('top', 'bottom'))

        # 2단계: (node_id, side) → [edge_idx 리스트]
        face_to_edges = defaultdict(list)
        for idx, (e, (sf, df)) in enumerate(zip(self._edges, edge_faces)):
            if not e['feedback']:
                face_to_edges[(e['src'], sf)].append(('src', idx))
                face_to_edges[(e['dst'], df)].append(('dst', idx))
            # feedback는 별도 처리

        # 3단계: 각 엣지에 port 좌표 할당
        port_pts = {}  # (role, edge_idx) → (x, y)
        for (nid, side), edge_list in face_to_edges.items():
            box_ref = self._nodes[nid]['box_ref']
            if box_ref is None:
                continue
            n = len(edge_list)
            for port_idx, (role, eidx) in enumerate(edge_list):
                pt = self._get_port(box_ref, side, n, port_idx)
                port_pts[(role, eidx)] = pt

        return port_pts, edge_faces

    # ── Safe via_y for elbow routing ──────────────────────────────────────────

    def _find_safe_via_y(self, rank_boxes_map, r_src, r_dst):
        """
        src rank와 dst rank 사이에서 모든 박스를 통과하지 않는 via_y 찾기.
        src가 dst보다 위에 있다고 가정 (r_src < r_dst in rank key, cy higher).
        """
        # src rank의 최하단
        src_bots = [b.bot for b in rank_boxes_map.get(r_src, [])]
        # dst rank의 최상단
        dst_tops = [b.top for b in rank_boxes_map.get(r_dst, [])]

        min_bot_src = min(src_bots) if src_bots else 0.0
        max_top_dst = max(dst_tops) if dst_tops else 0.0

        # 중간 rank 박스들도 고려
        min_rank, max_rank = min(r_src, r_dst), max(r_src, r_dst)
        for rk in range(min_rank + 1, max_rank):
            for b in rank_boxes_map.get(rk, []):
                min_bot_src = min(min_bot_src, b.bot)

        gap = min_bot_src - max_top_dst
        if gap >= 0.90:
            # 충분한 공간 → 정확히 중간
            return (min_bot_src + max_top_dst) / 2
        elif gap >= 0.30:
            # 공간은 있지만 좁음 → 여전히 중간 사용
            return (min_bot_src + max_top_dst) / 2
        else:
            # 공간 부족 → src rank 아래로 내려감
            return min_bot_src - 0.35

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, output_path):
        self._assign_ranks()
        self._order_within_ranks()
        self._assign_coordinates()
        self._classify_edges()

        d = Drawing(output_path, fig_num=self.fig_num, orientation=self.orientation)
        d.boundary(self.margin, self.margin,
                   self.page_w - self.margin, self.page_h - self.margin)

        # Draw nodes
        for nid, info in self._nodes.items():
            cx = info['cx']
            cy = info['cy']
            text = info['text']
            n_lines = len(text.split('\n'))
            est_h = 0.80 if n_lines > 1 else 0.55
            by = cy - est_h / 2
            est_w = info['w']
            bx = cx - est_w / 2
            ref_text = f"{nid}\n{info['text']}" if nid not in info['text'] else info['text']
            box = d.autobox(bx, by, ref_text, fs=10, pad_y=0.22)
            info['box_ref'] = box

        # Build rank → boxes map
        rank_boxes_map = defaultdict(list)
        for nid, info in self._nodes.items():
            if info['box_ref'] is not None:
                rank_boxes_map[info['rank']].append(info['box_ref'])

        # Now build port assignments (needs box_ref to be set)
        port_pts, edge_faces = self._build_port_assignments()

        MIN_SEG = 0.44  # library minimum segment length

        # Separate feedback edges
        feedback_edges = []
        forward_edges = []
        for idx, e in enumerate(self._edges):
            if e['feedback']:
                feedback_edges.append((idx, e))
            else:
                forward_edges.append((idx, e))

        # ── Draw forward edges ────────────────────────────────────────────────
        for idx, e in forward_edges:
            sb = self._nodes[e['src']]['box_ref']
            db = self._nodes[e['dst']]['box_ref']
            if sb is None or db is None:
                continue

            lbl = e['label'] or ''
            rt = e['route_type']

            # Get port-aware src/dst points
            src_pt = port_pts.get(('src', idx), None)
            dst_pt = port_pts.get(('dst', idx), None)

            if rt == 'horizontal':
                sp = src_pt if src_pt else sb.right_mid()
                dp = dst_pt if dst_pt else db.left_mid()
                if sb.cx > db.cx:
                    sp = src_pt if src_pt else sb.left_mid()
                    dp = dst_pt if dst_pt else db.right_mid()
                d.arrow_route([sp, dp], label=lbl)

            elif rt == 'vertical':
                sp = src_pt if src_pt else (sb.bot_mid() if sb.cy >= db.cy else sb.top_mid())
                dp = dst_pt if dst_pt else (db.top_mid() if sb.cy >= db.cy else db.bot_mid())
                # Snap to same x to prevent tiny diagonal from port offset
                mid_x = (sp[0] + dp[0]) / 2
                sp = (mid_x, sp[1])
                dp = (mid_x, dp[1])
                d.arrow_route([sp, dp], label=lbl)

            else:  # elbow
                src_rank = self._nodes[e['src']]['rank']
                dst_rank = self._nodes[e['dst']]['rank']

                if sb.cy >= db.cy:
                    # src above dst (higher y) → route downward
                    via_y = self._find_safe_via_y(rank_boxes_map, src_rank, dst_rank)
                    sp = src_pt if src_pt else sb.bot_mid()
                    dp = dst_pt if dst_pt else db.top_mid()

                    # Snap nearly-identical x values to avoid tiny diagonal segments
                    if abs(sp[0] - dp[0]) < MIN_SEG:
                        mid_x = (sp[0] + dp[0]) / 2
                        sp = (mid_x, sp[1])
                        dp = (mid_x, dp[1])

                    seg1 = sb.bot - via_y
                    seg2 = via_y - db.top

                    if seg1 >= MIN_SEG and seg2 >= MIN_SEG:
                        # Standard elbow through safe channel
                        d.arrow_route([
                            sp,
                            (sp[0], via_y),
                            (dp[0], via_y),
                            dp,
                        ], label=lbl)
                    else:
                        # Side bypass
                        src_boxes = rank_boxes_map.get(src_rank, [])
                        dst_boxes = rank_boxes_map.get(dst_rank, [])
                        all_relevant = list(src_boxes) + list(dst_boxes)
                        if db.cx >= sb.cx:
                            ch_x = max((b.right for b in all_relevant), default=sb.right) + MIN_SEG
                            sp2 = src_pt if src_pt else sb.right_mid()
                            dp2 = dst_pt if dst_pt else db.right_mid()
                            d.arrow_route([
                                sp2,
                                (ch_x, sp2[1]),
                                (ch_x, dp2[1]),
                                dp2,
                            ], label=lbl)
                        else:
                            ch_x = min((b.left for b in all_relevant), default=sb.left) - MIN_SEG
                            sp2 = src_pt if src_pt else sb.left_mid()
                            dp2 = dst_pt if dst_pt else db.left_mid()
                            d.arrow_route([
                                sp2,
                                (ch_x, sp2[1]),
                                (ch_x, dp2[1]),
                                dp2,
                            ], label=lbl)
                else:
                    # src below dst → route upward
                    via_y = self._find_safe_via_y(rank_boxes_map, dst_rank, src_rank)
                    sp = src_pt if src_pt else sb.top_mid()
                    dp = dst_pt if dst_pt else db.bot_mid()

                    # Snap nearly-identical x values to avoid tiny diagonal segments
                    if abs(sp[0] - dp[0]) < MIN_SEG:
                        mid_x = (sp[0] + dp[0]) / 2
                        sp = (mid_x, sp[1])
                        dp = (mid_x, dp[1])

                    seg1 = via_y - sb.top
                    seg2 = db.bot - via_y

                    if seg1 >= MIN_SEG and seg2 >= MIN_SEG:
                        d.arrow_route([
                            sp,
                            (sp[0], via_y),
                            (dp[0], via_y),
                            dp,
                        ], label=lbl)
                    else:
                        src_boxes = rank_boxes_map.get(src_rank, [])
                        dst_boxes = rank_boxes_map.get(dst_rank, [])
                        all_relevant = list(src_boxes) + list(dst_boxes)
                        if db.cx >= sb.cx:
                            ch_x = max((b.right for b in all_relevant), default=sb.right) + MIN_SEG
                            sp2 = src_pt if src_pt else sb.right_mid()
                            dp2 = dst_pt if dst_pt else db.right_mid()
                            d.arrow_route([
                                sp2,
                                (ch_x, sp2[1]),
                                (ch_x, dp2[1]),
                                dp2,
                            ], label=lbl)
                        else:
                            ch_x = min((b.left for b in all_relevant), default=sb.left) - MIN_SEG
                            sp2 = src_pt if src_pt else sb.left_mid()
                            dp2 = dst_pt if dst_pt else db.left_mid()
                            d.arrow_route([
                                sp2,
                                (ch_x, sp2[1]),
                                (ch_x, dp2[1]),
                                dp2,
                            ], label=lbl)

        # ── Draw feedback edges (dashed, separated lanes) ─────────────────────
        if feedback_edges:
            # Base x channel: just inside the feedback reserve area
            # Lane 0 is outermost (leftmost), increasing lanes go right
            ch_x_base = self.content_left + 0.15
            for lane_idx, (idx, e) in enumerate(feedback_edges):
                sb = self._nodes[e['src']]['box_ref']
                db = self._nodes[e['dst']]['box_ref']
                if sb is None or db is None:
                    continue
                lbl = e['label'] or ''
                ch_x = ch_x_base + lane_idx * self.feedback_lane_gap
                # Dashed feedback: src.left → ch_x → db.left (dashed line)
                d.arrow_route([
                    sb.left_mid(),
                    ('left_to', ch_x),
                    ('up_to', db.cy),
                    db.left_mid(),
                ], label=lbl, ls='--')

        # Mark terminal nodes (no outgoing forward edges)
        outgoing_forward = {e['src'] for e in self._edges if not e['feedback']}
        for nid, info in self._nodes.items():
            if nid not in outgoing_forward and info['box_ref'] is not None:
                d._terminal_boxes.add(id(info['box_ref']))

        d.fig_label()
        d.save()
        return output_path
