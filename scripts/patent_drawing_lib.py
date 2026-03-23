"""
patent_drawing_lib.py  v8.0
USPTO-Compliant Patent Drawing Library

변경 이력:
  v8.0  learn/new-shapes 브랜치 — 5개 신규 패턴 추가:
        - sequence_diagram(): UML 시퀀스 다이어그램 (행위자 박스 + lifeline + 메시지 화살표)
        - swimlane_columns(): 수직 스윔레인 (레인 헤더 + 프로세스 박스)
        - horizontal_pipeline_flow(): 수평 파이프라인 (스테이지 박스 + 화살표 자동 연결)
          · x_start 파라미터 추가 (left edge 기반 배치, cx_start 대체)
          · 실제 박스 폭 기반 간격 계산으로 화살표 too-short 방지
        - rounded_rect(): 둥근 모서리 사각형 (flowchart terminator)
        - numbered_sequence_arrows(): 번호 매긴 oval 노드 시퀀스
          · 텍스트 실측 기반 oval 크기 자동 결정 (OVAL_USABLE_FACTOR=0.70)
        validate 개선:
        - _no_ref_boxes: sequence/swimlane 행위자 박스 ref 검사 스킵
        - _terminal_boxes: pipeline/sequence 마지막 노드 dead-end 경고 스킵
        - 마진 검사 MARGIN_EPS=0.005 추가 (float 오차 허용)
        - horizontal padding 검사 PAD_EPS=0.005 추가
        - 공간 낭비 검사에 line(lifeline) 끝점 포함
        - rounded_rect 박스도 ref 검사 대상에 추가

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


def _normalize_node_text(text: str) -> str:
    """
    노드 텍스트 정규화:
    - 참조번호 뒤 첫 \\n은 유지 (번호/본문 분리)
    - 그 이후의 추가 \\n은 스페이스로 치환 (불필요한 래핑 방지)
    예: '340\\nBid Transmission\\nto Price Tags'
      → '340\\nBid Transmission to Price Tags'
    """
    parts = text.split('\n', 1)   # 첫 \n 기준으로 최대 2분할
    if len(parts) == 2:
        ref, body = parts
        body = body.replace('\n', ' ')   # 본문 내 추가 \n → 스페이스
        return ref + '\n' + body
    return text


def _wrap_text_to_width(text: str, max_w: float, measure_fn) -> str:
    """
    텍스트가 max_w를 초과할 경우 균등 2분할 래핑.
    참조번호(첫 줄)는 건드리지 않고 본문만 래핑.
    measure_fn: (text) → width_in
    """
    parts = text.split('\n', 1)
    if len(parts) != 2:
        return text
    ref, body = parts
    # 이미 너비 안에 들어오면 그대로
    if measure_fn(body) <= max_w:
        return text
    # 단어 기준 균등 2분할
    words = body.split()
    if len(words) <= 1:
        return text
    best_split = 1
    best_diff = float('inf')
    for i in range(1, len(words)):
        left  = ' '.join(words[:i])
        right = ' '.join(words[i:])
        diff = abs(measure_fn(left) - measure_fn(right))
        if diff < best_diff:
            best_diff = diff
            best_split = i
    left  = ' '.join(words[:best_split])
    right = ' '.join(words[best_split:])
    return ref + '\n' + left + '\n' + right


# ── NodeDef ───────────────────────────────────────────────────────────────────
class NodeDef:
    """
    Graph-first API에서 사용하는 노드 정의.
    텍스트만 보유; 크기/위치는 layout() 시 결정됨.
    layout() 완료 후 .box_ref로 BoxRef 접근 가능.
    """
    def __init__(self, text, fs=None, pad_x=None, pad_y=None):
        self.text   = text
        self.fs     = fs
        self.pad_x  = pad_x  # None이면 layout()의 pad_x 기본값 사용
        self.pad_y  = pad_y  # None이면 layout()의 pad_y 기본값 사용
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


# ── CloudRef ──────────────────────────────────────────────────────────────────
class CloudRef(BoxRef):
    """
    Cloud 도형용 BoxRef 확장.
    실제 구름 외곽 = 타원 + bubble_r 이므로
    edge_toward()는 (ea + bubble_r) 타원을 기준으로 교차점 계산.
    화살표가 구름 윤곽 바깥에서 출발/도착 보장.
    """
    def __init__(self, cx, cy, w, h):
        import numpy as np
        super().__init__(cx - w/2, cy - h/2, w, h)
        ea, eb = w / 2, h / 2
        # _render_cloud와 동일한 bubble_r 계산
        N = 12
        perim = np.pi * (3*(ea+eb) - np.sqrt((3*ea+eb)*(ea+3*eb)))
        bubble_r = perim / N * 0.58
        # 실제 구름 외곽 타원 반축 = 기준 타원 + bubble_r
        self._ea = ea + bubble_r
        self._eb = eb + bubble_r
        self._bubble_r = bubble_r

    def edge_toward(self, tx, ty, gap=0.05):
        """(타원+bubble_r) 경계 교차점 → 화살표가 구름 실제 외곽 밖에서 출발/도착."""
        import math
        dx = tx - self.cx
        dy = ty - self.cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 1e-9:
            return (self.cx, self.cy)
        ux, uy = dx/dist, dy/dist
        denom = (ux/self._ea)**2 + (uy/self._eb)**2
        if denom < 1e-12:
            return (self.cx, self.cy)
        t = math.sqrt(1.0 / denom)
        return (self.cx + ux*(t + gap), self.cy + uy*(t + gap))

    def left_mid(self):  return (self.cx - self._ea, self.cy)
    def right_mid(self): return (self.cx + self._ea, self.cy)
    def top_mid(self):   return (self.cx, self.cy + self._eb)
    def bot_mid(self):   return (self.cx, self.cy - self._eb)


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
        self._label_extents  = []  # 독립 라벨 실측 범위 [{x0,x1,y0,y1,text}]
        self._no_ref_boxes   = set()  # id(BoxRef) → validate ref 검사 스킵
        self._terminal_boxes = set()  # id(BoxRef) → dead-end 검사 스킵 (의도적 terminal)
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

    def node(self, text, fs=None, pad_x=None, pad_y=None) -> 'NodeDef':
        """
        노드 등록. 텍스트만 정의; 크기/위치는 layout() 시 자동 결정.
        반환된 NodeDef는 layout() 후 BoxRef처럼 사용 가능.

        사용:
            exhibitor = d.node('110\\nexhibitor')
            network   = d.node('130\\nwired/wireless\\ncommunication network')
        """
        # 참조번호 뒤(첫 \n 이후) 추가 개행을 스페이스로 치환
        # → LLM/에이전트가 무의식적으로 넣는 \n을 자동 제거
        text = _normalize_node_text(text)
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

        # Step 2b: 박스 크기 통일
        # LR: 같은 레이어 내 너비 통일
        # TB: 같은 레이어 내 높이 통일 + 모든 레이어 간 너비 통일 (1열 플로우 균일 박스)
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
            # TB: 모든 레이어에 걸쳐 너비를 max로 통일 (플로우차트 균일 폭)
            all_layer_nodes = [nd for layer in layers for nd in layer]
            global_max_w = max(nd._w for nd in all_layer_nodes)
            for nd in all_layer_nodes:
                nd._w = global_max_w

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

            # 박스 너비 최종 확정 후 — 오버플로우 시 강제 래핑 (bus와 동일 로직)
            _MIN_PAD_H = 0.18
            for layer in layers:
                for nd in layer:
                    body_max_w = nd._w - _MIN_PAD_H
                    nd.text = _wrap_text_to_width(
                        nd.text, body_max_w,
                        lambda t, _nd=nd: self.measure_text(t, _nd.fs)[0]
                    )
                    _, th_new = self.measure_text(nd.text, nd.fs)
                    nd._h = max(nd._h, th_new + (pad_y or 0.14))
            # 래핑 후 레이어 내 높이 재통일
            for layer in layers:
                max_h = max(nd._h for nd in layer)
                for nd in layer:
                    nd._h = max_h

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

        self._center_all_boxes()
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

        # 패딩 기본값: 검증 기준(좌우 각 0.09", 상하 각 0.07") + 여유
        # measure_text가 실제 렌더링보다 ~0.15" 작게 측정되는 경향이 있어 여유 확보
        pad_x = pad_x or 0.40
        pad_y = pad_y or 0.26
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
            # 최솟값: 텍스트 너비 + 최소 패딩(좌우 각 0.09" = 합 0.18")
            MIN_BOX_PAD_H = 0.18
            if excess > 0:
                internal_nodes_list = [nd for row in rows for nd in row]
                pad_reduce_per = excess / max(len(internal_nodes_list), 1)
                for nd in internal_nodes_list:
                    tw, _ = self.measure_text(nd.text, nd.fs)
                    min_w = tw + MIN_BOX_PAD_H
                    nd._w = max(nd._w - pad_reduce_per, min_w)
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

        # Step 2b: 박스 너비 최종 확정 후 — 오버플로우 시 강제 래핑
        # 텍스트가 (박스너비 - 최소패딩)을 초과하면 본문을 균등 2분할
        MIN_PAD_H = 0.18
        for nd in all_nodes:
            body_max_w = nd._w - MIN_PAD_H
            nd.text = _wrap_text_to_width(
                nd.text, body_max_w,
                lambda t, _nd=nd: self.measure_text(t, _nd.fs)[0]
            )
            # 래핑 후 높이 재측정 및 확장
            _, th_new = self.measure_text(nd.text, nd.fs)
            nd._h = max(nd._h, th_new + (nd.pad_y if nd.pad_y else pad_y))

        # 래핑 후 행 내 높이 재통일
        for row in rows:
            if row:
                max_h = max(nd._h for nd in row)
                for nd in row:
                    nd._h = max_h

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
        # 전체 콘텐츠(100점선+gap+60블록) 기준 중앙 정렬
        # 전체 폭 = BND_PAD + internal_row_w + BND_PAD + ext_gap + ext_w
        #           ^^^^^^^^ 점선 내부 왼쪽여백  ^^^^^^^^ 점선 내부 오른쪽여백
        EXT_GAP = BND_PAD + 0.50  # 점선↔ext 간격 (점선 오른쪽 + shaft)

        # ext 너비
        ext_w_total = 0
        if 'right' in external and external['right']:
            ext_w_total = max(nd._w for nd in external['right'])
        elif 'left' in external and external['left']:
            ext_w_total = max(nd._w for nd in external['left'])

        total_content_w = BND_PAD + max_row_w + BND_PAD + EXT_GAP + ext_w_total
        # 전체 콘텐츠를 페이지 boundary 안에서 중앙 정렬
        total_left = content_cx - total_content_w / 2
        # internal 박스 시작 x: total_left + 점선왼쪽여백
        internal_start_x = total_left + BND_PAD

        for ri, row in enumerate(rows):
            row_w = sum(nd._w for nd in row) + BOX_GAP_H * (len(row) - 1)
            # 행 내 중앙 정렬 (internal 영역 기준)
            internal_cx_local = internal_start_x + max_row_w / 2
            start_x = internal_cx_local - row_w / 2
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
                # ext_x: int_right(점선 포함) + 최소 shaft(0.44")
                # 점선 바깥 여백(EXT_BND_GAP) 제거 — 점선과 external 사이는 shaft만으로 충분
                ext_x = int_right + 0.44
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

        # Step 5: 버스 → 박스 단방향 화살표 (버스쪽은 선, 박스쪽에 화살촉)
        # 시작점을 버스선 반대편으로 0.05" 연장 → 버스선과 시각적으로 확실히 연결
        BUS_OVERSHOOT = 0.02
        for ri, row in enumerate(rows):
            for nd in row:
                if nd.box_ref is None:
                    continue
                b = nd.box_ref
                if ri == 0:  # 상단 행: 버스 → 박스 하단 (위로 향하는 화살촉)
                    self._cmds.append(('route', [(b.cx, bus_y - BUS_OVERSHOOT), (b.cx, b.bot)],
                                       '', None, None))
                else:  # 하단 행: 버스 → 박스 상단 (아래로 향하는 화살촉)
                    self._cmds.append(('route', [(b.cx, bus_y + BUS_OVERSHOOT), (b.cx, b.top)],
                                       '', None, None))

        # Step 6: 버스 → external 단방향 화살표 (버스쪽은 선, external 박스쪽에 화살촉)
        for side, ext_nodes in external.items():
            for ext_nd in ext_nodes:
                if ext_nd.box_ref is None:
                    continue
                if side == 'right':
                    # 버스 → external 좌측 (점선 통과 화살표, 버스쪽 overshoot)
                    self._cmds.append(('route', [
                        (int_right - BUS_OVERSHOOT, bus_y),
                        ext_nd.box_ref.left_mid(),
                    ], '', None, None))
                elif side == 'left':
                    self._cmds.append(('route', [
                        (int_left + BUS_OVERSHOOT, bus_y),
                        ext_nd.box_ref.right_mid(),
                    ], '', None, None))

        # Step 7: 페이지 boundary (라벨 없음 — internal에 이미 boundary_label)
        self.boundary(BND_X1, BND_Y1, BND_X2, BND_Y2)
        self._center_all_boxes()
        self.fig_label()

    # ── 요소 추가 ─────────────────────────────────────────────────────────────

    def boundary(self, x1, y1, x2, y2, label="", is_page_boundary=True):
        """페이지 경계 (점선 직사각형). is_page_boundary=True이면 마진 검증 대상."""
        self._cmds.append(('boundary', x1, y1, x2, y2, label, is_page_boundary))

    def layer(self, x1, y1, x2, y2, label="", dash='short'):
        """
        내부 레이어 경계 (점선 박스 + 참조번호).
        dash: 'long'(외곽과 같은 큰 점선), 'short'(짧은 점선, 기본),
              'dotted'(점), 'solid'(실선)
        → 외곽 boundary와 시각적 계층 구분.
        사용: d.layer(0.55, 7.40, 7.95, 10.10, "808 Storage", dash='short')
        """
        # dash 스타일을 label 뒤에 인코딩
        encoded_label = f"{label}|{dash}" if dash != 'long' else label
        self._cmds.append(('boundary', x1, y1, x2, y2, encoded_label, False))

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

    def _center_all_boxes(self):
        """
        공용 중앙 정렬: 모든 배치된 박스의 min_left ~ max_right 기준으로
        페이지 수평 중앙에 오도록 전체 shift.
        모든 레이아웃 타입에서 배치 완료 후 호출.
        """
        if not self._box_refs:
            return
        min_left  = min(b.left for b in self._box_refs)
        max_right = max(b.right for b in self._box_refs)

        # layer boundary (non-page)의 좌우도 콘텐츠 범위에 포함
        for cmd in self._cmds:
            if cmd[0] == 'boundary' and not cmd[6]:  # is_page=False → layer
                min_left  = min(min_left, cmd[1])
                max_right = max(max_right, cmd[3])

        # callout/label 예상 폭 반영 (렌더링 전이라 실측 불가 → 예상치)
        CALLOUT_EST = 0.35  # callout 텍스트 + 물결선 예상 폭
        for cmd in self._cmds:
            if cmd[0] == 'ref_callout':
                _, box, ref_num, side_enc, offset, fs = cmd
                base_side = side_enc.split(':')[0]
                if 'left' in base_side:
                    min_left = min(min_left, box.left - CALLOUT_EST)
                elif 'right' in base_side:
                    max_right = max(max_right, box.right + CALLOUT_EST)
            elif cmd[0] == 'ref_callout_bus':
                _, bus_x, ref_num, side, fs = cmd
                if side == 'right':
                    max_right = max(max_right, bus_x + CALLOUT_EST + 0.30)
                else:
                    min_left = min(min_left, bus_x - CALLOUT_EST - 0.30)
        content_cx = (min_left + max_right) / 2
        page_cx = PAGE_W / 2
        dx = page_cx - content_cx

        if abs(dx) < 0.01:
            return  # 이미 중앙

        # 모든 박스 x 좌표 shift
        for b in self._box_refs:
            b.x += dx

        # 모든 cmd 좌표도 shift (boundary, route, bidir, line, label, fig_label)
        new_cmds = []
        for cmd in self._cmds:
            if cmd[0] == 'boundary':
                _, x1, y1, x2, y2, lbl, is_page = cmd
                if is_page:
                    new_cmds.append(cmd)  # 페이지 boundary는 고정
                else:
                    new_cmds.append(('boundary', x1 + dx, y1, x2 + dx, y2, lbl, is_page))
            elif cmd[0] == 'box':
                new_cmds.append(cmd)  # BoxRef가 이미 shift됨, 렌더링 시 b.x 참조
            elif cmd[0] == 'route':
                _, pts, lbl, lpos, lopt, *rest = cmd
                new_pts = [(x + dx, y) for x, y in pts]
                new_cmds.append(('route', new_pts, lbl, lpos, lopt, *rest))
            elif cmd[0] == 'bidir':
                _, pts = cmd
                new_pts = [(x + dx, y) for x, y in pts]
                new_cmds.append(('bidir', new_pts))
            elif cmd[0] == 'line':
                _, x1, y1, x2, y2, ls = cmd
                new_cmds.append(('line', x1 + dx, y1, x2 + dx, y2, ls))
            elif cmd[0] == 'label':
                _, x, y, text, ha, fs = cmd
                new_cmds.append(('label', x + dx, y, text, ha, fs))
            else:
                new_cmds.append(cmd)
        self._cmds = new_cmds

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
        박스 추가. w/h가 텍스트+패딩보다 작으면 자동 확장.
        단, 자기가 속한 layer(container)보다 커지지 않도록 제한.
        text 형식: "102\\nCPU" (파이프 문자 금지)
        """
        # 텍스트 실측 → w/h가 부족하면 자동 확장
        MIN_PAD_W, MIN_PAD_H = 0.18, 0.14
        tw, th = self.measure_text(text, fs or FS_BODY)
        min_w = tw + MIN_PAD_W
        min_h = th + MIN_PAD_H

        # container(layer) 폭 제한 찾기
        cx_box = x + w / 2
        cy_box = y + h / 2
        max_w_from_layer = 9999
        for cmd in self._cmds:
            if cmd[0] == 'boundary' and not cmd[6]:  # layer
                lx1, ly1, lx2, ly2 = cmd[1], cmd[2], cmd[3], cmd[4]
                if lx1 - 0.1 < cx_box < lx2 + 0.1 and ly1 - 0.1 < cy_box < ly2 + 0.1:
                    max_w_from_layer = min(max_w_from_layer, (lx2 - lx1) - 0.12)

        min_w = min(min_w, max_w_from_layer)

        if w < min_w:
            cx = x + w / 2
            w = min_w
            x = cx - w / 2
        if h < min_h:
            cy = y + h / 2
            h = min_h
            y = cy - h / 2
        b = BoxRef(x, y, w, h)
        self._box_refs.append(b)
        self._cmds.append(('box', b, text, fs))
        return b

    def equalize_heights(self, boxes: list) -> float:
        """
        박스 리스트의 높이를 max로 통일 (중심 y 고정, 상하 대칭 확장).
        수동 layout(box() 직접 사용) 시 높이 균일화에 사용.
        반환값: 통일된 높이.
        사용:
            d.equalize_heights([b1, b2, b3, b4, b5])
        """
        max_h = max(b.h for b in boxes)
        for b in boxes:
            if abs(b.h - max_h) > 0.001:
                cy = b.cy
                b.h = max_h
                b.y = cy - max_h / 2
        return max_h

    def equalize_widths(self, boxes: list) -> float:
        """
        박스 리스트의 너비를 max로 통일 (중심 x 고정, 좌우 대칭 확장).
        반환값: 통일된 너비.
        """
        max_w = max(b.w for b in boxes)
        for b in boxes:
            if abs(b.w - max_w) > 0.001:
                cx = b.cx
                b.w = max_w
                b.x = cx - max_w / 2
        return max_w

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

    def cloud(self, cx, cy, w, h, text="", fs=None) -> BoxRef:
        """
        구름(Cloud) 도형. 원 여러 개를 겹쳐 구름 모양 생성.
        텍스트는 중앙에 표시. BoxRef(cx-w/2, cy-h/2, w, h) 반환.
        사용:
            c = d.cloud(4.0, 5.5, 1.8, 1.2, '310\nCloud')
        """
        b = CloudRef(cx, cy, w, h)   # 타원 기반 edge 계산
        self._box_refs.append(b)
        self._cmds.append(('cloud', cx, cy, w, h, text, fs or FS_BODY, b))
        return b

    # ── 신규 패턴 (learn/new-shapes) ──────────────────────────────────────────

    def database_cylinder(self, cx, cy, w, h, text="", fs=None) -> BoxRef:
        """
        실린더형 DB 도형 (특허 도면 표준 데이터 저장소).
        직사각형 몸체 + 상단/하단 타원으로 구성.
        반환: BoxRef(cx-w/2, cy-h/2, w, h) — box_refs에 등록됨.

        사용:
            db = d.database_cylinder(4.0, 5.5, 1.4, 1.0, '310\nDB')
            d.arrow_v(box, db)
        """
        b = BoxRef(cx - w / 2, cy - h / 2, w, h)
        self._box_refs.append(b)
        self._cmds.append(('database_cylinder', cx, cy, w, h, text, fs or FS_BODY, b))
        return b

    def oval(self, cx, cy, w, h, text="", fs=None) -> BoxRef:
        """
        타원형 프로세서 노드 (터미널/단말/처리 노드).
        특허 도면에서 시작/끝 단말(start/end terminal) 또는 CPU/처리 노드로 사용.
        반환: BoxRef — edge_toward() 등 BoxRef 메서드 사용 가능.

        사용:
            cpu = d.oval(4.0, 6.5, 1.6, 0.7, '200\nCPU')
            d.arrow_diagonal(cpu, db)  # or arrow_v, arrow_h
        """
        b = BoxRef(cx - w / 2, cy - h / 2, w, h)
        self._box_refs.append(b)
        self._cmds.append(('oval', cx, cy, w, h, text, fs or FS_BODY, b))
        return b

    def arrow_wireless(self, box_a: BoxRef, box_b: BoxRef, label="") -> None:
        """
        지그재그 무선 연결선 (wireless communication link).
        두 박스 사이를 지그재그 패턴으로 연결하여 무선 채널을 표현.
        label이 있으면 중간에 표시 (예: "802.11n").
        연결 방향: box_a → box_b (단방향 화살촉).

        사용:
            d.arrow_wireless(ap, device, label='802.11n')
        """
        self._cmds.append(('arrow_wireless', box_a, box_b, label))

    def wireless_signal(self, x, y, direction='right', n_arcs=3, scale=0.25) -> None:
        """
        ))) 동심원 방사 아이콘 — 안테나/무선 신호 방사 표현.
        direction: 'right'(→), 'left'(←), 'up'(↑), 'down'(↓)
        n_arcs: 호 개수 (기본 3)
        scale: 호 크기 단위 (인치, 기본 0.25")

        사용:
            d.wireless_signal(5.0, 7.0, direction='right')   # )))
            d.wireless_signal(3.0, 7.0, direction='left')    # (((
        """
        self._cmds.append(('wireless_signal', x, y, direction, n_arcs, scale))

    def ellipsis_repeat(self, box_a: BoxRef, box_b: BoxRef,
                        label_a="1", label_b="N") -> None:
        """
        A...N 반복 표현 — 두 박스 사이에 '...' 점줄임 + 반복 라벨 표시.
        특허 도면에서 복수 인스턴스(1~N)를 압축 표현할 때 사용.
        label_a: 시작 라벨 (기본 "1"), label_b: 끝 라벨 (기본 "N")

        시각 효과:
            [box_a] ---1--- ... ---N--- [box_b]
            또는 수직 배치 시 점선 연결 + 측면 라벨

        사용:
            d.ellipsis_repeat(node1, nodeN, label_a='1', label_b='N')
        """
        self._cmds.append(('ellipsis_repeat', box_a, box_b, label_a, label_b))

    def arrow_fanout_labeled(self, src: BoxRef,
                              destinations_with_labels: list) -> None:
        """
        라벨 붙은 다중 화살표 (fan-out with labels).
        1개 박스에서 N개 목적지로 각기 다른 라벨로 분기.
        destinations_with_labels: [(dst_box, label), ...]

        T-junction 없이 src 하단을 N등분한 출발점 사용 (split_from_box 방식).

        사용:
            d.arrow_fanout_labeled(router, [
                (client1, 'TCP/IP'),
                (client2, 'UDP'),
                (client3, 'HTTP'),
            ])
        """
        self._cmds.append(('arrow_fanout_labeled', src, destinations_with_labels))

    def autocloud(self, cx, cy, text="", fs=None, pad_x=0.55, pad_y=0.45,
                  max_w=None) -> BoxRef:
        """
        텍스트 크기를 실측 후 cloud w/h 자동 결정.
        구름 내부 유효 공간은 실제 w/h보다 작으므로 pad를 넉넉하게 설정.
        pad_x: 좌우 여백 합계 (기본 0.55" — 구름 곡선 여유)
        pad_y: 상하 여백 합계 (기본 0.45")
        max_w: 최대 구름 너비(인치). 초과 시 텍스트 자동 래핑.
               기본값 None → 페이지 폭(6.5") 기준 자동 제한
        사용:
            c = d.autocloud(4.0, 5.5, '310\nDevice Owner')
            c = d.autocloud(4.0, 5.5, '310\nDevice Owner', max_w=3.0)
        """
        fs = fs or FS_BODY
        text = _normalize_node_text(text)
        # max_w를 구름 내부 유효폭(w*0.65 기준)으로 환산
        if max_w is None:
            max_w = 7.35  # 페이지 기준 최대
        inner_max = max_w * 0.65 - pad_x
        # 텍스트가 내부 폭 초과 시 자동 래핑
        text = _wrap_text_to_width(text, inner_max,
                                   lambda t: self.measure_text(t, fs)[0])
        tw, th = self.measure_text(text, fs)
        w = (tw + pad_x) / 0.65
        h = (th + pad_y) / 0.50
        return self.cloud(cx, cy, w, h, text, fs)

    def iot_stack(self, x, y, w, h, text="", n=3, offset=0.07, fs=None) -> BoxRef:
        """
        IoT 디바이스 스택 — 사각형을 n개 비스듬히 겹쳐서 복수 디바이스 표현.
        x, y: 앞면 박스 좌하단. offset: 뒤 박스 당 이동량(인치).
        반환: 앞면 BoxRef.
        사용:
            s = d.iot_stack(1.0, 5.0, 1.2, 0.7, '314\nIoT', n=3)
        """
        b = BoxRef(x, y, w, h)
        self._box_refs.append(b)
        self._cmds.append(('iot_stack', x, y, w, h, text, n, offset, fs or FS_BODY, b))
        return b

    def ref_callout(self, box: BoxRef, ref_num: str, side='left',
                    offset=0.15, fs=None, style='tilde', strip_ref=False):
        """
        참조번호 외부 배치 callout. 두 가지 스타일 지원.

        style='tilde' (기본): '552~' 텍스트 방식 — 박스/플로우차트에 적합
        style='curve': 곡선 leader line — 원/구름/자유형 도형에 적합
        strip_ref: True면 박스 텍스트에서 참조번호 줄을 자동 제거 (중복 방지)

        side: 'left'(기본), 'right', 'top', 'bottom',
              'top-left', 'top-right', 'bottom-left', 'bottom-right'
        offset: 박스 변에서 참조번호까지 거리 (기본 0.15")

        사용:
            d.ref_callout(b, '552', side='left')                  # 552~ 스타일
            d.ref_callout(b, '910', side='right', style='curve')  # 곡선 스타일
            d.ref_callout(b, '830', side='left', style='curve', strip_ref=True)
        """
        # strip_ref: 박스 내부 텍스트에서 참조번호 줄 제거
        if strip_ref:
            for cmd in self._cmds:
                if cmd[0] == 'box' and cmd[1] is box:
                    old_text = cmd[2]
                    lines = old_text.split('\n')
                    # 첫 줄이 참조번호면 제거
                    if lines and lines[0].strip() == ref_num:
                        new_text = '\n'.join(lines[1:])
                        # cmd는 tuple이므로 리스트로 변환해서 수정
                        idx = self._cmds.index(cmd)
                        self._cmds[idx] = (cmd[0], cmd[1], new_text, cmd[3])
                    break
        # side에 style 인코딩 (렌더러에 전달)
        encoded_side = f"{side}:{style}"
        self._cmds.append(('ref_callout', box, ref_num, encoded_side, offset, fs or FS_BODY))

    def ref_callout_bus(self, bus_x, ref_num, side='right', fs=None):
        """
        버스선(수직 line)에 참조번호 callout 배치.
        버스 위 연결점(박스 cy) 사이 가장 넓은 빈 공간을 자동 탐색.
        빈 공간이 없으면 버스 상단/하단에 배치.

        bus_x: 버스선 x 좌표
        side: 'right'(기본) 또는 'left' — 참조번호 배치 방향
        사용:
            d.ref_callout_bus(BUS_X, '806')
        """
        self._cmds.append(('ref_callout_bus', bus_x, ref_num, side, fs or FS_BODY))

    def _render_ref_callout_bus(self, ax, bus_x, ref_num, side, fs):
        """버스선 빈 공간에 callout 자동 배치."""
        import numpy as np

        # 버스선 위의 모든 연결점(y좌표) 수집
        bus_ys = []
        for cmd in self._cmds:
            if cmd[0] in ('route', 'bidir'):
                pts = cmd[1]
                for px, py in pts:
                    if abs(px - bus_x) < 0.05:
                        bus_ys.append(py)
        bus_ys = sorted(set(bus_ys))

        if len(bus_ys) < 2:
            # 연결점 부족 → 버스선 중앙에 배치
            mid_y = sum(bus_ys) / len(bus_ys) if bus_ys else 5.5
        else:
            # 가장 넓은 gap 찾기
            best_gap = 0
            best_mid = bus_ys[0]
            for i in range(len(bus_ys) - 1):
                gap = bus_ys[i + 1] - bus_ys[i]
                if gap > best_gap:
                    best_gap = gap
                    best_mid = (bus_ys[i] + bus_ys[i + 1]) / 2
            mid_y = best_mid

        # 리더 라인 + 참조번호
        LEADER_LEN = 0.30
        if side == 'right':
            # 버스에서 오른쪽으로 짧은 수평선
            ax.plot([bus_x, bus_x + LEADER_LEN], [mid_y, mid_y],
                    color=BOX_EDGE, lw=LW_BOX * 0.8,
                    solid_capstyle='butt', zorder=Z_FIG_LABEL + 1)
            ax.text(bus_x + LEADER_LEN + 0.05, mid_y, ref_num,
                    ha='left', va='center',
                    fontsize=fs, fontweight=FW, zorder=Z_FIG_LABEL + 2)
        else:
            ax.plot([bus_x - LEADER_LEN, bus_x], [mid_y, mid_y],
                    color=BOX_EDGE, lw=LW_BOX * 0.8,
                    solid_capstyle='butt', zorder=Z_FIG_LABEL + 1)
            ax.text(bus_x - LEADER_LEN - 0.05, mid_y, ref_num,
                    ha='right', va='center',
                    fontsize=fs, fontweight=FW, zorder=Z_FIG_LABEL + 2)

    def brace(self, x1, y1, x2, y2, side='right', label="", fs=None):
        """
        중괄호(brace) — 그룹 범위 표시.
        side: 'right'(우측에 브레이스), 'left', 'top', 'bottom'
        (x1,y1)~(x2,y2): 감싸는 영역 범위.
        사용:
            d.brace(5.5, 6.0, 7.6, 9.5, side='right', label='306')
        """
        self._cmds.append(('brace', x1, y1, x2, y2, side, label, fs or FS_BODY))

    # ── 화살표 ────────────────────────────────────────────────────────────────

    def arrow_v(self, src_box: BoxRef, dst_box: BoxRef, label=""):
        """수직 단방향 화살표. dst 위치에 따라 위/아래 자동 선택 (관통 방지)."""
        if dst_box.cy <= src_box.cy:
            pts = [src_box.bot_mid(), dst_box.top_mid()]
        else:
            pts = [src_box.top_mid(), dst_box.bot_mid()]
        self._cmds.append(('route', pts, label, None, None))

    def arrow_h(self, src_box: BoxRef, dst_box: BoxRef, label=""):
        """수평 단방향 화살표. dst 위치에 따라 좌/우 자동 선택 (관통 방지)."""
        if dst_box.cx >= src_box.cx:
            pts = [src_box.right_mid(), dst_box.left_mid()]
        else:
            pts = [src_box.left_mid(), dst_box.right_mid()]
        self._cmds.append(('route', pts, label, None, None))

    def arrow_bidir(self, box_a: BoxRef, box_b: BoxRef, side='h'):
        """
        양방향 단일 선 (↔ 또는 ↕).
        side='h': 수평, side='v': 수직.
        박스 상대 위치를 자동 감지하여 올바른 edge를 선택 (관통 방지).
        """
        if side == 'h':
            if box_b.cx >= box_a.cx:
                pts = [box_a.right_mid(), box_b.left_mid()]
            else:
                pts = [box_a.left_mid(), box_b.right_mid()]
        else:
            if box_b.cy <= box_a.cy:
                pts = [box_a.bot_mid(), box_b.top_mid()]
            else:
                pts = [box_a.top_mid(), box_b.bot_mid()]
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
        두 박스 사이 직선 대각선 화살표 (단방향: a→b).
        각 박스의 경계 교차점에서 출발/도착.
        사용: d.arrow_diagonal(cloud, iot)
        """
        sx, sy = box_a.edge_toward(box_b.cx, box_b.cy, gap)
        ex, ey = box_b.edge_toward(box_a.cx, box_a.cy, gap)
        self._cmds.append(('route', [(sx, sy), (ex, ey)], '', None, None))

    def arrow_fork_bidir(self, src: BoxRef, destinations: list, via_x: float = None):
        """
        1개 박스에서 N개 목적지로 양방향 fork.
        src 우측 변을 N등분하여 각 출발점에서 독립 양방향 화살표.
        via_x: 중간 꺾임 x 좌표 (기본: src.right + 0.5")

        사용:
            d.arrow_fork_bidir(iface, [sensors, actuators])
            d.arrow_fork_bidir(iface, [sensors, actuators], via_x=5.8)
        """
        n = len(destinations)
        if n == 0:
            return
        if via_x is None:
            via_x = src.right + 0.50

        # src 우측 변을 n등분 (위→아래)
        step = src.h / (n + 1)
        start_ys = [src.top - step * (i + 1) for i in range(n)]

        for i, (dst, sy) in enumerate(zip(destinations, start_ys)):
            src_pt = (src.right, sy)
            dst_pt = dst.left_mid()
            # via_x → dst.cy로 꺾임
            mid_pt = (via_x, dst.cy)
            self._cmds.append(('bidir', [src_pt, (via_x, sy), mid_pt, dst_pt]))

    def arrow_diagonal_bidir(self, box_a: BoxRef, box_b: BoxRef, gap=0.08):
        """
        두 박스 사이 직선 대각선 양방향 화살표 (↔).
        원형/방사형 다이어그램에서 사용.
        사용: d.arrow_diagonal_bidir(cloud, iot)
        """
        sx, sy = box_a.edge_toward(box_b.cx, box_b.cy, gap)
        ex, ey = box_b.edge_toward(box_a.cx, box_a.cy, gap)
        self._cmds.append(('bidir', [(sx, sy), (ex, ey)]))

    def arrow_to_cloud_child(self, external: BoxRef, cloud: 'CloudRef',
                              internal: BoxRef, bidir=True, gap=0.05):
        """
        Cloud 내부 도형과 외부 도형을 연결하는 화살표.
        Cloud를 통과하여 internal 박스까지 직선으로 연결.
        external ↔ internal (cloud 통과)
        bidir=True: 양방향, False: external→internal 단방향
        사용:
            server = d.box(...)   # cloud 내부
            d.arrow_to_cloud_child(iot, cloud, server, bidir=True)
        """
        # 출발점: external에서 internal 방향으로 external edge
        sx, sy = external.edge_toward(internal.cx, internal.cy, gap)
        # 도착점: internal에서 external 방향으로 internal edge (gap 최소)
        ex, ey = internal.edge_toward(external.cx, external.cy, gap)
        if bidir:
            self._cmds.append(('bidir', [(sx, sy), (ex, ey)]))
        else:
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

    # ── 신규 패턴 (v8.0: learn/new-shapes) ────────────────────────────────────

    def sequence_diagram(self, actors: list, messages: list,
                         x_start=0.60, y_top=9.50,
                         actor_spacing=2.20,
                         row_gap=0.75,
                         actor_h=0.50, actor_w=1.60,
                         lifeline_bottom=None,
                         fs=None) -> dict:
        """
        UML-스타일 시퀀스 다이어그램.

        actors  : [{'text': 'BROWSER\\n115', 'ref': 0}, ...]
                  ref = actor index (0-based). ref 생략시 순서대로.
        messages: [{'from': 0, 'to': 1, 'label': 'REQUEST 410a'}, ...]
                  'dashed': True 이면 응답(점선) 스타일.

        반환: {'actors': [BoxRef, ...], 'lifeline_y_bottom': float}

        사용 예:
            actors = [
                {'text': 'BROWSER\\n115'},
                {'text': 'SERVER\\n130'},
                {'text': 'SERVER\\n140'},
            ]
            msgs = [
                {'from': 0, 'to': 1, 'label': 'HTTP REQUEST FOR BID 410a'},
                {'from': 0, 'to': 2, 'label': 'HTTP REQUEST FOR BID 410b'},
                {'from': 1, 'to': 0, 'label': 'HTTP RESPONSE TO BID 430a', 'dashed': True},
                {'from': 2, 'to': 0, 'label': 'HTTP RESPONSE TO BID 430b', 'dashed': True},
            ]
            d.sequence_diagram(actors, msgs)
        """
        fs = fs or FS_BODY
        n = len(actors)
        actor_boxes = []

        # 1. 행위자 박스 배치 (ref 검사 스킵 — actor 이름이 첫 줄)
        for i, actor in enumerate(actors):
            text = actor.get('text', f'Actor {i}')
            x = x_start + i * actor_spacing
            y = y_top - actor_h
            tw, th = self.measure_text(text, fs)
            w = max(actor_w, tw + 0.24)
            b = self.box(x - w/2, y, w, actor_h, text, fs)
            self._no_ref_boxes.add(id(b))
            actor_boxes.append(b)

        # 2. 생명선 길이 결정
        n_msgs = len(messages)
        lifeline_len = (n_msgs + 0.5) * row_gap
        if lifeline_bottom is None:
            lifeline_bottom = y_top - actor_h - lifeline_len

        lifeline_top = y_top - actor_h  # 박스 바닥

        # 3. 각 행위자 생명선 (수직 점선) 등록
        for b in actor_boxes:
            self._cmds.append(('line', b.cx, lifeline_top, b.cx, lifeline_bottom, ':'))

        # 4. 메시지 화살표 배치
        for idx, msg in enumerate(messages):
            fi = msg.get('from', 0)
            ti = msg.get('to', 1)
            lbl = msg.get('label', '')
            is_dashed = msg.get('dashed', False)

            y_msg = lifeline_top - (idx + 1) * row_gap

            sx = actor_boxes[fi].cx
            ex = actor_boxes[ti].cx
            GAP = 0.08  # 생명선 → 화살표 끝 gap

            # 생명선은 line이므로 화살표는 lifeline 위의 점에서 출발
            # dangling 검증 예외 처리: lifeline 위 점이므로 _on_bus_line이 처리
            pts = [(sx, y_msg), (ex, y_msg)]
            ls = '--' if is_dashed else '-'
            self._cmds.append(('route', pts, lbl, 0,
                                (0.12, 'center'), ls))
            # label_ha='center' 처리를 위해 label_pos=0, ldx=0, lha='center' 사용
            # (실제로 _render_route에서 segment 중앙에 label 위치)

        return {'actors': actor_boxes, 'lifeline_y_bottom': lifeline_bottom}

    def swimlane_columns(self, lanes: list, rows: list,
                         connections=None,
                         x_start=0.50, y_top=10.20,
                         lane_w=None, header_h=0.50,
                         row_h=0.65, row_gap=0.95,
                         fs=None) -> dict:
        """
        수직 스윔레인 (Vertical Swimlane) — 역할별 레인 + 프로세스 박스.

        lanes: ['BROWSER\\n115', 'SERVER\\n120', 'SERVERS 130\\nand 140']
        rows:  [
            {'lane': 0, 'text': '310\\nBROWSER REQUESTS\\nWEBPAGE'},
            {'lane': 1, 'text': '320\\nSERVER RECEIVES\\nREQUEST'},
            ...
        ]
        lane_w: 레인 폭 (None이면 자동: 가장 긴 박스 텍스트 기준)

        반환: {'lane_boxes': [BoxRef header...], 'step_boxes': [BoxRef...]}

        사용 예:
            d.swimlane_columns(
                lanes=['BROWSER\\n115', 'SERVER\\n120'],
                rows=[
                    {'lane': 0, 'text': '310\\nBROWSER REQUESTS WEBPAGE'},
                    {'lane': 1, 'text': '320\\nSERVER RECEIVES REQUEST'},
                ]
            )
        """
        fs = fs or FS_BODY
        n_lanes = len(lanes)

        # 자동 레인 폭: 최대 텍스트 폭 기준
        if lane_w is None:
            max_tw = 0
            for r in rows:
                tw, _ = self.measure_text(r.get('text', ''), fs)
                max_tw = max(max_tw, tw)
            for l in lanes:
                tw, _ = self.measure_text(l, fs)
                max_tw = max(max_tw, tw)
            lane_w = max_tw + 0.40
            lane_w = max(lane_w, 1.60)

        total_w = lane_w * n_lanes
        page_cx = x_start + total_w / 2

        # 1. 레인 헤더 박스 (ref 검사 스킵 — lane 이름이 첫 줄)
        header_boxes = []
        for i, lane_text in enumerate(lanes):
            lx = x_start + i * lane_w
            ly = y_top - header_h
            b = self.box(lx, ly, lane_w, header_h, lane_text, fs)
            self._no_ref_boxes.add(id(b))
            header_boxes.append(b)

        # 2. 레인 경계선 (수직선)
        for i in range(n_lanes + 1):
            lx = x_start + i * lane_w
            self._cmds.append(('line', lx, y_top - header_h, lx, y_top - header_h - (len(rows)+1)*(row_h+row_gap), '-'))

        # 3. 단계 박스 배치
        step_boxes = []
        # 3. 박스 배치 — 같은 시점 박스는 같은 y행에 나란히
        # connections에서 연결된 src→dst 쌍을 보고, dst가 이전 행과 같은 y에 올 수 있으면 같은 행
        cur_y = y_top - header_h - row_gap
        ARR_GAP = 0.50  # 행 간 화살표 공간 (반으로 줄임)

        for row in rows:
            li = row.get('lane', 0)
            text = row.get('text', '')
            box_w = lane_w - 0.30
            box_x = x_start + li * lane_w + 0.15
            box_y = cur_y - row_h
            b = self.box(box_x, box_y, box_w, row_h, text, fs)
            step_boxes.append(b)
            cur_y = box_y - ARR_GAP

        # 4. connections 화살표
        if connections:
            for conn in connections:
                src_idx = conn[0]
                dst_idx = conn[1]
                ls = conn[2] if len(conn) > 2 else '-'
                src_box = step_boxes[src_idx]
                dst_box = step_boxes[dst_idx]

                same_lane = abs(src_box.cx - dst_box.cx) < 0.1
                adjacent = abs(src_idx - dst_idx) == 1

                if same_lane and adjacent:
                    # 같은 레인 인접: 수직 화살표
                    self.arrow_v(src_box, dst_box)
                elif same_lane:
                    # 같은 레인 비인접: 수직 (중간 박스 피해서)
                    self.arrow_v(src_box, dst_box)
                else:
                    # 다른 레인: 옆면 수평 연결 (공간 절약)
                    # src와 dst가 같은 y행이면 직접 수평
                    if abs(src_box.cy - dst_box.cy) < row_h:
                        if dst_box.cx > src_box.cx:
                            self.arrow_route([src_box.right_mid(), dst_box.left_mid()], ls=ls)
                        else:
                            self.arrow_route([src_box.left_mid(), dst_box.right_mid()], ls=ls)
                    else:
                        # src 아래 → 중간 y → dst 레인 → dst 위
                        mid_y = dst_box.top + 0.25
                        if dst_box.cx > src_box.cx:
                            self.arrow_route([
                                src_box.bot_mid(),
                                ('down_to', mid_y),
                                ('right_to', dst_box.cx),
                                dst_box.top_mid(),
                            ], ls=ls)
                        else:
                            self.arrow_route([
                                src_box.bot_mid(),
                                ('down_to', mid_y),
                                ('left_to', dst_box.cx),
                                dst_box.top_mid(),
                            ], ls=ls)

        return {'lane_headers': header_boxes, 'step_boxes': step_boxes}

    def horizontal_pipeline_flow(self, stages: list,
                                  x_start=None, cx_start=None, cy=5.50,
                                  stage_gap=0.55,
                                  stage_w=None, stage_h=0.65,
                                  fs=None) -> list:
        """
        수평 파이프라인 플로우 — 스테이지 박스들이 좌→우로 연결.

        stages: ['INPUT\\n100', 'PROCESS\\n200', 'OUTPUT\\n300']
                또는 [{'text': '...', 'w': 1.5}, ...]

        x_start: 첫 박스 left 좌표 (cx_start의 대안 — 마진 계산이 쉬움)
        cx_start: 첫 박스 중심 x (deprecated, x_start 권장)

        반환: [BoxRef, ...] (각 스테이지 박스)

        사용 예:
            d.horizontal_pipeline_flow(
                ['INPUT\\n100', 'EMBEDDING\\n200', 'CLUSTERING\\n300'],
                x_start=0.80, cy=5.5
            )
        """
        fs = fs or FS_BODY
        boxes = []

        # stage 폭 자동 계산 (가장 넓은 텍스트 기준)
        texts = []
        for s in stages:
            if isinstance(s, dict):
                texts.append(s.get('text', ''))
            else:
                texts.append(str(s))

        if stage_w is None:
            max_tw = 0
            for t in texts:
                tw, _ = self.measure_text(t, fs)
                max_tw = max(max_tw, tw)
            stage_w = max_tw + 0.30
            stage_w = max(stage_w, 1.20)

        # x_start 우선, cx_start fallback
        if x_start is not None:
            cur_cx = x_start + stage_w / 2
        elif cx_start is not None:
            cur_cx = cx_start
        else:
            cur_cx = stage_w / 2 + 0.50  # 기본: 페이지 왼쪽 0.5" 여백
        for i, s in enumerate(stages):
            text = texts[i]
            w = stage_w if not isinstance(s, dict) else s.get('w', stage_w)
            x = cur_cx - w / 2
            y = cy - stage_h / 2
            b = self.box(x, y, w, stage_h, text, fs)
            boxes.append(b)
            # 실제 박스 폭(auto-expand 후) 기반: 다음 박스의 cx = b.right + gap + next_w/2
            # next_w는 다음 박스 실제폭을 모르므로 stage_w 사용 (auto-expand로 cx 보정됨)
            cur_cx = b.right + stage_gap + stage_w / 2

        # 화살표 연결: 실제 박스 edge 기반 (stage→stage)
        for i in range(len(boxes) - 1):
            src = boxes[i]
            dst = boxes[i + 1]
            self.arrow_h(src, dst)

        # 마지막 박스는 의도적 terminal (dead-end 경고 스킵)
        if boxes:
            self._terminal_boxes.add(id(boxes[-1]))

        return boxes

    def rounded_rect(self, x, y, w, h, text, fs=None, radius=0.15) -> BoxRef:
        """
        둥근 모서리 사각형 (flowchart terminator / 시작·끝 노드).

        사용:
            start = d.rounded_rect(2.0, 8.5, 2.5, 0.55, 'START\\n100')
            end   = d.rounded_rect(2.0, 1.5, 2.5, 0.55, 'END\\n900')
        """
        fs = fs or FS_BODY
        MIN_PAD_W, MIN_PAD_H = 0.24, 0.14
        tw, th = self.measure_text(text, fs or FS_BODY)
        min_w = tw + MIN_PAD_W
        min_h = th + MIN_PAD_H
        if w < min_w:
            cx = x + w / 2; w = min_w; x = cx - w / 2
        if h < min_h:
            cy = y + h / 2; h = min_h; y = cy - h / 2
        b = BoxRef(x, y, w, h)
        self._box_refs.append(b)
        self._cmds.append(('rounded_rect', b, text, fs, radius))
        return b

    def numbered_sequence_arrows(self, steps: list,
                                  x_start=1.00, y_top=9.00,
                                  x_gap=2.20, y_gap=1.00,
                                  node_r=0.35, fs=None,
                                  direction='TB') -> list:
        """
        번호 매긴 순서 화살표 — 원형 노드 + 순서 번호 + 화살표.

        steps: [
            {'num': '1', 'text': 'FBL\\nFire Hose Bidder', 'ref': ''},
            {'num': '2', 'text': 'INDEX\\nReal-Time DB', 'ref': ''},
            {'num': '3', 'text': 'RG\\nRendering Crawler', 'ref': ''},
        ]

        direction: 'TB' (위→아래) 또는  'LR' (좌→우)

        반환: [BoxRef(oval), ...] 각 노드

        사용 예:
            d.numbered_sequence_arrows(
                steps=[
                    {'num': '1', 'text': 'FBL\\nFire Hose Bidder'},
                    {'num': '2', 'text': 'INDEX\\nReal-Time DB'},
                    {'num': '3', 'text': 'RG\\nRendering Crawler'},
                ],
                direction='TB'
            )
        """
        fs = fs or FS_BODY
        ovals = []

        # 텍스트 기반 oval 크기 자동 결정
        # oval 내부 유효 수평 폭 ≈ oval_width * 0.70 (곡선으로 인한 감소)
        # 따라서 oval_width = (text_width + pad) / 0.70
        OVAL_USABLE_FACTOR = 0.70
        OVAL_PAD_X = 0.20
        OVAL_PAD_Y = 0.18

        for i, step in enumerate(steps):
            num = step.get('num', str(i+1))
            text = step.get('text', f'Step {i+1}')

            if direction == 'TB':
                cx = x_start
                cy = y_top - i * y_gap
            else:  # LR
                cx = x_start + i * x_gap
                cy = y_top

            # 텍스트 실측 기반 oval 크기 결정
            tw, th = self.measure_text(text, fs)
            min_oval_w = (tw + OVAL_PAD_X) / OVAL_USABLE_FACTOR
            min_oval_h = (th + OVAL_PAD_Y) / OVAL_USABLE_FACTOR
            oval_w = max(node_r * 2, min_oval_w)
            oval_h = max(node_r * 2, min_oval_h)
            # 원형 유지 옵션: 긴 쪽으로 통일
            # oval_w = oval_h = max(oval_w, oval_h)  # 원형 강제시

            # oval 노드 생성 (ref 검사 스킵 — 약칭 + 전체명 형식)
            o = self.oval(cx, cy, oval_w, oval_h, text, fs)
            self._no_ref_boxes.add(id(o))
            ovals.append(o)

            # 순서 번호를 oval 외부 왼쪽 상단에 표시
            num_x = cx - node_r - 0.15
            num_y = cy + node_r + 0.05
            self._cmds.append(('label', num_x, num_y, num, 'right', fs))

        # 화살표 연결 (sequential)
        for i in range(len(ovals) - 1):
            src = ovals[i]
            dst = ovals[i + 1]
            if direction == 'TB':
                self.arrow_route([src.bot_mid(), dst.top_mid()])
            else:
                self.arrow_route([src.right_mid(), dst.left_mid()])

        # 마지막 노드는 의도적 terminal (dead-end 경고 스킵)
        if ovals:
            self._terminal_boxes.add(id(ovals[-1]))

        return ovals

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
        DASH_STYLES = {
            'long': '--',           # 외곽 boundary 기본
            'short': (0, (3, 2, 1, 2)),  # 내부 layer (dash-dot, 외곽과 뚜렷히 구분)
            'dotted': ':',          # 점선
            'solid': '-',           # 실선
        }
        for cmd in self._cmds:
            if cmd[0] == 'boundary':
                _, x1, y1, x2, y2, lbl, is_page = cmd
                # layer dash 스타일 파싱 ('label|short' 형식)
                dash_style = '--'
                display_lbl = lbl
                if not is_page and '|' in lbl:
                    parts = lbl.rsplit('|', 1)
                    display_lbl = parts[0]
                    dash_style = DASH_STYLES.get(parts[1], '--')
                ax.add_patch(FancyBboxPatch(
                    (x1, y1), x2-x1, y2-y1,
                    boxstyle="square,pad=0",
                    facecolor='none', edgecolor=BOX_EDGE,
                    linewidth=LW_FRAME, linestyle=dash_style, zorder=Z_BOUNDARY))
                if display_lbl:
                    ax.text(x1+0.12, y2-0.12, display_lbl,
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

        # Pass 2b: cloud / iot_stack / brace / ref_callout / new patterns 렌더링
        import numpy as np
        from matplotlib.patches import Circle, Polygon, FancyArrowPatch
        for cmd in self._cmds:
            if cmd[0] == 'cloud':
                _, cx, cy, w, h, text, fs, b = cmd
                self._render_cloud(ax, cx, cy, w, h, text, fs)
            elif cmd[0] == 'iot_stack':
                _, x, y, w, h, text, n, offset, fs, b = cmd
                self._render_iot_stack(ax, x, y, w, h, text, n, offset, fs)
            elif cmd[0] == 'brace':
                _, x1, y1, x2, y2, side, label, fs = cmd
                self._render_brace(ax, x1, y1, x2, y2, side, label, fs)
            elif cmd[0] == 'ref_callout':
                _, box, ref_num, side, offset, fs = cmd
                self._render_ref_callout(ax, box, ref_num, side, offset, fs)
            elif cmd[0] == 'ref_callout_bus':
                _, bus_x, ref_num, side, fs = cmd
                self._render_ref_callout_bus(ax, bus_x, ref_num, side, fs)
            elif cmd[0] == 'database_cylinder':
                _, cx, cy, w, h, text, fs, b = cmd
                self._render_database_cylinder(ax, cx, cy, w, h, text, fs)
            elif cmd[0] == 'oval':
                _, cx, cy, w, h, text, fs, b = cmd
                self._render_oval(ax, cx, cy, w, h, text, fs)
            elif cmd[0] == 'arrow_wireless':
                _, box_a, box_b, label = cmd
                self._render_arrow_wireless(ax, box_a, box_b, label)
            elif cmd[0] == 'wireless_signal':
                _, x, y, direction, n_arcs, scale = cmd
                self._render_wireless_signal(ax, x, y, direction, n_arcs, scale)
            elif cmd[0] == 'ellipsis_repeat':
                _, box_a, box_b, label_a, label_b = cmd
                self._render_ellipsis_repeat(ax, box_a, box_b, label_a, label_b)
            elif cmd[0] == 'arrow_fanout_labeled':
                _, src, destinations_with_labels = cmd
                self._render_arrow_fanout_labeled(ax, src, destinations_with_labels)
            elif cmd[0] == 'rounded_rect':
                _, b, text, fs_rr, radius = cmd
                self._render_rounded_rect(ax, b, text, fs_rr, radius)

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
                # axes.transData.inverted() 방식으로 정확한 인치 단위 측정
                try:
                    self.fig.canvas.draw()
                    renderer = self.fig.canvas.get_renderer()
                    bb = t_obj.get_window_extent(renderer=renderer)
                    inv = ax.transData.inverted()
                    pt0 = inv.transform((bb.x0, bb.y0))
                    pt1 = inv.transform((bb.x1, bb.y1))
                    tw_data = abs(pt1[0] - pt0[0])
                    th_data = abs(pt1[1] - pt0[1])
                    self._box_text_sizes[id(b)] = (tw_data, th_data)
                except Exception:
                    pass

        # Pass 5: 독립 라벨
        for cmd in self._cmds:
            if cmd[0] == 'label':
                _, x, y, text, ha, fs = cmd
                t_lbl = ax.text(x, y, text, ha=ha, va='center',
                        fontsize=fs, fontweight=FW,
                        bbox=LABEL_BG, zorder=Z_SEC_LABEL)
                # 독립 라벨 실측 크기 저장 (boundary 초과 검증용)
                try:
                    self.fig.canvas.draw()
                    renderer = self.fig.canvas.get_renderer()
                    bb = t_lbl.get_window_extent(renderer=renderer)
                    inv = ax.transData.inverted()
                    pt0 = inv.transform((bb.x0, bb.y0))
                    pt1 = inv.transform((bb.x1, bb.y1))
                    self._label_extents.append({
                        'x0': min(pt0[0], pt1[0]), 'x1': max(pt0[0], pt1[0]),
                        'y0': min(pt0[1], pt1[1]), 'y1': max(pt0[1], pt1[1]),
                        'text': text[:30],
                    })
                except Exception:
                    pass

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

    # ── 신규 도형 렌더 ────────────────────────────────────────────────────────

    def _render_rounded_rect(self, ax, b, text, fs, radius):
        """둥근 모서리 사각형 렌더링."""
        from matplotlib.patches import FancyBboxPatch as FBP
        r = min(radius, b.w / 2 - 0.01, b.h / 2 - 0.01)
        pad = r
        # FancyBboxPatch round style: boxstyle="round,pad=0,rounding_size=r"
        ax.add_patch(FBP(
            (b.x, b.y), b.w, b.h,
            boxstyle=f"round,pad=0,rounding_size={r}",
            facecolor=BOX_FILL, edgecolor=BOX_EDGE,
            linewidth=LW_BOX, zorder=Z_BOX_EDGE))
        fs_fit = self._fit_font(text, b.w - 0.24, b.h - 0.10, fs or FS_BODY)
        ax.text(b.cx, b.cy, text,
                ha='center', va='center',
                fontsize=fs_fit, fontweight=FW,
                multialignment='center', wrap=False,
                zorder=Z_BOX_TEXT)

    def _render_cloud(self, ax, cx, cy, w, h, text, fs):
        """구름 모양 — 타원 둘레에 원 N개 배치 후 바깥쪽 호만 그림.
        타원이 콘텐츠를 감싸고, 원들이 타원 테두리를 구름 모양으로 표현."""
        import numpy as np
        from matplotlib.patches import Circle, Ellipse

        ea = w / 2
        eb = h / 2
        N_BUBBLES = 12
        ellipse_perim = np.pi * (3*(ea+eb) - np.sqrt((3*ea+eb)*(ea+3*eb)))
        bubble_r = ellipse_perim / N_BUBBLES * 0.58

        # 타원 둘레를 호 길이 기준으로 N등분
        angles_all = np.linspace(0, 2*np.pi, 2000, endpoint=False)
        ds = np.sqrt((ea*np.sin(angles_all))**2 + (eb*np.cos(angles_all))**2)
        cumlen = np.cumsum(ds) * (angles_all[1] - angles_all[0])
        targets = np.linspace(0, cumlen[-1], N_BUBBLES, endpoint=False)
        bubble_angles = np.interp(targets, cumlen, angles_all)

        circles = [(cx + ea*np.cos(a), cy + eb*np.sin(a), bubble_r)
                   for a in bubble_angles]

        # Step 1: 흰색 fill
        ax.add_patch(Ellipse((cx, cy), w, h,
                             facecolor=BOX_FILL, edgecolor='none',
                             linewidth=0, zorder=Z_BOX_FILL))
        for bx, by, br in circles:
            ax.add_patch(Circle((bx, by), br,
                                facecolor=BOX_FILL, edgecolor='none',
                                linewidth=0, zorder=Z_BOX_FILL))

        # Step 2: 각 원의 교차점 계산 → 바깥쪽+타원 바깥 호만 그림
        TWO_PI = 2 * np.pi
        for i, (ocx, ocy, orad) in enumerate(circles):
            cut_angles = []
            for j, (ocx2, ocy2, orad2) in enumerate(circles):
                if i == j:
                    continue
                dist = np.hypot(ocx2 - ocx, ocy2 - ocy)
                if dist >= orad + orad2 or dist <= abs(orad - orad2) + 1e-9:
                    continue
                cos_a = np.clip((orad**2 + dist**2 - orad2**2) / (2*orad*dist), -1, 1)
                half = np.arccos(cos_a)
                base = np.arctan2(ocy2 - ocy, ocx2 - ocx)
                cut_angles.append((base - half) % TWO_PI)
                cut_angles.append((base + half) % TWO_PI)

            if not cut_angles:
                a_arr = np.linspace(0, TWO_PI, 120)
                ax.plot(ocx + orad*np.cos(a_arr), ocy + orad*np.sin(a_arr),
                        color=BOX_EDGE, lw=LW_BOX, zorder=Z_BOX_EDGE)
                continue

            cut_angles = sorted(set(cut_angles))
            cut_angles.append(cut_angles[0] + TWO_PI)

            for k in range(len(cut_angles) - 1):
                a0, a1 = cut_angles[k], cut_angles[k+1]
                amid = (a0 + a1) / 2
                mx = ocx + orad * np.cos(amid)
                my = ocy + orad * np.sin(amid)
                # 다른 원 안이면 skip
                if any((mx-ocx2)**2+(my-ocy2)**2 < (orad2*0.999)**2
                       for j,(ocx2,ocy2,orad2) in enumerate(circles) if j!=i):
                    continue
                # 타원 안이면 skip
                if (mx-cx)**2/ea**2 + (my-cy)**2/eb**2 < 0.90**2:
                    continue
                n_pts = max(4, int((a1-a0)/TWO_PI*200))
                a_arr = np.linspace(a0, a1, n_pts)
                ax.plot(ocx + orad*np.cos(a_arr), ocy + orad*np.sin(a_arr),
                        color=BOX_EDGE, lw=LW_BOX,
                        solid_capstyle='butt', zorder=Z_BOX_EDGE)

        # Step 3: 텍스트
        if text:
            fs_use = self._fit_font(text, w * 0.65, h * 0.50, fs)
            ax.text(cx, cy, text,
                    ha='center', va='center',
                    fontsize=fs_use, fontweight=FW,
                    multialignment='center', zorder=Z_BOX_TEXT)

    def _render_iot_stack(self, ax, x, y, w, h, text, n, offset, fs):
        """IoT 스택 — 사각형 n개를 뒤에서 앞으로 비스듬히 겹쳐서 그림."""
        for i in range(n - 1, -1, -1):
            dx = -i * offset
            dy =  i * offset
            zf = Z_BOX_FILL - i
            ze = Z_BOX_EDGE - i
            ax.add_patch(FancyBboxPatch(
                (x + dx, y + dy), w, h, boxstyle="square,pad=0",
                facecolor=BOX_FILL, edgecolor=BOX_EDGE,
                linewidth=LW_BOX, zorder=zf))
        # 앞면 텍스트
        if text:
            fs_use = self._fit_font(text, w - 0.18, h - 0.10, fs)
            ax.text(x + w/2, y + h/2, text,
                    ha='center', va='center',
                    fontsize=fs_use, fontweight=FW,
                    multialignment='center', zorder=Z_BOX_TEXT)

    def _render_ref_callout(self, ax, box, ref_num, side, offset, fs):
        """USPTO callout — 참조번호 텍스트 + 물결선(sine) 직접 그리기.
        tilde 문자 미사용 → 텍스트 끝에서 박스 변까지 물결선을 정확히 그림.
        offset 파라미터는 참조번호와 박스 사이 최소 갭(기본 0.08").
        style은 side에 ':curve' 또는 ':tilde' 인코딩 (기본 tilde → 물결선)."""
        import numpy as np

        parts = side.split(':')
        base_side = parts[0]
        style = parts[1] if len(parts) > 1 else 'tilde'
        
        MIN_GAP = 0.08  # 참조번호 텍스트와 박스 변 사이 최소 갭

        # ── 공통: 박스 변 좌표 + 텍스트 위치 계산 ────────────────────────────
        if base_side in ('left', 'top-left', 'bottom-left'):
            edge_x = box.left
            anc_y = box.cy if base_side == 'left' else (box.top - box.h*0.25 if 'top' in base_side else box.bot + box.h*0.25)
            txt_ha, txt_va = 'right', 'center'
            wave_dir = 'h'  # 수평 물결
        elif base_side in ('right', 'top-right', 'bottom-right'):
            edge_x = box.right
            anc_y = box.cy if base_side == 'right' else (box.top - box.h*0.25 if 'top' in base_side else box.bot + box.h*0.25)
            txt_ha, txt_va = 'left', 'center'
            wave_dir = 'h'
        elif base_side == 'top':
            edge_y = box.top
            anc_x = box.left + box.w * 0.3
            txt_ha, txt_va = 'center', 'bottom'
            wave_dir = 'v'
        else:  # bottom
            edge_y = box.bot
            anc_x = box.left + box.w * 0.3
            txt_ha, txt_va = 'center', 'top'
            wave_dir = 'v'

        if style == 'curve':
            # ── Curve 스타일 (기존 베지에) ────────────────────────────────────
            if wave_dir == 'h':
                anc = np.array([edge_x, anc_y])
                normal = np.array([-1.0, 0.0]) if 'left' in base_side else np.array([1.0, 0.0])
                txt_x = edge_x + normal[0] * (offset * 2.5)
                txt_y = anc_y + offset * 1.4
            else:
                anc = np.array([anc_x, edge_y])
                normal = np.array([0.0, 1.0]) if base_side == 'top' else np.array([0.0, -1.0])
                txt_x = anc_x
                txt_y = edge_y + normal[1] * (offset * 2.5)

            p3 = np.array([txt_x, txt_y])
            ctrl_len = max(np.linalg.norm(p3 - anc) * 0.70, 0.35)
            p1 = anc + normal * ctrl_len
            p2 = p3 - normal * ctrl_len * 0.4

            t_vals = np.linspace(0, 1, 40)
            bx = (1-t_vals)**3*anc[0] + 3*(1-t_vals)**2*t_vals*p1[0] + 3*(1-t_vals)*t_vals**2*p2[0] + t_vals**3*p3[0]
            by = (1-t_vals)**3*anc[1] + 3*(1-t_vals)**2*t_vals*p1[1] + 3*(1-t_vals)*t_vals**2*p2[1] + t_vals**3*p3[1]
            ax.plot(bx, by, color=BOX_EDGE, lw=LW_BOX*0.8,
                    solid_capstyle='round', zorder=Z_FIG_LABEL + 1)

            t_obj = ax.text(txt_x, txt_y, ref_num,
                            ha=txt_ha if wave_dir == 'h' else 'right',
                            va=txt_va if wave_dir == 'h' else ('bottom' if base_side == 'top' else 'top'),
                            fontsize=fs, fontweight=FW, zorder=Z_FIG_LABEL + 2)

        else:
            # ── Tilde 스타일 → 물결선 직접 그리기 ─────────────────────────────
            # 1. 참조번호 텍스트를 임시 렌더 → 실측
            if wave_dir == 'h':
                # 좌측: 텍스트 right edge → 박스 left edge 사이 물결선
                # 우측: 박스 right edge → 텍스트 left edge 사이 물결선
                if 'left' in base_side:
                    # 텍스트를 박스 왼쪽에 배치 (ha='right', x는 나중에 조정)
                    tmp_x = edge_x - MIN_GAP * 3  # 임시 위치
                    t_obj = ax.text(tmp_x, anc_y, ref_num,
                                    ha='right', va='center',
                                    fontsize=fs, fontweight=FW, zorder=Z_FIG_LABEL + 2)
                    self.fig.canvas.draw()
                    renderer = self.fig.canvas.get_renderer()
                    bb = t_obj.get_window_extent(renderer=renderer)
                    inv = ax.transData.inverted()
                    pt0 = inv.transform((bb.x0, bb.y0))
                    pt1 = inv.transform((bb.x1, bb.y1))
                    txt_w = abs(pt1[0] - pt0[0])
                    # 실측 텍스트 right edge에서 박스 left edge까지 물결선
                    txt_right = max(pt0[0], pt1[0])
                    # 텍스트를 최종 위치로: right edge + gap + wave = edge_x
                    WAVE_LEN = max(edge_x - txt_right - MIN_GAP, 0.10)
                    final_x = edge_x - WAVE_LEN - MIN_GAP
                    t_obj.set_position((final_x, anc_y))
                    # 재측정
                    self.fig.canvas.draw()
                    bb2 = t_obj.get_window_extent(renderer=renderer)
                    pt0b = inv.transform((bb2.x0, bb2.y0))
                    pt1b = inv.transform((bb2.x1, bb2.y1))
                    wave_start_x = max(pt0b[0], pt1b[0]) + 0.02  # 텍스트 실제 right + 약간
                    wave_end_x = edge_x
                else:
                    tmp_x = edge_x + MIN_GAP * 3
                    t_obj = ax.text(tmp_x, anc_y, ref_num,
                                    ha='left', va='center',
                                    fontsize=fs, fontweight=FW, zorder=Z_FIG_LABEL + 2)
                    self.fig.canvas.draw()
                    renderer = self.fig.canvas.get_renderer()
                    bb = t_obj.get_window_extent(renderer=renderer)
                    inv = ax.transData.inverted()
                    pt0 = inv.transform((bb.x0, bb.y0))
                    pt1 = inv.transform((bb.x1, bb.y1))
                    txt_w = abs(pt1[0] - pt0[0])
                    WAVE_LEN = 0.12
                    final_x = edge_x + MIN_GAP + WAVE_LEN
                    t_obj.set_position((final_x, anc_y))
                    wave_start_x = edge_x
                    wave_end_x = final_x - txt_w * 0.02

                # 거리에 따라 자동 스타일: 짧으면 곡선, 길면 sine
                wave_len = abs(wave_end_x - wave_start_x)
                n_pts = 30
                wx = np.linspace(wave_start_x, wave_end_x, n_pts)
                # 진폭: 거리에 비례 (짧으면 거의 직선, 길면 물결)
                wave_amp = min(wave_len * 0.15, 0.03)  # 최대 0.03"
                if wave_len < 0.15:
                    # 매우 짧은: 직선에 가까운 미세 곡선
                    wy = anc_y + wave_amp * np.sin(np.pi * np.linspace(0, 1, n_pts))
                elif wave_len < 0.25:
                    # 짧은: S자 곡선 1사이클
                    wy = anc_y + wave_amp * np.sin(2 * np.pi * np.linspace(0, 1, n_pts))
                else:
                    # 긴: sine wave 다중 사이클
                    n_cycles = max(2, int(wave_len / 0.10))
                    wy = anc_y + wave_amp * np.sin(n_cycles * 2 * np.pi * np.linspace(0, 1, n_pts))
                ax.plot(wx, wy, color=BOX_EDGE, lw=LW_BOX * 0.7,
                        solid_capstyle='round', zorder=Z_FIG_LABEL + 1)

            else:
                # 수직 물결 (top/bottom) — 간단 구현
                if base_side == 'top':
                    t_obj = ax.text(anc_x, edge_y + MIN_GAP + 0.12, ref_num,
                                    ha='center', va='bottom',
                                    fontsize=fs, fontweight=FW, zorder=Z_FIG_LABEL + 2)
                    wy = np.linspace(edge_y, edge_y + MIN_GAP + 0.10, 30)
                    wave_amp = 0.03
                    wx = anc_x + wave_amp * np.sin(2 * 2 * np.pi * np.linspace(0, 1, 30))
                    ax.plot(wx, wy, color=BOX_EDGE, lw=LW_BOX * 0.7,
                            solid_capstyle='round', zorder=Z_FIG_LABEL + 1)
                else:
                    t_obj = ax.text(anc_x, edge_y - MIN_GAP - 0.12, ref_num,
                                    ha='center', va='top',
                                    fontsize=fs, fontweight=FW, zorder=Z_FIG_LABEL + 2)
                    wy = np.linspace(edge_y - MIN_GAP - 0.10, edge_y, 30)
                    wave_amp = 0.03
                    wx = anc_x + wave_amp * np.sin(2 * 2 * np.pi * np.linspace(0, 1, 30))
                    ax.plot(wx, wy, color=BOX_EDGE, lw=LW_BOX * 0.7,
                            solid_capstyle='round', zorder=Z_FIG_LABEL + 1)

        # 겹침 감지 + boundary 검증용 실측 등록
        try:
            self.fig.canvas.draw()
            renderer = self.fig.canvas.get_renderer()
            bb = t_obj.get_window_extent(renderer=renderer)
            inv = ax.transData.inverted()
            pt0 = inv.transform((bb.x0, bb.y0))
            pt1 = inv.transform((bb.x1, bb.y1))
            new_ext = {
                'x0': min(pt0[0], pt1[0]), 'x1': max(pt0[0], pt1[0]),
                'y0': min(pt0[1], pt1[1]), 'y1': max(pt0[1], pt1[1]),
                'text': ref_num,
            }
            for ex in self._label_extents:
                if (new_ext['x0'] < ex['x1'] + 0.05 and new_ext['x1'] > ex['x0'] - 0.05 and
                    new_ext['y0'] < ex['y1'] + 0.03 and new_ext['y1'] > ex['y0'] - 0.03):
                    shift = ex['y0'] - new_ext['y1'] - 0.06
                    pos = t_obj.get_position()
                    t_obj.set_position((pos[0], pos[1] + shift))
                    self.fig.canvas.draw()
                    bb2 = t_obj.get_window_extent(renderer=renderer)
                    pt0 = inv.transform((bb2.x0, bb2.y0))
                    pt1 = inv.transform((bb2.x1, bb2.y1))
                    new_ext = {
                        'x0': min(pt0[0], pt1[0]), 'x1': max(pt0[0], pt1[0]),
                        'y0': min(pt0[1], pt1[1]), 'y1': max(pt0[1], pt1[1]),
                        'text': ref_num,
                    }
                    break
            self._label_extents.append(new_ext)
        except Exception:
            pass

    def _render_brace(self, ax, x1, y1, x2, y2, side, label, fs):
        """중괄호 — matplotlib path로 그림."""
        import numpy as np
        from matplotlib.path import Path
        import matplotlib.patches as mpatches

        if side == 'right':
            bx = x2 + 0.15   # 브레이스 x
            mid_y = (y1 + y2) / 2
            tip_x = bx + 0.20
            # 상단 반 + 하단 반
            verts = [
                (bx, y2),
                (bx, mid_y + 0.10),
                (tip_x, mid_y),
                (bx, mid_y - 0.10),
                (bx, y1),
            ]
            codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3, Path.CURVE3, Path.LINETO]
            # 실제로는 두 곡선 분리
            ax.plot([bx, bx], [y1, y2], color=BOX_EDGE, lw=LW_BOX, zorder=Z_ARROW)
            ax.plot([bx, tip_x, bx], [(y1+y2)/2 + (y2-y1)*0.25,
                                       mid_y,
                                       (y1+y2)/2 - (y2-y1)*0.25],
                    color=BOX_EDGE, lw=LW_BOX, zorder=Z_ARROW)
            # 상단/하단 수평 돌출
            for yy in [y1, y2]:
                ax.plot([bx - 0.10, bx], [yy, yy],
                        color=BOX_EDGE, lw=LW_BOX, zorder=Z_ARROW)
            # 라벨
            if label:
                ax.text(tip_x + 0.08, mid_y, label,
                        ha='left', va='center',
                        fontsize=fs, fontweight=FW, zorder=Z_SEC_LABEL)
        elif side == 'bottom':
            by = y1 - 0.15
            mid_x = (x1 + x2) / 2
            tip_y = by - 0.20
            ax.plot([x1, x2], [by, by], color=BOX_EDGE, lw=LW_BOX, zorder=Z_ARROW)
            ax.plot([mid_x - (x2-x1)*0.25, mid_x, mid_x + (x2-x1)*0.25],
                    [by, tip_y, by],
                    color=BOX_EDGE, lw=LW_BOX, zorder=Z_ARROW)
            for xx in [x1, x2]:
                ax.plot([xx, xx], [by, by + 0.10],
                        color=BOX_EDGE, lw=LW_BOX, zorder=Z_ARROW)
            if label:
                ax.text(mid_x, tip_y - 0.08, label,
                        ha='center', va='top',
                        fontsize=fs, fontweight=FW, zorder=Z_SEC_LABEL)

    # ── 신규 패턴 렌더 (learn/new-shapes) ────────────────────────────────────

    def _render_database_cylinder(self, ax, cx, cy, w, h, text, fs):
        """실린더형 DB 도형 렌더링.
        구조: 상단 타원 + 직사각형 몸체 + 하단 타원 (반쪽만 visible).
        """
        import numpy as np
        ry = h * 0.15   # 타원 세로 반축 (전체 높이의 15%)
        rx = w / 2

        body_top    = cy + h / 2 - ry
        body_bottom = cy - h / 2 + ry

        # ① 직사각형 몸체 (흰 fill → border)
        ax.fill([cx-rx, cx+rx, cx+rx, cx-rx],
                [body_bottom, body_bottom, body_top, body_top],
                color=BOX_FILL, zorder=Z_BOX_FILL)
        ax.plot([cx-rx, cx-rx], [body_bottom, body_top],
                color=BOX_EDGE, lw=LW_BOX, zorder=Z_BOX_EDGE)
        ax.plot([cx+rx, cx+rx], [body_bottom, body_top],
                color=BOX_EDGE, lw=LW_BOX, zorder=Z_BOX_EDGE)

        # ② 상단 타원 (완전 타원)
        theta = np.linspace(0, 2*np.pi, 100)
        ex = cx + rx * np.cos(theta)
        ey = body_top + ry * np.sin(theta)
        ax.fill(ex, ey, color=BOX_FILL, zorder=Z_BOX_FILL + 1)
        ax.plot(ex, ey, color=BOX_EDGE, lw=LW_BOX, zorder=Z_BOX_EDGE + 1)

        # ③ 하단 타원 — 아랫쪽 반호만 표시 (반원 arc, 위쪽은 몸체로 가려짐)
        theta_bot = np.linspace(np.pi, 2*np.pi, 60)
        bex = cx + rx * np.cos(theta_bot)
        bey = body_bottom + ry * np.sin(theta_bot)
        ax.plot(bex, bey, color=BOX_EDGE, lw=LW_BOX, zorder=Z_BOX_EDGE)

        # ④ 텍스트 (몸체 중앙)
        if text:
            text_cy = (body_top + body_bottom) / 2
            fs_use = self._fit_font(text, w - 0.18, (body_top - body_bottom) - 0.10, fs)
            ax.text(cx, text_cy, text,
                    ha='center', va='center',
                    fontsize=fs_use, fontweight=FW,
                    multialignment='center', zorder=Z_BOX_TEXT)

    def _render_oval(self, ax, cx, cy, w, h, text, fs):
        """타원형 프로세서 노드 렌더링 (matplotlib Ellipse 패치)."""
        from matplotlib.patches import Ellipse
        # 흰 fill
        ax.add_patch(Ellipse((cx, cy), w, h,
                             facecolor=BOX_FILL, edgecolor='none',
                             linewidth=0, zorder=Z_BOX_FILL))
        # 테두리
        ax.add_patch(Ellipse((cx, cy), w, h,
                             facecolor='none', edgecolor=BOX_EDGE,
                             linewidth=LW_BOX, zorder=Z_BOX_EDGE))
        # 텍스트 (내접 사각형 기준 90% 폭)
        if text:
            fs_use = self._fit_font(text, w * 0.80, h * 0.70, fs)
            ax.text(cx, cy, text,
                    ha='center', va='center',
                    fontsize=fs_use, fontweight=FW,
                    multialignment='center', zorder=Z_BOX_TEXT)

    def _render_arrow_wireless(self, ax, box_a: BoxRef, box_b: BoxRef, label: str):
        """지그재그 무선 연결선 렌더링.
        직선 경로 위에 지그재그(sinusoidal) 패턴을 겹쳐서 무선 채널 표현.
        마지막 세그먼트에 화살촉 추가.
        """
        import numpy as np

        # 두 박스의 가장 가까운 edge 좌표 계산
        # box_a → box_b 방향으로 edge 선택
        if abs(box_a.cx - box_b.cx) > abs(box_a.cy - box_b.cy):
            # 수평 주도
            if box_b.cx > box_a.cx:
                sx, sy = box_a.right_mid()
                ex, ey = box_b.left_mid()
            else:
                sx, sy = box_a.left_mid()
                ex, ey = box_b.right_mid()
        else:
            # 수직 주도
            if box_b.cy < box_a.cy:
                sx, sy = box_a.bot_mid()
                ex, ey = box_b.top_mid()
            else:
                sx, sy = box_a.top_mid()
                ex, ey = box_b.bot_mid()

        # 경로 벡터
        dx = ex - sx
        dy = ey - sy
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1e-6:
            return
        ux, uy = dx / length, dy / length        # 단위 벡터 (경로 방향)
        nx, ny = -uy, ux                          # 법선 벡터 (지그재그 방향)

        # 지그재그 파라미터
        n_pts = 80
        t = np.linspace(0, 1, n_pts)
        # 양 끝 10% 구간은 직선, 중간은 지그재그
        amp_envelope = np.clip(np.minimum(t, 1.0 - t) / 0.10, 0.0, 1.0)
        ZIG_FREQ = 8      # 지그재그 주파수 (왕복 횟수)
        ZIG_AMP  = 0.06   # 지그재그 진폭 (인치)
        zz = ZIG_AMP * amp_envelope * np.sign(np.sin(ZIG_FREQ * 2 * np.pi * t))

        wx = sx + t * dx + zz * nx
        wy = sy + t * dy + zz * ny

        # 지그재그 선 그리기
        ax.plot(wx, wy, color=BOX_EDGE, lw=LW_ARR,
                solid_capstyle='round', zorder=Z_ARROW)

        # 화살촉 (끝점 방향으로)
        ax.annotate('', xy=(ex, ey), xytext=(wx[-5], wy[-5]),
                    arrowprops=dict(arrowstyle='->', color=BOX_EDGE,
                                   lw=LW_ARR, mutation_scale=12),
                    zorder=Z_ARROWHEAD)

        # 라벨 (경로 중앙, 법선 방향으로 0.15" 오프셋)
        if label:
            mid = n_pts // 2
            mx, my = wx[mid], wy[mid]
            ax.text(mx + nx * 0.15, my + ny * 0.15, label,
                    ha='center', va='center',
                    fontsize=FS_BODY, fontweight=FW,
                    bbox=LABEL_BG, zorder=Z_ARR_LABEL)

    def _render_wireless_signal(self, ax, x, y, direction, n_arcs, scale):
        """))) 동심원 방사 아이콘 렌더링.
        direction: 'right'→))) , 'left'→((( , 'up'→^^^ , 'down'→vvv
        """
        import numpy as np
        # 방향별 호 각도 범위 (시작, 끝)
        DIR_ANGLES = {
            'right': (-60,  60),
            'left':  (120, 240),
            'up':    ( 30, 150),
            'down':  (210, 330),
        }
        a_start, a_end = DIR_ANGLES.get(direction, (-60, 60))
        theta = np.linspace(np.radians(a_start), np.radians(a_end), 60)

        for i in range(1, n_arcs + 1):
            r = scale * i
            ax.plot(x + r * np.cos(theta),
                    y + r * np.sin(theta),
                    color=BOX_EDGE, lw=LW_ARR * 0.9,
                    solid_capstyle='round', zorder=Z_ARROW)

    def _render_ellipsis_repeat(self, ax, box_a: BoxRef, box_b: BoxRef,
                                 label_a: str, label_b: str):
        """A...N 반복 표현 렌더링.
        두 박스 중간에 '...' 텍스트와 라벨을 배치.
        박스 간 연결은 점선으로 표현.
        """
        import numpy as np

        # 두 박스의 가장 가까운 edge 사이 중간점 계산
        if abs(box_a.cx - box_b.cx) > abs(box_a.cy - box_b.cy):
            # 수평 배치
            if box_b.cx > box_a.cx:
                sx, sy = box_a.right_mid()
                ex, ey = box_b.left_mid()
            else:
                sx, sy = box_a.left_mid()
                ex, ey = box_b.right_mid()
            is_horiz = True
        else:
            # 수직 배치
            if box_b.cy < box_a.cy:
                sx, sy = box_a.bot_mid()
                ex, ey = box_b.top_mid()
            else:
                sx, sy = box_a.top_mid()
                ex, ey = box_b.bot_mid()
            is_horiz = False

        mx = (sx + ex) / 2
        my = (sy + ey) / 2

        # 점선 연결 (박스 a→중간 절반, 중간→박스 b 절반)
        GAP = 0.15  # '...' 텍스트 양쪽 여백
        if is_horiz:
            ax.plot([sx, mx - GAP], [sy, my], color=BOX_EDGE, lw=LW_ARR,
                    linestyle='--', solid_capstyle='butt', zorder=Z_ARROW)
            ax.plot([mx + GAP, ex], [my, ey], color=BOX_EDGE, lw=LW_ARR,
                    linestyle='--', solid_capstyle='butt', zorder=Z_ARROW)
            # '...' 텍스트
            ax.text(mx, my, '...', ha='center', va='center',
                    fontsize=FS_BODY + 2, fontweight='bold', zorder=Z_ARR_LABEL)
            # 라벨 위쪽에 표시
            ax.text(sx + (mx-sx)*0.3, sy + 0.15, label_a,
                    ha='center', va='bottom',
                    fontsize=FS_BODY, fontweight=FW,
                    bbox=LABEL_BG, zorder=Z_ARR_LABEL)
            ax.text(ex - (ex-mx)*0.3, ey + 0.15, label_b,
                    ha='center', va='bottom',
                    fontsize=FS_BODY, fontweight=FW,
                    bbox=LABEL_BG, zorder=Z_ARR_LABEL)
        else:
            ax.plot([sx, mx], [sy, my - GAP], color=BOX_EDGE, lw=LW_ARR,
                    linestyle='--', solid_capstyle='butt', zorder=Z_ARROW)
            ax.plot([mx, ex], [my + GAP, ey], color=BOX_EDGE, lw=LW_ARR,
                    linestyle='--', solid_capstyle='butt', zorder=Z_ARROW)
            ax.text(mx, my, '...', ha='center', va='center',
                    fontsize=FS_BODY + 2, fontweight='bold', zorder=Z_ARR_LABEL)
            ax.text(sx + 0.18, (sy + my) / 2, label_a,
                    ha='left', va='center',
                    fontsize=FS_BODY, fontweight=FW,
                    bbox=LABEL_BG, zorder=Z_ARR_LABEL)
            ax.text(ex + 0.18, (my + ey) / 2, label_b,
                    ha='left', va='center',
                    fontsize=FS_BODY, fontweight=FW,
                    bbox=LABEL_BG, zorder=Z_ARR_LABEL)

    def _render_arrow_fanout_labeled(self, ax, src: BoxRef,
                                      destinations_with_labels: list):
        """라벨 붙은 다중 화살표 렌더링.
        src 하단을 N등분 → 각 목적지까지 꺾인 화살표 + 라벨.
        """
        n = len(destinations_with_labels)
        if n == 0:
            return

        # src 하단 N+1 등분점 계산 (T-junction 방지)
        step = src.w / (n + 1)
        start_xs = [src.left + step * (i + 1) for i in range(n)]

        # via_y: 모든 목적지 top 중 최대 + 0.20"
        all_tops = [dst.top for dst, _ in destinations_with_labels]
        via_y = max(all_tops) + 0.20

        for i, ((dst, lbl), sx) in enumerate(zip(destinations_with_labels, start_xs)):
            src_pt = (sx, src.bot)
            dst_pt = dst.top_mid()

            if abs(sx - dst.cx) < 0.01:
                # 수직 직선
                pts = [src_pt, dst_pt]
            else:
                pts = [src_pt, (sx, via_y), (dst.cx, via_y), dst_pt]

            # 경로 렌더링
            for k in range(len(pts) - 2):
                ax.plot([pts[k][0], pts[k+1][0]],
                        [pts[k][1], pts[k+1][1]],
                        color=BOX_EDGE, lw=LW_ARR,
                        solid_capstyle='butt', zorder=Z_ARROW)
            # 마지막 세그먼트 → 화살촉
            ax.annotate('', xy=pts[-1], xytext=pts[-2],
                        arrowprops=dict(arrowstyle='->', color=BOX_EDGE,
                                       lw=LW_ARR, mutation_scale=12),
                        zorder=Z_ARROWHEAD)

            # 라벨: via_y 아래 수직 구간 (또는 수평 구간)에 배치
            if lbl and len(pts) >= 3:
                # 수평 구간(via_y 구간) 중간에 배치
                seg_mx = (pts[1][0] + pts[2][0]) / 2 if len(pts) >= 4 else pts[-1][0]
                ax.text(seg_mx, via_y + 0.10, lbl,
                        ha='center', va='bottom',
                        fontsize=FS_BODY, fontweight=FW,
                        bbox=LABEL_BG, zorder=Z_ARR_LABEL)

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
        MARGIN_EPS = 0.005  # 부동소수점 오차 허용치
        if bnd_rect:
            bx1, by1, bx2, by2 = bnd_rect
            PAD = self.MIN_BND_PAD
            for cmd in self._cmds:
                if cmd[0] == 'box':
                    _, b, text, _ = cmd
                    short = text[:30].replace('\n', ' ')
                    if b.left - bx1 < PAD - MARGIN_EPS and b.left >= bx1 - 0.05:
                        issues.append(f'Box "{short}": left margin {b.left-bx1:.2f}" < {PAD}" min')
                    if bx2 - b.right < PAD - MARGIN_EPS and b.right <= bx2 + 0.05:
                        issues.append(f'Box "{short}": right margin {bx2-b.right:.2f}" < {PAD}" min')
                    if b.bot - by1 < PAD - MARGIN_EPS and b.bot >= by1 - 0.05:
                        issues.append(f'Box "{short}": bottom margin {b.bot-by1:.2f}" < {PAD}" min')
                    if by2 - b.top < PAD - MARGIN_EPS and b.top <= by2 + 0.05:
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
                if id(b) in self._no_ref_boxes:
                    continue  # 시퀀스 다이어그램 행위자 등 ref 불필요 박스
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

        # 버스선(line) 구간 수집 — bus 패턴에서 화살표 출발점이 버스선 위에 있는 건 정상
        line_segs = []
        for cmd in self._cmds:
            if cmd[0] == 'line':
                _, lx1, ly1, lx2, ly2, _ = cmd
                line_segs.append((lx1, ly1, lx2, ly2))

        def _near_box_edge(px, py):
            for (bx_l, bx_b, bx_r, bx_t) in box_rects:
                on_left   = abs(px - bx_l) < EDGE_TOL and bx_b - EDGE_TOL <= py <= bx_t + EDGE_TOL
                on_right  = abs(px - bx_r) < EDGE_TOL and bx_b - EDGE_TOL <= py <= bx_t + EDGE_TOL
                on_top    = abs(py - bx_t) < EDGE_TOL and bx_l - EDGE_TOL <= px <= bx_r + EDGE_TOL
                on_bottom = abs(py - bx_b) < EDGE_TOL and bx_l - EDGE_TOL <= px <= bx_r + EDGE_TOL
                if on_left or on_right or on_top or on_bottom:
                    return True
            return False

        def _on_bus_line(px, py):
            """버스선(수평/수직 라인) 위에 있는 점인지 확인 — bus 패턴 예외 처리."""
            for (lx1, ly1, lx2, ly2) in line_segs:
                if abs(ly1 - ly2) < 0.01:  # 수평선
                    if abs(py - ly1) < EDGE_TOL and min(lx1, lx2) - EDGE_TOL <= px <= max(lx1, lx2) + EDGE_TOL:
                        return True
                elif abs(lx1 - lx2) < 0.01:  # 수직선
                    if abs(px - lx1) < EDGE_TOL and min(ly1, ly2) - EDGE_TOL <= py <= max(ly1, ly2) + EDGE_TOL:
                        return True
            return False

        # CloudRef 목록 (확장 타원 edge 허용)
        cloud_refs = [b for b in self._box_refs if isinstance(b, CloudRef)]

        def _on_cloud_edge(px, py):
            """CloudRef의 확장 타원(ea+bubble_r) 위에 있는 점인지 확인."""
            for cr in cloud_refs:
                dx, dy = px - cr.cx, py - cr.cy
                # 확장 타원 위 ± EDGE_TOL
                val = (dx / cr._ea)**2 + (dy / cr._eb)**2
                if 0.70 <= val <= 1.60:   # 타원 근방 (여유있게)
                    return True
            return False

        for cmd in self._cmds:
            if cmd[0] in ('route', 'bidir'):
                pts = cmd[1]
                if len(pts) >= 2:
                    src, dst = pts[0], pts[-1]
                    if not _near_box_edge(src[0], src[1]) and not _on_bus_line(src[0], src[1]) and not _on_cloud_edge(src[0], src[1]):
                        issues.append(
                            f'Arrow src ({src[0]:.2f},{src[1]:.2f}) NOT on any box edge. '
                            f'Dangling tail.')
                    if not _near_box_edge(dst[0], dst[1]) and not _on_bus_line(dst[0], dst[1]) and not _on_cloud_edge(dst[0], dst[1]):
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

        # 3b. 독립 라벨 실측 boundary 초과 검증 (기존 #3은 좌표만 봄 → 렌더링 크기 기반으로 강화)
        if bnd_rect and self._label_extents:
            bx1, by1, bx2, by2 = bnd_rect
            for le in self._label_extents:
                short = le['text']
                if le['x0'] < bx1 - 0.02:
                    issues.append(
                        f'Label "{short}": left edge ({le["x0"]:.2f}") outside boundary left ({bx1:.2f}"). '
                        f'Move label right or reduce text.')
                if le['x1'] > bx2 + 0.02:
                    issues.append(
                        f'Label "{short}": right edge ({le["x1"]:.2f}") outside boundary right ({bx2:.2f}"). '
                        f'Move label left or reduce text.')
                if le['y0'] < by1 - 0.02:
                    issues.append(
                        f'Label "{short}": bottom edge ({le["y0"]:.2f}") outside boundary bottom ({by1:.2f}"). '
                        f'Move label up.')
                if le['y1'] > by2 + 0.02:
                    issues.append(
                        f'Label "{short}": top edge ({le["y1"]:.2f}") outside boundary top ({by2:.2f}"). '
                        f'Move label down.')

        # 0. 텍스트가 박스 경계를 벗어나는지 실측 검증 (axes.transData 기반 정확한 측정)
        # 최소 내부 패딩: 수평 0.09", 수직 0.07" (텍스트가 박스 내벽에 너무 붙으면 경고)
        BOX_PAD_H = 0.09  # 좌우 각각
        BOX_PAD_V = 0.07  # 상하 각각
        for cmd in self._cmds:
            if cmd[0] == 'box':
                _, b, text, fs_override = cmd
                short = text[:30].replace('\n', ' ')
                if id(b) in self._box_text_sizes:
                    tw_in, th_in = self._box_text_sizes[id(b)]
                    # 오버플로우 검사 (패딩 무시, 절대 넘으면 안 됨)
                    if tw_in > b.w + 0.01:
                        issues.append(
                            f'Box "{short}": text overflows horizontally '
                            f'(text={tw_in:.2f}", box={b.w:.2f}"). '
                            f'Increase box width to at least {tw_in + BOX_PAD_H*2:.2f}".')
                    if th_in > b.h + 0.01:
                        issues.append(
                            f'Box "{short}": text overflows vertically '
                            f'(text={th_in:.2f}", box={b.h:.2f}"). '
                            f'Increase box height to at least {th_in + BOX_PAD_V*2:.2f}".')
                    # 패딩 검사 (텍스트가 내벽에 너무 가까움)
                    elif th_in > b.h - BOX_PAD_V * 2:
                        issues.append(
                            f'Box "{short}": vertical padding too tight '
                            f'(text={th_in:.2f}", box={b.h:.2f}", pad={((b.h-th_in)/2):.2f}" < {BOX_PAD_V}" min). '
                            f'Increase box height to at least {th_in + BOX_PAD_V*2:.2f}".')
                    PAD_EPS = 0.005  # float 측정 오차 허용치
                    if tw_in > b.w - BOX_PAD_H * 2 + PAD_EPS and tw_in <= b.w + 0.01:
                        issues.append(
                            f'Box "{short}": horizontal padding too tight '
                            f'(text={tw_in:.2f}", box={b.w:.2f}", pad={((b.w-tw_in)/2):.2f}" < {BOX_PAD_H}" min). '
                            f'Increase box width to at least {tw_in + BOX_PAD_H*2:.2f}".')

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
        # (sequence_diagram actor, swimlane header 등 _no_ref_boxes는 스킵)
        REF_FIRST_LINE = re.compile(r'^\d{2,4}$')
        for cmd in self._cmds:
            if cmd[0] in ('box', 'rounded_rect'):
                _, b, text, *_ = cmd
                if id(b) in self._no_ref_boxes:
                    continue  # 시퀀스 다이어그램 행위자 등 ref 불필요 박스
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
                # _terminal_boxes로 마킹된 박스는 의도적 terminal → 스킵
                if id(b) in self._terminal_boxes:
                    continue
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

        # 12. 공간 낭비 검증: boundary 내 빈 공간이 35% 이상이면 경고
        if bnd_rect and self._box_refs:
            bx1, by1, bx2, by2 = bnd_rect
            bnd_area = (bx2 - bx1) * (by2 - by1)
            # 모든 박스 및 line(lifeline 등) 의 최대 범위 계산
            content_top = max(b.top for b in self._box_refs)
            content_bot = min(b.bot for b in self._box_refs)
            # line 끝점도 포함 (sequence diagram lifeline 등)
            for cmd in self._cmds:
                if cmd[0] == 'line':
                    _, lx1, ly1, lx2, ly2, _ = cmd
                    content_top = max(content_top, ly1, ly2)
                    content_bot = min(content_bot, ly1, ly2)
            content_h = content_top - content_bot + 0.60  # 상하 여백
            bnd_h = by2 - by1
            usage = content_h / bnd_h if bnd_h > 0 else 1.0
            if usage < 0.65:
                issues.append(
                    f'Space usage {usage*100:.0f}%: boundary height {bnd_h:.1f}" but '
                    f'content height {content_h:.1f}". Consider reducing boundary or '
                    f'increasing content spacing for better space utilization.')

        # 12b. line-line 접합 검증: line 끝점이 다른 line에 닿는지
        LINE_JOIN_TOL = 0.03
        for i_cmd, cmd1 in enumerate(self._cmds):
            if cmd1[0] == 'line':
                _, lx1, ly1, lx2, ly2, ls1 = cmd1
                # 이 line의 양 끝점이 다른 line 위에 있는지 확인
                for pt_x, pt_y, pt_name in [(lx1, ly1, 'start'), (lx2, ly2, 'end')]:
                    on_any = False
                    # 박스 edge에 있으면 OK
                    if _near_box_edge(pt_x, pt_y):
                        on_any = True
                    # 다른 line 위에 있으면 OK
                    for j_cmd, cmd2 in enumerate(self._cmds):
                        if j_cmd == i_cmd or cmd2[0] != 'line':
                            continue
                        _, ox1, oy1, ox2, oy2, _ = cmd2
                        # 수평선
                        if abs(oy1 - oy2) < 0.01:
                            if abs(pt_y - oy1) < LINE_JOIN_TOL and min(ox1,ox2)-LINE_JOIN_TOL <= pt_x <= max(ox1,ox2)+LINE_JOIN_TOL:
                                on_any = True; break
                        # 수직선
                        elif abs(ox1 - ox2) < 0.01:
                            if abs(pt_x - ox1) < LINE_JOIN_TOL and min(oy1,oy2)-LINE_JOIN_TOL <= pt_y <= max(oy1,oy2)+LINE_JOIN_TOL:
                                on_any = True; break
                    if not on_any and not _on_bus_line(pt_x, pt_y):
                        issues.append(
                            f'Line {pt_name} ({pt_x:.2f},{pt_y:.2f}) not connected to any box or line. '
                            f'Ensure leader lines attach to target elements.')

        # 13. 도형 간 겹침 감지 (box-box, box-cloud overlap)
        for i, b1 in enumerate(self._box_refs):
            for j, b2 in enumerate(self._box_refs):
                if j <= i:
                    continue
                # CloudRef는 타원 반축(_ea, _eb) 사용
                if isinstance(b1, CloudRef):
                    r1_l, r1_r = b1.cx - b1._ea, b1.cx + b1._ea
                    r1_b, r1_t = b1.cy - b1._eb, b1.cy + b1._eb
                else:
                    r1_l, r1_r, r1_b, r1_t = b1.left, b1.right, b1.bot, b1.top
                if isinstance(b2, CloudRef):
                    r2_l, r2_r = b2.cx - b2._ea, b2.cx + b2._ea
                    r2_b, r2_t = b2.cy - b2._eb, b2.cy + b2._eb
                else:
                    r2_l, r2_r, r2_b, r2_t = b2.left, b2.right, b2.bot, b2.top
                # 겹침 감지 (완전 포함은 제외 — container-child 관계)
                overlap_x = r1_l < r2_r and r1_r > r2_l
                overlap_y = r1_b < r2_t and r1_t > r2_b
                if overlap_x and overlap_y:
                    # 한쪽이 다른쪽을 완전히 포함하면 container-child → skip
                    contains_1in2 = (r2_l <= r1_l and r1_r <= r2_r and r2_b <= r1_b and r1_t <= r2_t)
                    contains_2in1 = (r1_l <= r2_l and r2_r <= r1_r and r1_b <= r2_b and r2_t <= r1_t)
                    if not contains_1in2 and not contains_2in1:
                        # 부분 겹침 → 경고
                        t1 = ''
                        t2 = ''
                        for c in self._cmds:
                            if c[0] == 'box' and c[1] is b1: t1 = c[2][:20].replace('\n',' ')
                            if c[0] == 'box' and c[1] is b2: t2 = c[2][:20].replace('\n',' ')
                            if c[0] == 'cloud' and c[7] is b1: t1 = c[5][:20].replace('\n',' ')
                            if c[0] == 'cloud' and c[7] is b2: t2 = c[5][:20].replace('\n',' ')
                        issues.append(
                            f'Box overlap: "{t1}" and "{t2}" partially overlap. '
                            f'Adjust positions to avoid collision.')

        # 14. container(layer) < child(box) 감지
        for cmd in self._cmds:
            if cmd[0] == 'boundary' and not cmd[6]:  # layer (not page boundary)
                _, lx1, ly1, lx2, ly2, lbl, _ = cmd
                display_lbl = lbl.split('|')[0] if '|' in lbl else lbl
                for bcmd in self._cmds:
                    if bcmd[0] == 'box':
                        b = bcmd[1]
                        # 박스가 layer 안에 있는지 먼저 확인 (중심이 layer 안)
                        in_layer = (lx1 - 0.10 < b.cx < lx2 + 0.10 and
                                    ly1 - 0.10 < b.cy < ly2 + 0.10)
                        if in_layer:
                            if b.left < lx1 - 0.02:
                                issues.append(
                                    f'Box "{bcmd[2][:20].replace(chr(10)," ")}" left ({b.left:.2f}) '
                                    f'exceeds layer "{display_lbl}" left ({lx1:.2f}). '
                                    f'Enlarge container or shrink box.')
                            if b.right > lx2 + 0.02:
                                issues.append(
                                    f'Box "{bcmd[2][:20].replace(chr(10)," ")}" right ({b.right:.2f}) '
                                    f'exceeds layer "{display_lbl}" right ({lx2:.2f}). '
                                    f'Enlarge container or shrink box.')

        return issues
