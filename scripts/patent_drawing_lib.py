"""
patent_drawing_lib.py  v7.3
USPTO-Compliant Patent Drawing Library

변경 이력:
  v3.0  라벨 겹침 원천 차단: 화살표 라벨을 선분 중간이 아닌
        박스-free 구간에 자동 배치. 박스 텍스트 w+h 동시 축소.
        zorder 체계 정비. 검증 강화.

  v4.0  FIG.1 실전 반영:
        - layer(): 레이어 점선 박스 + 참조번호
        - split_from_box(): T-junction 없는 1→N 분기
        - validate: T-junction 감지, 화살표 too-short 검증

  v4.1  FIG.2 실전 반영:
        - arrow_bidir(): 직선 양방향 (단일 선 양쪽 화살촉)
        - arrow_bidir_route(): elbow 양방향
        - 양방향 elbow 규칙: 각 연결마다 전용 채널 x

  v6.1  같은 레이어 박스 크기 통일:
        - LR 방향: 같은 레이어 내 모든 박스 너비를 max 너비로 통일
          → 같은 레이어의 right edge가 정렬되어 via_x가 모두 같은 지점으로 꺾임
        - TB 방향: 같은 레이어 내 모든 박스 높이를 max 높이로 통일
          → 같은 레이어의 bottom edge 정렬

  v6.0  Graph-first API 추가:
        - NodeDef: 텍스트만 정의하는 노드 클래스
        - Drawing.node(text): 노드 등록 → NodeDef 반환
        - Drawing.connect(src, dst, label): 엣지 등록
        - Drawing.layout(direction='LR'|'TB'): 크기 측정 → 레이어 배치 → 렌더
          · direction='LR': 좌→우 계층형 (기본)
          · direction='TB': 위→아래 계층형
          · 화살표 간격 자동 확보 (0.50" gap)
          · boundary 자동 계산 (박스 영역 + 0.50" 여백)
        - 기존 box()/arrow_route() 등 수동 API 완전 유지

  v5.6  measure_text() 픽셀→인치 변환 수정:
        - axes.transData.inverted()로 data coordinate 기준 실측 (정확)
        - 기존 bb.width/dpi 방식은 axes padding 때문에 과소 측정됨

  v5.5  autobox() 추가 — 텍스트 크기 기반 박스 자동 크기 결정:
        - autobox(x, y, text, fs, pad_x, pad_y): 텍스트를 실측 후 박스 w/h 자동 계산
        - 기존 box()는 유지 (좌표+크기 직접 지정 시)
        - 설계 원칙: 폰트에 맞춰 박스 크기 결정 (반대로 하지 말 것)

  v5.4  텍스트 박스 초과 감지 추가:
        - validate: 텍스트가 박스 경계를 벗어나는지 실측 검증
          (renderer를 통해 실제 렌더링 크기 측정 후 박스 크기와 비교)

  v5.3  USPTO 규칙 추가 코드화 (LLM 몫 → 코드로):
        - validate: 텍스트 최소 10pt 미달 경고 (auto-fit 결과 기준)
        - validate: 특수기호/유니코드 아래첨자 감지
        - validate: 박스 참조번호 완전 누락 감지

  v5.2  코드 자동화 강화 (LLM 실수 방지):
        - validate: dead-end 박스 감지 (입력↑ 출력=0인 중간 박스)
        - validate: 화살표 경로가 박스 텍스트 중심 관통 감지

  v5.1  (이전)
  v5.0  FIG.3 원형 다이어그램 실전 반영:
        - BoxRef.edge_toward(other_cx, other_cy): 박스 경계 교차점 계산
          (원형/타원 배치에서 대각선 화살표 정확한 출발/도착점)
        - arrow_diagonal(box_a, box_b): 두 박스 사이 직선 대각선 화살표
          rect_edge 기반으로 경계 정확 처리
        - _resolve_steps(): 중복점(0.00" 세그먼트) 자동 제거
        - validate 강화:
          · 박스 텍스트 파이프 문자(|) 감지 → 줄바꿈 사용 권고
          · bidir 경로도 T-junction 체크에 포함
          · arrow_bidir 경로도 too-short 검증

  설계 원칙 (실전에서 확립):
  1. 박스 텍스트: "102\\nCPU" 형식 — 파이프(|) 금지
  2. 화살표: 박스→박스, T-junction 금지
  3. 양방향: arrow_bidir() 또는 arrow_bidir_route() 사용
  4. 원형 배치: arrow_diagonal() 사용
  5. 중앙 설명 텍스트: label() — 참조번호 없는 다이어그램 명칭
  6. 검토: 한 도면씩, 검증 통과 + 시각 확인 후 다음으로
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os, math

# ── USPTO 상수 ────────────────────────────────────────────────────────────────
FS_BODY  = 10
FS_FIG   = 13
FW       = 'normal'
BOX_FILL = 'white'
BOX_EDGE = 'black'
LW_BOX   = 1.5
LW_ARR   = 1.3
LW_FRAME = 1.0
PAD      = 0.01
LABEL_BG = dict(facecolor='white', edgecolor='none', pad=2)

PAGE_W, PAGE_H = 8.5, 11.0

Z_BOUNDARY  = 1
Z_BND_LABEL = 2
Z_ARROW     = 4
Z_ARROWHEAD = 13   # 화살촉은 박스 fill/border/text 위에 — 도착점에서 가려지지 않도록
Z_BOX_FILL  = 10
Z_BOX_EDGE  = 11
Z_BOX_TEXT  = 12
Z_ARR_LABEL = 20
Z_SEC_LABEL = 21
Z_FIG_LABEL = 22


# ── NodeDef ───────────────────────────────────────────────────────────────────
class NodeDef:
    """
    Graph-first API에서 사용하는 노드 정의.
    텍스트만 보유; 크기/위치는 layout() 시 결정됨.
    layout() 완료 후 .box_ref로 BoxRef 접근 가능.
    """
    def __init__(self, text, fs=None, pad_x=0.20, pad_y=0.14):
        self.text   = text
        self.fs     = fs
        self.pad_x  = pad_x
        self.pad_y  = pad_y
        self.box_ref: 'BoxRef | None' = None  # layout() 후 설정

    # layout() 후 BoxRef 속성 위임
    def __getattr__(self, name):
        if name == 'box_ref':
            raise AttributeError('box_ref not set — call layout() first')
        if self.box_ref is not None:
            return getattr(self.box_ref, name)
        raise AttributeError(f"NodeDef.{name} not available before layout()")


# ── BoxRef ────────────────────────────────────────────────────────────────────
class BoxRef:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def cx(self): return self.x + self.w / 2
    @property
    def cy(self): return self.y + self.h / 2
    @property
    def top(self): return self.y + self.h
    @property
    def bot(self): return self.y
    @property
    def left(self): return self.x
    @property
    def right(self): return self.x + self.w

    def top_mid(self):   return (self.cx, self.top)
    def bot_mid(self):   return (self.cx, self.bot)
    def left_mid(self):  return (self.left, self.cy)
    def right_mid(self): return (self.right, self.cy)
    def side(self, which): return getattr(self, f"{which}_mid")()

    def edge_toward(self, tx, ty, gap=0.08):
        """
        이 박스 중심에서 (tx, ty) 방향으로 나가는 경계 교차점.
        gap: 경계에서 추가로 나올 거리 (화살표 시작/끝 여백).
        원형 배치 대각선 화살표에서 사용.
        """
        dx = tx - self.cx
        dy = ty - self.cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 1e-9:
            return (self.cx, self.cy)
        ux, uy = dx/dist, dy/dist
        t = min((self.w/2) / max(abs(ux), 1e-9),
                (self.h/2) / max(abs(uy), 1e-9))
        return (self.cx + ux*(t + gap), self.cy + uy*(t + gap))

    def contains(self, x, y, margin=0.05):
        return (self.x - margin < x < self.right + margin and
                self.y - margin < y < self.top + margin)


# ── Drawing ───────────────────────────────────────────────────────────────────
class Drawing:

    MIN_BND_PAD = 0.30

    def __init__(self, filename, fig_num="1", dpi=150):
        self.filename  = filename
        self.fig_num   = fig_num
        self.dpi       = dpi
        self._cmds     = []
        self._box_refs = []
        self._box_text_sizes = {}  # id(BoxRef) → (tw_in, th_in) 실측 텍스트 크기
        # Graph-first API
        self._nodes: list['NodeDef'] = []
        self._edges: list[tuple] = []  # (src_NodeDef, dst_NodeDef, label)

        self.fig, self.ax = plt.subplots(figsize=(PAGE_W, PAGE_H))
        self.ax.set_xlim(0, PAGE_W)
        self.ax.set_ylim(0, PAGE_H)
        self.ax.axis('off')
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')

    # ── Graph-first API ───────────────────────────────────────────────────────

    def node(self, text, fs=None, pad_x=0.20, pad_y=0.14) -> 'NodeDef':
        """
        노드 등록. 텍스트만 정의; 크기/위치는 layout() 시 자동 결정.
        반환된 NodeDef는 layout() 후 BoxRef처럼 사용 가능.

        사용:
            exhibitor = d.node('110\\nexhibitor')
            network   = d.node('130\\nwired/wireless\\ncommunication network')
        """
        nd = NodeDef(text, fs=fs, pad_x=pad_x, pad_y=pad_y)
        self._nodes.append(nd)
        return nd

    def connect(self, src: 'NodeDef', dst: 'NodeDef', label="", bidir=False):
        """
        엣지 등록 (src → dst, 또는 bidir=True로 양방향).
        layout() 전에 호출; 실제 화살표는 layout() 시 생성.

        사용:
            d.connect(exhibitor, network)              # 단방향
            d.connect(network, device, label='request') # 단방향 + 라벨
            d.connect(gen1, bus_node, bidir=True)       # 양방향
        """
        self._edges.append((src, dst, label, bidir))

    def layout(self, mode='flow', direction='LR', gap=1.10, pad_x=None, pad_y=None,
               boundary_label="",
               # bus mode 전용
               rows=None, external=None):
        """
        Graph-first 레이아웃 실행.

        mode='flow': 방향성 흐름도 (FIG.1 스타일)
            1. 모든 노드 텍스트 크기 측정
            2. 엣지 기반 레이어 계산 (topological sort)
            3. 레이어 간 배치 + 화살표 자동 생성

        mode='bus': 버스 연결 블록 다이어그램 (FIG.2 스타일)
            1. rows로 행 배치 정의 (상단/하단)
            2. 중앙 수평 버스선 + 각 박스 수직 양방향 연결
            3. external로 버스 외부 노드 연결

        Args:
            mode      : 'flow' | 'bus'
            direction : 'LR' | 'TB' (flow 전용)
            gap       : 박스 간 gap (기본 1.10")
            pad_x/y   : 텍스트 패딩
            boundary_label: boundary 라벨
            rows      : bus 전용 — [[node, ...], [node, ...]] (위→아래 순)
            external  : bus 전용 — {'right': [node, ...]} 등
        """
        # Step 0: 자동 word wrap (모든 레이아웃 타입 공용)
        BND_W = 7.90 - 0.55 - 0.35 * 2  # boundary 내부 사용 가능 폭
        all_layout_nodes = list(self._nodes)
        if rows:
            for row in rows:
                all_layout_nodes.extend(row)
        if external:
            for ext_list in external.values():
                all_layout_nodes.extend(ext_list)

        # 노드 수 기반 max_w 추정
        n_unique = len(set(id(n) for n in all_layout_nodes))
        if mode == 'bus' and rows:
            max_cols = max(len(row) for row in rows)
            est_gap = (gap or 1.10) * 0.4
            # external 공간 미리 차감
            ext_reserve_est = 0
            if external:
                for ext_list in external.values():
                    # 대략 ext 박스 1.5" + 점선통과(0.30*2) + shaft(0.50)
                    ext_reserve_est += 2.60
            avail_for_internal = BND_W - ext_reserve_est
            max_box_w = (avail_for_internal - est_gap * (max_cols - 1)) / max_cols if max_cols > 0 else BND_W
        else:
            # flow: 레이어당 박스는 세로로 쌓이므로 가로 폭은 넉넉하게
            # gap 분만 빼고 나머지를 박스 하나가 쓸 수 있음
            from collections import defaultdict
            _in_deg = defaultdict(int)
            _adj = defaultdict(list)
            for edge in self._edges:
                _adj[id(edge[0])].append(id(edge[1]))
                _in_deg[id(edge[1])] += 1
            sources = [n for n in self._nodes if _in_deg[id(n)] == 0]
            if not sources:
                sources = self._nodes[:1]
            from collections import deque
            max_depth = 1
            visited = set()
            q = deque([(id(s), 1) for s in sources])
            while q:
                nid, depth = q.popleft()
                if nid in visited:
                    continue
                visited.add(nid)
                max_depth = max(max_depth, depth)
                for nxt_id in _adj[nid]:
                    q.append((nxt_id, depth + 1))
            est_layers = max(2, max_depth)
            est_gap = gap or 1.10
            # flow: 같은 레이어의 박스들은 세로 배치 → 가로 폭 여유 있음
            # 전체 폭에서 gap만 빼고 2줄 이내로 들어갈 수 있게 넓게 설정
            max_box_w = (BND_W - est_gap * (est_layers - 1)) / est_layers
            max_box_w = max(max_box_w, 2.5)  # flow에서 최소 2.5" 보장 (2줄 이내)

        max_box_w = max(1.0, min(max_box_w, 3.0))  # 최소 1", 최대 3"

        # bus mode: external 노드는 가용 공간이 더 좁으므로 별도 max_w
        ext_max_w = max_box_w
        if mode == 'bus' and rows and external:
            max_cols = max(len(row) for row in rows)
            est_gap_h = (gap or 1.10) * 0.4
            internal_w = max_cols * max_box_w + est_gap_h * (max_cols - 1)
            # internal + boundary padding + ext 공간
            avail_ext = BND_W - internal_w - 0.30 * 2 - 0.50  # BND_PAD*2 + shaft
            ext_max_w = max(1.0, avail_ext)

        for nd in all_layout_nodes:
            is_external = False
            if external:
                for ext_list in external.values():
                    if nd in ext_list:
                        is_external = True
                        break
            mw = ext_max_w if is_external else max_box_w
            nd.text = self._auto_wrap(nd.text, mw, nd.fs)

        if mode == 'bus':
            return self._layout_bus(rows=rows, external=external,
                                    gap=gap, pad_x=pad_x, pad_y=pad_y,
                                    boundary_label=boundary_label)
        if not self._nodes:
            return

        pad_x = pad_x or 0.20
        pad_y = pad_y or 0.14

        # Step 1: 크기 측정
        for nd in self._nodes:
            tw, th = self.measure_text(nd.text, nd.fs)
            nd._w = tw + (nd.pad_x if nd.pad_x else pad_x)
            nd._h = th + (nd.pad_y if nd.pad_y else pad_y)

        # Step 1b: 레이어 내 박스 크기 통일 (크기 측정 후 레이어 계산 전에 적용 불가 → Step 2 후 처리)

        # Step 2: 레이어 계산 (Kahn's algorithm)
        from collections import defaultdict, deque
        in_degree = defaultdict(int)
        adj = defaultdict(list)
        node_set = set(id(n) for n in self._nodes)

        for edge in self._edges:
            src, dst = edge[0], edge[1]
            # 레이어 계산은 항상 단방향 (src→dst) — bidir은 렌더링만 양방향
            adj[id(src)].append(dst)
            in_degree[id(dst)] += 1

        queue = deque([n for n in self._nodes if in_degree[id(n)] == 0])
        layers = []  # layers[i] = [NodeDef, ...]
        layer_of = {}  # id(nd) → layer index

        while queue:
            layer_nodes = list(queue)
            queue.clear()
            layers.append(layer_nodes)
            for nd in layer_nodes:
                layer_of[id(nd)] = len(layers) - 1
                for nxt in adj[id(nd)]:
                    in_degree[id(nxt)] -= 1
                    if in_degree[id(nxt)] == 0:
                        queue.append(nxt)

        # 레이어에 속하지 않은 노드 마지막에 추가
        assigned = set(id(n) for layer in layers for n in layer)
        orphans = [n for n in self._nodes if id(n) not in assigned]
        if orphans:
            layers.append(orphans)

        # Step 2b: 레이어 내 박스 크기 통일
        # LR: 같은 레이어의 너비를 max로 통일 → right edge 정렬, via_x 동일
        # TB: 같은 레이어의 높이를 max로 통일 → bottom edge 정렬
        if direction == 'LR':
            for layer in layers:
                max_w = max(nd._w for nd in layer)
                for nd in layer:
                    nd._w = max_w
        else:
            for layer in layers:
                max_h = max(nd._h for nd in layer)
                for nd in layer:
                    nd._h = max_h

        # Step 3: 위치 계산
        # USPTO 표준 boundary: x1=0.55, y1=1.10, x2=7.90, y2=10.15
        BND_X1, BND_Y1, BND_X2, BND_Y2 = 0.55, 1.10, 7.90, 10.15
        INNER_PAD = 0.35  # boundary 안쪽 여백 (MIN_BND_PAD=0.30" 초과 확보)
        CONTENT_W = BND_X2 - BND_X1 - INNER_PAD * 2  # 사용 가능 폭
        CONTENT_H = BND_Y2 - BND_Y1 - INNER_PAD * 2  # 사용 가능 높이

        INTER_LAYER_GAP = gap
        INTRA_LAYER_GAP = gap * 0.7

        if direction == 'LR':
            layer_widths  = [max(nd._w for nd in layer) for layer in layers]
            layer_heights = []
            for layer in layers:
                total_h = sum(nd._h for nd in layer) + INTRA_LAYER_GAP * (len(layer) - 1)
                layer_heights.append(total_h)

            raw_w = sum(layer_widths) + INTER_LAYER_GAP * (len(layers) - 1)
            raw_h = max(layer_heights)

            # 페이지 범위 초과 시 gap 자동 축소
            total_box_w = sum(layer_widths)
            n_gaps = max(len(layers) - 1, 1)
            # elbow 화살표: via_x 양쪽 segment 각 0.44" 필요 → 최소 gap = 0.88"
            MIN_INTER = 0.88
            # 요청 gap 우선, 공간 부족 시 축소, 단 최소 MIN_INTER 보장
            avail_for_gaps = CONTENT_W - total_box_w
            if avail_for_gaps < MIN_INTER * n_gaps:
                # 박스 패딩을 줄여서 공간 확보 (pad 최소 0.10")
                excess = MIN_INTER * n_gaps - avail_for_gaps
                pad_reduce = min(excess / len(self._nodes), pad_x - 0.10)
                pad_x = max(0.10, pad_x - pad_reduce)
                # 박스 크기 재계산
                for layer in layers:
                    for nd in layer:
                        tw, th = self.measure_text(nd.text, nd.fs)
                        nd._w = tw + pad_x
                        nd._h = th + (pad_y or 0.14)
                # 재계산 후 레이어 내 크기 통일 재적용 (LR: max_w, TB: max_h)
                if direction == 'LR':
                    for layer in layers:
                        max_w = max(nd._w for nd in layer)
                        for nd in layer:
                            nd._w = max_w
                else:
                    for layer in layers:
                        max_h = max(nd._h for nd in layer)
                        for nd in layer:
                            nd._h = max_h
                layer_widths = [max(nd._w for nd in layer) for layer in layers]
                total_box_w = sum(layer_widths)
                avail_for_gaps = CONTENT_W - total_box_w
            INTER_LAYER_GAP = max(MIN_INTER, min(gap, avail_for_gaps / n_gaps))
            raw_w = total_box_w + INTER_LAYER_GAP * n_gaps

            if raw_h > CONTENT_H:
                # 레이어 내 gap 축소
                max_boxes_in_layer = max(len(layer) for layer in layers)
                total_box_h = sum(max(nd._h for nd in layer) for layer in layers)
                avail_gap_h = CONTENT_H - total_box_h / len(layers) * len(layers)
                INTRA_LAYER_GAP = max(0.44, avail_gap_h / max(max_boxes_in_layer - 1, 1))

            # 콘텐츠 영역 center-to-center 등간격 배치
            content_cy = (BND_Y1 + BND_Y2) / 2  # 수직 중앙

            # 레이어 center x 좌표를 등간격으로 계산
            # 좌우 끝 레이어의 center가 boundary 안에 들어오도록 배치
            n_layers = len(layers)
            half_w_first = layer_widths[0] / 2
            half_w_last  = layer_widths[-1] / 2

            # 사용 가능 범위: first_cx ~ last_cx
            first_cx_min = BND_X1 + INNER_PAD + half_w_first
            last_cx_max  = BND_X2 - INNER_PAD - half_w_last
            avail_span = last_cx_max - first_cx_min

            if n_layers > 1:
                cx_gap = avail_span / (n_layers - 1)
            else:
                cx_gap = 0

            layer_cxs = [first_cx_min + i * cx_gap for i in range(n_layers)]

            for i, layer in enumerate(layers):
                layer_total_h = sum(nd._h for nd in layer) + INTRA_LAYER_GAP * (len(layer) - 1)
                cur_y = content_cy + layer_total_h / 2
                lcx = layer_cxs[i]
                for nd in layer:
                    box_x = lcx - nd._w / 2
                    box_y = cur_y - nd._h
                    nd.box_ref = self.box(box_x, box_y, nd._w, nd._h, nd.text, nd.fs)
                    cur_y -= (nd._h + INTRA_LAYER_GAP)

        else:  # TB: 위→아래
            layer_heights = [max(nd._h for nd in layer) for layer in layers]
            layer_widths_list = []
            for layer in layers:
                total_w = sum(nd._w for nd in layer) + INTRA_LAYER_GAP * (len(layer) - 1)
                layer_widths_list.append(total_w)

            raw_h = sum(layer_heights) + INTER_LAYER_GAP * (len(layers) - 1)
            raw_w = max(layer_widths_list)

            if raw_h > CONTENT_H:
                total_box_h = sum(layer_heights)
                avail_gap_h = CONTENT_H - total_box_h
                INTER_LAYER_GAP = max(0.44, avail_gap_h / max(len(layers) - 1, 1))
                raw_h = total_box_h + INTER_LAYER_GAP * (len(layers) - 1)

            content_cx = (BND_X1 + BND_X2) / 2
            content_start_y = (BND_Y1 + BND_Y2) / 2 + raw_h / 2

            cur_y = content_start_y
            for i, layer in enumerate(layers):
                layer_total_w = sum(nd._w for nd in layer) + INTRA_LAYER_GAP * (len(layer) - 1)
                cur_x = content_cx - layer_total_w / 2
                lh = layer_heights[i]
                for nd in layer:
                    box_x = cur_x
                    box_y = cur_y - lh + (lh - nd._h) / 2
                    nd.box_ref = self.box(box_x, box_y, nd._w, nd._h, nd.text, nd.fs)
                    cur_x += nd._w + INTRA_LAYER_GAP
                cur_y -= (lh + INTER_LAYER_GAP)

        # Step 4: boundary 고정 (USPTO 표준)
        self.boundary(BND_X1, BND_Y1, BND_X2, BND_Y2, label=boundary_label)

        # Step 5: 엣지 → 화살표 자동 생성
        # LR 방향: 레이어별 경계 x 사전 계산 (via_x를 레이어 경계 중간으로 고정)
        layer_boundary_xs = {}  # layer_idx → (max_right_of_layer, min_left_of_next_layer)
        if direction == 'LR':
            nd_to_layer = {}
            for li, layer in enumerate(layers):
                for nd in layer:
                    nd_to_layer[id(nd)] = li
            for li, layer in enumerate(layers):
                if li + 1 < len(layers):
                    max_right = max(nd.box_ref.right for nd in layer if nd.box_ref)
                    min_left  = min(nd.box_ref.left for nd in layers[li+1] if nd.box_ref)
                    layer_boundary_xs[li] = (max_right + min_left) / 2  # 레이어 간 중간 x

        for edge in self._edges:
            src, dst, lbl = edge[0], edge[1], edge[2]
            bidir = edge[3] if len(edge) > 3 else False
            if src.box_ref is None or dst.box_ref is None:
                continue
            sb, db = src.box_ref, dst.box_ref
            if direction == 'LR':
                if sb.right < db.left - 0.01:
                    if abs(sb.cy - db.cy) < 0.02:
                        if bidir:
                            self.arrow_bidir(sb, db, side='h')
                        else:
                            self.arrow_route([sb.right_mid(), db.left_mid()], label=lbl)
                    else:
                        MIN_S = 0.44
                        via_x = sb.right + MIN_S
                        if db.left - via_x < MIN_S:
                            via_x = (sb.right + db.left) / 2
                        pts = [
                            sb.right_mid(),
                            (via_x, sb.cy),
                            (via_x, db.cy),
                            db.left_mid(),
                        ]
                        if bidir:
                            self.arrow_bidir_route(pts)
                        else:
                            self.arrow_route(pts, label=lbl)
                else:
                    pts = [
                        sb.bot_mid(),
                        (sb.cx, sb.bot - 0.40),
                        (db.cx, db.bot - 0.40),
                        db.bot_mid(),
                    ]
                    if bidir:
                        self.arrow_bidir_route(pts)
                    else:
                        self.arrow_route(pts, label=lbl)
            else:  # TB
                if sb.bot > db.top + 0.01:
                    if bidir:
                        self.arrow_bidir(sb, db, side='v')
                    else:
                        self.arrow_v(sb, db, label=lbl)
                else:
                    pts = [
                        sb.right_mid(),
                        (sb.right + 0.40, sb.cy),
                        (sb.right + 0.40, db.cy),
                        db.right_mid(),
                    ]
                    if bidir:
                        self.arrow_bidir_route(pts)
                    else:
                        self.arrow_route(pts, label=lbl)

        self.fig_label()

    def _layout_bus(self, rows=None, external=None, gap=1.10,
                    pad_x=None, pad_y=None, boundary_label=""):
        """
        버스 레이아웃: 중앙 수평 버스선 + 상/하 행 배치.
        rows: [[node, ...], [node, ...]] — 위→아래 순
        external: {'right': [node, ...], 'left': [...]} — 버스 외부 연결
        """
        if not rows:
            return

        pad_x = pad_x or 0.20
        pad_y = pad_y or 0.14
        external = external or {}

        # Step 1: 모든 노드 크기 측정
        all_nodes = []
        for row in rows:
            all_nodes.extend(row)
        for side_nodes in external.values():
            all_nodes.extend(side_nodes)

        for nd in all_nodes:
            tw, th = self.measure_text(nd.text, nd.fs)
            nd._w = tw + (nd.pad_x if nd.pad_x else pad_x)
            nd._h = th + (nd.pad_y if nd.pad_y else pad_y)

        # Step 1b: 같은 행 내 높이 통일
        for row in rows:
            if row:
                max_h = max(nd._h for nd in row)
                for nd in row:
                    nd._h = max_h

        # 행 내 너비 통일 (행 간은 다를 수 있음 — 공간 확보)
        for row in rows:
            if row:
                max_w = max(nd._w for nd in row)
                for nd in row:
                    nd._w = max_w

        # Step 2: 레이아웃 계산
        BND_X1, BND_Y1, BND_X2, BND_Y2 = 0.55, 1.10, 7.90, 10.15
        INNER_PAD = 0.35
        BND_PAD = self.MIN_BND_PAD  # 0.30" — 점선↔박스 여백
        CONTENT_W = BND_X2 - BND_X1 - INNER_PAD * 2
        CONTENT_H = BND_Y2 - BND_Y1 - INNER_PAD * 2
        content_cx = (BND_X1 + BND_X2) / 2
        content_cy = (BND_Y1 + BND_Y2) / 2

        BOX_GAP_H = gap * 0.4   # 같은 행 내 수평 간격 (줄여서 external 공간 확보)
        BOX_GAP_V = gap * 0.5   # 버스↔박스 수직 간격
        BUS_SPACE = 0.15         # 버스선 두께 공간

        # 가장 넓은 행 기준으로 전체 폭 계산
        row_widths = []
        for row in rows:
            rw = sum(nd._w for nd in row) + BOX_GAP_H * (len(row) - 1)
            row_widths.append(rw)
        max_row_w = max(row_widths) if row_widths else 0

        # external 노드 공간: 박스폭 + 점선통과(BND_PAD*2) + 화살표shaft(0.50)
        EXT_RESERVE = BND_PAD * 2 + 0.50
        ext_right_w = 0
        if 'right' in external and external['right']:
            ext_right_w = max(nd._w for nd in external['right']) + EXT_RESERVE
        ext_left_w = 0
        if 'left' in external and external['left']:
            ext_left_w = max(nd._w for nd in external['left']) + EXT_RESERVE

        total_w = max_row_w + ext_right_w + ext_left_w

        # 페이지 초과 시 내부 gap + 박스 패딩 축소
        if total_w > CONTENT_W:
            excess = total_w - CONTENT_W
            # 1차: gap 축소
            max_cols = max(len(row) for row in rows)
            n_gaps = max(max_cols - 1, 1)
            gap_reduce = min(excess / n_gaps, BOX_GAP_H * 0.7)
            BOX_GAP_H -= gap_reduce
            BOX_GAP_H = max(0.20, BOX_GAP_H)
            excess -= gap_reduce * n_gaps

            # 2차: 내부 박스 패딩 축소
            if excess > 0:
                internal_nodes_list = [nd for row in rows for nd in row]
                pad_reduce_per = excess / max(len(internal_nodes_list), 1)
                for nd in internal_nodes_list:
                    nd._w = max(nd._w - pad_reduce_per, 0.8)
                # 행 내 너비 재통일
                for row in rows:
                    if row:
                        mx = max(nd._w for nd in row)
                        for nd in row:
                            nd._w = mx
                # row_widths 재계산
                row_widths = []
                for row in rows:
                    rw = sum(nd._w for nd in row) + BOX_GAP_H * (len(row) - 1)
                    row_widths.append(rw)
                max_row_w = max(row_widths) if row_widths else 0

            total_w = max_row_w + ext_right_w + ext_left_w

        # 버스 y 좌표 (중앙)
        bus_y = content_cy

        # 행 배치: 위→아래 순으로 rows[0]이 가장 위
        n_rows = len(rows)
        # rows[0]: 버스 위, rows[1]: 버스 아래, rows[2+]: 더 아래...
        row_ys = []
        if n_rows == 1:
            row_ys = [bus_y + BOX_GAP_V + rows[0][0]._h / 2]
        elif n_rows == 2:
            row_ys = [
                bus_y + BOX_GAP_V + rows[0][0]._h / 2,  # 위
                bus_y - BOX_GAP_V - rows[1][0]._h / 2,  # 아래
            ]
        else:
            # 3행 이상
            for i in range(n_rows):
                if i == 0:
                    row_ys.append(bus_y + BOX_GAP_V + rows[0][0]._h / 2)
                else:
                    prev_h = rows[i-1][0]._h if rows[i-1] else 0.5
                    row_ys.append(row_ys[-1] - prev_h / 2 - BOX_GAP_V - rows[i][0]._h / 2)

        # 내부 박스 left edge 시작 x
        internal_start_x = content_cx - max_row_w / 2 + ext_left_w / 2 - ext_right_w / 2

        # Step 3: 박스 배치
        # 내부 영역 사용 가능 범위: page boundary + 점선여백 확보
        INT_BND_MARGIN = 0.20  # 점선↔page boundary 여백
        int_area_left  = BND_X1 + INT_BND_MARGIN + BND_PAD  # 점선 안쪽 시작
        int_area_right = BND_X2 - INNER_PAD - ext_right_w   # ext 공간 차감
        internal_cx = (int_area_left + int_area_right) / 2

        for ri, row in enumerate(rows):
            row_w = sum(nd._w for nd in row) + BOX_GAP_H * (len(row) - 1)
            start_x = internal_cx - row_w / 2
            cur_x = start_x
            cy = row_ys[ri]
            for nd in row:
                box_x = cur_x
                box_y = cy - nd._h / 2
                nd.box_ref = self.box(box_x, box_y, nd._w, nd._h, nd.text, nd.fs)
                cur_x += nd._w + BOX_GAP_H

        # Step 4: 버스선 + internal boundary + external 배치
        BND_PAD = self.MIN_BND_PAD  # 0.30" — 점선↔박스 여백
        all_internal = [nd for row in rows for nd in row if nd.box_ref]

        if all_internal:
            # 버스 범위: 가장 왼쪽/오른쪽 내부 박스의 cx에서 시작
            bus_left  = min(nd.box_ref.cx for nd in all_internal)
            bus_right = max(nd.box_ref.cx for nd in all_internal)

            # Internal boundary (100 점선): 내부 박스들만 감싸는 점선
            int_left   = min(nd.box_ref.left for nd in all_internal) - BND_PAD
            int_right  = max(nd.box_ref.right for nd in all_internal) + BND_PAD
            int_top    = max(nd.box_ref.top for nd in all_internal) + BND_PAD
            int_bot    = min(nd.box_ref.bot for nd in all_internal) - BND_PAD
            # 버스선도 포함하도록 (bus_y가 internal 영역 안에 있어야)
            int_top = max(int_top, bus_y + 0.10)
            int_bot = min(int_bot, bus_y - 0.10)

            # External 배치: internal boundary 바깥에 배치
            # General Rule: internal_boundary_edge + BND_PAD + gap + ext_box
            # 즉 점선이 internal과 external 사이를 지나갈 공간 확보
            EXT_BND_GAP = BND_PAD  # 점선 바깥에서 external까지 여백

            if 'right' in external and external['right']:
                ext_nd = external['right'][0]
                # ext_x: int_right(점선 우측) + EXT_BND_GAP + 화살표 shaft(0.50)
                ext_x = int_right + EXT_BND_GAP + 0.50
                max_ext_right = BND_X2 - INNER_PAD
                ext_x = min(ext_x, max_ext_right - ext_nd._w)
                ext_y = bus_y - ext_nd._h / 2
                ext_nd.box_ref = self.box(ext_x, ext_y, ext_nd._w, ext_nd._h,
                                          ext_nd.text, ext_nd.fs)
                # 버스선을 internal boundary 우측 edge까지 연장
                bus_right = int_right

            if 'left' in external and external['left']:
                ext_nd = external['left'][0]
                ext_right = int_left - EXT_BND_GAP - 0.44
                ext_x = max(ext_right - ext_nd._w, BND_X1 + INNER_PAD)
                ext_y = bus_y - ext_nd._h / 2
                ext_nd.box_ref = self.box(ext_x, ext_y, ext_nd._w, ext_nd._h,
                                          ext_nd.text, ext_nd.fs)
                bus_left = int_left

            # 버스선 (수평) — 내부 박스 cx 범위
            self.line(bus_left, bus_y, bus_right, bus_y)

            # Internal boundary 점선 (boundary_label로 라벨)
            # 라벨 영역 확보: 상단에 0.35" 추가
            if boundary_label:
                int_top += 0.35  # 라벨 공간 확보
                self.layer(int_left, int_bot, int_right, int_top, label=boundary_label)

        # Step 5: 각 박스 ↔ 버스 수직 양방향 화살표
        for ri, row in enumerate(rows):
            for nd in row:
                if nd.box_ref is None:
                    continue
                b = nd.box_ref
                if ri == 0:  # 상단 행: 박스 아래 ↔ 버스
                    # 양방향 화살표: 버스 → 박스 하단
                    self._cmds.append(('bidir', [(b.cx, bus_y), (b.cx, b.bot)]))
                else:  # 하단 행: 버스 ↔ 박스 상단
                    self._cmds.append(('bidir', [(b.cx, bus_y), (b.cx, b.top)]))

        # Step 6: 버스 → external 양방향 화살표
        for side, ext_nodes in external.items():
            for ext_nd in ext_nodes:
                if ext_nd.box_ref is None:
                    continue
                if side == 'right':
                    # int boundary 우측 → external 좌측 (점선 통과 화살표)
                    self._cmds.append(('bidir', [
                        (int_right, bus_y),
                        ext_nd.box_ref.left_mid(),
                    ]))
                elif side == 'left':
                    self._cmds.append(('bidir', [
                        ext_nd.box_ref.right_mid(),
                        (int_left, bus_y),
                    ]))

        # Step 7: 페이지 boundary (라벨 없음 — internal에 이미 boundary_label)
        self.boundary(BND_X1, BND_Y1, BND_X2, BND_Y2)
        self.fig_label()

    # ── 요소 추가 ─────────────────────────────────────────────────────────────

    def boundary(self, x1, y1, x2, y2, label="", is_page_boundary=True):
        """페이지 경계 (점선 직사각형). is_page_boundary=True이면 마진 검증 대상."""
        self._cmds.append(('boundary', x1, y1, x2, y2, label, is_page_boundary))

    def layer(self, x1, y1, x2, y2, label=""):
        """
        내부 레이어 경계 (점선 박스 + 참조번호).
        boundary(is_page_boundary=False) 단축 메서드.
        사용: d.layer(0.55, 7.40, 7.95, 10.10, "EDGE LAYER  110")
        """
        self._cmds.append(('boundary', x1, y1, x2, y2, label, False))

    def _auto_wrap(self, text, max_w, fs=None):
        """
        텍스트 자동 word wrap. 모든 레이아웃 타입에서 공용으로 사용.
        - 첫 줄(참조번호)은 건드리지 않음
        - 두 번째 줄부터 단어 단위로 줄바꿈
        - 1단계: max_w 기준으로 wrap 시도
        - 2단계: 한 줄이 max_w를 초과하면 균등 2분할 시도

        반환: wrap된 텍스트 (\\n 포함)
        """
        fs = fs or FS_BODY
        lines = text.split('\n')
        if len(lines) < 2:
            return text

        ref_line = lines[0]
        body = ' '.join(lines[1:])
        words = body.split()

        if not words:
            return text

        # 본문 전체 폭 측정
        body_w, _ = self.measure_text(body, fs)
        usable_w = max_w - 0.15

        if body_w <= usable_w:
            # 한 줄에 들어감 → wrap 불필요
            return ref_line + '\n' + body

        # 균등 분할: 본문을 N줄로 나눠서 가장 넓은 줄이 usable_w 이하가 되도록
        best_lines = [body]  # fallback
        for n_lines in range(2, len(words) + 1):
            # 단어를 n_lines 줄로 분배
            candidates = self._split_words_balanced(words, n_lines, fs)
            max_line_w = max(self.measure_text(l, fs)[0] for l in candidates)
            if max_line_w <= usable_w:
                best_lines = candidates
                break
            # usable_w 없이도 2줄이면 충분히 좋음
            if n_lines == 2:
                best_lines = candidates

        return ref_line + '\n' + '\n'.join(best_lines)

    def _split_words_balanced(self, words, n_lines, fs):
        """단어 리스트를 n_lines줄로 최대한 균등하게 분배."""
        if n_lines >= len(words):
            return words

        if n_lines == 2:
            # 모든 분할점을 시도해서 max(줄1폭, 줄2폭)이 최소인 지점 선택
            best_split = 1
            best_max_w = float('inf')
            for i in range(1, len(words)):
                line1 = ' '.join(words[:i])
                line2 = ' '.join(words[i:])
                w1, _ = self.measure_text(line1, fs)
                w2, _ = self.measure_text(line2, fs)
                max_w = max(w1, w2)
                if max_w < best_max_w:
                    best_max_w = max_w
                    best_split = i
            return [' '.join(words[:best_split]), ' '.join(words[best_split:])]

        # 3줄 이상: greedy wrap
        target_w_per_line = sum(self.measure_text(w, fs)[0] for w in words) / n_lines
        result = []
        current = ''
        current_w = 0
        for word in words:
            ww, _ = self.measure_text(word, fs)
            test_w = current_w + ww + (self.measure_text(' ', fs)[0] if current else 0)
            if current and test_w > target_w_per_line * 1.2 and len(result) < n_lines - 1:
                result.append(current)
                current = word
                current_w = ww
            else:
                current = f'{current} {word}'.strip() if current else word
                current_w = test_w
        if current:
            result.append(current)
        return result

    def measure_text(self, text, fs=None) -> tuple:
        """
        텍스트를 실제 렌더링하여 크기(인치)를 반환.
        반환: (width_in, height_in)
        """
        fs = fs or FS_BODY
        # visible=True로 렌더링 후 크기 측정, 이후 제거
        t = self.ax.text(0, 0, text, fontsize=fs, fontweight=FW,
                         multialignment='center',
                         transform=self.ax.transData, visible=True)
        self.fig.canvas.draw()
        try:
            renderer = self.fig.canvas.get_renderer()
            bb = t.get_window_extent(renderer=renderer)
            # axes.transData.inverted()로 pixel → data coordinate(inches) 변환
            inv = self.ax.transData.inverted()
            p0 = inv.transform((bb.x0, bb.y0))
            p1 = inv.transform((bb.x1, bb.y1))
            tw = abs(p1[0] - p0[0])
            th = abs(p1[1] - p0[1])
        except Exception:
            # fallback: 글자 수 기반 근사값
            lines = text.split('\n')
            max_chars = max(len(l) for l in lines)
            tw = max_chars * fs * 0.6 / 72
            th = len(lines) * fs * 1.2 / 72
        t.remove()
        return (tw, th)

    def autobox(self, x, y, text, fs=None, pad_x=0.20, pad_y=0.14) -> BoxRef:
        """
        텍스트 크기를 실측 후 박스 w/h 자동 결정.
        폰트 크기에 맞춰 박스 크기가 결정됨 (반대로 하지 말 것).

        Args:
            x, y   : 박스 좌하단 좌표 (인치)
            text   : 박스 텍스트 (첫 줄 참조번호 + \\n)
            fs     : 폰트 크기 (기본 10pt, 고정됨 — 축소 없음)
            pad_x  : 좌우 여백 합계 (기본 0.20")
            pad_y  : 상하 여백 합계 (기본 0.14")
        Returns:
            BoxRef (w, h 자동 결정됨)
        """
        fs = fs or FS_BODY
        tw, th = self.measure_text(text, fs)
        w = tw + pad_x
        h = th + pad_y
        return self.box(x, y, w, h, text, fs)

    def box(self, x, y, w, h, text, fs=None) -> BoxRef:
        """
        박스 추가. 텍스트 폰트 자동 축소.
        text 형식: "102\\nCPU" (파이프 문자 금지)
        """
        b = BoxRef(x, y, w, h)
        self._box_refs.append(b)
        self._cmds.append(('box', b, text, fs))
        return b

    def fig_label(self, y=None):
        """FIG. N 라벨 (하단 중앙 자동 배치)."""
        self._cmds.append(('fig_label', y))

    def label(self, x, y, text, ha='center', fs=None):
        """
        독립 텍스트 라벨 (참조번호 없는 설명용).
        원형 다이어그램 중앙 명칭, 섹션 구분 등에 사용.
        박스가 아니므로 참조번호 불필요.
        """
        self._cmds.append(('label', x, y, text, ha, fs or FS_BODY))

    def line(self, x1, y1, x2, y2, ls='-'):
        """화살촉 없는 단순 선분. 브래킷, 구분선, 버스 등에 사용."""
        self._cmds.append(('line', x1, y1, x2, y2, ls))

    # ── 화살표 ────────────────────────────────────────────────────────────────

    def arrow_v(self, src_box: BoxRef, dst_box: BoxRef, label=""):
        """수직 단방향 화살표 (src 하단 → dst 상단)."""
        self._cmds.append(('route', [src_box.bot_mid(), dst_box.top_mid()],
                           label, None, None))

    def arrow_h(self, src_box: BoxRef, dst_box: BoxRef, label=""):
        """수평 단방향 화살표 (src 우측 → dst 좌측)."""
        self._cmds.append(('route', [src_box.right_mid(), dst_box.left_mid()],
                           label, None, None))

    def arrow_bidir(self, box_a: BoxRef, box_b: BoxRef, side='h'):
        """
        양방향 단일 선 (↔ 또는 ↕).
        side='h': 수평, side='v': 수직.
        두 화살표 겹침 대신 사용 — 명확성 규칙 준수.
        """
        if side == 'h':
            pts = [box_a.right_mid(), box_b.left_mid()]
        else:
            pts = [box_a.bot_mid(), box_b.top_mid()]
        self._cmds.append(('bidir', pts))

    def arrow_bidir_route(self, steps):
        """
        양방향 elbow 화살표 (단일 선, 양 끝 화살촉).
        steps: arrow_route()와 동일 형식.
        각 연결마다 전용 채널 x 사용 (이웃 연결과 공유 금지).
        사용: d.arrow_bidir_route([mem.right_mid(), (CH_MEM, mem.cy), (CH_MEM, cpu.cy+0.20), (cpu.left, cpu.cy+0.20)])
        """
        pts = self._resolve_steps(steps)
        self._cmds.append(('bidir', pts))

    def arrow_diagonal(self, box_a: BoxRef, box_b: BoxRef, gap=0.08):
        """
        두 박스 사이 직선 대각선 화살표.
        각 박스의 경계 교차점에서 출발/도착 (정확한 rect_edge 계산).
        원형/타원 배치 다이어그램에서 사용.
        사용: d.arrow_diagonal(boxes[i], boxes[j])
        """
        sx, sy = box_a.edge_toward(box_b.cx, box_b.cy, gap)
        ex, ey = box_b.edge_toward(box_a.cx, box_a.cy, gap)
        self._cmds.append(('route', [(sx, sy), (ex, ey)], '', None, None))

    def arrow_route(self, steps, label="", label_pos=1,
                    label_dx=0.18, label_ha='left', ls='-'):
        """
        꺾인 단방향 화살표.
        steps: (x,y) 절대좌표 또는 ('right_to',x) 등 명령어.
        중복점은 자동 제거됨.
        """
        pts = self._resolve_steps(steps)
        self._cmds.append(('route', pts, label, label_pos,
                            (label_dx, label_ha), ls))

    def split_from_box(self, src_box: BoxRef, destinations, via_y=None):
        """
        1→N 팬아웃 (T-junction 없음).
        src_box 하단을 n등분한 위치에서 각 dst로 독립 화살표.
        사용: d.split_from_box(eng, [out1, out2, out3], via_y=4.5)
        """
        dsts = [(item, "") if not isinstance(item, tuple) else item
                for item in destinations]
        n = len(dsts)
        if n == 0:
            return

        step = src_box.w / (n + 1)
        start_xs = [src_box.left + step * (i + 1) for i in range(n)]

        if via_y is None:
            max_top = max(d.top for d, _ in dsts)
            via_y = max_top + 0.20

        for i, ((dst, lbl), sx) in enumerate(zip(dsts, start_xs)):
            if abs(sx - dst.cx) < 0.01 or abs(via_y - dst.top) < 0.01:
                pts = [(sx, src_box.bot), dst.top_mid()]
            else:
                pts = [(sx, src_box.bot), (sx, via_y), (dst.cx, via_y), dst.top_mid()]
            self._cmds.append(('route', pts, lbl,
                                1 if lbl else None, (0.12, 'left'), '-'))

    # ── 렌더링 ────────────────────────────────────────────────────────────────

    def save(self):
        ax = self.ax
        bnd_rect = None

        # Pass 1: boundary / layer
        for cmd in self._cmds:
            if cmd[0] == 'boundary':
                _, x1, y1, x2, y2, lbl, is_page = cmd
                ax.add_patch(FancyBboxPatch(
                    (x1, y1), x2-x1, y2-y1,
                    boxstyle="square,pad=0",
                    facecolor='none', edgecolor=BOX_EDGE,
                    linewidth=LW_FRAME, linestyle='--', zorder=Z_BOUNDARY))
                if lbl:
                    ax.text(x1+0.12, y2-0.12, lbl,
                            ha='left', va='top',
                            fontsize=FS_BODY, fontweight=FW, zorder=Z_BND_LABEL)
                if is_page:
                    bnd_rect = (x1, y1, x2, y2)

        # Pass 2: 화살표 + 단순 선 (박스 fill 아래)
        for cmd in self._cmds:
            if cmd[0] == 'route':
                _, pts, lbl, lpos, lopt, *rest = cmd
                ls = rest[0] if rest else '-'
                ldx, lha = lopt if lopt else (0.18, 'left')
                self._render_route(ax, pts, lbl, lpos, ldx, lha, ls)
            elif cmd[0] == 'bidir':
                self._render_bidir(ax, cmd[1])
            elif cmd[0] == 'line':
                _, x1, y1, x2, y2, ls = cmd
                ax.plot([x1, x2], [y1, y2],
                        color=BOX_EDGE, lw=LW_ARR, linestyle=ls,
                        solid_capstyle='round', zorder=Z_ARROW)

        # Pass 3: 박스 white fill
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, _, _ = cmd
                ax.add_patch(FancyBboxPatch(
                    (b.x, b.y), b.w, b.h, boxstyle="square,pad=0",
                    facecolor=BOX_FILL, edgecolor='none',
                    linewidth=0, zorder=Z_BOX_FILL))

        # Pass 4: 박스 border + text
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, fs_override = cmd
                ax.add_patch(FancyBboxPatch(
                    (b.x, b.y), b.w, b.h, boxstyle="square,pad=0",
                    facecolor='none', edgecolor=BOX_EDGE,
                    linewidth=LW_BOX, zorder=Z_BOX_EDGE))
                fs = self._fit_font(text, b.w-0.18, b.h-0.10,
                                    fs_override or FS_BODY)
                t_obj = ax.text(b.cx, b.cy, text,
                        ha='center', va='center',
                        fontsize=fs, fontweight=FW,
                        multialignment='center', wrap=False,
                        zorder=Z_BOX_TEXT)
                # 실측 텍스트 크기 저장 (validate에서 박스 초과 검사용)
                try:
                    self.fig.canvas.draw()
                    bb = t_obj.get_window_extent(renderer=self.fig.canvas.get_renderer())
                    self._box_text_sizes[id(b)] = (bb.width / self.dpi, bb.height / self.dpi)
                except Exception:
                    pass

        # Pass 5: 독립 라벨
        for cmd in self._cmds:
            if cmd[0] == 'label':
                _, x, y, text, ha, fs = cmd
                ax.text(x, y, text, ha=ha, va='center',
                        fontsize=fs, fontweight=FW,
                        bbox=LABEL_BG, zorder=Z_SEC_LABEL)

        # Pass 6: FIG. 라벨
        for cmd in self._cmds:
            if cmd[0] == 'fig_label':
                fig_y = cmd[1] if (len(cmd) > 1 and cmd[1] is not None) else None
                if fig_y is None:
                    for c in self._cmds:
                        if c[0] == 'boundary' and c[6]:  # is_page_boundary
                            fig_y = c[2] - 0.28
                            break
                    if fig_y is None:
                        fig_y = 0.50
                ax.text(PAGE_W/2, fig_y, f'FIG. {self.fig_num}',
                        ha='center', va='center',
                        fontsize=FS_FIG, fontweight=FW, zorder=Z_FIG_LABEL)

        os.makedirs(os.path.dirname(os.path.abspath(self.filename)), exist_ok=True)
        self.fig.savefig(self.filename, dpi=self.dpi,
                         facecolor='white', bbox_inches='tight')

        issues = self._validate(bnd_rect)
        if issues:
            print(f"⚠  {self.filename}")
            for iss in issues:
                print(f"   · {iss}")
        else:
            print(f"✓  {self.filename}")

        plt.close(self.fig)

    # ── 내부 렌더 ─────────────────────────────────────────────────────────────

    def _render_bidir(self, ax, pts):
        """양방향 화살촉 (직선 또는 elbow)."""
        if len(pts) == 2:
            ax.annotate('', xy=pts[1], xytext=pts[0],
                        arrowprops=dict(arrowstyle='<->', color=BOX_EDGE,
                                       lw=LW_ARR, mutation_scale=12),
                        zorder=Z_ARROWHEAD)
        else:
            for i in range(len(pts)-1):
                ax.plot([pts[i][0], pts[i+1][0]],
                        [pts[i][1], pts[i+1][1]],
                        color=BOX_EDGE, lw=LW_ARR,
                        solid_capstyle='butt', zorder=Z_ARROW)
            ax.annotate('', xy=pts[0], xytext=pts[1],
                        arrowprops=dict(arrowstyle='->', color=BOX_EDGE,
                                       lw=LW_ARR, mutation_scale=12),
                        zorder=Z_ARROWHEAD)
            ax.annotate('', xy=pts[-1], xytext=pts[-2],
                        arrowprops=dict(arrowstyle='->', color=BOX_EDGE,
                                       lw=LW_ARR, mutation_scale=12),
                        zorder=Z_ARROWHEAD)

    def _render_route(self, ax, pts, lbl, lpos, ldx, lha, ls='-'):
        n = len(pts)
        if n < 2:
            return
        for i in range(n-2):
            ax.plot([pts[i][0], pts[i+1][0]],
                    [pts[i][1], pts[i+1][1]],
                    color=BOX_EDGE, lw=LW_ARR, linestyle=ls,
                    solid_capstyle='butt', zorder=Z_ARROW)
        ax.annotate('', xy=pts[-1], xytext=pts[-2],
                    arrowprops=dict(arrowstyle='->', color=BOX_EDGE,
                                   lw=LW_ARR, linestyle=ls, mutation_scale=12),
                    zorder=Z_ARROWHEAD)
        if lbl:
            idx = self._best_label_segment(pts, lpos)
            if idx is not None:
                mx = (pts[idx][0] + pts[idx+1][0]) / 2
                my = (pts[idx][1] + pts[idx+1][1]) / 2
                if abs(pts[idx][0] - pts[idx+1][0]) < 0.01:
                    ax.text(mx + (ldx or 0.18), my, lbl,
                            ha=lha or 'left', va='center',
                            fontsize=FS_BODY, fontweight=FW,
                            bbox=LABEL_BG, zorder=Z_ARR_LABEL)
                else:
                    ax.text(mx, my+0.18, lbl,
                            ha='center', va='bottom',
                            fontsize=FS_BODY, fontweight=FW,
                            bbox=LABEL_BG, zorder=Z_ARR_LABEL)

    def _best_label_segment(self, pts, preferred_pos):
        n = len(pts)
        if n < 2:
            return None

        def clear(i):
            mx = (pts[i][0]+pts[i+1][0])/2
            my = (pts[i][1]+pts[i+1][1])/2
            return not any(b.contains(mx, my, 0.12) for b in self._box_refs)

        def seg_len(i):
            return math.sqrt((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2)

        if preferred_pos is not None:
            p = max(0, min(preferred_pos, n-2))
            if clear(p):
                return p
        candidates = [(seg_len(i), i) for i in range(n-1) if clear(i)]
        return max(candidates)[1] if candidates else None

    def _resolve_steps(self, steps):
        """steps → 절대 좌표 목록. 중복점(0.00" 세그먼트) 자동 제거."""
        pts = []
        cx, cy = 0.0, 0.0
        for s in steps:
            if isinstance(s, tuple) and len(s) == 2:
                if isinstance(s[0], (int, float)):
                    cx, cy = float(s[0]), float(s[1])
                    pts.append((cx, cy))
                elif isinstance(s[0], str):
                    cmd, val = s
                    if   cmd == 'right_to': cx = val
                    elif cmd == 'left_to':  cx = val
                    elif cmd == 'up_to':    cy = val
                    elif cmd == 'down_to':  cy = val
                    elif cmd == 'right':    cx += val
                    elif cmd == 'left':     cx -= val
                    elif cmd == 'up':       cy += val
                    elif cmd == 'down':     cy -= val
                    pts.append((cx, cy))
            else:
                raise ValueError(f"Invalid step: {s}")

        # 중복점 제거 (연속된 동일 좌표)
        deduped = [pts[0]] if pts else []
        for p in pts[1:]:
            if abs(p[0]-deduped[-1][0]) > 1e-4 or abs(p[1]-deduped[-1][1]) > 1e-4:
                deduped.append(p)
        return deduped

    def _fit_font(self, text, box_w_in, box_h_in, fs_start):
        """박스 크기에 맞게 폰트 자동 축소. 최소 8pt."""
        box_w_px = box_w_in * self.fig.dpi
        box_h_px = box_h_in * self.fig.dpi
        fs = float(fs_start)
        for _ in range(25):
            t = self.ax.text(0, 0, text, fontsize=fs, fontweight=FW,
                             multialignment='center',
                             transform=self.ax.transData, visible=False)
            self.fig.canvas.draw()
            try:
                bb = t.get_window_extent(renderer=self.fig.canvas.get_renderer())
                tw, th = bb.width, bb.height
            except Exception:
                tw, th = 0, 0
            t.remove()
            if tw <= box_w_px*0.88 and th <= box_h_px*0.85:
                break
            fs = max(8.0, fs*0.88)
        return fs

    # ── 검증 ──────────────────────────────────────────────────────────────────

    def _validate(self, bnd_rect):
        issues = []

        # 1. 박스 마진 검증
        if bnd_rect:
            bx1, by1, bx2, by2 = bnd_rect
            PAD = self.MIN_BND_PAD
            for cmd in self._cmds:
                if cmd[0] == 'box':
                    _, b, text, _ = cmd
                    short = text[:30].replace('\n', ' ')
                    if b.left - bx1 < PAD and b.left >= bx1 - 0.05:
                        issues.append(f'Box "{short}": left margin {b.left-bx1:.2f}" < {PAD}" min')
                    if bx2 - b.right < PAD and b.right <= bx2 + 0.05:
                        issues.append(f'Box "{short}": right margin {bx2-b.right:.2f}" < {PAD}" min')
                    if b.bot - by1 < PAD and b.bot >= by1 - 0.05:
                        issues.append(f'Box "{short}": bottom margin {b.bot-by1:.2f}" < {PAD}" min')
                    if by2 - b.top < PAD and b.top <= by2 + 0.05:
                        issues.append(f'Box "{short}": top margin {by2-b.top:.2f}" < {PAD}" min')

        # 2. 파이프 문자 감지 (비표준 — 줄바꿈 사용 권고)
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, _ = cmd
                if '|' in text:
                    short = text[:30].replace('\n', ' ')
                    issues.append(f'Box "{short}": pipe character "|" found. Use "\\n" instead.')

        # 5. 레이어 라벨 겹침 검사
        # boundary 라벨은 좌상단(x1+0.12, y2-0.12)에 위치 — 높이 약 0.30"
        # 박스 상단이 레이어 boundary y2 - 0.32" 이상이면 라벨과 겹침
        LBL_RESERVE = 0.32
        for cmd in self._cmds:
            if cmd[0] == 'boundary':
                _, bx1, by1, bx2, by2, lbl, is_page = cmd
                if not is_page and lbl:   # 레이어(layer) 경계만 체크
                    for bcmd in self._cmds:
                        if bcmd[0] == 'box':
                            _, b, text, _ = bcmd
                            short = text[:25].replace('\n', ' ')
                            # 박스가 이 레이어 안에 있는지 먼저 확인
                            in_layer = (b.left >= bx1 - 0.05 and
                                        b.right <= bx2 + 0.05 and
                                        b.bot >= by1 - 0.05 and
                                        b.top <= by2 + 0.05)
                            if in_layer and b.top > by2 - LBL_RESERVE:
                                issues.append(
                                    f'Box "{short}" top ({b.top:.2f}) overlaps '
                                    f'layer label area (layer top={by2:.2f}, '
                                    f'reserve={LBL_RESERVE}"). '
                                    f'Move box down: box_y < {by2 - LBL_RESERVE - b.h:.2f}')

        # 3. 화살표 too-short (route + bidir) — MIN 0.44"
        MIN_ARR = 0.44
        EPS = 0.005  # float 오차 보정
        for cmd in self._cmds:
            if cmd[0] in ('route', 'bidir'):
                pts = cmd[1]
                for i in range(len(pts)-1):
                    dx = pts[i+1][0]-pts[i][0]
                    dy = pts[i+1][1]-pts[i][1]
                    length = math.sqrt(dx*dx + dy*dy)
                    if length < MIN_ARR - EPS:
                        issues.append(
                            f'Arrow segment too short ({length:.2f}"): '
                            f'{pts[i]} → {pts[i+1]}. Min: {MIN_ARR}"')

        # 4. T-junction 감지 (route만, 동일 시작점 3개 이상)
        from collections import Counter
        start_pts = []
        for cmd in self._cmds:
            if cmd[0] == 'route':
                pts = cmd[1]
                if pts:
                    start_pts.append((round(pts[0][0], 2), round(pts[0][1], 2)))
        for pt, cnt in Counter(start_pts).items():
            if cnt >= 3:
                issues.append(
                    f'T-junction warning: {cnt} arrows share start point {pt}. '
                    f'Use split_from_box() or separate start points.')

        # 6a. 대각선 화살표 감지 (화살촉 가려짐 위험)
        for cmd in self._cmds:
            if cmd[0] == 'route':
                pts = cmd[1]
                for i in range(len(pts)-1):
                    dx = abs(pts[i+1][0] - pts[i][0])
                    dy = abs(pts[i+1][1] - pts[i][1])
                    if dx > 0.01 and dy > 0.01:
                        issues.append(
                            f'Diagonal arrow segment: ({pts[i][0]:.2f},{pts[i][1]:.2f}) → '
                            f'({pts[i+1][0]:.2f},{pts[i+1][1]:.2f}). '
                            f'Use elbow (H+V) to avoid arrowhead clipping.')

        # 6b. 참조번호 위치 검증 — 뒤에 붙으면 경고, 첫 줄 + \n 권장
        import re
        REF_PATTERN = re.compile(r'\b\d{2,4}\b')
        CROSS_REF_PREFIXES = ('see ', 'ref. ', 'ref ', '(ref.', '(see')
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, _ = cmd
                short = text[:30].replace('\n', ' ')
                lines = text.strip().split('\n')
                if lines:
                    last_line = lines[-1].strip()
                    # 마지막 줄이 순수 참조번호이고 첫 줄이 아닌 경우
                    if REF_PATTERN.fullmatch(last_line) and len(lines) > 1:
                        issues.append(
                            f'Box "{short}": ref "{last_line}" at END. Move to FIRST line + \\n')
                    # 마지막 줄 끝에 참조번호가 붙어있는 경우
                    if not REF_PATTERN.match(last_line) and REF_PATTERN.search(last_line):
                        m = REF_PATTERN.findall(last_line)
                        if m and last_line.endswith(m[-1]):
                            ref_num = m[-1]
                            ref_idx = last_line.rfind(ref_num)
                            prefix = last_line[:ref_idx].strip().lower()
                            is_cross_ref = any(prefix.endswith(p.strip()) for p in CROSS_REF_PREFIXES)
                            if not is_cross_ref:
                                issues.append(
                                    f'Box "{short}": ref "{ref_num}" at end of '
                                    f'"{last_line[:35]}". Move to FIRST line + \\n')

        # 7. 화살표 양끝 도형 연결 (Dangling head/tail) 검증
        EDGE_TOL = 0.15  # 허용 오차 (인치)
        box_rects = [(b.left, b.bot, b.right, b.top) for b in self._box_refs]

        def _near_box_edge(px, py):
            for (bx_l, bx_b, bx_r, bx_t) in box_rects:
                on_left   = abs(px - bx_l) < EDGE_TOL and bx_b - EDGE_TOL <= py <= bx_t + EDGE_TOL
                on_right  = abs(px - bx_r) < EDGE_TOL and bx_b - EDGE_TOL <= py <= bx_t + EDGE_TOL
                on_top    = abs(py - bx_t) < EDGE_TOL and bx_l - EDGE_TOL <= px <= bx_r + EDGE_TOL
                on_bottom = abs(py - bx_b) < EDGE_TOL and bx_l - EDGE_TOL <= px <= bx_r + EDGE_TOL
                if on_left or on_right or on_top or on_bottom:
                    return True
            return False

        for cmd in self._cmds:
            if cmd[0] in ('route', 'bidir'):
                pts = cmd[1]
                if len(pts) >= 2:
                    src, dst = pts[0], pts[-1]
                    if not _near_box_edge(src[0], src[1]):
                        issues.append(
                            f'Arrow src ({src[0]:.2f},{src[1]:.2f}) NOT on any box edge. '
                            f'Dangling tail.')
                    if not _near_box_edge(dst[0], dst[1]):
                        issues.append(
                            f'Arrow dst ({dst[0]:.2f},{dst[1]:.2f}) NOT on any box edge. '
                            f'Dangling head.')

        # 8. 라벨 있는 화살표 최소 길이 (라벨 구간 shaft ≥ 0.80")
        MIN_LABELED = 0.80
        for cmd in self._cmds:
            if cmd[0] == 'route' and len(cmd) >= 4:
                pts, lbl = cmd[1], cmd[2]
                if lbl and len(pts) >= 2:
                    lpos = cmd[3]
                    if lpos is not None:
                        i = max(0, min(lpos, len(pts) - 2))
                    else:
                        # 자동 배치: 가장 긴 구간 찾기
                        i = max(range(len(pts)-1),
                                key=lambda j: math.sqrt(
                                    (pts[j+1][0]-pts[j][0])**2 +
                                    (pts[j+1][1]-pts[j][1])**2))
                    seg_len = math.sqrt(
                        (pts[i+1][0]-pts[i][0])**2 +
                        (pts[i+1][1]-pts[i][1])**2)
                    if seg_len < MIN_LABELED - EPS:
                        issues.append(
                            f'Labeled arrow "{lbl}" segment too short ({seg_len:.2f}"). '
                            f'Need {MIN_LABELED}" for label visibility.')

        # 0. 텍스트가 박스 경계를 벗어나는지 실측 검증
        # _fit_font()가 폰트를 줄여도 실제 렌더링 크기가 박스를 넘는지 다시 확인
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, fs_override = cmd
                short = text[:30].replace('\n', ' ')
                if id(b) in self._box_text_sizes:
                    tw_in, th_in = self._box_text_sizes[id(b)]
                    # 패딩 없이 박스 크기와 직접 비교 (더 엄격하게)
                    if tw_in > b.w + 0.01:
                        issues.append(
                            f'Box "{short}": text overflows horizontally '
                            f'(text={tw_in:.2f}", box={b.w:.2f}"). '
                            f'Increase box width to at least {tw_in + 0.15:.2f}".')
                    if th_in > b.h + 0.01:
                        issues.append(
                            f'Box "{short}": text overflows vertically '
                            f'(text={th_in:.2f}", box={b.h:.2f}"). '
                            f'Increase box height to at least {th_in + 0.12:.2f}".')

        # 9a. 텍스트 최소 10pt 검증 (§1.84(p)(3))
        MIN_FS = 10.0
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, fs_override = cmd
                fs_start = fs_override or FS_BODY
                fs_result = self._fit_font(text, b.w - 0.18, b.h - 0.10, fs_start)
                if fs_result < MIN_FS - 0.5:
                    short = text[:30].replace('\n', ' ')
                    issues.append(
                        f'Box "{short}": font auto-fit to {fs_result:.1f}pt < 10pt min (§1.84(p)(3)). '
                        f'Increase box size or shorten text.')

        # 9b. 특수기호 / 유니코드 아래첨자 감지
        SPECIAL_CHARS = ['★', '☆', '©', '®', '™', '°', '±', '×', '÷', '→', '←', '↑', '↓',
                         '①', '②', '③', '④', '⑤', '❶', '❷', '❸']
        SUBSCRIPT_CHARS = 'ₐₑₒₓₔₕₖₗₘₙₚₛₜ₀₁₂₃₄₅₆₇₈₉'
        SUPERSCRIPT_CHARS = 'ⁿ⁰¹²³⁴⁵⁶⁷⁸⁹'
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, _ = cmd
                short = text[:30].replace('\n', ' ')
                for ch in SPECIAL_CHARS:
                    if ch in text:
                        issues.append(
                            f'Box "{short}": special char "{ch}" may not print safely. '
                            f'Replace with plain text.')
                for ch in text:
                    if ch in SUBSCRIPT_CHARS:
                        issues.append(
                            f'Box "{short}": unicode subscript "{ch}" found. '
                            f'Use plain ASCII (e.g. t1 instead of t₁).')
                    if ch in SUPERSCRIPT_CHARS:
                        issues.append(
                            f'Box "{short}": unicode superscript "{ch}" found. '
                            f'Use plain ASCII.')

        # 9c. 박스 참조번호 완전 누락 감지
        # 박스 텍스트 첫 줄이 3~4자리 숫자가 아니면 참조번호 없는 것으로 간주
        REF_FIRST_LINE = re.compile(r'^\d{2,4}$')
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, _ = cmd
                short = text[:30].replace('\n', ' ')
                lines = text.strip().split('\n')
                first_line = lines[0].strip() if lines else ''
                if not REF_FIRST_LINE.match(first_line):
                    issues.append(
                        f'Box "{short}": no reference number on first line. '
                        f'Add ref num as first line + \\n (e.g. "100\\nMy Component").')

        # 9. Dead-end 박스 감지
        # 들어오는 화살표가 하나 이상 있고 나가는 화살표가 없는 중간 박스는 dead-end
        all_routes = [cmd[1] for cmd in self._cmds if cmd[0] in ('route', 'bidir')]
        box_has_outgoing = {id(b): False for b in self._box_refs}
        box_has_incoming = {id(b): False for b in self._box_refs}

        for pts in all_routes:
            if len(pts) < 2:
                continue
            src_pt = pts[0]
            dst_pt = pts[-1]
            for b in self._box_refs:
                # tail(src)에 가까운 박스 = 출발 박스
                if (abs(src_pt[0] - b.cx) < b.w / 2 + EDGE_TOL and
                        abs(src_pt[1] - b.cy) < b.h / 2 + EDGE_TOL):
                    box_has_outgoing[id(b)] = True
                # head(dst)에 가까운 박스 = 도착 박스
                if (abs(dst_pt[0] - b.cx) < b.w / 2 + EDGE_TOL and
                        abs(dst_pt[1] - b.cy) < b.h / 2 + EDGE_TOL):
                    box_has_incoming[id(b)] = True

        for b in self._box_refs:
            # 입력은 있는데 출력이 없고, 전체 박스가 2개 이상인 경우만 체크
            if (box_has_incoming[id(b)] and not box_has_outgoing[id(b)]
                    and len(self._box_refs) > 1):
                # bidir 화살표는 양방향이므로 outgoing으로도 간주 — 이미 위에서 처리됨
                # 마지막 노드(terminal)는 dead-end가 아닐 수 있음
                # 단, 모든 박스 중 outgoing이 있는 게 하나라도 있으면 terminal 아님
                has_any_downstream = any(box_has_outgoing[id(ob)] for ob in self._box_refs)
                if has_any_downstream:
                    # 이 박스에서만 outgoing 없음 → dead-end 경고
                    for cmd in self._cmds:
                        if cmd[0] == 'box' and cmd[1] is b:
                            short = cmd[2][:30].replace('\n', ' ')
                            issues.append(
                                f'Dead-end box "{short}": has incoming arrows but no outgoing. '
                                f'Add output arrow or verify it is an intentional terminal node.')
                            break

        # 10. 화살표 경로가 박스 텍스트 중심 관통 감지
        # 화살표 선분이 어떤 박스의 내부 영역(텍스트 중심 근처)을 지나는지 확인
        TEXT_ZONE_PAD = 0.10  # 박스 중심 텍스트 영역 여백
        for cmd in self._cmds:
            if cmd[0] in ('route', 'bidir'):
                pts = cmd[1]
                for i in range(len(pts) - 1):
                    ax0, ay0 = pts[i]
                    ax1, ay1 = pts[i + 1]
                    seg_dx = ax1 - ax0
                    seg_dy = ay1 - ay0
                    seg_len_sq = seg_dx * seg_dx + seg_dy * seg_dy
                    for b in self._box_refs:
                        # 이 선분이 출발/도착 박스면 스킵 (연결 지점)
                        is_endpoint = (
                            (abs(pts[0][0] - b.cx) < b.w / 2 + EDGE_TOL and
                             abs(pts[0][1] - b.cy) < b.h / 2 + EDGE_TOL) or
                            (abs(pts[-1][0] - b.cx) < b.w / 2 + EDGE_TOL and
                             abs(pts[-1][1] - b.cy) < b.h / 2 + EDGE_TOL)
                        )
                        if is_endpoint:
                            continue
                        # 선분에서 박스 중심까지 최단거리 계산
                        if seg_len_sq < 1e-8:
                            continue
                        t = max(0.0, min(1.0, (
                            (b.cx - ax0) * seg_dx + (b.cy - ay0) * seg_dy
                        ) / seg_len_sq))
                        closest_x = ax0 + t * seg_dx
                        closest_y = ay0 + t * seg_dy
                        if (b.left + TEXT_ZONE_PAD < closest_x < b.right - TEXT_ZONE_PAD and
                                b.bot + TEXT_ZONE_PAD < closest_y < b.top - TEXT_ZONE_PAD):
                            short = cmd[2][:20] if len(cmd) > 2 else '?'
                            box_text = ''
                            for bc in self._cmds:
                                if bc[0] == 'box' and bc[1] is b:
                                    box_text = bc[2][:25].replace('\n', ' ')
                                    break
                            issues.append(
                                f'Arrow passes through box "{box_text}": '
                                f'segment ({ax0:.2f},{ay0:.2f})→({ax1:.2f},{ay1:.2f}) '
                                f'crosses box text area. Reroute the arrow.')

        return issues
