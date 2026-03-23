# patent-drawing 설계 원칙

> 이 문서는 라이브러리의 아키텍처와 설계 철학을 정의합니다.
> 모든 코드 변경은 이 원칙을 따라야 합니다.

---

## 1. Core와 Pattern 분리

### Core (핵심)
패턴과 무관하게 변하지 않는 기본/핵심 기능.

| 영역 | 포함 내용 |
|------|----------|
| **Drawing 엔진** | Drawing 클래스, save(), 렌더링 파이프라인 (Pass 1~6) |
| **기본 도형** | BoxRef, CloudRef, box(), autobox(), line() |
| **기본 화살표** | arrow_h(), arrow_v(), arrow_bidir(), arrow_route(), arrow_diagonal() |
| **텍스트 처리** | measure_text(), _fit_font(), _normalize_node_text(), _wrap_text_to_width() |
| **레이아웃 기본** | boundary(), layer(), fig_label(), _center_all_boxes() |
| **검증 엔진** | _validate() — 모든 검증 항목 (#0~#14) |
| **참조번호** | ref_callout() (tilde/curve/bus), strip_ref |
| **좌표 계산** | BoxRef.edge_toward(), CloudRef.edge_toward(), _resolve_steps() |
| **크기 보장** | box() 자동 확장, container 폭 제한, equalize_heights/widths() |
| **Edge 자동 감지** | arrow_h/v/bidir 위치 기반 자동 선택 |

### Core 도형 (Shapes)
모든 패턴에서 사용하는 기본 빌딩블록.

| 도형 | 메서드 | 반환 | 설명 |
|------|--------|------|------|
| 직사각형 | `box()`, `autobox()` | BoxRef | 기본 블록. autobox는 텍스트 실측 자동 크기 |
| 구름 | `cloud()`, `autocloud()` | CloudRef | 타원 기반, 화살표 침범 방지 |
| IoT 스택 | `iot_stack()` | BoxRef | n개 사각형 비스듬히 겹침 |
| 실린더 DB | `database_cylinder()` | BoxRef | 상단 타원 + 몸체 |
| 타원 | `oval()` | BoxRef | 프로세서/처리 노드 |
| 둥근 사각형 | `rounded_rect()` | BoxRef | 플로우차트 터미네이터 |

### Core 화살표/연결선 (Arrows & Lines)

| 종류 | 메서드 | 설명 |
|------|--------|------|
| 수직 단방향 | `arrow_v(src, dst)` | 위치 자동 감지 |
| 수평 단방향 | `arrow_h(src, dst)` | 위치 자동 감지 |
| 양방향 수평/수직 | `arrow_bidir(a, b, side)` | 위치 자동 감지 |
| 꺾인 단방향 | `arrow_route(steps)` | elbow 화살표 |
| 꺾인 양방향 | `arrow_bidir_route(steps)` | elbow 양방향 |
| 대각선 단방향 | `arrow_diagonal(a, b)` | rect_edge 교차점 |
| 대각선 양방향 | `arrow_diagonal_bidir(a, b)` | rect_edge 교차점 |
| 양방향 fork | `arrow_fork_bidir(src, dsts)` | 1→N 분기 |
| Cloud 통과 | `arrow_to_cloud_child(ext, cloud, internal)` | Cloud 내부 도형 연결 |
| 무선 지그재그 | `arrow_wireless(a, b, label)` | sine wave + 화살촉 |
| 화살촉 없는 선 | `line(x1,y1,x2,y2,ls)` | 버스선, 구분선 등 |

### Core 선 스타일 (Line Styles)

| 스타일 | 값 | 용도 |
|--------|---|------|
| 실선 | `'-'` | 기본 연결 |
| 대시 | `'--'` | boundary, 무선 |
| dash-dot | `(0,(3,2,1,2))` | 내부 layer |
| 점선 | `':'` | lifeline |

### Core 라벨/참조번호 (Labels & Callouts)

| 종류 | 메서드 | 설명 |
|------|--------|------|
| 독립 라벨 | `label(x,y,text)` | 설명용 텍스트 |
| callout (물결) | `ref_callout(box,num,style='tilde')` | sine wave leader |
| callout (곡선) | `ref_callout(box,num,style='curve')` | 베지에 leader |
| 버스 callout | `ref_callout_bus(bus_x,num)` | 빈 공간 자동 탐색 |
| 반복 표현 | `ellipsis_repeat(a,b,lbl_a,lbl_b)` | A...N 패턴 |
| 다중 화살표 | `arrow_fanout_labeled(src,dsts)` | 라벨 붙은 fan-out |

### Core 무선/신호 (Wireless & Signal)

| 종류 | 메서드 | 설명 |
|------|--------|------|
| 신호 방사 | `wireless_signal(x,y,dir)` | `)))` 동심 호 |

### Core 컨테이너 (Containers)

| 종류 | 메서드 | 설명 |
|------|--------|------|
| 페이지 경계 | `boundary(x1,y1,x2,y2,label)` | 외곽 점선 (대시) |
| 내부 레이어 | `layer(x1,y1,x2,y2,label,dash)` | dash-dot (외곽과 구분) |
| 중괄호 | `brace(x1,y1,x2,y2,side,label)` | 그룹 표시 |

### Core 유틸리티 (Utilities)

| 기능 | 메서드 | 설명 |
|------|--------|------|
| 텍스트 측정 | `measure_text(text,fs)` | 렌더링 크기 실측 |
| 너비 통일 | `equalize_widths(boxes)` | 그룹 내 균일화 |
| 높이 통일 | `equalize_heights(boxes)` | 그룹 내 균일화 |
| FIG 라벨 | `fig_label(y)` | 하단 자동 배치 |

---

### Pattern (확장)
Core 기능을 조합하여 만든 도면 유형별 템플릿.

| 패턴 | 사용하는 Core |
|------|-------------|
| **layout(mode='flow')** | node(), connect(), box(), arrow_route(), _wrap_text_to_width() |
| **layout(mode='bus')** | node(), box(), line(), arrow_route(), layer() |
| **cloud()** | CloudRef, _render_cloud(), edge_toward() |
| **iot_stack()** | BoxRef, FancyBboxPatch |
| **arrow_fork_bidir()** | arrow_bidir_route(), BoxRef.right/left |
| **sequence_diagram** | box(), line(), arrow_route() |
| **swimlane_columns** | box(), layer(), boundary() |
| **database_cylinder** | BoxRef, matplotlib patches |
| **oval** | BoxRef, Ellipse |
| **arrow_wireless** | line(), sine wave |

---

## 2. 핵심 설계 원칙

### 2.1 "규칙이 명확하면 코드로, 판단이 필요하면 LLM으로"

| 코드가 할 일 | LLM이 할 일 |
|-------------|------------|
| 패딩/마진 보장 | 노드 텍스트/번호 결정 |
| 텍스트 오버플로우 래핑 | 도면 유형 선택 (flow/bus/radial) |
| 도형 겹침 감지 | 논리적 연결 관계 결정 |
| 화살표 방향 자동 감지 | 레이아웃 구조 설계 |
| container-child 크기 제한 | 어떤 정보를 도면에 넣을지 |
| 공간 낭비 경고 | 미적 판단 (사람이 리뷰) |

### 2.2 "검증이 생성보다 중요하다"

- save() 시 자동 검증 → 경고 0건이 목표
- 비전 모델 검증은 보조 수단, **좌표 계산으로 잡을 수 있는 건 코드로**
- 새 검증 항목 추가 시 기존 도면 리그레션 테스트 필수

### 2.3 "autobox > box"

- LLM이 크기를 직접 지정하면 실수함 → autobox() 우선 사용
- box()도 최소 크기 자동 보장 (텍스트+패딩)
- container 안의 box()는 container 폭 초과 불가 (자동 제한)

### 2.4 "offset 추측 금지"

- callout, 화살표 등에서 offset을 LLM이 추측하지 않음
- 텍스트 실측 → 좌표 역산 → 정확한 위치 결정
- 예: ref_callout()의 sine wave가 텍스트 끝~박스 변 사이를 정확히 채움

---

## 3. Core 확장 규칙

### 패턴 추가 시 Core 확장이 필요한 경우:

```
패턴 개발 중 Core 부족 발견
    ↓
해당 패턴만을 위한 것인가?
    ├─ YES → 패턴 내부에 구현 (private method)
    └─ NO (다른 패턴에도 유용) → Core에 범용적으로 추가
```

### Core 확장 시 체크리스트:
- [ ] 특정 패턴에 종속되지 않는 범용 API인가?
- [ ] 기존 Core API와 일관된 시그니처인가? (BoxRef 반환, 좌표 체계 등)
- [ ] 기존 validate와 호환되는가?
- [ ] 기존 도면 리그레션 없는가?
- [ ] SKILL.md에 사용법 문서화했는가?

### 예시:
| 상황 | 올바른 처리 |
|------|-----------|
| cloud()에서 타원 edge 계산 필요 | → Core에 CloudRef.edge_toward() 추가 (다른 타원 도형에도 사용 가능) |
| bus callout이 빈 공간 필요 | → Core에 ref_callout_bus() 추가 (모든 버스 도면에서 사용 가능) |
| sequence_diagram에서 lifeline 점선 | → 패턴 내부에 구현 (sequence 전용) |
| 도형 겹침 감지 | → Core validate #13 추가 (모든 도면에서 사용) |

---

## 4. 검증 체계

### 자동 검증 (save() 시 실행)
| # | 검증 | Core/Pattern |
|---|------|-------------|
| 0 | 텍스트 박스 초과 | Core |
| 1 | 박스 boundary 마진 | Core |
| 3 | 화살표 최소 길이 | Core |
| 6 | 참조번호 위치 | Core |
| 7 | Dangling head/tail | Core |
| 9a | 텍스트 최소 10pt | Core |
| 11 | 화살표 관통 | Core |
| 12 | 공간 낭비 | Core |
| 12b | line-line 접합 | Core |
| 13 | 도형 겹침 | Core |
| 14 | container-child overflow | Core |

### 수동 검증 (비전 모델)
- 화살표 방향 논리적 정확성
- 전체적 미적 판단
- 화살촉 가려짐 여부

---

## 5. Git 브랜치 전략

```
master (안정 버전, 태그 관리)
  ├── v1.0-andy-session
  ├── v2.0-taesung-session
  └── learn/{특허번호} 또는 learn/{패턴명}
       ├── 승인 → master merge + 태그
       └── 거절 → 브랜치 삭제 (master 무영향)
```

### 태그 규칙
- `vN.0-{작업자}-session` — 주요 세션 완료 시
- `vN.M` — 마이너 업데이트 (Core 확장 등)

---

## 6. 파일 구조

```
patent-drawing/
├── SKILL.md              ← 사용법 가이드 (LLM이 읽음)
├── DESIGN_PRINCIPLES.md  ← 이 문서 (설계 원칙)
├── CHANGELOG.md          ← 변경 이력
├── scripts/
│   └── patent_drawing_lib.py  ← Core + Pattern 코드
└── (upgrades/ 등은 브랜치로 관리)
```

### 향후 분리 고려
코드가 더 커지면 Core와 Pattern을 파일 분리:
```
scripts/
├── core.py           ← Drawing, BoxRef, CloudRef, validate
├── patterns/
│   ├── flow.py       ← layout(mode='flow')
│   ├── bus.py        ← layout(mode='bus')
│   ├── cloud.py      ← cloud(), autocloud()
│   ├── sequence.py   ← sequence_diagram()
│   └── ...
└── patent_drawing_lib.py  ← import all (하위 호환)
```

---

_최초 작성: 2026-03-23 (Andy Shim 요청)_
_기반: Andy 세션 원칙 + 태성 세션 교훈_
