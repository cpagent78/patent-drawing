---
name: patent-drawing
description: Generate USPTO-compliant patent drawings using Python matplotlib. Use when creating patent figures (block diagrams, flowcharts, data flow diagrams, system architecture), generating FIG. 1-N drawings for patent specifications, or fixing/regenerating existing patent drawings. Triggers on "patent drawing", "도면 생성", "FIG.", "특허 도면", "USPTO drawing".
---

# Patent Drawing Skill

Generate USPTO-compliant patent drawings using the `patent_drawing_lib.py` library (v2.6).

## Setup

Library location: `<skill_dir>/patent_drawing_lib.py`

Import in drawing scripts:
```python
import sys
sys.path.insert(0, '<skill_dir>')
from patent_drawing_lib import Drawing
```

## Quick Start

```python
d = Drawing("fig1.png", fig_num="1")
d.boundary(0.55, 1.10, 7.90, 10.15, label='1000')

# ✅ autobox: 텍스트 크기에 맞춰 박스 자동 결정 (권장)
b1 = d.autobox(2.0, 8.5, '100\nMy Component')
b2 = d.autobox(2.0, 7.3, '200\nNext Component')

# box: 크기 직접 지정 (레이아웃 강제 시)
# b1 = d.box(2.0, 8.5, 4.0, 0.7, '100\nMy Component')

d.arrow_v(b1, b2)
d.save()  # 자동 검증 + 저장
```

## ⚠️ 절대 규칙 (위반 시 도면 재생성)

### 1. 참조번호 배치
- 참조번호는 **반드시 텍스트 맨 첫 줄**에 단독 배치
- 참조번호 뒤에 **반드시 개행문자(\n)** 추가하여 본문과 분리
- 다른 도면 참조(교차참조)는 "see 810", "ref. 200" 형태로 별도 표기 가능

```python
# ✅ 올바른 예
'806\nMulti-Touch Attribution Engine'
'200\nPlatform Dashboard / Settlement System'

# ❌ 잘못된 예
'Multi-Touch Attribution Engine  806'     # 뒤에 붙음
'806  Multi-Touch Attribution Engine'     # 개행 없이 같은 줄
'Platform Dashboard / Settlement System  200'  # 뒤에 붙음
```

### 2. 화살표 양쪽 끝 도형 연결 (Dangling 금지)
- 모든 화살표의 **머리(head)와 꼬리(tail)는 반드시 어떤 박스의 변(edge)에 연결**
- 어떤 도형에도 안 닿는 화살표 → 잘못 그린 것 또는 불필요 → 즉시 제거/수정
- 라이브러리 v2.6이 자동 검증: `Dangling head/tail detected` 경고

### 3. 화살표 최소 길이
- 화살표는 **"화살표처럼 보여야"** 한다 — 촉(▶)만 보이고 shaft(선)가 없으면 실패
- **최소 shaft: 0.44"** (라이브러리 MIN_ARROW)
- **라벨 있는 화살표: 최소 0.80"** (라벨 텍스트가 보여야 함)
- 길이 부족 → **한두 박스만 밀지 말고 전체 도형 재배치**

### 4. 화살표 라벨 공간
- 화살표에 라벨이 있는데 도형 사이 간격이 부족하면 → 라벨이 잘려서 안 보임
- 해결: **도형 간 거리 확보를 위해 전체 레이아웃 재배치**
- 최소 라벨 구간 shaft: 0.80"

### 5. 화살촉이 도착 박스에 의해 가려지는 문제
- 화살표 shaft(선)는 박스 fill 뒤로 숨는 것이 정상 (깔끔한 진입)
- 하지만 **화살촉(▶)까지 가려지면 안 됨** — 화살표가 끊긴 것처럼 보임
- 근본 원인: 화살촉 zorder가 박스 fill zorder보다 낮을 때 발생
- 라이브러리 v5.1에서 Z_ARROWHEAD=13으로 수정하여 해결됨
- **검증**: 도착 박스 상단/좌측에 화살촉이 보이는지 비전 검증 시 확인

### 6. 화살표가 텍스트 관통 금지
- 화살표 경로가 다른 박스의 텍스트를 **관통(취소선처럼 보이는 현상)하면 안 됨**
- 해결: 화살표 방향 변경 또는 박스 위치 재배치

## 도면 생성 후 필수 검증 절차

### Step 1: 라이브러리 자동 검증 확인
`save()` 호출 시 자동 검증. `✓`이면 통과, `⚠`이면 반드시 수정.
```
✓  fig1.png                    → 통과
⚠  fig1.png                    → 수정 필요
   · Dangling head detected     → 화살표 끝이 도형에 안 닿음
   · Arrow too short             → 도형 간격 확보 필요
   · ref number at END           → 참조번호를 첫 줄로 이동
   · Labeled arrow too short     → 라벨 공간 확보 필요
```

### Step 2: 비전 모델 검증 (생성 후 반드시 실행)
이미지를 비전 모델에 보내서 확인:
```
화살표들이 모두 논리적으로 올바른지, 이상한 화살표
(방향 오류, dead-end, 겹침, 어색한 경로, 텍스트 관통)가 있는지 확인해줘
```

### Step 3: 체크리스트 (수동 확인)
아래 항목 중 ✅ 표시는 라이브러리가 자동 검증. 비전 모델로 확인 필요한 항목만 수동 체크.

- ✅ 모든 화살표의 머리/꼬리가 도형에 연결되어 있는가? (검증 #7)
- ✅ 화살표 shaft가 최소 0.44" 이상인가? (검증 #4)
- ✅ 화살표 라벨이 잘려 보이지 않는 곳은 없는가? (검증 #8)
- ✅ 참조번호가 박스 내부 맨 첫 줄에 있는가? (검증 #6, #9c)
- ✅ 참조번호가 아예 없는 박스는 없는가? (검증 #9c)
- ✅ 텍스트가 10pt 이상인가? (검증 #9a)
- ✅ 특수기호/유니코드 아래첨자 없는가? (검증 #9b)
- ✅ dead-end 노드(출력 화살표 없는 중간 박스)가 없는가? (검증 #10)
- ✅ 화살표가 다른 박스 텍스트를 관통하지 않는가? (검증 #11)
- [ ] 모든 박스 텍스트가 잘림 없이 완전히 보이는가? (비전 확인)
- [ ] 화살촉(▶)이 도착 박스의 흰색 fill에 가려지지 않는가? (비전 확인)
- [ ] 화살표 방향이 논리적으로 올바른가? (비전 확인)

### Step 4: 문제 발견 시
1. 코드 수정
2. 재생성
3. Step 1~3 반복
4. `✓` + 비전 통과 + 체크리스트 전체 통과 시에만 완료

## API Reference

### 핵심 메서드
| 메서드 | 용도 |
|--------|------|
| `Drawing(filename, fig_num)` | 새 도면 생성 |
| `boundary(x1,y1,x2,y2,label)` | 전체 시스템 경계 (dashed) |
| `autobox(x,y,text,fs,pad_x,pad_y)` | **텍스트 실측 후 박스 크기 자동 결정** (권장) |
| `box(x,y,w,h,text,fs)` | 박스 + 텍스트, 크기 직접 지정 (→ BoxRef) |
| `measure_text(text,fs)` | 텍스트 렌더링 크기 측정 → (width_in, height_in) |
| `arrow_v(src,dst,label)` | 수직 직선 화살표 |
| `arrow_h(src,dst,label)` | 수평 직선 화살표 |
| `arrow_route(steps,label,label_pos)` | 꺾인 화살표 |
| `line(x1,y1,x2,y2)` | 화살촉 없는 연결선 |
| `label(x,y,text)` | 독립 텍스트 라벨 |
| `fig_label(y)` | FIG. N 라벨 |
| `save()` | 렌더링 + 자동 검증 + PNG 저장 |

### BoxRef 속성
```python
b.cx, b.cy         # 중심 좌표
b.top, b.bot        # 상하 y
b.left, b.right     # 좌우 x
b.top_mid()         # (cx, top)
b.bot_mid()         # (cx, bot)
b.left_mid()        # (left, cy)
b.right_mid()       # (right, cy)
b.side("top")       # top_mid() 과 동일
```

### arrow_route steps 명령어
```python
(x, y)              # 절대 좌표
("right_to", x)     # x까지 수평 이동
("left_to", x)      # x까지 수평 이동
("up_to", y)        # y까지 수직 이동
("down_to", y)      # y까지 수직 이동
("right", dx)       # dx만큼 우측
("left", dx)        # dx만큼 좌측
("up", dy)          # dy만큼 상승
("down", dy)        # dy만큼 하강
```

## 라이브러리 자동 검증 항목 (v5.2)

| # | 검증 | 내용 |
|---|------|------|
| 1 | 박스 boundary 내부 | 모든 박스가 boundary 안에 있는지 |
| 2 | 박스 마진 | boundary와 최소 0.30" 여백 |
| 3 | 라벨 boundary 내부 | 독립 라벨이 boundary 넘지 않는지 |
| 4 | 화살표 최소 길이 | shaft ≥ 0.44" (MIN_ARROW) |
| 5 | 라벨 박스 겹침 | 라벨이 박스 내부에 위치하는지 |
| 6 | 참조번호 위치 | 텍스트 뒤에 참조번호 붙으면 경고 |
| 7 | 화살표 양끝 연결 | Dangling head/tail 감지 |
| 8 | 라벨 화살표 길이 | 라벨 있는 화살표 shaft ≥ 0.80" |
| 0 | 텍스트 박스 초과 | 실측 렌더링 크기로 텍스트가 박스 밖으로 나가는지 검사 |
| 9a | 텍스트 최소 10pt | auto-fit 결과가 10pt 미달이면 경고 (§1.84(p)(3)) |
| 9b | 특수기호/아래첨자 | ★ © ₁ 등 인쇄 불안전 문자 감지 |
| 9c | 참조번호 누락 | 박스 첫 줄에 3~4자리 숫자 없으면 경고 |
| 10 | Dead-end 박스 | 입력↑ 출력=0인 중간 박스 자동 감지 |
| 11 | 화살표 관통 | 화살표 경로가 박스 텍스트 영역 관통 감지 |

## USPTO 형식 규칙

| 규칙 | 내용 |
|------|------|
| 텍스트 크기 | 최소 10pt (§1.84(p)(3)) |
| 폰트 | 균일 weight, bold 금지 (§1.84(p)(1)) |
| 색상 | 흑백만, 회색 음영 금지 (§1.84(m)) |
| FIG. 라벨 | `FIG. N` 형식, boundary 아래 중앙 (§1.84(u)) |
| 참조번호 | 모든 요소에 번호. 도면 = 명세서 번호 (§1.84(p)) |
| 특수기호 | ★ 같은 장식 기호 지양, 텍스트로 대체 |
| 아래첨자 | t₁ → t1 (인쇄 안전성) |

## 레이아웃 설계 원칙

### 도형 재배치 우선 원칙
- 화살표 길이 부족 → **해당 화살표만 늘리지 말고 전체 도형 재배치**
- 라벨 공간 부족 → **전체 레이아웃 재조정**
- 한 도형만 밀면 다른 곳에서 문제 발생 → 연쇄 수정 필요

### 라우팅 채널 패턴 (피드백 루프)
```
Left channels:  x < content_left
Content column: CL ~ CR
Right channel:  x > content_right
```

### 박스 간격 가이드
| 구간 | 최소 간격 |
|------|-----------|
| 수직 화살표 (라벨 없음) | 0.44" |
| 수직 화살표 (라벨 있음) | 0.80" |
| 수평 화살표 (라벨 없음) | 0.44" |
| 수평 화살표 (라벨 있음) | 0.80" |
| 박스 ↔ boundary | 0.30" |

## 과거 실수 교훈 (반복 금지)

| 실수 | 근본 원인 | 해결 |
|------|-----------|------|
| 참조번호 텍스트 뒤에 붙음 | 습관적으로 "Description 200" 형태 사용 | 첫 줄에 번호 단독 + \n |
| 화살표가 텍스트 관통 (취소선처럼 보임) | 박스 옆에 바로 붙여서 수평 화살표 | 박스 위/아래로 우회하거나 재배치 |
| 화살표 촉만 보이고 shaft 없음 | 도형 간격 0.2" 등 부족 | 전체 재배치로 0.44" 이상 확보. 10+ 박스 시 박스 높이(min 0.45")를 줄이되 간격(min 0.40")은 절대 줄이지 말 것. 분기점 전후는 0.45" 이상 |
| 라벨 잘려서 안 보임 | 도형 사이 공간에 라벨이 안 들어감 | 도형 간 0.80" 이상 확보 |
| dead-end 박스 | 출력 화살표 연결 누락 | 생성 후 비전 모델로 검증 |
| "model config" 화살표 뜬금없음 | 화살표 양쪽 끝이 도형 안 닿음 | Dangling 검증 통과 필수 |
| 동사 시제 불일치 | viewed/browsed vs add/purchase | 동일 카테고리 내 시제 통일 |
| float 오차로 0.44"가 경고 | 부동소수점 비교 | 라이브러리에 epsilon 보정 적용됨 |
| 화살촉이 도착 박스에 가려짐 | Z_ARROWHEAD < Z_BOX_FILL + 대각선 화살촉 날개가 박스 안으로 진입 | Z_ARROWHEAD=13 + 대각선 금지: arrow_v 사용 시 cx 같은지 확인, 다르면 elbow 라우팅 |
| arrow_v로 cx 다른 박스 연결 시 대각선 | arrow_v가 src.cx→dst.cx 직선이라 cx 다르면 사선 | cx 다르면 arrow_route로 elbow(수직+수평+수직) 사용 |
| 화살표 라벨이 인접 박스 텍스트와 겹침 | 좌측 채널 수직 구간에 라벨 배치 시 옆 박스와 근접 | label_pos를 박스가 없는 구간으로 변경. 공간 부족 시 라벨 제거(명세서에서 설명) |
| elbow 화살표 경유점이 밀집하여 교차/혼잡 | 여러 elbow가 같은 VIA_Y에서 수평 이동 | 출발점을 src 하변에서 분산, 각각 다른 x에서 출발 |
| 피드백 루프 라벨이 boundary 밖으로 벗어남 | 좌측/우측 채널이 boundary edge에 너무 가까움 | 라벨 제거하고 화살표만 유지, 또는 채널 x를 boundary+0.30 이상으로 |

## v2.0 신규 기능 (IoT/Cloud 도면)

### Cloud 도형
```python
# 기본: 크기 직접 지정
c = d.cloud(cx, cy, w, h, '310\nCloud')

# 자동: 텍스트에 맞게 크기 결정
c = d.autocloud(cx, cy, '310\nDevice Owner', max_w=3.0)
```
- CloudRef 반환 → 화살표가 구름 실제 외곽(타원+bubble_r) 밖에서 출발/도착
- `arrow_to_cloud_child(ext, cloud, internal)` → Cloud 통과 화살표

### IoT Stack (복수 디바이스)
```python
s = d.iot_stack(x, y, w, h, '812\nMesh Devices', n=3)
```

### Callout (외부 참조번호)
```python
# tilde 스타일 (기본) — 짧은 곡선/물결선으로 박스 변에 연결
d.ref_callout(b, '830', side='left')
d.ref_callout(b, '830', side='left', strip_ref=True)  # 박스 내 번호 제거

# curve 스타일 — 베지에 곡선 leader line
d.ref_callout(b, '910', side='right', style='curve')

# 버스선 callout — 빈 공간 자동 탐색
d.ref_callout_bus(BUS_X, '806')
```

### 양방향 Fork
```python
d.arrow_fork_bidir(iface, [sensors, actuators])
d.arrow_fork_bidir(iface, [sensors, actuators], via_x=5.8)
```

### Layer (Container 점선)
```python
# dash='short' (기본): dash-dot → 외곽 boundary와 시각적 구분
d.layer(x1, y1, x2, y2, label='808 Storage')
d.layer(x1, y1, x2, y2, label='808 Storage', dash='dotted')
```

## v2.0 필수 규칙 (코드가 강제)

### 1. autobox() 우선 사용
- `box()`도 텍스트+패딩 부족 시 자동 확장됨
- 단, `autobox()` 사용이 권장 — 크기 계산을 코드에 맡기기
- container(layer) 안의 box()는 container 폭을 초과하지 않도록 자동 제한

### 2. 수동 좌표 계산 최소화
- `layout(mode='flow'|'bus')` 사용 권장
- 수동 배치 시에도 `equalize_heights()`, `equalize_widths()` 활용
- 공간 낭비 65% 이상이면 validate 경고

### 3. 화살표 방향 자동 감지
- `arrow_h()`, `arrow_v()`, `arrow_bidir()` 모두 박스 상대 위치 자동 감지
- LLM이 left/right 방향 신경 안 써도 됨

### 4. 도형 겹침 자동 감지 (validate #13)
- 모든 BoxRef/CloudRef 쌍에 대해 부분 겹침 경고
- container 완전 포함은 허용 (layer-child 관계)

### 5. container-child overflow 자동 감지 (validate #14)
- layer 안의 box가 layer 밖으로 벗어나면 경고

## v2.0 교훈 (LLM 실수 방지)

| 실수 | 근본 원인 | 해결 |
|------|-----------|------|
| 수동 box()로 패딩 부족 | autobox 파이프라인 우회 | box() 자동 확장 + autobox 권장 |
| Cloud와 인접 박스 겹침 | 겹침 검증 부재 | validate #13 추가 |
| container보다 큰 서브블록 | 자동 확장 시 container 제한 없음 | box()에 layer 폭 제한 |
| callout이 대상에 안 닿음 | tilde 문자 → 폰트 의존 | sine wave 직접 그리기 |
| 버스 callout 위치 어색 | LLM 수동 배치 | ref_callout_bus() 빈 공간 자동 탐색 |
| 점선 계층 구분 안 됨 | boundary/layer 동일 스타일 | layer dash-dot 패턴 |

## 페이지 방향 (Orientation)

```python
# 세로 (기본, 8.5" × 11")
d = Drawing("fig1.png", fig_num="1")

# 가로 (11" × 8.5") — 수평 파이프라인, 타임라인 등에 적합
d = Drawing("fig1.png", fig_num="1", orientation='landscape')
```

- `portrait` (기본): 세로 8.5" × 11" — 블록다이어그램, 플로우차트, bus
- `landscape`: 가로 11" × 8.5" — 파이프라인, 시퀀스, swimlane, 타임라인

---

## PatentFigure — 선언적 플로우차트 엔진

`patent_figure.py`는 노드와 엣지만 선언하면 자동으로 레이아웃과 라우팅을 처리하는 고수준 엔진이다.
특허 플로우차트(flowchart)에 최적화. `patent_drawing_lib.py`의 저수준 API 위에서 동작한다.

### Import

```python
import sys
sys.path.insert(0, '<skill_dir>/scripts')
from patent_figure import PatentFigure
```

### 기본 사용법

```python
fig = PatentFigure('FIG. 6')

# 노드 추가 (순서가 레이아웃 순서)
fig.node('S400', '400\nStart', shape='start')
fig.node('S410', '410\nProcess Input')
fig.node('S420', '420\nValid?', shape='diamond')
fig.node('S430', '430\nContinue')
fig.node('S440', '440\nEnd', shape='end')

# 엣지 추가 (자동 back-edge 탐지)
fig.edge('S400', 'S410')
fig.edge('S410', 'S420')
fig.edge('S420', 'S430', label='Yes')
fig.edge('S420', 'S410', label='No')   # 루프백 자동 탐지
fig.edge('S430', 'S440')

# 렌더링
fig.render('fig6.png')
```

### 도형 옵션 (shape=)

| shape | 외형 | 용도 |
|-------|------|------|
| `'process'` (기본) | 사각형 | 일반 처리 단계 |
| `'start'` | 둥근 사각형 | 시작 노드 |
| `'end'` | 둥근 사각형 | 종료 노드 |
| `'diamond'` | 마름모 | 조건 분기 (Yes/No) |
| `'oval'` | 타원 | 대안 시작/종료 |
| `'cylinder'` | 실린더 | 데이터베이스 |

### 방향 (direction=)

```python
# 위→아래 플로우차트 (기본)
fig = PatentFigure('FIG. 6', direction='TB')

# 왼→오른 블록 다이어그램
fig = PatentFigure('FIG. 2', direction='LR')
```

- **TB (top-bottom)**: 플로우차트, 워크플로우에 적합. 루프백 자동 지원.
- **LR (left-right)**: 데이터 파이프라인, 아키텍처 계층 다이어그램. 3-4 컬럼 권장.

### 양방향 화살표 (bidir=True)

```python
fig.edge('A', 'B', bidir=True)   # ↔ 양쪽 화살촉
```

### 컨테이너 그룹핑

```python
# 여러 노드를 점선 박스로 묶기 (레이아웃 후 장식적 추가)
fig.container('grp1', ['S410', 'S420'], label='210\nProcessing Layer')
```

- `id`: 컨테이너 고유 ID
- `node_ids`: 포함할 노드 ID 목록
- `label`: 박스 위에 표시할 텍스트 (참조번호\n이름 형식 권장)
- `pad`: 노드 주변 여백 (기본 0.14")

### 딥 플로우 자동 분할 (`render_multi`)

9개 이상 노드는 단일 페이지에 물리적으로 들어가지 않을 수 있다.
`render_multi()`를 사용하면 자동으로 두 페이지로 분할한다.

```python
fig = PatentFigure('FIG. 5')
# 12개 노드 추가...
fig.edge(...)

# 자동 분할: fig5a.png (앞부분) + fig5b.png (뒷부분)
fig.render_multi('fig5a.png', 'fig5b.png')

# 분할 위치 지정 (0-based 인덱스)
fig.render_multi('fig5a.png', 'fig5b.png', split_at=7)
```

- 각 페이지 하단/상단에 `(A) Cont'd` 연결 심볼 자동 추가
- 분할 위치는 `split_at` 파라미터로 조정 (기본: 중간)
- 현재 2페이지까지만 지원

### 루프백 (Loop-back) 자동 처리

```python
fig.edge('S420', 'S410', label='Retry')  # 뒤로 가는 엣지: 자동 감지
```

- DFS로 back-edge 자동 감지
- 좌측 채널(left side channel)로 자동 라우팅
- 2중 루프: 각 루프가 별도 채널 사용 (내부 루프 가까이, 외부 루프 멀리)

### skip-rank 엣지

```python
# rank 차이가 2 이상인 엣지 — 중간 박스를 통과하지 않도록 우측 채널 라우팅
fig.edge('S100', 'S400', label='Skip')   # rank 0 → rank 3
fig.edge('S200', 'S500', label='Fast')   # rank 1 → rank 4 (별도 채널)
```

- 여러 skip-rank 엣지는 각각 다른 우측 채널 레인 할당
- 작은 rank 차이 = 안쪽 레인, 큰 rank 차이 = 바깥쪽 레인

### 레이아웃 규칙

1. **노드 추가 순서 = 레이아웃 순서**: `fig.node()` 호출 순서대로 위에서 아래로 배치
2. **같은 레이어**: 동시에 에지를 받는 노드들은 같은 행에 나란히 배치
3. **자동 폰트 축소**: 공간이 부족하면 8pt→7pt→6pt 자동 시도 (10pt 이하 경고는 무시 가능)
4. **컨테이너는 레이아웃에 영향 없음**: 노드 위치 결정 후 장식적으로 추가

### 한계 및 권고사항

| 한계 | 설명 | 권고 |
|------|------|------|
| 9+ 노드 단일 라인 텍스트 제한 | 물리적 공간 부족 | `render_multi()` 사용 또는 텍스트 단축 |
| LR 레이아웃 5컬럼 이상 | 텍스트 압축 발생 | 3-4컬럼 권장, 짧은 라벨 사용 |
| 2중 루프 시각적 혼잡 | 루프 경로가 노드와 근접 | 루프 수를 2개 이하로 제한 |
| T-junction 경고 | N-way 분기 시 발생 | 경고는 무시 가능 (시각적으로 OK) |
| LR 루프백 | LR 방향에서 back-edge 미지원 | TB 방향 사용 |
| 10pt 폰트 경고 | 딥 플로우에서 자동 축소 시 발생 | 텍스트 단축 또는 render_multi 사용 |

### 완전한 예제

```python
import sys
sys.path.insert(0, '<skill_dir>/scripts')
from patent_figure import PatentFigure

# 특허 주문 처리 플로우 FIG. 3
fig = PatentFigure('FIG. 3')

fig.node('S500', '500\nReceive Order', shape='start')
fig.node('S502', '502\nValidate Input')
fig.node('S504', '504\nCheck Inventory', shape='diamond')
fig.node('S506', '506\nAlert: Out of Stock')
fig.node('S508', '508\nProcess Payment', shape='diamond')
fig.node('S510', '510\nNotify Failure')
fig.node('S512', '512\nCreate Shipment')
fig.node('S514', '514\nEnd', shape='end')

fig.edge('S500', 'S502')
fig.edge('S502', 'S504')
fig.edge('S504', 'S506', label='No')
fig.edge('S504', 'S508', label='Yes')
fig.edge('S506', 'S502')             # 루프백 자동 탐지
fig.edge('S508', 'S510', label='No')
fig.edge('S508', 'S512', label='Yes')
fig.edge('S510', 'S508')             # 루프백
fig.edge('S512', 'S514')

fig.render('fig3.png')
```

### patent_drawing_lib vs PatentFigure 선택 기준

| 상황 | 권장 도구 |
|------|---------|
| 플로우차트, 워크플로우 | **PatentFigure** |
| 시스템 아키텍처 블록다이어그램 | **PatentFigure** `direction='LR'` |
| 시퀀스 다이어그램 | **PatentSequence** (Research 9 신규) |
| 수평 파이프라인 (3-5 단계) | **PatentFigure** `direction='LR'` |
| 버스 아키텍처 (CPU-Memory-Bus) | **PatentFigure + bus()** (Research 9 신규) |
| 수동 좌표가 필요한 특수 레이아웃 | `patent_drawing_lib` 직접 사용 |
| 9+ 노드 플로우차트 | **PatentFigure + render_multi()** |

---

## Phase 9 신기능 (Research 9)

### 1. from_spec() 정확도 개선

```
# 진단 키워드 자동 → diamond 형태
S400: 신뢰도 여부 판단          → diamond (여부 판단 감지)
S700: 전문의 승인 여부 판단      → diamond (여부 판단 감지)

# "후 종료" 패턴 → 자동 End 노드 분기
S800: 거부 시 수동 프로세스로 전환 후 종료   → diamond + _end_S800 END 노드 생성
S300: 실패 시 거부 후 종료                  → diamond + _end_S300 END 노드 생성

# 병렬 노드 (S600a, S600b, S600c) → node_group() 자동 적용
S600a: 토큰 잔액 차감 처리
S600b: 수신자 잔액 증가 처리
S600c: 트랜잭션 로그 기록
→ 세 노드가 같은 행에 나란히 배치됨

# 참조번호: Sxxx → 숫자만 (S100 → 첫 줄 "100")
# from_spec() 생성 노드는 모두 USPTO 참조번호 규칙 자동 준수
```

### 2. bus() — 버스 연결 토폴로지

```python
fig = PatentFigure('FIG. 6', direction='LR')
fig.node('CPU',   '610\nCPU', shape='process')
fig.node('MEM',   '620\nMemory', shape='process')
fig.node('GPU',   '630\nGPU', shape='process')
fig.node('STORE', '640\nStorage', shape='cylinder')

fig.node_group(['CPU', 'MEM', 'GPU', 'STORE'])

# 수평 버스 바 그리기 — 각 노드에서 stub 연결
fig.bus('DATA_BUS', ['CPU', 'MEM', 'GPU', 'STORE'],
        label='810\nData Bus', orientation='H')

# 수직 버스: orientation='V' (노드 오른쪽에 수직 버스)
```

### 3. edge() label_back — 양방향 화살표 각각 라벨

```python
# 단방향 (기존)
fig.edge('A', 'B', label='request')

# 양방향 — 양쪽 라벨 각각
fig.edge('A', 'B', label='request', label_back='response', bidir=True)
# 결과: 화살표 위에 "request", 아래에 "response"
```

### 4. PatentSequence — 시퀀스 다이어그램

```python
import sys
sys.path.insert(0, '<skill_dir>/scripts')
from patent_figure import PatentSequence

fig = PatentSequence('FIG. 3')

# 액터 등록 (왼→오른 순서로 균등 배치)
fig.actor('User',   'user')
fig.actor('Server', 'server')
fig.actor('DB',     'db')

# 메시지 (순서대로 위→아래)
fig.message('user',   'server', 'login(id, pw)')
fig.message('server', 'db',     'query(id)')
fig.message('db',     'server', 'result',       return_msg=True)  # 점선 ←
fig.message('server', 'user',   'JWT token',    return_msg=True)  # 점선 ←

fig.render('fig3_seq.png')
```

- `return_msg=True` → 점선 화살표 (응답 메시지)
- 생략 시 → 실선 화살표 (요청 메시지)
- 액터 수직 라이프라인 자동 그리기
- 메시지 수가 많을수록 자동으로 수직 간격 확보

### 5. 에러 복구 (Phase 9)

```python
# 빈 텍스트 → 경고 + id 사용
fig.node('S100', '')   # warning: empty text, uses 'S100'

# 중복 ID → 경고 + 덮어쓰기
fig.node('S100', 'First')
fig.node('S100', 'Second')  # warning: duplicate id, overwrites

# 200자+ 텍스트 → 자동 줄바꿈 + 경고
fig.node('S200', '매우긴텍스트' * 30)  # warning + auto-wrap

# validate()에서 순환 감지
warnings = fig.validate()
# → "Cycle detected (will be treated as back-edge): S100 → S200 → S100"
```

### 6. 한글 폰트 자동 설정 (Research 8)

한글 텍스트 사용 시 특별한 설정 필요 없음:

```python
# 그냥 한글로 쓰면 됨 — Apple SD Gothic Neo 자동 감지
fig.node('S100', '100\n환자 데이터 수집', shape='start')
fig.node('S200', '200\n데이터 전처리')

# 확인: import 시 자동으로 폰트 설정됨
# from patent_figure import PatentFigure  ← 이 줄에서 _setup_korean_font() 실행
```

지원 폰트 우선순위:
1. Apple SD Gothic Neo (macOS 기본 — 권장)
2. AppleGothic
3. NanumGothic / NanumMyeongjo
4. Arial Unicode MS
5. DejaVu Sans (폴백 — 한글 미지원)

### 7. 스타일 프리셋 (Research 8)

```python
fig.preset('uspto')        # 표준 USPTO — 실선, 표준 크기
fig.preset('draft')        # 초안 — 두꺼운 선, 라운드 코너
fig.preset('presentation') # 발표용 — 굵은 선, 큰 화살촉
```

### 8. EdgeRouter corner_radius (Research 7-8)

```python
fig.preset('draft')  # corner_radius=0.08 자동 설정
# 또는 직접:
fig.style(corner_radius=0.10)  # 라운드 코너 반경 (인치)
```

`corner_radius`가 설정되면 EdgeRouter가 활성화되어:
- 베지에 곡선 라운드 코너 렌더링
- A* 격자 기반 장애물 회피 자동 활성화 (교차 감지 시)

---

## 특허방 모모 빠른 시작 (v2.0)

사용자가 명세서 텍스트를 주면 **한 줄**로 도면 생성:

```python
import sys
sys.path.insert(0, '<skill_dir>/scripts')
from patent_figure import quick_draw

# 한글 명세서
spec = """
S100: 사용자 위치 정보 수신
S200: 주변 가맹점 검색 (반경 500m)
S300: 검색 결과 없을 경우 반경 확장 후 S200으로 복귀
S400: 가맹점 목록 정렬 (거리순, 평점순)
S500: 사용자에게 추천 목록 제공
S600: 사용자 선택 수신
S700: 선택 가맹점으로 경로 안내 시작
"""
result = quick_draw(spec, 'fig1.png')

# result['pages']      → ['fig1.png']  (생성된 파일 목록, 11개+ 시 2페이지)
# result['node_count'] → 7             (파싱된 노드 수)
# result['warnings']   → []            (구조 경고 목록)
# result['validation'] → {'passed': True, 'issues': []}
# result['elapsed_sec']→ 0.1           (생성 소요 시간)
```

### quick_draw() API

```python
def quick_draw(
    spec_text: str,       # 명세서 텍스트 (S100: ... 형식)
    output_path: str,     # 출력 PNG 경로
    preset: str = 'uspto',        # 'uspto' | 'draft' | 'presentation'
    lang: str = 'auto',           # 'auto' | 'ko' | 'en'  (현재 자동 감지)
    direction: str = 'TB',        # 'TB' (위→아래) | 'LR' (좌→우)
    fig_label: str = 'FIG. 1',    # FIG. 라벨
) -> dict
```

**반환값:**
| 키 | 타입 | 설명 |
|---|---|---|
| `pages` | `list[str]` | 생성된 PNG 경로 (1~2개) |
| `node_count` | `int` | 파싱된 노드 수 |
| `warnings` | `list[str]` | 구조 경고 (루프, 중복 등) |
| `validation` | `dict` | `{'passed': bool, 'issues': list}` |
| `elapsed_sec` | `float` | 생성 소요 시간 |

### 자동 처리 항목
- **한글/영어 자동 감지**: from_spec()이 판별
- **자동 2페이지 분할**: 노드 14개 초과 시 `_p2.png` 생성
- **USPTO preset 자동 적용**: 흑백, 10pt 이상, FIG. 라벨 규격 준수
- **루프 자동 감지**: `후 S200으로 복귀` → back-edge 자동 처리

### USPTO 규격 검증 (validate_uspto.py)

```bash
# 생성된 PNG 파일 검증
python scripts/validate_uspto.py research10/
python scripts/validate_uspto.py fig1.png -v
```

---

## 현재 기능 목록 (v2.5 완성)

| 기능 | 메서드 | 설명 |
|---|---|---|
| **고수준 API** | `quick_draw()` | 명세서 텍스트 → PNG 한방 생성 |
| **선언적 엔진** | `PatentFigure` | 좌표 0개, 자동 레이아웃 |
| **자동 파싱** | `from_spec()` | 한글/영어 명세서 → 노드/엣지 자동 생성 |
| **6종 노드** | `node(shape=)` | start/end/process/diamond/oval/cylinder |
| **엣지** | `edge()` | bidir, label_back, 루프 자동 처리 |
| **컨테이너** | `container()` | 점선 그룹 박스 |
| **노드 그룹** | `node_group()` | 병렬 노드 정렬 |
| **강조** | `highlight()` | 특정 노드 배경색 |
| **주석** | `add_note()` | 말풍선 주석 |
| **역공학** | `export_spec()` | 도면 → 명세서 텍스트 |
| **검증** | `validate()` | 구조 사전 검증 |
| **다중 페이지** | `render_multi()` | 2페이지 분할 |
| **자동 분할** | `render(auto_split=True)` | 14개 초과 자동 2페이지 |
| **스타일 프리셋** | `preset()` | 'uspto'/'draft'/'presentation' |
| **버스 토폴로지** | `bus()` | 가로 버스 + 다중 연결 |
| **시퀀스 다이어그램** | `PatentSequence` | 행위자 + 메시지 시퀀스 |
| **상태 다이어그램** | `PatentState` | UML 상태 머신 (초기/최종/self-loop) |
| **하드웨어 블록** | `PatentHardware` | chip/mux/register/memory_array |
| **레이어드 아키텍처** | `PatentLayered` | 수평 레이어 + 인터페이스 화살표 |
| **타이밍 다이어그램** | `PatentTiming` | clock/data/X파형 + 마커 |
| **데이터 플로우** | `PatentDFD` | external/process/store + 흐름 |
| **ER 다이어그램** | `PatentER` | entity/relationship/cardinality |
| **한글 폰트** | 자동 | Apple SD Gothic Neo 자동 감지 |
| **EdgeRouter** | 자동 | Bezier 라운드, A* 장애물 회피 |
| **USPTO 검증** | `validate_uspto.py` | PNG 규격 자동 리포트 |

---

## v2.5 신규 기능 (Research 11~13)

### PatentState — 상태 다이어그램

```python
import sys
sys.path.insert(0, '<skill_dir>/scripts')
from patent_figure import PatentState

fig = PatentState('FIG. 4')
fig.state('IDLE',   '100\nIdle',    initial=True)
fig.state('ACTIVE', '200\nActive')
fig.state('DONE',   '300\nDone',    final=True)
fig.transition('IDLE',   'ACTIVE', label='start()')
fig.transition('ACTIVE', 'DONE',   label='finish()')
fig.transition('ACTIVE', 'IDLE',   label='cancel()')
fig.transition('ACTIVE', 'ACTIVE', label='heartbeat')  # self-loop
fig.render('fig4_state.png')
```

- 방향: `direction='TB'` (기본) 또는 `'LR'`
- `initial=True`: UML 채운 원 → 화살표
- `final=True`: bull's-eye 이중 원
- self-loop: 같은 상태 전이 자동 처리
- 양방향 전이: arc 곡선으로 자동 구분

### PatentHardware — 하드웨어 블록 다이어그램

```python
from patent_figure import PatentHardware

fig = PatentHardware('FIG. 2')
cpu   = fig.chip('CPU', '610\nALU', cx=2.5, cy=7.5,
                  n_pins_left=4, n_pins_right=4)
cache = fig.register('CACHE', '620\nCache', cx=2.5, cy=5.5, cells=8)
mux   = fig.mux('MUX', '630\nMUX', cx=5.0, cy=7.5, direction='right')
mem   = fig.memory_array('MEM', '640\nMemory', cx=5.0, cy=5.5,
                           rows=4, cols=6)
blk   = fig.block('BUS', '650\nBus', cx=2.5, cy=4.0)
fig.connect(cpu, cache, label='data')
fig.connect(mux, mem, bidir=True)
fig.render('fig2_hw.png')
```

도형 종류:
- `chip(id, text, cx, cy, n_pins_left, n_pins_right)` — IC 칩 (핀 포함)
- `mux(id, text, cx, cy, direction)` — 사다리꼴 멀티플렉서
- `register(id, text, cx, cy, cells, cell_w, cell_h)` — 레지스터 셀 배열
- `memory_array(id, text, cx, cy, rows, cols, cell_w, cell_h)` — 메모리 행렬
- `block(id, text, cx, cy, w, h)` — 일반 블록
- `connect(src, dst, label, bidir)` — 연결 화살표

### PatentLayered — 레이어드 아키텍처

```python
from patent_figure import PatentLayered

fig = PatentLayered('FIG. 2')
fig.layer('Application Layer', ['Browser', 'Mobile App', 'API Client'], ref='100')
fig.layer('Service Layer',     ['Auth', 'Business Logic', 'Cache'],     ref='200')
fig.layer('Data Layer',        ['PostgreSQL', 'Redis', 'S3'],           ref='300')
fig.interface('100', '200', label='REST API')
fig.interface('200', '300', label='ORM/Query')
fig.render('fig2_layered.png')
```

### PatentTiming — 타이밍 다이어그램

```python
from patent_figure import PatentTiming

fig = PatentTiming('FIG. 5')
fig.signal('CLK',   '100', wave='clock', period=1.0)
fig.signal('DATA',  '200', wave=[0,0,1,1,0,1,0,0], labels=['D0','D1'])
fig.signal('VALID', '300', wave=[0,1,1,1,1,1,0,0])
fig.signal('X_SIG', '400', wave=[0,'X','X',1,0,0,1,0])  # X=don't care
fig.marker(t=2.0, label='T_setup')
fig.marker(t=6.0, label='T_hold')
fig.render('fig5_timing.png')
```

- `wave='clock'`: 자동 square wave
- `wave=[0,1,'X',...]`: 커스텀 파형 (X=don't care)
- `marker(t, label)`: 수직 점선 마커

### PatentDFD — 데이터 플로우 다이어그램

```python
from patent_figure import PatentDFD

fig = PatentDFD('FIG. 3')
fig.external('USER',  '100\nUser')              # 사각형
fig.process( 'AUTH',  '200\nAuthentication')     # 타원
fig.store(   'DB',    '300\nUser Database')      # 열린 사각형
fig.flow('USER', 'AUTH', label='credentials')
fig.flow('AUTH', 'DB',   label='lookup')
fig.flow('DB',   'AUTH', label='user record')
fig.render('fig3_dfd.png')
```

위치를 지정하려면 `cx`, `cy` 파라미터 추가:
```python
fig.external('USER', '100\nUser', cx=2.0, cy=8.0)
```

### PatentER — ER 다이어그램

```python
from patent_figure import PatentER

fig = PatentER('FIG. 6')
fig.entity('USER',    '100\nUser',
           attrs=['user_id (PK)', 'username', 'email'])
fig.entity('ORDER',   '200\nOrder',
           attrs=['order_id (PK)', 'date', 'total'])
fig.entity('PRODUCT', '300\nProduct',
           attrs=['product_id (PK)', 'name', 'price'])
fig.relationship('USER',  'ORDER',   '1', 'N', label='places')
fig.relationship('ORDER', 'PRODUCT', 'N', 'M', label='contains')
fig.render('fig6_er.png')
```

- `attrs`: 속성 목록. `'(PK)'` 포함 시 PK 밑줄 자동 표시
- `relationship(e1, e2, card1, card2, label)`: 카디널리티 표기

### quick_draw() 다이어그램 타입 확장

```python
from patent_figure import quick_draw

# 상태 다이어그램
spec = """
IDLE: 100 Idle [initial]
ACTIVE: 200 Active
DONE: 300 Done [final]
IDLE -> ACTIVE: start()
ACTIVE -> DONE: finish()
"""
result = quick_draw(spec, 'fig.png', diagram_type='state')

# 시퀀스 다이어그램
spec = """
actor C: Client
actor S: Server
C -> S: request
S <- C: response
"""
result = quick_draw(spec, 'fig.png', diagram_type='sequence')

# 레이어드 다이어그램
spec = """
100: App Layer | Browser, Mobile
200: Service Layer | Auth, Orders
INTERFACE: 100 -> 200 REST API
"""
result = quick_draw(spec, 'fig.png', diagram_type='layered')

# 타이밍 다이어그램
spec = """
100: CLK clock
200: DATA 0,1,1,0,1,0
MARKER: t=2.0 T1
"""
result = quick_draw(spec, 'fig.png', diagram_type='timing')
```

지원 diagram_type 목록:
| 값 | 엔진 | 설명 |
|---|---|---|
| `'flowchart'` (기본) | `PatentFigure` | 플로우차트/블록 다이어그램 |
| `'state'` | `PatentState` | 상태 머신 |
| `'sequence'` | `PatentSequence` | 시퀀스 다이어그램 |
| `'layered'` | `PatentLayered` | 레이어드 아키텍처 |
| `'timing'` | `PatentTiming` | 타이밍 다이어그램 |
