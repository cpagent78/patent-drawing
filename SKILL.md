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
| 시스템 아키텍처 블록다이어그램 | `patent_drawing_lib.layout()` |
| 시퀀스 다이어그램 | `patent_drawing_lib.sequence_diagram()` |
| 수평 파이프라인 (3-5 단계) | `patent_drawing_lib.horizontal_pipeline_flow()` |
| 수동 좌표가 필요한 특수 레이아웃 | `patent_drawing_lib` 직접 사용 |
| 9+ 노드 플로우차트 | **PatentFigure + render_multi()** |
