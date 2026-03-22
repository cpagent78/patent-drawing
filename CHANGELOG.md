# patent-drawing 이슈 & 수정 이력

> 컴팩션 후 참고용. 실제 작업일: 2026-03-22 (Andy Shim)

---

## 버그 수정

### [BUG-01] bus layout 화살표 양방향 → 단방향으로 수정
- **증상**: bus 레이아웃에서 버스↔박스 연결이 양방향(`<->`) 화살촉으로 그려짐
- **원인**: `_layout_bus()` Step 5/6에서 `('bidir', ...)` 커맨드 사용
- **수정**: `('route', ...)` 커맨드로 교체 → 버스 출발, 박스에 화살촉 (단방향)
- **파일**: `patent_drawing_lib.py` `_layout_bus()`

### [BUG-02] bus 화살표 시작점과 버스선 사이 미세 gap
- **증상**: 버스선과 수직 연결선 사이에 육안으로 보이는 gap 발생
- **원인**: 화살표 시작점이 버스선 위에 정확히 겹쳐 matplotlib 렌더링 gap 발생
- **수정**: `BUS_OVERSHOOT = 0.02"` — 시작점을 버스선 반대편으로 0.02" 연장
- **파일**: `patent_drawing_lib.py` `_layout_bus()` Step 5/6

### [BUG-03] dangling tail 오검출 — bus 패턴 예외 처리 누락
- **증상**: 버스선 위에서 출발하는 화살표마다 `Dangling tail` 경고 발생
- **원인**: 검증 #7이 박스 edge만 허용하고 라인(line) 위 점을 미허용
- **수정**: `_on_bus_line()` 함수 추가 → 수평/수직 라인 위의 점은 dangling 예외 처리
- **파일**: `patent_drawing_lib.py` `_validate()`

### [BUG-04] 라벨 boundary 초과 미검출
- **증상**: `d.label()`로 추가한 독립 라벨이 boundary 밖으로 나가도 경고 없음
- **원인**: 기존 검증 #3이 라벨 기준점(x,y) 좌표만 확인하고 실제 렌더링 크기 미고려
- **수정**: 렌더링 후 `axes.transData.inverted()`로 실측 x0~x1, y0~y1 범위 전체 검증
- **파일**: `patent_drawing_lib.py` `_render()` Pass 5, `_validate()` 검증 #3b

### [BUG-05] 박스 텍스트 오버플로우 검증 부정확
- **증상**: 텍스트가 박스 밖으로 넘쳐도 검증 통과
- **원인**: 텍스트 크기 측정을 `bb.width / self.dpi` (픽셀/dpi) 방식 사용 → 과소 측정
- **수정**: `axes.transData.inverted()`로 data coordinate 기반 정확한 실측으로 교체
- **파일**: `patent_drawing_lib.py` `_render()` Pass 4, `_validate()` 검증 #0

### [BUG-06] 박스 내부 패딩 부족 미검출
- **증상**: 텍스트가 박스 내벽에 거의 붙어있어도 경고 없음 (숫자가 상변에 닿음)
- **원인**: 패딩 검증 로직 부재
- **수정**: 최소 내부 패딩 기준 추가 (수평 0.09", 수직 0.07") — 미달 시 경고
- **파일**: `patent_drawing_lib.py` `_validate()` 검증 #0 확장

### [BUG-07] 불필요한 `\n` 래핑으로 텍스트 3줄화
- **증상**: LLM이 `'340\nBid Transmission\nto Price Tags'` 처럼 본문에 `\n`을 넣으면 3줄이 되어 박스 높이 초과
- **원인**: LLM 습관적 래핑, 라이브러리에 자동 제거 로직 없음
- **수정**: `_normalize_node_text()` 추가 — 참조번호 뒤 첫 `\n` 이후 추가 `\n` → 스페이스 자동 치환
- **적용 범위**: `node()`, `autobox()` 진입점에서 자동 적용. `box()`는 이미 래핑된 텍스트 보호를 위해 미적용
- **파일**: `patent_drawing_lib.py`

### [BUG-08] bus layout — excess 축소 시 텍스트 너비 무시
- **증상**: 페이지 공간 초과 시 박스를 줄이다가 텍스트가 박스 밖으로 넘침
- **원인**: 2차 축소의 최솟값이 `0.8"`로 고정 — 텍스트 너비 미고려
- **수정**: `min_w = measure_text(nd.text) + 0.18"` 로 텍스트 기반 최솟값 보장
- **파일**: `patent_drawing_lib.py` `_layout_bus()` excess 처리

### [BUG-09] bus layout — 오버플로우 시 자동 래핑 없음
- **증상**: 박스 너비를 최대로 늘려도 텍스트가 여전히 넘치는 경우 그냥 그려짐
- **원인**: excess 축소 후 오버플로우 자동 처리 로직 부재
- **수정**: `_wrap_text_to_width()` 함수 추가 — 박스 너비 최종 확정 후 텍스트가 `(박스너비 - 0.18")` 초과 시 균등 2분할 래핑 자동 적용. 래핑 후 박스 높이 자동 확장 + 행 내 높이 재통일
- **적용**: bus 레이아웃 Step 2b, flow 레이아웃 내 동일 로직 추가
- **파일**: `patent_drawing_lib.py`

### [BUG-10] box() 내부 `_normalize_node_text()` 재호출로 의도적 래핑 파괴
- **증상**: `_wrap_text_to_width()`로 래핑된 텍스트가 `box()` 호출 시 다시 펴짐
- **원인**: `box()`에서 `_normalize_node_text()`를 재호출하여 래핑 후 `\n` → 스페이스 치환
- **수정**: `box()`에서 `_normalize_node_text()` 제거 — 정규화는 `node()`/`autobox()` 진입점에서만 1회 적용
- **파일**: `patent_drawing_lib.py` `box()`

### [BUG-11] NodeDef/node() pad_x 기본값이 layout() 기본값 무시
- **증상**: `_layout_bus()` pad_x 기본값 변경해도 노드에 반영 안 됨
- **원인**: `NodeDef.__init__`과 `node()` 시그니처에 `pad_x=0.20`이 하드코딩 → `nd.pad_x if nd.pad_x else pad_x` 조건에서 항상 `nd.pad_x` 사용
- **수정**: `NodeDef.__init__`, `node()` 의 `pad_x`, `pad_y` 기본값 → `None`으로 변경
- **파일**: `patent_drawing_lib.py`

### [BUG-12] bus layout — internal→external 박스 간 간격 과도
- **증상**: 100 점선 오른쪽 끝 ↔ external(60번) 박스 왼쪽 사이 간격이 너무 넓음
- **원인**: `ext_x = int_right + EXT_BND_GAP(0.30") + 0.50"` = 총 0.80" 여유
- **수정**: `ext_x = int_right + 0.44"` (최소 shaft만) — 불필요한 EXT_BND_GAP 제거
- **파일**: `patent_drawing_lib.py` `_layout_bus()`

### [BUG-13] flow TB 레이아웃 — 레이어 간 박스 너비 미통일
- **증상**: `layout(mode='flow', direction='TB')` 사용 시 각 박스 너비가 텍스트 길이에 따라 제각각
- **원인**: 레이어 내 크기 통일 로직이 있으나, TB direction에서 레이어 **간** 너비 통일 누락
- **수정**: TB direction에서 모든 레이어 노드의 너비를 `global_max_w`로 통일
- **파일**: `patent_drawing_lib.py` `layout()` Step 2b

---

## 신규 기능

### [FEAT-01] bus layout (`layout(mode='bus')`)
- 중앙 수평 버스선 + 상/하 행 배치 + external 노드 지원
- `boundary_label` 파라미터로 internal 점선 자동 생성
- 버스 → 박스 단방향 화살표 (표준 버스 다이어그램 패턴)

### [FEAT-02] `autobox()` — 텍스트 실측 기반 자동 박스 크기 결정

### [FEAT-03] `equalize_heights()` / `equalize_widths()` — 수동 box 그룹 크기 통일 헬퍼

### [FEAT-04] `_wrap_text_to_width()` — 박스 너비 초과 시 균등 2분할 자동 래핑

### [FEAT-05] `_normalize_node_text()` — LLM 불필요 `\n` 자동 제거

---

## 알려진 한계 (미해결)

| 항목 | 내용 |
|------|------|
| S10~S70 참조번호 경고 | 플로우차트 스텝 번호는 숫자 형식이 아니라 검증 #9c 경고 발생. 플로우차트에서는 의도적 — 무시 가능 |
| Dead-end 터미널 노드 경고 | 플로우차트 마지막 단계, 시스템 아키텍처 종단 노드 등은 정상적으로 outgoing 없음. 의도적 터미널은 경고 무시 가능 |
| bus dangling tail 경고 | BUS_OVERSHOOT 0.02" 적용 후 출발점이 버스선 위로 벗어나 dangling 예외로 처리됨. `_on_bus_line()` 으로 정상 처리 |
| 60번 external 박스 우측 마진 | 테스트용 텍스트("communication unit")가 길어 0.16" < 0.30" 경고. 실제 특허 텍스트 사용 시 해소 예정 |

---

## GitHub
- 라이브러리: https://github.com/cpagent78/patent-drawing
- 마지막 커밋: `e0fecd1` (flow TB: unify box width across all layers)
