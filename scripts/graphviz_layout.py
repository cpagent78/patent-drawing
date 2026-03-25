"""
graphviz_layout.py  v1.0
Graphviz 하이브리드 특허 도면 엔진

Graphviz로 레이아웃 계산 (노드 좌표 + 엣지 경로),
patent_drawing_lib.py로 USPTO 규격 렌더링.

핵심 아이디어:
  - Graphviz DOT (splines=ortho) → 노드 좌표 + 직교 엣지 경로 추출
  - 좌표를 USPTO 페이지 좌표로 변환 (points → inches, 스케일링 + 여백)
  - patent_drawing_lib.Drawing으로 박스 + arrow_route() 렌더링

Usage:
    layout = GraphvizLayout('FIG. 2', orientation='portrait')
    layout.node('70', 'AI Agent\\nOrchestration Unit')
    layout.node('80', 'Context Analysis\\nUnit')
    layout.edge('70', '80')
    layout.edge('130', '80', feedback=True)
    layout.render('fig2.png')
"""

import sys, os, subprocess, tempfile, math, re
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from patent_drawing_lib import Drawing, BoxRef, FS_BODY

# ── USPTO 페이지 설정 ─────────────────────────────────────────────────────────
PORTRAIT_W,  PORTRAIT_H  = 8.5, 11.0
LANDSCAPE_W, LANDSCAPE_H = 11.0, 8.5

# 드로잉 가능 영역 (USPTO 마진 포함)
MARGIN_TOP   = 1.00   # 상단 1"
MARGIN_LEFT  = 1.00   # 좌측 1"
MARGIN_RIGHT = 0.625  # 우측 0.625"
MARGIN_BOT   = 0.625  # 하단 0.625"

# Graphviz 기본 노드 크기 (DOT 단위: inches)
GV_NODE_W    = 1.50   # 노드 기본 너비 (인치)
GV_NODE_H    = 0.55   # 노드 기본 높이 (인치)

# 노드 텍스트 패딩 (인치) - patent_drawing_lib 기본값보다 약간 크게
GV_PAD_X     = 0.24   # 좌우 여백 합계 (0.20 + 0.04 여유)
GV_PAD_Y     = 0.18   # 상하 여백 합계 (0.14 + 0.04 여유)

# nodesep / ranksep 기본값 (인치)
GV_NODESEP   = 0.5
GV_RANKSEP   = 0.8


class GraphvizLayout:
    """
    Graphviz를 레이아웃 엔진으로, patent_drawing_lib를 렌더링 백엔드로 사용하는
    하이브리드 특허 도면 생성기.

    Graphviz DOT (splines=ortho) 로 노드 좌표 및 엣지 경로를 계산하고
    USPTO 규격 페이지에 맞게 변환 후 patent_drawing_lib.Drawing으로 렌더링.

    Parameters
    ----------
    fig_label : str
        도면 번호 라벨 (예: 'FIG. 2')
    orientation : str
        'portrait' (기본, 8.5×11) | 'landscape' (11×8.5)
    rankdir : str
        'TB' (위→아래, 기본) | 'LR' (왼쪽→오른쪽)
    nodesep : float
        같은 rank 내 노드 간격 (인치, Graphviz 단위)
    ranksep : float
        rank 간 간격 (인치, Graphviz 단위)
    splines : str
        'ortho' (직교, 기본) | 'polyline' | 'curved'
    fig_num : str
        Drawing 도면 번호 (기본: fig_label에서 추출)
    """

    def __init__(self, fig_label: str, orientation: str = 'portrait',
                 rankdir: str = 'TB', nodesep: float = GV_NODESEP,
                 ranksep: float = GV_RANKSEP, splines: str = 'ortho',
                 fig_num: str = None):
        self.fig_label   = fig_label
        self.orientation = orientation
        self.rankdir     = rankdir
        self.nodesep     = nodesep
        self.ranksep     = ranksep
        self.splines     = splines

        # fig_num 추출 (예: 'FIG. 2' → '2')
        if fig_num is None:
            m = re.search(r'(\d+)', fig_label)
            self.fig_num = m.group(1) if m else '1'
        else:
            self.fig_num = fig_num

        # 페이지 크기
        if orientation == 'landscape':
            self.page_w, self.page_h = LANDSCAPE_W, LANDSCAPE_H
        else:
            self.page_w, self.page_h = PORTRAIT_W, PORTRAIT_H

        # 드로잉 가능 영역
        self.draw_x0 = MARGIN_LEFT
        self.draw_y0 = MARGIN_BOT
        self.draw_w  = self.page_w - MARGIN_LEFT - MARGIN_RIGHT
        self.draw_h  = self.page_h - MARGIN_TOP  - MARGIN_BOT

        # 노드/엣지 저장소
        self._nodes  = {}   # node_id → {'text': str, 'shape': str, 'rank': int|None}
        self._edges  = []   # [{'src', 'dst', 'label', 'feedback', 'bidir'}]
        self._ranks  = {}   # node_id → rank (hint)
        self._groups = []   # [[node_id, ...], ...]  같은 rank subgraph

    # ── 노드/엣지 등록 ────────────────────────────────────────────────────────

    def node(self, node_id: str, text: str, shape: str = 'box',
             rank: int = None) -> 'GraphvizLayout':
        """
        노드 등록.

        Parameters
        ----------
        node_id : str   Graphviz 노드 ID (참조번호, 예: '70')
        text    : str   박스 표시 텍스트 ('70\\nAI Agent Unit')
        shape   : str   'box' | 'diamond' (미래 확장)
        rank    : int   수동 rank 힌트 (선택)
        """
        self._nodes[node_id] = {'text': text, 'shape': shape, 'rank': rank}
        if rank is not None:
            self._ranks[node_id] = rank
        return self

    def edge(self, src: str, dst: str, label: str = '',
             feedback: bool = False, bidir: bool = False) -> 'GraphvizLayout':
        """
        엣지 등록.

        Parameters
        ----------
        src      : str    출발 노드 ID
        dst      : str    도착 노드 ID
        label    : str    엣지 라벨 (선택)
        feedback : bool   피드백 엣지 → constraint=false + style=dashed
        bidir    : bool   양방향 화살표
        """
        self._edges.append({
            'src': src, 'dst': dst, 'label': label,
            'feedback': feedback, 'bidir': bidir
        })
        return self

    def rank_hint(self, node_id: str, rank: int) -> 'GraphvizLayout':
        """노드 rank 힌트 (동일 rank는 같은 줄에 배치)."""
        self._ranks[node_id] = rank
        return self

    def group(self, node_ids: list) -> 'GraphvizLayout':
        """같은 rank에 묶을 노드 그룹 (Graphviz subgraph rank=same)."""
        self._groups.append(node_ids)
        return self

    # ── 텍스트 크기 측정 ──────────────────────────────────────────────────────

    def _measure_node_sizes(self) -> dict:
        """
        모든 노드 텍스트 크기를 사전 측정.
        patent_drawing_lib.Drawing의 box()를 실제로 호출해서
        자동 확장 후의 최종 크기를 측정 (auto-expand 반영).

        Returns
        -------
        sizes : {node_id: (width_inches, height_inches)}
        """
        # matplotlib 전역 상태 초기화 (이전 figure가 측정에 영향을 주지 않도록)
        plt.close('all')

        # 임시 Drawing으로 box() 호출 후 최종 크기 측정
        tmp_drawing = Drawing('/tmp/_gvlayout_measure.png',
                               orientation=self.orientation)
        sizes = {}
        for nid, ndata in self._nodes.items():
            text = ndata['text']
            # 초기 크기: 기본값으로 box() 호출 → auto-expand 결과 확인
            b = tmp_drawing.box(0.5, 0.5, GV_NODE_W, GV_NODE_H, text)
            # 여유 마진 추가 (측정 오차 + 렌더링 환경 차이 보정)
            # 0.25" 마진: matplotlib figure 상태에 따른 크기 변동 흡수
            # 넓은 노드(>2")에서 겹침 방지
            w = b.w + 0.25
            h = b.h + 0.10
            sizes[nid] = (w, h)
        plt.close(tmp_drawing.fig)
        return sizes

    # ── DOT 소스 생성 ─────────────────────────────────────────────────────────

    def _build_dot(self, node_sizes: dict = None,
                   nodesep: float = None, ranksep: float = None,
                   page_size: tuple = None) -> str:
        """
        Graphviz DOT 소스 문자열 생성.

        Parameters
        ----------
        node_sizes : {node_id: (w, h)} - 노드별 실측 크기 (None이면 기본값)
        nodesep    : 노드 간격 오버라이드 (None이면 self.nodesep)
        ranksep    : rank 간격 오버라이드 (None이면 self.ranksep)
        page_size  : (w, h) - Graphviz size 제한 (None이면 제한 없음)
        """
        ns = nodesep if nodesep is not None else self.nodesep
        rs = ranksep if ranksep is not None else self.ranksep

        lines = ['digraph patent {']
        lines.append(f'  rankdir={self.rankdir};')
        lines.append(f'  nodesep={ns:.2f};')
        lines.append(f'  ranksep={rs:.2f};')
        if page_size:
            pw, ph = page_size
            lines.append(f'  size="{pw:.3f},{ph:.3f}";')
            lines.append(f'  ratio=compress;')
        lines.append(f'  splines={self.splines};')
        lines.append(f'  node [shape=box, style=filled, fillcolor=white,')
        lines.append(f'        fontsize=10, fixedsize=true];')
        lines.append('')

        # 노드 정의 - 실측 크기 사용 (fixedsize=true로 일관성 보장)
        for nid, ndata in self._nodes.items():
            escaped = nid.replace('"', '\\"')
            shape = ndata.get('shape', 'box')

            if node_sizes and nid in node_sizes:
                nw, nh = node_sizes[nid]
                # 마진 빼기 (measure에서 추가한 마진 제거)
                nw = max(nw - 0.10, GV_NODE_W)
                nh = max(nh - 0.06, GV_NODE_H)
            else:
                nw, nh = GV_NODE_W, GV_NODE_H

            if shape == 'diamond':
                lines.append(f'  "{escaped}" [label="{escaped}", shape=diamond,'
                              f' width={nw:.3f}, height={nh:.3f}];')
            else:
                lines.append(f'  "{escaped}" [label="{escaped}",'
                              f' width={nw:.3f}, height={nh:.3f}];')

        lines.append('')

        # rank 힌트를 사용한 subgraph
        # 같은 rank 값을 가진 노드들을 same rank subgraph로 묶음
        rank_groups = {}
        for nid, r in self._ranks.items():
            rank_groups.setdefault(r, []).append(nid)

        # 명시적 그룹도 rank=same으로
        for grp in self._groups:
            # 그룹 내 rank 값 찾기 (있으면 사용, 없으면 새 rank 번호 부여)
            existing_ranks = [self._ranks.get(n) for n in grp if n in self._ranks]
            if existing_ranks:
                r = existing_ranks[0]
            else:
                r = max(rank_groups.keys(), default=-1) + 1
            for n in grp:
                self._ranks[n] = r
                rank_groups.setdefault(r, []).append(n)

        for r, nids in sorted(rank_groups.items()):
            unique = list(dict.fromkeys(nids))  # 중복 제거
            if len(unique) > 1:
                ids_str = ' '.join(f'"{n}"' for n in unique)
                lines.append(f'  {{ rank=same; {ids_str} }}')

        lines.append('')

        # 엣지 정의 (피드백 엣지는 DOT에서 제외 → 수동 라우팅)
        # 이유: constraint=false 피드백 엣지가 있으면 Graphviz가 레이아웃을 망침
        for e in self._edges:
            if e.get('feedback'):
                continue  # 피드백은 DOT에서 제외 (render()에서 수동 처리)
            src = e['src'].replace('"', '\\"')
            dst = e['dst'].replace('"', '\\"')
            lbl = e.get('label', '')
            attrs = []
            if e.get('bidir'):
                attrs.append('dir=both')
            if lbl:
                escaped_lbl = lbl.replace('"', '\\"')
                attrs.append(f'label="{escaped_lbl}"')
            attr_str = f' [{", ".join(attrs)}]' if attrs else ''
            lines.append(f'  "{src}" -> "{dst}"{attr_str};')

        lines.append('}')
        return '\n'.join(lines)

    # ── Graphviz 레이아웃 계산 ────────────────────────────────────────────────

    def _run_graphviz(self, dot_src: str) -> str:
        """
        dot -Tplain 실행 → plain 형식 출력 반환.
        plain 형식: https://graphviz.org/docs/outputs/plain/
          graph scale width height
          node name x y w h label style shape color fillcolor
          edge tail head n x1 y1 .. xn yn [label xl yl] style color
          stop
        좌표 단위: points (1 point = 1/72 inch)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dot',
                                         delete=False) as f:
            f.write(dot_src)
            dot_path = f.name

        try:
            result = subprocess.run(
                ['dot', '-Tplain', dot_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                raise RuntimeError(f"Graphviz error: {result.stderr}")
            return result.stdout
        finally:
            os.unlink(dot_path)

    def _parse_plain(self, plain: str) -> dict:
        """
        Graphviz plain 형식 파싱.

        Returns
        -------
        {
          'graph': {'scale': float, 'width': float, 'height': float},
          'nodes': {name: {'x': float, 'y': float, 'w': float, 'h': float}},
          'edges': [{'src', 'dst', 'points': [(x,y),...], 'style', 'label'}]
        }
        좌표 단위: inches (plain 출력은 이미 inches 단위)
        """
        result = {'graph': {}, 'nodes': {}, 'edges': []}
        lines = plain.strip().split('\n')

        for line in lines:
            parts = line.split()
            if not parts:
                continue

            if parts[0] == 'graph':
                result['graph'] = {
                    'scale': float(parts[1]),
                    'width': float(parts[2]),
                    'height': float(parts[3])
                }

            elif parts[0] == 'node':
                # node name x y w h label style shape color fillcolor
                name = parts[1].strip('"')
                x, y, w, h = float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])
                result['nodes'][name] = {'x': x, 'y': y, 'w': w, 'h': h}

            elif parts[0] == 'edge':
                # edge tail head n x1 y1 x2 y2 ... [label xl yl] style color
                src = parts[1].strip('"')
                dst = parts[2].strip('"')
                n   = int(parts[3])
                pts = []
                idx = 4
                for _ in range(n):
                    pts.append((float(parts[idx]), float(parts[idx+1])))
                    idx += 2

                # 나머지: label? style color
                style = 'solid'
                label = ''
                if idx < len(parts):
                    # style은 마지막에서 두 번째
                    if len(parts) - idx >= 2:
                        style = parts[-2]
                        possible_label = parts[idx]
                        if possible_label not in ('solid', 'dashed', 'dotted'):
                            label = possible_label

                result['edges'].append({
                    'src': src, 'dst': dst,
                    'points': pts, 'style': style, 'label': label
                })

        return result

    # ── 좌표 변환 ──────────────────────────────────────────────────────────────

    def _gv_to_page(self, gv_x: float, gv_y: float,
                    gv_graph_w: float, gv_graph_h: float) -> tuple:
        """
        Graphviz 좌표 → USPTO 페이지 좌표 변환.

        Graphviz plain 출력:
          - 단위: inches
          - 원점: 왼쪽 아래 (y증가 = 위로)
          - (0,0) ~ (graph_w, graph_h)

        USPTO 페이지 좌표:
          - 단위: inches
          - 원점: 왼쪽 아래 (matplotlib 동일)
          - draw_x0 ~ draw_x0+draw_w, draw_y0 ~ draw_y0+draw_h

        변환:
          scale_x = draw_w / graph_w
          scale_y = draw_h / graph_h
          scale   = min(scale_x, scale_y) * padding_factor
          (중앙 정렬)
        """
        if gv_graph_w <= 0 or gv_graph_h <= 0:
            return (self.draw_x0 + gv_x, self.draw_y0 + gv_y)

        # 스케일 계산 (가로세로 비율 유지, 90% 사용)
        scale_x = self.draw_w / gv_graph_w
        scale_y = self.draw_h / gv_graph_h
        scale   = min(scale_x, scale_y) * 0.90

        # 중앙 정렬 오프셋
        scaled_w = gv_graph_w * scale
        scaled_h = gv_graph_h * scale
        off_x = self.draw_x0 + (self.draw_w - scaled_w) / 2
        off_y = self.draw_y0 + (self.draw_h - scaled_h) / 2

        page_x = off_x + gv_x * scale
        page_y = off_y + gv_y * scale
        return (page_x, page_y)

    def _gv_size_to_page(self, gv_w: float, gv_h: float,
                          gv_graph_w: float, gv_graph_h: float) -> tuple:
        """Graphviz 크기 → 페이지 크기 변환."""
        if gv_graph_w <= 0 or gv_graph_h <= 0:
            return (gv_w, gv_h)

        scale_x = self.draw_w / gv_graph_w
        scale_y = self.draw_h / gv_graph_h
        scale   = min(scale_x, scale_y) * 0.90

        return (gv_w * scale, gv_h * scale)

    # ── 렌더링 ─────────────────────────────────────────────────────────────────

    def render(self, output_path: str) -> list:
        """
        도면 생성 + 저장.

        1. DOT 소스 생성
        2. Graphviz 레이아웃 계산
        3. 좌표 파싱 + 변환
        4. patent_drawing_lib로 렌더링
        5. 저장

        Returns
        -------
        warnings : list[str]  save() 경고 목록
        """
        # 1. 노드 텍스트 크기 사전 측정
        node_sizes = self._measure_node_sizes()

        # 2. DOT 소스 (실측 크기 반영)
        dot_src = self._build_dot(node_sizes)

        # 3. Graphviz 실행 (첫 시도)
        plain = self._run_graphviz(dot_src)

        # 4. 파싱
        gv = self._parse_plain(plain)

        # 4b. 겹침 방지: 실측 크기 기반 nodesep 자동 조정
        # 같은 rank의 노드들이 페이지에서 겹치지 않도록 nodesep 보정
        gv_w_tmp = gv['graph'].get('width', 1.0)
        gv_h_tmp = gv['graph'].get('height', 1.0)

        if node_sizes:
            sc_x_tmp = self.draw_w / gv_w_tmp if gv_w_tmp > 0 else 1.0
            sc_y_tmp = self.draw_h / gv_h_tmp if gv_h_tmp > 0 else 1.0
            sc_tmp = min(sc_x_tmp, sc_y_tmp) * 0.90

            # 각 rank에서 박스 겹침 여부 확인
            by_rank = {}
            for nid2, n2 in gv['nodes'].items():
                ry = round(n2['y'], 3)
                by_rank.setdefault(ry, []).append((n2['x'], nid2))

            max_required_nodesep = self.nodesep  # 현재 nodesep 이상
            for ry, nodes_at_rank in by_rank.items():
                if len(nodes_at_rank) >= 2:
                    sorted_n = sorted(nodes_at_rank, key=lambda x: x[0])
                    for k in range(len(sorted_n) - 1):
                        nid_l = sorted_n[k][1]
                        nid_r = sorted_n[k+1][1]
                        gv_center_gap = sorted_n[k+1][0] - sorted_n[k][0]
                        pw_l = (node_sizes.get(nid_l, (GV_NODE_W,))[0] - 0.10)
                        pw_r = (node_sizes.get(nid_r, (GV_NODE_W,))[0] - 0.10)
                        # 페이지에서 필요한 중심 간격
                        needed_center = (pw_l + pw_r) / 2 + 0.30  # 0.30" gap
                        # 현재 sc로 얻는 중심 간격
                        current_center = gv_center_gap * sc_tmp
                        if current_center < needed_center:
                            # GV 노드 크기 (기본)
                            gv_nw = GV_NODE_W
                            # 필요한 nodesep: needed_center_gv = needed_center / sc
                            # GV 중심 간격 = GV 폭 + nodesep_actual
                            # 현재 nodesep_actual ≈ gv_center_gap - gv_nw
                            current_ns_actual = gv_center_gap - gv_nw
                            extra = (needed_center / sc_tmp - gv_center_gap)
                            new_nodesep = max(max_required_nodesep,
                                              self.nodesep + extra)
                            max_required_nodesep = max(max_required_nodesep, new_nodesep)

            if max_required_nodesep > self.nodesep + 0.05:
                dot_src2 = self._build_dot(node_sizes,
                                            nodesep=max_required_nodesep)
                gv = self._parse_plain(self._run_graphviz(dot_src2))
        gv_graph = gv['graph']
        gv_nodes = gv['nodes']
        gv_edges = gv['edges']

        gv_w = gv_graph.get('width', 1.0)
        gv_h = gv_graph.get('height', 1.0)

        # 5. Drawing 초기화
        d = Drawing(output_path, fig_num=self.fig_num,
                    orientation=self.orientation)

        # 6. 노드 → 박스
        # 전략:
        # - 노드 중심 좌표: Graphviz 스케일로 변환 (페이지 배치)
        # - 박스 크기: 실측 크기 사용 (텍스트 가독성 보장)
        # - 단, 실측 크기 기반으로 Graphviz nodesep을 사전에 충분히 설정했으므로
        #   겹침 없음 보장
        scale_x = self.draw_w / gv_w if gv_w > 0 else 1.0
        scale_y = self.draw_h / gv_h if gv_h > 0 else 1.0
        scale   = min(scale_x, scale_y) * 0.90

        scaled_w = gv_w * scale
        scaled_h = gv_h * scale
        off_x = self.draw_x0 + (self.draw_w - scaled_w) / 2
        off_y = self.draw_y0 + (self.draw_h - scaled_h) / 2

        def gv_pt_to_page(gx, gy):
            """Graphviz 좌표 → 페이지 좌표 (현재 스케일 기준)."""
            return (off_x + gx * scale, off_y + gy * scale)

        box_map = {}   # node_id → BoxRef
        for nid, ndata in self._nodes.items():
            if nid not in gv_nodes:
                print(f"  ⚠ node '{nid}' not found in Graphviz output")
                continue

            gv_n = gv_nodes[nid]
            gv_cx, gv_cy = gv_n['x'], gv_n['y']

            # 중심좌표 변환
            px, py = gv_pt_to_page(gv_cx, gv_cy)

            # 박스 크기: 실측 크기 사용
            if node_sizes and nid in node_sizes:
                pw, ph = node_sizes[nid]
                # 마진 제거 (render()에서 box()가 자동으로 패딩 처리)
                pw = max(pw - 0.10, GV_NODE_W * 0.8)
                ph = max(ph - 0.06, GV_NODE_H * 0.7)
            else:
                gv_nw, gv_nh = gv_n['w'], gv_n['h']
                pw = max(gv_nw * scale, 0.70)
                ph = max(gv_nh * scale, 0.36)

            # 중심→좌하단
            bx = px - pw / 2
            by = py - ph / 2

            text = ndata['text']
            b = d.box(bx, by, pw, ph, text)
            box_map[nid] = b

        # 7. 엣지 → 화살표
        # 피드백 엣지 정보 사전 준비
        edge_feedback_map = {}  # (src_id, dst_id) → feedback bool
        for e_orig in self._edges:
            key = (e_orig['src'], e_orig['dst'])
            edge_feedback_map[key] = e_orig.get('feedback', False)

        feedback_count = 0  # 피드백 채널 카운터

        for e_gv in gv_edges:
            src_id = e_gv['src']
            dst_id = e_gv['dst']
            pts    = e_gv['points']
            style  = e_gv['style']

            if src_id not in box_map or dst_id not in box_map:
                continue

            # 출발/도착 박스
            src_box = box_map[src_id]
            dst_box = box_map[dst_id]

            # 피드백 여부: 원본 엣지 정보 우선 (Graphviz style보다 정확)
            is_feedback = edge_feedback_map.get((src_id, dst_id), style == 'dashed')
            ls = '--' if is_feedback else '-'

            if is_feedback:
                # 피드백 엣지: side channel 라우팅 (박스 통과 방지)
                waypoints = self._route_feedback(
                    src_box, dst_box, feedback_count, box_map)
                feedback_count += 1
                if waypoints:
                    d.arrow_route(waypoints, ls=ls)
                else:
                    d.arrow_v(src_box, dst_box)
            else:
                # 일반 엣지: Graphviz 경로 사용
                page_pts = []
                for (gx, gy) in pts:
                    px, py = gv_pt_to_page(gx, gy)
                    page_pts.append((px, py))

                if len(page_pts) >= 2:
                    waypoints = self._snap_and_extract(page_pts, src_box, dst_box)
                    if waypoints:
                        d.arrow_route(waypoints, ls=ls)
                    else:
                        d.arrow_v(src_box, dst_box)
                else:
                    d.arrow_v(src_box, dst_box)

        # 8. FIG. 라벨
        d.fig_label()

        # 9. 저장
        warnings = d.save()

        return warnings

    # ── 피드백 엣지 라우팅 ────────────────────────────────────────────────────

    def _route_feedback(self, src_box, dst_box, count: int, box_map: dict) -> list:
        '''
        피드백 엣지 (역방향 화살표) 라우팅.
        박스를 통과하지 않도록 side channel 경로 생성.
        '''
        all_boxes = list(box_map.values())
        min_x = min(b.left  for b in all_boxes)
        max_x = max(b.right for b in all_boxes)

        CHANNEL_MARGIN = 0.35

        src_cy = src_box.cy
        dst_cy = dst_box.cy
        src_cx = src_box.cx
        dst_cx = dst_box.cx

        if abs(src_cy - dst_cy) > 0.1:
            # 수직 방향 피드백 → side channel
            if count % 2 == 0:
                # 왼쪽 채널
                ch_x = min_x - CHANNEL_MARGIN * (1 + count // 2)
                p1 = src_box.left_mid()
                p2 = (ch_x, p1[1])
                p3 = (ch_x, dst_box.cy)
                p4 = dst_box.left_mid()
            else:
                # 오른쪽 채널
                ch_x = max_x + CHANNEL_MARGIN * (1 + count // 2)
                p1 = src_box.right_mid()
                p2 = (ch_x, p1[1])
                p3 = (ch_x, dst_box.cy)
                p4 = dst_box.right_mid()
            return [p1, p2, p3, p4]
        else:
            # 수평 방향
            if src_cx > dst_cx:
                return [src_box.left_mid(), dst_box.right_mid()]
            else:
                return [src_box.right_mid(), dst_box.left_mid()]

    def _snap_and_extract(self, page_pts: list, src_box: BoxRef,
                           dst_box: BoxRef) -> list:
        """
        Graphviz 엣지 포인트 → arrow_route() waypoints.

        핵심 전략:
        1. 박스 크기가 실측 크기이므로, 엣지 첫/마지막 점이
           실제 박스 경계에서 벗어날 수 있음.
        2. 해결: 경로의 방향성을 분석해 박스의 올바른 면(top/bot/left/right)
           중심으로 스냅 → 직교 화살표 보장.
        3. 중간 꺾임점은 Graphviz ortho 경로에서 추출.
        """
        if not page_pts:
            return []

        # 1. 중복 제거
        unique = [page_pts[0]]
        for p in page_pts[1:]:
            last = unique[-1]
            if abs(p[0]-last[0]) > 0.001 or abs(p[1]-last[1]) > 0.001:
                unique.append(p)

        if len(unique) < 2:
            return [src_box.bot_mid(), dst_box.top_mid()]

        # 2. 경로 방향 분석
        # 출발: 경로 시작점에서 두 번째 점 방향
        dep_dx = unique[1][0] - unique[0][0]
        dep_dy = unique[1][1] - unique[0][1]
        # 도착: 마지막 세그먼트 방향
        arr_dx = unique[-1][0] - unique[-2][0]
        arr_dy = unique[-1][1] - unique[-2][1]

        # 3. 박스 면 중심으로 스냅 (직교 화살표 보장)
        start = self._snap_exit(src_box, dep_dx, dep_dy)
        end   = self._snap_entry(dst_box, arr_dx, arr_dy)

        # 4. 중간 꺾임점 (경로가 복잡한 경우)
        if len(unique) <= 4:
            # 단순 경로: 출발면 → x 또는 y에 ortho 경유점 추가
            mid_pts = self._build_ortho_mid(start, end, dep_dx, dep_dy)
        else:
            mid_pts = self._extract_ortho_turns(unique[1:-1])

        if not mid_pts:
            return [start, end]

        return [start] + mid_pts + [end]

    def _build_ortho_mid(self, start: tuple, end: tuple,
                          dep_dx: float, dep_dy: float) -> list:
        """
        단순 경로용 직교 경유점 생성.
        출발 방향(dep)에 따라 수직 또는 수평 먼저 이동.
        start와 end가 이미 직교 정렬되어 있으면 경유점 불필요.
        """
        sx, sy = start
        ex, ey = end
        tol = 0.01

        # 이미 직선?
        if abs(sx - ex) < tol or abs(sy - ey) < tol:
            return []

        # 출발이 수직이면 (위/아래): y 먼저 이동 → x 이동
        if abs(dep_dy) >= abs(dep_dx):
            return [(sx, ey)]
        else:
            # 출발이 수평이면: x 먼저 이동 → y 이동
            return [(ex, sy)]

    def _snap_exit(self, box: BoxRef, dx: float, dy: float) -> tuple:
        """
        박스 출발점 스냅 — 이동 방향(dx, dy)에 따라 박스 면 중심 반환.
        dx>0=오른쪽, dx<0=왼쪽, dy>0=위, dy<0=아래
        """
        if abs(dx) < abs(dy):
            # 수직 이동 우세
            if dy > 0:
                return box.top_mid()
            else:
                return box.bot_mid()
        else:
            # 수평 이동 우세
            if dx > 0:
                return box.right_mid()
            else:
                return box.left_mid()

    def _snap_entry(self, box: BoxRef, dx: float, dy: float) -> tuple:
        """
        박스 도착점 스냅 — 마지막 이동 방향(dx, dy)에 따라 박스 면 중심 반환.
        도착 방향이 dy<0이면 위에서 아래로 진행 → 위 면에서 도착
        """
        if abs(dx) < abs(dy):
            # 수직 이동 우세
            if dy < 0:  # 아래로 이동 → 위 면에 도착
                return box.top_mid()
            else:       # 위로 이동 → 아래 면에 도착
                return box.bot_mid()
        else:
            # 수평 이동 우세
            if dx < 0:  # 왼쪽으로 이동 → 오른쪽 면에 도착
                return box.right_mid()
            else:       # 오른쪽으로 이동 → 왼쪽 면에 도착
                return box.left_mid()

    def _extract_waypoints_ortho(self, page_pts: list) -> list:
        """
        Graphviz ortho spline 제어점 → arrow_route() waypoints.

        Graphviz plain 출력의 엣지 포인트 구조 (splines=ortho):
          - 4개 포인트: [p0, p1, p2, p3] (모두 같은 x 또는 y → 직선)
          - n*3+1개 포인트: B-spline 제어점 (꺾임 경로)
            형식: [start, c0a, c0b, c0c, c1a, c1b, c1c, ..., end]

        ortho 경우 제어점은 직교선 세그먼트를 이루므로:
          - 같은 x: 수직 세그먼트
          - 같은 y: 수평 세그먼트
          - 꺾임점 = 두 세그먼트의 교차점

        전략:
        1. 중복점 제거
        2. 연속된 동일 x/y 그룹의 대표점으로 압축
        3. 꺾임점(x→y 전환 또는 y→x 전환)만 추출

        Returns
        -------
        steps : list[(x, y)]  또는 빈 리스트
        """
        if not page_pts:
            return []

        # 1. 중복 제거 (같은 좌표 연속)
        unique = [page_pts[0]]
        for p in page_pts[1:]:
            last = unique[-1]
            if abs(p[0]-last[0]) > 0.001 or abs(p[1]-last[1]) > 0.001:
                unique.append(p)

        if len(unique) < 2:
            return []

        # 2. collinear 제거 - 직선상의 중간점 제거
        result = [unique[0]]
        for i in range(1, len(unique)-1):
            p0 = result[-1]
            p1 = unique[i]
            p2 = unique[i+1]
            # 세 점이 collinear인지 확인 (cross product ≈ 0)
            cross = (p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0])
            if abs(cross) > 0.001:  # 꺾임
                result.append(p1)
        result.append(unique[-1])

        return result

    def _extract_ortho_turns(self, pts: list, tol: float = 0.01) -> list:
        """
        Graphviz ortho spline 제어점에서 직교 꺾임점 추출.

        ortho spline에서 제어점은 3개씩 묶임:
          [ctrl1a, ctrl1b, ctrl1c, ctrl2a, ctrl2b, ctrl2c, ...]
        실제 꺾임점 = 각 그룹의 중간 점 (또는 x/y가 변하는 점)

        전략: 연속된 점들에서 x 또는 y가 변하는 전환점을 찾음.
        collinear한 점들은 제거.
        """
        if not pts:
            return []

        # 1. 중복 점 제거 (tol 이내)
        unique = self._deduplicate(pts, tol)
        if not unique:
            return []

        # 2. collinear 점 제거 (직선상의 중간점 제거)
        result = []
        for i in range(len(unique)):
            if i == 0 or i == len(unique) - 1:
                result.append(unique[i])
                continue
            p0 = unique[i-1]
            p1 = unique[i]
            p2 = unique[i+1]
            # x 방향으로 진행 중인지 y 방향으로 진행 중인지 확인
            dx1 = abs(p1[0] - p0[0])
            dy1 = abs(p1[1] - p0[1])
            dx2 = abs(p2[0] - p1[0])
            dy2 = abs(p2[1] - p1[1])
            # 방향이 바뀌면 꺾임점
            dir1_is_h = dx1 > dy1  # True=수평, False=수직
            dir2_is_h = dx2 > dy2
            if dir1_is_h != dir2_is_h:
                result.append(p1)
            # 같은 방향 계속이면 제거 (collinear)

        return result

    def _deduplicate(self, pts: list, tol: float = 0.05) -> list:
        """인접한 중복 점 제거."""
        if not pts:
            return pts
        result = [pts[0]]
        for p in pts[1:]:
            last = result[-1]
            dist = math.sqrt((p[0]-last[0])**2 + (p[1]-last[1])**2)
            if dist > tol:
                result.append(p)
        return result

    # ── 유틸리티 ──────────────────────────────────────────────────────────────

    def get_dot_source(self, with_sizes: bool = False) -> str:
        """디버깅용: 생성된 DOT 소스 반환."""
        if with_sizes:
            node_sizes = self._measure_node_sizes()
            return self._build_dot(node_sizes)
        return self._build_dot()

    def get_layout_info(self) -> dict:
        """디버깅용: Graphviz 레이아웃 계산 결과 반환 (실측 크기 포함)."""
        node_sizes = self._measure_node_sizes()
        dot_src = self._build_dot(node_sizes)
        plain   = self._run_graphviz(dot_src)
        return self._parse_plain(plain)


# ── 편의 함수 ─────────────────────────────────────────────────────────────────

def quick_graphviz(nodes: list, edges: list, output_path: str,
                   fig_label: str = 'FIG. 1',
                   orientation: str = 'portrait',
                   rankdir: str = 'TB') -> list:
    """
    간단한 일회성 도면 생성 헬퍼.

    Parameters
    ----------
    nodes : [{'id': str, 'text': str}, ...]
    edges : [{'src': str, 'dst': str, 'label': str, 'feedback': bool}, ...]
    output_path : str
    fig_label   : str
    orientation : str
    rankdir     : str

    Returns
    -------
    warnings : list[str]
    """
    layout = GraphvizLayout(fig_label, orientation=orientation, rankdir=rankdir)
    for n in nodes:
        layout.node(n['id'], n['text'], n.get('shape', 'box'))
    for e in edges:
        layout.edge(e['src'], e['dst'],
                    label=e.get('label', ''),
                    feedback=e.get('feedback', False),
                    bidir=e.get('bidir', False))
    return layout.render(output_path)
