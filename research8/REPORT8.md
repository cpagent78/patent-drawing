# Research 8 Report — PatentFigure 8차 자율 연구

**날짜**: 2026-03-24  
**엔진 버전**: patent_figure.py (Phase 8), edge_router.py (Research 8)

---

## 생성 도면 목록

| 파일 | 설명 | 기능 |
|------|------|------|
| `fig_B_korean.png` | 한글 결제 플로우 (10노드) | Phase 1: 한글 폰트 렌더링 |
| `fig_astar_test.png` | A* vs Cohen-Sutherland 비교 | Phase 2: A* 시각화 |
| `fig_C_triple_loopback.png` | 3중 루프백 + EdgeRouter | Phase 2: A* 통합 |
| `fig_3D_diamond_polish.png` | 다이아몬드 화살표 품질 | Phase 3: 꼭짓점 정확 출발 |
| `fig_A_16node_autosplit.png` | 16노드 플로우차트 1페이지 | Phase 4: auto_split |
| `fig_A_16node_autosplit_p2.png` | 16노드 플로우차트 2페이지 | Phase 4: auto_split |
| `fig_D_uspto.png` | USPTO 프리셋 스타일 | Phase 5: preset('uspto') |
| `fig_D_draft.png` | Draft 프리셋 스타일 | Phase 5: preset('draft') |
| `fig_D_presentation.png` | Presentation 프리셋 | Phase 5: preset('presentation') |
| `fig_INT_korean_draft.png` | 한글 + Draft 통합 | Phase 6: 통합 테스트 |
| `fig_6_regression.png` | FIG.6 회귀 테스트 | Phase 7: 회귀 |
| `fig_ER_regression.png` | EdgeRouter LR 회귀 | Phase 7: 회귀 |

---

## Phase 1: 한글 폰트 깨짐 완전 해결 ✅

### 문제
matplotlib 기본 폰트(DejaVu Sans)는 한글 미지원 → □□□□ 렌더링

### 해결
`patent_figure.py` 임포트 시 `_setup_korean_font()` 자동 실행:

```python
KOREAN_PRIORITY = [
    'Apple SD Gothic Neo',   # macOS 기본 한글 폰트 (우선 1순위)
    'AppleGothic',
    'AppleMyungjo',
    'Nanum Gothic',
    'NanumGothic',
    'Arial Unicode MS',
]
```

- `matplotlib.rcParams['font.sans-serif']` 앞에 감지된 폰트 삽입
- macOS에서 `Apple SD Gothic Neo` 정상 감지 및 적용 확인
- 모듈 수준에서 한 번 실행 (idempotent)

### 결과
`fig_B_korean.png`: 결제, 인증, 배송 등 한글 텍스트 정상 렌더링 확인

---

## Phase 2: EdgeRouter A* 경로 탐색 고도화 ✅

### 구현 내용 (`edge_router.py`)

#### `_astar_route()` 메서드 추가
- Grid-based A* 라우팅
- `grid_step=0.10"` (기본값, EdgeRouter 생성 시 조정 가능)
- 휴리스틱: Manhattan distance
- 비용: `move_cost(step) + bend_penalty(0.5)` — 직선 선호
- 장애물 블록: `MARGIN=0.08"` 확장으로 안전 거리 확보
- 성능 가드: `cols × rows ≤ 40,000`셀 제한 (그리드 자동 축소)

#### `_has_collision()` 메서드 추가
- Cohen-Sutherland bypass 후 충돌 잔존 여부 확인
- A* 자동 전환 조건

#### `route()` 업데이트
```python
def route(self, ..., use_astar=True):
    pts = self._build_initial_path(...)
    pts = self._avoid_obstacles(pts)
    if use_astar and self._has_collision(pts):
        astar_pts = self._astar_route(src, dst, ...)
        if astar_pts and not self._has_collision(astar_pts):
            pts = astar_pts
    return ...
```

#### `_simplify_path()` — collinear 점 제거
- 연속된 3점이 일직선이면 중간 점 제거
- A* 그리드 경로 → 간결한 waypoint 리스트

### 적용 기준
| 조건 | 라우팅 방식 |
|------|------------|
| 장애물 없음 | Z/L/U 기본 라우팅 (빠름) |
| bypass로 해결 | Cohen-Sutherland bypass |
| bypass 후 충돌 잔존 | A* 자동 전환 |

### 성능
- `fig_astar_test.png` 생성: bypass 5 waypoints → A* 4 waypoints (단순화됨)
- 30노드 도면 기준 < 0.5초 (40,000셀 이내)

---

## Phase 3: 다이아몬드 분기 화살표 품질 개선 ✅

### 문제
다이아몬드 화살표가 bbox_mid에서 출발 → 꼭짓점에서 부자연스럽게 이탈

### 해결 (`patent_figure.py` `_draw()`)
`_diamond_exit()` 헬퍼 함수 추가:
```python
def _diamond_exit(box, direction):
    if direction == 'down':  return (box.cx, box.bot)   # 하단 꼭짓점
    if direction == 'up':    return (box.cx, box.top)   # 상단 꼭짓점
    if direction == 'left':  return (box.left, box.cy)  # 좌측 꼭짓점
    if direction == 'right': return (box.right, box.cy) # 우측 꼭짓점
```

- 직선 하향 화살표: 하단 꼭짓점(`box.cx, box.bot`)에서 정확 출발
- 측면 분기: 좌/우 꼭짓점에서 출발
- Yes/No 라벨: 꼭짓점 위치 기준으로 배치 개선
  - 직선 하향: `(cx+0.10, bot-0.12)` (꼭짓점 바로 오른쪽)
  - 측면 분기: `(left-0.08, cy+0.12)` / `(right+0.08, cy+0.12)`

---

## Phase 4: render() 자동 분할 개선 ✅

### 구현
```python
def render(self, output_path, auto_split=True, max_nodes_per_page=14):
    if auto_split and len(self._nodes) > max_nodes_per_page:
        base, ext = os.path.splitext(output_path)
        path2 = base + '_p2' + ext
        return self.render_multi(output_path, path2)[0]
    # 기존 단일 페이지 렌더링
```

### 테스트 결과
- 16노드 플로우차트 → `fig_A_16node_autosplit.png` (페이지 1) + `fig_A_16node_autosplit_p2.png` (페이지 2)
- `auto_split=False` → 기존 동작 유지

---

## Phase 5: 스타일 프리셋 시스템 ✅

### 구현 (`preset()` 메서드)

| 프리셋 | 설정 |
|--------|------|
| `'uspto'` | line_width=1.0, arrow_scale=1.0 (표준 USPTO 중량) |
| `'draft'` | line_width=1.2, arrow_scale=1.1, corner_radius=0.08 (라운드 코너) |
| `'presentation'` | line_width=1.8, arrow_scale=1.4, corner_radius=0.10 (굵고 큼) |

```python
fig.preset('uspto')        # 흑백, 규격 엄격
fig.preset('draft')        # 라운드 코너, 주석 친화
fig.preset('presentation') # 굵은 선, 큰 화살촉
```

### 테스트 결과
3종 프리셋 비교 도면(`fig_D_*.png`) 생성 완료

---

## Phase 6: 복잡 도면 통합 테스트 ✅

### fig_INT_korean_draft.png
- 한글 텍스트 (주문 접수, 재고 확인, 결제 처리, 배송 준비, 배송 완료)
- `preset('draft')` 적용 → EdgeRouter 라운드 코너 활성화
- 6노드, 다이아몬드 분기 포함

---

## Phase 7: 회귀 테스트 ✅

### FIG.6 회귀 (`fig_6_regression.png`)
- 9노드, diamond(S410), node_group(S412/S414), 양방향 없음
- 동일 레이아웃 재현 확인

### EdgeRouter LR 회귀 (`fig_ER_regression.png`)
- LR 방향, bidir edge, container 그룹박스
- corner_radius=0.08 적용

---

## 버그 수정 내역

| 버그 | 수정 |
|------|------|
| 한글 □□□□ 렌더링 | `_setup_korean_font()` 자동 감지 + rcParams 설정 |
| 다이아몬드 화살표 부자연스러운 출발 | `_diamond_exit()` 헬퍼로 정확 꼭짓점 사용 |
| 16+노드 수동 분할 필요 | `render(auto_split=True)` 자동 처리 |

---

## 신기능 요약

1. **`_setup_korean_font()`** — 임포트 시 한글 폰트 자동 감지
2. **`EdgeRouter._astar_route()`** — Grid-based A* 최단 경로
3. **`EdgeRouter._has_collision()`** — 충돌 감지 (A* 전환 트리거)
4. **`EdgeRouter._simplify_path()`** — collinear 점 제거
5. **`PatentFigure.preset(name)`** — 스타일 프리셋 3종
6. **`PatentFigure.render(auto_split, max_nodes_per_page)`** — 자동 분할

---

## 9차 방향 (개선 제안)

1. **A* 성능 최적화**: 현재 python heapq 기반 → numpy/scipy.sparse 활용으로 50ms 이하 목표
2. **한글 폰트 다운로드 fallback**: `fc-list`에서 한글 폰트 없을 시 NanumGothic 자동 다운로드 (urllib)
3. **diamond arrow 품질 추가 개선**: 
   - 다이아몬드에서 Yes/No 동시 출발 시 충돌 방지 로직
   - 비스듬한 다이아몬드→다이아몬드 연결 최적화
4. **render_multi() 3페이지 이상 지원**: 현재 2페이지 한정 → N페이지 일반화
5. **from_spec() 한글 파싱 개선**: 한글 조건 키워드('성공', '실패', '예', '아니오') 인식 고도화
6. **validation 한글 인식**: 현재 한글 텍스트에 대한 참조번호 감지 오탐 수정
7. **interactive preview**: matplotlib GUI 모드에서 실시간 렌더 미리보기

---

## 파일 목록

```
research8/
  REPORT8.md                       # 이 파일
  test_phase1_korean.py            # Phase 1 테스트
  test_phase2_astar.py             # Phase 2 테스트
  test_phases_4567.py              # Phase 3-7 테스트
  fig_B_korean.png                 # 한글 결제 플로우
  fig_astar_test.png               # A* vs bypass 비교
  fig_C_triple_loopback.png        # 3중 루프백
  fig_3D_diamond_polish.png        # 다이아몬드 품질 개선
  fig_A_16node_autosplit.png       # 16노드 자동 분할 p1
  fig_A_16node_autosplit_p2.png    # 16노드 자동 분할 p2
  fig_D_uspto.png                  # USPTO 프리셋
  fig_D_draft.png                  # Draft 프리셋
  fig_D_presentation.png           # Presentation 프리셋
  fig_INT_korean_draft.png         # 한글+Draft 통합
  fig_6_regression.png             # FIG.6 회귀
  fig_ER_regression.png            # EdgeRouter 회귀
```
